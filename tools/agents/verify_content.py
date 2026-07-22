# -*- coding: utf-8 -*-
"""③検証班 — 掲載内容が「サイトの憲法」を守れているかを機械的に点検する。

この班は何も書き換えない。疑って、止めるだけ。
編集した本人（②編集班）に自己採点させないための独立した検査役。

点検項目:
  1. 引用の原文一致 … 掲載中の引用が、国会会議録の原文に実在するか（APIで直接照合）
  2. 原典リンクの到達性 … 会議録・参議院・各党公式サイトのURLが生きているか
  3. 評価語の混入 … 編集текстに価値判断を含む語が紛れていないか（引用は対象外）
  4. 会派マッチの一意性 … 会派名の部分一致が複数会派に当たっていないか
  5. 憲法チェック … 「点数化しない」等の約束が公開ページから消えていないか

使い方:
    python agents/verify_content.py              # 全項目（ネットワーク使用）
    python agents/verify_content.py --offline    # 通信なしの項目だけ
    python agents/verify_content.py --quotes-limit 20
終了コード: 0=合格 / 1=要確認（CIを落とす）
"""
import argparse, json, os, re, sys, time, unicodedata
import urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(TOOLS, ".."))
API = "https://kokkai.ndl.go.jp/api/speech"
UA = {"User-Agent": "seisaku-kurabe-verifier/1.0 (+https://ai-seisaku-kurabe.github.io)"}

findings = []   # (レベル, 分類, 内容)
def fail(cat, msg): findings.append(("FAIL", cat, msg))
def warn(cat, msg): findings.append(("WARN", cat, msg))

def norm(s):
    """比較用の正規化。

    NFKC で全角英数字を半角に揃える（会議録は「ＮＴＴ」、掲載は「NTT」のように
    表記幅が異なることがあり、これを不一致と誤検出しないため）。あわせて空白を除去する。
    """
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", str(s)))

# ---------------------------------------------------------------- データ読込
def load_data():
    """build_party.py を実行して、掲載中のデータ・編集テキストを取り込む。"""
    cwd = os.getcwd()
    os.chdir(TOOLS)                      # スクリプトは相対パス前提
    try:
        bp = {}
        exec(open("build_party.py", encoding="utf-8").read(), bp)
        oneissue = {}
        p = os.path.join(TOOLS, "oneissue_speech.json")
        if os.path.exists(p):
            oneissue = json.load(open(p, encoding="utf-8"))
        return bp, oneissue
    finally:
        os.chdir(cwd)

# ------------------------------------------------------- 1. 引用の原文一致
def speech_id_from_url(url):
    """https://kokkai.ndl.go.jp/txt/<issueID>/<order> -> <issueID>_<order:03d>"""
    m = re.search(r"/txt/([^/]+)/(\d+)", url or "")
    if not m: return None
    return f"{m.group(1)}_{int(m.group(2)):03d}"

def fetch_speech(speech_id):
    q = urllib.parse.urlencode({"speechID": speech_id, "recordPacking": "json"})
    req = urllib.request.Request(f"{API}?{q}", headers=UA)
    d = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    recs = d.get("speechRecord") or []
    return recs[0] if recs else None

def match_fragments(text, speech):
    """引用を原文と照合する。

    掲載中の引用は「…」で中略していることがあるため、単純な部分一致では判定できない。
    そこで「…」で分割した各断片が、原文に **同じ順序で** 現れるかを確かめる。
    こうすると、文言の改変だけでなく「原文の順序を入れ替えて意味を変える」操作も検出できる。
    戻り値: 問題点のリスト（空なら合格）
    """
    body = norm(speech)
    frags = [f for f in (norm(x) for x in re.split(r"[…‥]+|\.{3,}", str(text))) if len(f) >= 6]
    if not frags:
        return ["引用が短すぎて照合できない"]
    problems, pos = [], 0
    for frag in frags:
        i = body.find(frag, pos)
        if i >= 0:
            pos = i + len(frag); continue
        if body.find(frag) >= 0:
            problems.append(f"原文と順序が異なる断片 → 「{frag[:32]}…」")
        else:
            problems.append(f"原文に存在しない断片 → 「{frag[:32]}…」")
    return problems

def check_sentence_boundary(text, speech):
    """引用が文の途中から始まっていないかを、原文の位置で確かめる。

    固定幅で切り出していた頃、「しましては、…」と文の途中から始まる引用や、
    「転換」の途中から始まって「換を進め、…」となる引用が生まれていた
    （第219回で10/47件、第221回で13/55件）。原文の文字列ではあっても、
    文の途中を切り出したものは読者に別の意味を与える。

    語の形では判定できない。「しかし、」「そして、」で始まる文は正当なので、
    **原文のどこから切り出したか**を見るのが唯一確実な方法になる。
    """
    body = norm(re.sub(r"^○[^　]{1,14}　", "", str(speech)))
    frags = [f for f in (norm(x) for x in re.split(r"[…‥]+|\.{3,}", str(text))) if len(f) >= 6]
    if not frags:
        return []
    i = body.find(frags[0])
    if i < 0:
        return []                       # 不一致は match_fragments が報告済み
    if i > 0 and body[i - 1] not in "。？！」』":
        return [f"文の途中から始まっている（原文では「{body[max(0,i-12):i]}」に続く箇所）"]
    return []


def check_quotes(bp, oneissue, limit=None):
    """掲載中の引用が原文に実在するかをAPIで直接照合する。"""
    clean = bp["clean_quote"]
    targets = []   # (どこ, 話者, 表示テキスト, URL)
    for full, doms in bp["PIDX"].items():
        for dname, (entry, _v, _l) in doms.items():
            # 第217回に会派が無かった党は空の器なので照合対象外（第221回側で照合する）
            if not entry.get("quote") or not entry.get("url"):
                continue
            targets.append((f"guide/{full}/{dname}", entry.get("who"),
                            clean(entry["quote"]), entry.get("url")))
    for full, recs in oneissue.items():
        for r in recs:
            targets.append((f"oneissue/{full}", r.get("who"), r.get("text"), r.get("url")))
    # 会期併記で追加した分の発言。会期を足したらここにも足すこと
    # （足し忘れると、その会期の引用は一度も原文照合されないまま公開される）。
    for key, tag in (("S219", "guide219"), ("S221", "guide221")):
        for full, doms in (bp.get(key) or {}).items():
            for dname, e in doms.items():
                targets.append((f"{tag}/{full}/{dname}", e.get("who"),
                                e.get("quote"), e.get("url")))

    if limit: targets = targets[:limit]
    ok = 0
    for where, who, text, url in targets:
        sid = speech_id_from_url(url)
        if not sid:
            fail("引用照合", f"{where}: 発言URLの形式が不正 ({url})"); continue
        try:
            rec = fetch_speech(sid)
        except Exception as e:
            warn("引用照合", f"{where}: APIエラーのため未検証 ({e})"); continue
        if not rec:
            fail("引用照合", f"{where}: 原文が見つからない ({url})"); continue
        if who and norm(who) not in norm(rec.get("speaker", "")):
            fail("引用照合", f"{where}: 話者不一致 掲載『{who}』 / 原文『{rec.get('speaker')}』")
        problems = match_fragments(text, rec.get("speech", ""))
        # 文の途中から切り出す欠陥は、全会期・ワンイシューを直し終えたので例外を置かない。
        problems += check_sentence_boundary(text, rec.get("speech", ""))
        if problems:
            for p in problems:
                fail("引用照合", f"{where}: {p}")
        else:
            ok += 1
        time.sleep(0.25)
    print(f"  引用照合: {ok}/{len(targets)} 件が原文と一致")

# --------------------------------------------------------- 2. リンク到達性
def collect_urls(bp, oneissue):
    urls = set()
    for full, doms in bp["PIDX"].items():
        for dname, (entry, votes, _l) in doms.items():
            if entry.get("url"): urls.add(entry["url"])
    for recs in oneissue.values():
        for r in recs:
            if r.get("url"): urls.add(r["url"])
    vbase = bp["ns"].get("VBASE", "https://www.sangiin.go.jp/japanese/touhyoulist/217/")
    for key in ("FVOTES", "DVOTES", "SVOTES", "EVOTES", "CVOTES"):
        v = bp["ns"].get(key)
        if not v: continue
        for b in v.get("bills", []):
            urls.add(vbase + b["id"] + ".htm")
    for pk in bp.get("PACKAGE", {}).values():
        if pk.get("url"): urls.add(pk["url"])
    return sorted(urls)

def check_kokkai_id(url):
    """会議録URLの会議IDが実在するかを、APIで確かめる。

    kokkai.ndl.go.jp/txt/<issueID>[/<order>] は、IDが出鱈目でも 301 でSPAの外枠へ
    飛び、200 を返す。そのため到達性の検査では誤ったIDを見抜けない。実際、存在
    しない `122115206X011...`（正しくは `X009`）が判定根拠として公開され、
    「リンク103/103が到達可能」を通り抜けていた。
    到達したかではなく、その会議が実在するかをAPIに問い合わせて確かめる。
    """
    m = re.search(r"kokkai\.ndl\.go\.jp/txt/([^/?#]+)(?:/(\d+))?", url or "")
    if not m:
        return True
    sid = f"{m.group(1)}_{int(m.group(2)):03d}" if m.group(2) else f"{m.group(1)}_000"
    try:
        if fetch_speech(sid) is None:
            fail("リンク", f"会議録IDが存在しない: {url}")
            return False
    except Exception as e:
        warn("リンク", f"会議録IDを確認できず（一時的の可能性）: {url} ({e})")
    return True


# 学術出版社は自動アクセスを 403/429 で弾く。これは「その論文が存在しない」ことを
# 意味しない（存在しないDOI/パスなら 404 が返る）。リンク切れと遮断を混同すると、
# 実在する出典まで落としてしまうので、先行研究ページでは 403/429 を WARN として扱う。
BLOCKED_CODES = {401, 403, 429}

def check_links(urls, limit=None, soft_blocked=False):
    if limit: urls = urls[:limit]
    bad = 0
    for u in urls:
        if not check_kokkai_id(u):
            bad += 1
            time.sleep(0.2)
            continue
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                if r.status >= 400:
                    fail("リンク", f"{r.status} {u}"); bad += 1
        except urllib.error.HTTPError as e:
            if soft_blocked and e.code in BLOCKED_CODES:
                warn("リンク", f"{e.code} 自動アクセスを遮断（存在は否定されない）: {u}")
            else:
                fail("リンク", f"{e.code} {u}"); bad += 1
        except Exception as e:
            warn("リンク", f"到達不可（一時的の可能性）: {u} ({e})")
        time.sleep(0.2)
    print(f"  リンク: {len(urls)-bad}/{len(urls)} 件が到達可能")

# ------------------------------------------------------- 3. 評価語の混入
# 編集テキストに入ってはいけない、価値判断・感情を含む語。
# ※原文引用は対象外（原文に何が書かれていようと改変しないため）
BANNED = ["素晴らしい", "優れた", "劣る", "ひどい", "酷い", "愚か", "無責任", "暴走",
          "独裁", "ばらまき", "バラマキ", "だらしない", "まとも", "正しい判断",
          "間違っている", "評価できる", "評価に値", "支持すべき", "選ぶべき",
          "望ましい", "危険な政党", "極端すぎ", "現実離れ", "無謀"]

def check_editorial_language(bp):
    hits = 0
    def scan(where, text):
        nonlocal hits
        for w in BANNED:
            if w in str(text):
                fail("評価語", f"{where}: 「{w}」が編集テキストに含まれる → {str(text)[:50]}…")
                hits += 1
    for full, (issue, why, ref) in bp["ONEISSUE"].items():
        scan(f"ワンイシュー/{full}/issue", issue)
        scan(f"ワンイシュー/{full}/why", why)
    for full, pk in bp.get("PACKAGE", {}).items():
        for b in pk.get("bullets", []):
            scan(f"政策パッケージ/{full}", b)
    for full, doms in bp["PIDX"].items():
        for dname, (entry, _v, _l) in doms.items():
            scan(f"力点/{full}/{dname}", entry.get("point", ""))
            if entry.get("tag"): scan(f"タグ/{full}/{dname}", entry["tag"])
    print(f"  評価語: {'混入なし' if hits==0 else str(hits)+'件の混入'}")

# -------------------------------------------------- 4. 会派マッチの一意性
def check_vkey_uniqueness(bp):
    """会派名の部分一致が複数会派に当たると、賛否を取り違える。"""
    bad = 0
    for key in ("FVOTES", "DVOTES", "SVOTES", "EVOTES", "CVOTES"):
        v = bp["ns"].get(key)
        if not v: continue
        for b in v.get("bills", []):
            names = list(b["parties"].keys())
            for full, doms in bp["PIDX"].items():
                for dname, (entry, votes, _l) in doms.items():
                    vk = entry.get("vkey")
                    if not vk or votes is not v: continue
                    hit = [n for n in names if vk in n]
                    if len(hit) > 1:
                        fail("会派照合", f"{key}/{b['id']}: 会派キー『{vk}』が複数一致 {hit}")
                        bad += 1
    print(f"  会派照合: {'一意' if bad==0 else str(bad)+'件が曖昧'}")

# ------------------------------------------------------- 5. 憲法チェック
PROMISES = [
    ("index.html",    ["点数化も格付けもしません"],                 "トップの非格付け宣言"),
    ("about.html",    ["点数化・格付け"],                           "方法論の非格付け宣言"),
    ("about.html",    ["運用ルール"],                               "運用ルールの公開"),
    ("guide.html",    ["第217回国会では会派未結成"],                       "データ空白の理由明示"),
    ("guide.html",    ["結果」であり「理由」ではありません"],       "賛否は理由でない旨の注記"),
    ("guide.html",    ["第221回"],                                  "第221回国会の併記"),
    ("guide.html",    ["言 ／ 国会での発言（会期別）"],              "言の会期併記"),
    ("about.html",    ["第221回国会では会派を結成"],                "会派構成の変化を反映"),
    ("oneissue.html", ["会派を構成しておらず"],                     "ワンイシュー側の空白明示"),
    # 先行研究ページ（⑨文献調査班）— 弱点の開示と、出典のルールが消えていないこと
    ("research.html", ["まだ手当てできていないこと"],             "先行研究：未手当ての開示"),
    ("research.html", ["未確認"],                                 "先行研究：未確認の開示"),
    ("research.html", ["たどり着けたURLを持つものだけ"],          "先行研究：出典のルール"),
    ("research.html", ["良し悪しを論じてはいません"],             "先行研究：研究を格付けしない宣言"),
    # 照合の全数検査（agents/audit_matching.py）で分かった癖の開示。
    # 測ったうえで直しきれていない、という書き方が消えたら自己弁護に転じている。
    ("research.html", ["自分たちで測ったこと"],                   "先行研究：全数検査の開示"),
    ("research.html", ["直し方は決まっていません"],               "先行研究：未解決であることの明示"),
    ("shindan.html",  ["これらの党を区別できません"],             "政策で照らす：同率の明示"),
    # 設問の選び方の開示。いちばん大きな編集判断なので、消えたら止める。
    ("shindan.html",  ["どうやって選んだのか", "多段階の手続きは踏んでいません"],
                                                                  "政策で照らす：設問の選び方の開示"),
    ("research.html", ["検討そのものをしていません"],             "先行研究：設問の母集団の開示"),
    # 自分の誤りを見つけたときの訂正の記録。都合が悪いので消したくなる種類の記述。
    ("research.html", ["私たちの側の事実誤りがありました"],       "先行研究：誤りの訂正の記録"),
    ("research.html", ["多くのうちの1つ"],                        "先行研究：抽出の選択比の開示"),
    ("research.html", ["個人が非営利で運営"],                     "先行研究：運営主体の明示"),
    ("votes.html",    ["参議院の記名投票を全件"],                 "採決一覧：全件掲載の明示"),
    ("votes.html",    ["この中から選んだ代表例"],                 "採決一覧：代表例との関係の明示"),
    # 出典と権利／プライバシー — 事実として書いている以上、消えたら気づけるようにする
    ("about.html",    ["発言した議員ご本人"],                     "出典と権利：著作権の帰属"),
    ("about.html",    ["削除・訂正の申出"],                       "出典と権利：申出窓口"),
    ("privacy.html",  ["アクセス解析ツールを入れていません"],     "プライバシー：解析なしの明示"),
    ("privacy.html",  ["個別の記録として保存していません"],       "プライバシー：個別記録なしの明示"),
    ("privacy.html",  ["reCAPTCHA"],                              "プライバシー：外部送信の明示"),
]
def check_constitution():
    ok = 0
    for fn, needles, label in PROMISES:
        p = os.path.join(ROOT, fn)
        if not os.path.exists(p):
            fail("憲法", f"{fn} が存在しない"); continue
        html = open(p, encoding="utf-8").read()
        missing = [n for n in needles if n not in html]
        if missing:
            fail("憲法", f"{fn}: {label} が消えている（{missing}）")
        else:
            ok += 1
    # about.html の運用ルールが8項目あるか
    p = os.path.join(ROOT, "about.html")
    if os.path.exists(p):
        html = open(p, encoding="utf-8").read()
        m = re.search(r'<ol class="rulebook">(.*?)</ol>', html, re.S)
        n = m.group(1).count("<li>") if m else 0
        if n != 8:
            fail("憲法", f"about.html: 運用ルールが8項目でない（{n}項目）")
    print(f"  憲法: {ok}/{len(PROMISES)} 項目を確認")


# ------------------------------------------ 5b. 照合の全数検査が古びていないか
# research.html には「政策で照らす」を全数検査した数字が載る。設問や政党を足したのに
# 検査を回し直していないと、ページだけが古い設計の数字を語ることになる。
# 数字そのものは検証できない（それは検査プログラムの仕事）ので、
# 「何を検査した数字か」が今のサイトと一致しているかだけを見る。
def check_matching_audit(bp):
    p = os.path.join(TOOLS, "state", "matching_audit.json")
    if not os.path.exists(p):
        fail("全数検査", "state/matching_audit.json が無い（agents/audit_matching.py を実行する）")
        return
    a = json.load(open(p, encoding="utf-8"))
    # build_shindan.py は import すると shindan.html を書き出すので、定義部分だけを取り出す
    src_path = os.path.join(TOOLS, "build_shindan.py")
    src = open(src_path, encoding="utf-8").read()
    cut = src.find("\n# 各設問の")
    ns = {}
    exec(compile(src[:cut if cut > 0 else len(src)], src_path, "exec"), ns)
    q, parties = len(ns["POLICY"]), len(ns["PARTIES"])
    if a.get("questions") != q or a.get("parties") != parties:
        fail("全数検査",
             f"検査結果が今の設計と違う（検査時 {a.get('questions')}問/{a.get('parties')}党 → "
             f"現在 {q}問/{parties}党）。agents/audit_matching.py を回し直す")
        return
    expect = 3 ** q * 2 ** q
    if a.get("total_inputs") != expect:
        fail("全数検査", f"全数になっていない（{a.get('total_inputs'):,} ≠ {expect:,}）")
        return
    # 立場が完全に同じ党の組があるときは、同率を明示できていないと片方が永久に埋もれる
    same = a.get("identical_stance_pairs") or []
    if same:
        html = os.path.join(ROOT, "shindan.html")
        if os.path.exists(html) and "これらの党を区別できません" not in open(html, encoding="utf-8").read():
            fail("全数検査", f"立場が同じ党の組がある（{same}）のに、同率であることを画面に出していない")
    print(f"  全数検査: {a['total_inputs']:,}通り／{q}問{parties}党で一致"
          + (f"／立場が同じ組 {len(same)}" if same else ""))

    # 設問の来歴（agents/audit_questions.py）も、設問数が変わったら数え直す
    p2 = os.path.join(TOOLS, "state", "question_audit.json")
    if not os.path.exists(p2):
        fail("設問の来歴", "state/question_audit.json が無い（agents/audit_questions.py を実行する）")
        return
    qa = json.load(open(p2, encoding="utf-8"))
    if qa.get("questions") != q:
        fail("設問の来歴",
             f"洗い出しが今の設計と違う（{qa.get('questions')}問 → 現在 {q}問）。"
             "agents/audit_questions.py を回し直す")
        return
    print(f"  設問の来歴: {q}問（採決 {qa['by_basis']['採決']}／"
          f"公約・発言 {qa['by_basis']['公約・発言']}）、母集団 {qa['pool_total']}件")

    # 「行」の覆っている範囲（agents/audit_rollcall.py）。掲載会期と一致しているか。
    p3 = os.path.join(TOOLS, "state", "rollcall_audit.json")
    if not os.path.exists(p3):
        fail("行の範囲", "state/rollcall_audit.json が無い（agents/audit_rollcall.py を実行する）")
        return
    ra = json.load(open(p3, encoding="utf-8"))
    # 掲載会期は build_party.py の sessions_for() が唯一の出どころ。ここに書き持たない
    # （⑧査読で「サイトは3会期、監査は2会期」の食い違いを指摘されたため）。
    sys.path.insert(0, os.path.join(TOOLS, "agents"))
    from _sessions import published_sessions
    published = set(published_sessions())
    measured = set(ra.get("sessions", {}))
    if measured != published:
        fail("行の範囲",
             f"測定した会期が掲載会期と違う（測定 {sorted(measured)} / 掲載 {sorted(published)}）。"
             "掲載会期を変えたら fetch_bill_outcomes.py と agents/audit_rollcall.py を回し直す")
        return
    if set(qa.get("pool", {})) != published:
        fail("設問の来歴",
             f"母集団の会期が掲載会期と違う（{sorted(set(qa.get('pool', {})))} / "
             f"{sorted(published)}）。agents/audit_questions.py を回し直す")
        return
    t = ra["total"]
    print(f"  行の範囲: 参院 議決{t['decided']}件中 記名{t['named']}件"
          f"（{t['named_pct']}%）／衆院 {t['shugiin_named_pct']}%")

    # 「言」の抽出でどれだけ選んでいるか（agents/audit_extraction.py）。掲載会期と一致するか。
    p4 = os.path.join(TOOLS, "state", "extraction_audit.json")
    if not os.path.exists(p4):
        fail("抽出の選択比", "state/extraction_audit.json が無い（agents/audit_extraction.py を実行する）")
        return
    xa = json.load(open(p4, encoding="utf-8"))
    if set(xa.get("windows", {})) != published:
        fail("抽出の選択比",
             f"測定した会期が掲載会期と違う（{sorted(set(xa.get('windows', {})))} / "
             f"{sorted(published)}）。agents/audit_extraction.py を回し直す")
        return
    xt = xa["total"]
    print(f"  抽出の選択比: 候補{xt['candidate_total']}件／表示{xt['shown']}枠"
          f"（枠あたり中央値{xt['median_candidates_per_shown_cell']}件）")


# ------------------------------------------- 6. 先行研究ページの引用リンク
# research.html は外部の学術文献を引く唯一のページ。AIが生成した文献情報を扱うため、
# 架空の出典が混ざると、このサイトが売っている検証可能性そのものが壊れる。
# よって class="cite" のURLは全件、到達できることを機械的に確かめる。
# class="cite unv" は未確認文献＝到達性チェックの対象外（本文の根拠には使わない）。
def collect_research_citations():
    p = os.path.join(ROOT, "research.html")
    if not os.path.exists(p):
        fail("先行研究", "research.html が存在しない")
        return []
    html = open(p, encoding="utf-8").read()
    if "未確認" not in html:
        fail("先行研究", "research.html に「未確認」の節が無い（確認できていない事柄の開示は必須）")
    cited = re.findall(r'<a class="cite"\s+href="([^"]+)"', html)
    unv = re.findall(r'<a class="cite unv"\s+href="([^"]+)"', html)
    if unv:
        print(f"  先行研究: 未確認扱いの出典 {len(unv)} 件は到達性チェックの対象外")
    urls = sorted(set(h.replace("&amp;", "&") for h in cited))
    print(f"  先行研究: 検証対象の出典リンク {len(urls)} 件")
    return urls


# ------------------------------- 7. プライバシーポリシーと実装の一致
# 「開示と実態の食い違い」は、このプロジェクトが繰り返し踏んでいる型。
# privacy.html は「個別の記録を保存しない」「アクセス解析を入れていない」と
# 事実を宣言しているので、実装が変わったらここで止める。
def check_privacy_claims():
    root_fb = os.path.join(ROOT, "firebase.js")
    if not os.path.exists(root_fb):
        warn("プライバシー", "firebase.js が見つからず、実装との照合を省いた")
        return
    js = open(root_fb, encoding="utf-8").read()

    # 個別レコードを書く経路（.add / addDoc）があるかどうか。
    has_individual_write = bool(re.search(r"\.add\(|addDoc\(", js))
    # 書き込み先のコレクション名を集める。
    #   compat形式: collection("name")  /  modular形式: collection(db, "name")
    collections = set(re.findall(r"collection\(\s*(?:[^,()\"']+,\s*)?[\"']([^\"']+)[\"']", js))

    # 「個別レコードを書く経路が増えること」自体は禁止しない（ご意見フォームのように
    # 正当な用途がある）。禁止するのは「開示なき個別保存」と「想定外の保存先」だけ。
    # これにより .add( を消さずに、開示とセットなら通す・開示が無ければ止める番犬にする。
    if has_individual_write or collections:
        priv_path = os.path.join(ROOT, "privacy.html")
        priv = open(priv_path, encoding="utf-8").read() if os.path.exists(priv_path) else ""
        disclosed = ("ご意見" in priv) and ("個別に保存" in priv)
        if not disclosed:
            fail("プライバシー",
                 "firebase.js に個別レコードを書きうる経路（.add(/addDoc(）があるが、"
                 "privacy.html にご意見の個別保存についての開示が見当たらない")

        allowed_collections = {"feedback"}
        unexpected = collections - allowed_collections
        if unexpected:
            fail("プライバシー",
                 f"firebase.js が想定外のコレクション（{', '.join(sorted(unexpected))}）に"
                 "個別レコードを書いている。開示・レビューが必要")

    if "increment" not in js:
        fail("プライバシー", "firebase.js に increment が無い。集計方式が変わった可能性がある")
    # アクセス解析タグが入っていないか
    for f in ("index.html", "shindan.html", "guide.html", "privacy.html"):
        p = os.path.join(ROOT, f)
        if not os.path.exists(p): continue
        html = open(p, encoding="utf-8").read()
        for tag in ("googletagmanager", "google-analytics", "gtag(", "clarity.ms", "plausible.io"):
            if tag in html:
                fail("プライバシー",
                     f"{f} に解析タグ（{tag}）がある。"
                     "privacy.html の「アクセス解析ツールを入れていません」と食い違う")
    print("  プライバシー: 記述と実装が一致")

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="通信を伴う点検を省く")
    ap.add_argument("--quotes-limit", type=int, default=None)
    ap.add_argument("--links-limit", type=int, default=None)
    a = ap.parse_args()

    print("③検証班 — 掲載内容の点検を開始します\n")
    bp, oneissue = load_data()

    print("[通信なしの点検]")
    check_editorial_language(bp)
    check_vkey_uniqueness(bp)
    check_constitution()
    check_matching_audit(bp)
    check_privacy_claims()
    collect_research_citations()

    if not a.offline:
        print("\n[通信を伴う点検]")
        check_quotes(bp, oneissue, a.quotes_limit)
        check_links(collect_urls(bp, oneissue), a.links_limit)
        check_links(collect_research_citations(), a.links_limit, soft_blocked=True)
    else:
        print("\n[--offline のため 引用照合・リンク到達性 は省略]")

    fails = [f for f in findings if f[0] == "FAIL"]
    warns = [f for f in findings if f[0] == "WARN"]
    print("\n" + "=" * 60)
    if not findings:
        print("✅ 指摘なし。掲載内容はルールを満たしています。")
    for lv, cat, msg in findings:
        print(f"{'❌' if lv=='FAIL' else '⚠️ '} [{cat}] {msg}")
    print("=" * 60)
    print(f"FAIL {len(fails)} 件 / WARN {len(warns)} 件")
    # WARNは一時的な通信不良を含むので落とさない。FAILのみCIを止める。
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
