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
    # ワンイシュー/ニッチ政党の先行研究(lit/G)から起こした弱点の開示。消えたら止める。
    ("research.html", ["少数政党の「際立ち」を埋もれさせている"], "先行研究：6分野とニッチ政党の非対称"),
    ("research.html", ["賛否で表せないもの"],                     "先行研究：位置争点とvalence争点"),
    # 顕出性理論でワンイシューに足場を与えつつ、強調/賛否/重視度を混ぜない明示。消えたら止める。
    ("research.html", ["顕出性理論そのものの実装ではありません"], "先行研究：ワンイシューの顕出性理論の位置づけ"),
    ("research.html", ["投票行動を予測する係数ではありません"],   "先行研究：◎重視は投票予測でない明示"),
    # 話題の配分は「順位・割合で出さない」と決めた開示（⑧査読で憲法5条違反の指摘を受け取り下げ）。
    # この宣言が消えたら止める。
    ("research.html", ["順位や割合では出さないと決めた"],         "先行研究：話題の配分を順位化しない宣言"),
    # 「どちらでもない」の扱い。計算から外れることの明示が消えたら止める（結果の読み方が変わる）。
    ("shindan.html",  ["一致度の計算から外れます"],               "政策で照らす：どちらでもないの扱いの明示"),
    ("research.html", ["いくつもの意味を抱え込んでいる"],         "先行研究：中間の選択肢の多義性の開示"),
    # 争点所有を主張しない宣言／因果・採点に踏み込まない切り分け。消えたら止める。
    ("research.html", ["この争点に強い／得意だ」とは一切言いません"], "先行研究：争点所有は主張しない宣言"),
    ("research.html", ["意味づけは読者に返す"],                   "先行研究：因果の断定をしない切り分け"),
    ("research.html", ["突き合わせる作業は、読者の手に残します"], "先行研究：能力の採点をしない切り分け"),
    # 出典と権利／プライバシー — 事実として書いている以上、消えたら気づけるようにする
    ("about.html",    ["発言した議員ご本人"],                     "出典と権利：著作権の帰属"),
    ("about.html",    ["削除・訂正の申出"],                       "出典と権利：申出窓口"),
    ("privacy.html",  ["アクセス解析ツールを入れていません"],     "プライバシー：解析なしの明示"),
    ("privacy.html",  ["個別の記録として保存していません"],       "プライバシー：個別記録なしの明示"),
    ("privacy.html",  ["reCAPTCHA"],                              "プライバシー：外部送信の明示"),
    # ⑦応答班(FEEDBACK_CHARTER.md) — ご意見の取り扱いの開示。
    # 「補助AIが読む」「要旨を公開することがある」が消えたまま運用が続くと、
    # 開示なき実態(過去2回査読で刺された型)に戻るので機械で止める。
    ("feedback.html", ["補助するAI", "書き直した要旨", "30日以内"],
                                                                  "ご意見：AI関与・要旨公開・削除期限の開示"),
    ("privacy.html",  ["補助するAI", "30日以内", "AIにも渡しません"],
                                                                  "ご意見：プライバシー側の開示と不遡及"),
    ("kiroku.html",   ["原文は公開しません", "採否の根拠にしません", "変更を完結させません"],
                                                                  "記録：原文非公開・件数非根拠・AI非完結の宣言"),
    # 窓口の新着をどれくらいの頻度で確認しているかの開示。
    # 「確認のうえ対応します」とだけ書いて監視が無い状態に戻らないよう、機械で縛る
    # （実装との一致は check_intake_watch() が見る）。
    ("feedback.html", ["新着の有無を機械的に確認"],             "ご意見：窓口の確認頻度の開示"),
    # 採決トリアージ(agents/TRIAGE_CRITERIA.md) — 全件判定の開示。
    # 「重要度の格付けではない」「編集判断を含む」が消えると、分類が格付けに見え始める。
    ("votes.html",    ["判定の基準", "重要度の格付けではありません", "編集判断を含みます"],
                                                                  "採決一覧：全件判定と非格付けの明示"),
    ("shindan.html",  ["設問候補になるか・ならないなら理由は何か"], "政策で照らす：全件判定の開示"),
    # ワンイシュー/valence争点の注意(⑨ニッチ政党研究 lit/G の帰結)。
    # ワンイシューの単純化への注意と「賛否で測れない訴えがある」開示が消えたら止める。
    ("oneissue.html", ["党の全体像ではありません", "推し量"],     "ワンイシュー：単純化への注意書き"),
    # 第1問の深掘りは、1件の会議録直リンクから複数の発言・採決へ変えた。
    # 数を増やしたぶん「網羅・重要度順」と誤読されやすいので、その否定が消えたら止める。
    ("shindan.html",  ["網羅でも重要度の順でもありません"],
                                                                  "政策で照らす：関連発言は例であることの明示"),
    ("shindan.html",  ["賛成・反対で答えられる争点", "賛否の代わりにはなりません"],
                                                                  "政策で照らす：valence争点の限界開示"),
    ("about.html",    ["賛否で表せない訴え"],                     "限界：valence争点の開示"),
    # 次の国政選挙の日程（①収集班）。日付は一次情報で確認できたものだけを載せ、
    # 決まっていないものは「未定」と書く、という約束。ここが消えると、
    # 報道や推測の日付を置くことへの歯止めが無くなる（実装との一致は check_election_schedule()）。
    ("index.html",    ["一次情報で確認できたものだけ", "推測の日付は置きません"],
                                                                  "トップ：選挙日程の出典ルール"),
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

    # （話題の配分＝旧 audit_saliency.py の会期一致チェックは撤去。順位・割合を出す測定自体を
    #   憲法5条抵触として取り下げたため。⑧査読 chunk A/B の指摘。）


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


# ------------------------------- 6b. 採決トリアージが全件・現在の掲載と一致しているか
# votes.html は「全件に設問候補性の判定を付けています」と約束する(agents/TRIAGE_CRITERIA.md)。
# 判定表が母集団・設問根拠・基準の版と食い違ったまま公開されると約束が嘘になるので機械で止める。
def check_vote_triage():
    from _sessions import published_sessions
    tp = os.path.join(TOOLS, "vote_triage.json")
    cp = os.path.join(TOOLS, "vote_triage_criteria.json")
    if not (os.path.exists(tp) and os.path.exists(cp)):
        fail("トリアージ", "vote_triage.json / vote_triage_criteria.json が無い"
             "（agents/triage_votes.py を実行する）")
        return
    tri = json.load(open(tp, encoding="utf-8"))
    crit = json.load(open(cp, encoding="utf-8"))
    if tri.get("criteria_version") != crit.get("criteria_version"):
        fail("トリアージ", f"判定表の版 {tri.get('criteria_version')} が"
             f"基準の版 {crit.get('criteria_version')} と違う（triage_votes.py を回し直す）")
    ses = published_sessions()
    if tri.get("sessions") != ses:
        fail("トリアージ", f"判定した会期 {tri.get('sessions')} が掲載会期 {ses} と違う"
             "（triage_votes.py を回し直す）")
        return
    by_id = {r["id"]: r for r in tri["items"]}
    pool = {}
    for s in ses:
        for b in json.load(open(os.path.join(TOOLS, f"{s}_votes.json"), encoding="utf-8"))["bills"]:
            pool[b["id"]] = b
    missing = [i for i in pool if i not in by_id]
    extra = [i for i in by_id if i not in pool]
    if missing:
        fail("トリアージ", f"判定の無い採決が {len(missing)} 件ある（例 {missing[:3]}）")
    if extra:
        fail("トリアージ", f"母集団に無い判定が {len(extra)} 件ある（例 {extra[:3]}）")
    bad = [r["id"] for r in tri["items"] if r["code"] not in crit["codes"]]
    if bad:
        fail("トリアージ", f"基準に無いコードの判定がある（{bad[:3]}）")
    # USED が今の設問根拠と一致しているか（設問を変えたら判定表も回し直す）
    qa_p = os.path.join(TOOLS, "state", "question_audit.json")
    if os.path.exists(qa_p):
        used_now = set(json.load(open(qa_p, encoding="utf-8"))["vote_ids_used"])
        used_tri = {r["id"] for r in tri["items"] if r["code"] == "USED"}
        if used_now != used_tri:
            fail("トリアージ", f"USED {sorted(used_tri)} が設問根拠 {sorted(used_now)} と一致しない")
    # 機械段の再現性：全会一致の採決が人間コードに紛れていないか
    for vid, b in pool.items():
        r = by_id.get(vid)
        if not r or not b.get("parties"):
            continue
        una = all(v.get("no", 0) == 0 for v in b["parties"].values())
        if una and r["code"] in ("CANDIDATE", "TOO_NARROW", "AMBIGUOUS", "REPRESENTED"):
            fail("トリアージ", f"{vid} は全会一致なのに {r['code']}（機械段が回っていない）")
    # REPRESENTED の代表採決が実在し、連鎖していないか
    for r in tri["items"]:
        if r["code"] == "REPRESENTED":
            t = by_id.get(r.get("rep"))
            if not t:
                fail("トリアージ", f"{r['id']} の代表採決 {r.get('rep')} が存在しない")
            elif t["code"] == "REPRESENTED":
                fail("トリアージ", f"{r['id']} の代表採決 {t['id']} も REPRESENTED（連鎖は不可）")
    print(f"  トリアージ: {len(pool)} 件の判定を確認（版 {tri.get('criteria_version')}）")


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

    # 端末内に保存するものは、privacy.html に列挙してあることを実装側からも縛る。
    # 表示テーマ(kg_theme)はマイノート(kg_notes)と同じ扱いなので、開示なしに増えたら止める。
    priv_path = os.path.join(ROOT, "privacy.html")
    priv = open(priv_path, encoding="utf-8").read() if os.path.exists(priv_path) else ""
    for key, word in (("kg_theme", "表示テーマ"), ("kg_notes", "マイノート")):
        used = any(key in open(os.path.join(ROOT, f), encoding="utf-8").read()
                   for f in os.listdir(ROOT) if f.endswith(".html"))
        if used and word not in priv:
            fail("プライバシー",
                 f"ローカルストレージに {key} を保存しているが、privacy.html に"
                 f"「{word}」の開示が見当たらない")

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


# キーワード検索の「入力した語は送信も保存もしません」という約束を、実装側から縛る。
# 文章だけの約束は、あとから検索を外部サービスに置き換えたときに残ったまま嘘になる
# （同じ型の食い違いを、このサイトは何度も出している）。
# 縛り方: 公開ページの fetch() は**同じフォルダの .json だけ**を読む、を機械で確かめる。
# 外部の検索APIに投げる形に変えれば、この検査で止まる。
def check_search_disclosure():
    FETCH = re.compile(r"fetch\(\s*(['\"])([^'\"]*)\1")
    ANY_FETCH = re.compile(r"fetch\(")
    LOCAL_JSON = re.compile(r"^[A-Za-z0-9_.\-]+\.json$")
    pages = sorted(f for f in os.listdir(ROOT) if f.endswith(".html"))
    boxes = 0
    for f in pages:
        html = open(os.path.join(ROOT, f), encoding="utf-8").read()
        if 'class="nw-kw"' in html:
            boxes += 1
            if "送信も保存もしません" not in html:
                fail("検索の開示", f"{f}: 検索欄があるのに、送信しない旨の開示が無い")
            for tag in ("navigator.sendBeacon", "XMLHttpRequest"):
                if tag in html:
                    fail("検索の開示", f"{f}: 検索欄のあるページに {tag} がある。送信経路が増えていないか確認が要る")
        lits = FETCH.findall(html)
        if len(lits) != len(ANY_FETCH.findall(html)):
            fail("検索の開示",
                 f"{f}: 宛先が文字列で書かれていない fetch がある。"
                 "どこへ送っているかを機械で確かめられないため、実装を確認すること")
        for _q, url in lits:
            if not LOCAL_JSON.match(url):
                fail("検索の開示",
                     f"{f}: 同じフォルダのJSON以外を読む fetch がある（{url}）。"
                     "『入力した語は送信しない』『解析を置いていない』開示と食い違わないか確認が要る")
    if boxes == 0:
        fail("検索の開示", "キーワード検索欄がどのページにも無い（発言一覧・採決一覧・ニュースに置いている）")
    print(f"  検索の開示: 検索欄 {boxes} ページ／外部への送信経路なし")

# 暗い背景でのリンクの可読性。
# 個別に色を指定していないリンクは、CSSに既定のリンク色が無いとブラウザ既定
# （未訪問 #0000EE / 訪問済み #551A8B）のままになり、ダークモードの背景（#12151d）
# ではコントラスト比1.3程度でほぼ読めない。実測で公開7ページ・221か所がこの状態だった
# （guide.html の「全文→」原典リンク145か所を含む＝このサイトの中心的な導線）。
# 生成CSSから既定の指定が消えたら止める。
def check_link_colors():
    pat = re.compile(r"(^|[};])a\{color:var\(--accent\)")
    pages = sorted(f for f in os.listdir(ROOT) if f.endswith(".html"))
    missing = []
    for f in pages:
        html = open(os.path.join(ROOT, f), encoding="utf-8").read()
        css = re.sub(r"\s+", "", re.sub(r"/\*.*?\*/", "", html, flags=re.S))
        if not pat.search(css):
            missing.append(f)
    if missing:
        fail("リンクの可読性",
             "既定のリンク色（a{color:var(--accent)}）がCSSに無い: " + ", ".join(missing)
             + "。個別指定の無いリンクがブラウザ既定色になり、暗い背景で読めなくなる")
    else:
        print(f"  リンクの可読性: {len(pages)} ページに既定のリンク色あり")

# 窓口の監視（⑥運用班 feedback-count.yml）と、その開示が一致しているか。
# サイトは削除・訂正の申出をご意見フォームとGitHubのIssue・PRで受け付け、
# 「半日ごとに新着の有無を機械的に確認している」と書いている。監視を外したのに
# 開示だけ残る／頻度を変えたのに開示が古いまま、はどちらも約束と実態のずれになる。
def check_intake_watch():
    fb = os.path.join(ROOT, "feedback.html")
    html = open(fb, encoding="utf-8").read() if os.path.exists(fb) else ""
    claimed = "新着の有無を機械的に確認" in html
    wf = os.path.join(ROOT, ".github", "workflows", "feedback-count.yml")
    if not os.path.exists(wf):
        if claimed:
            fail("窓口の監視",
                 "feedback.html は半日ごとの機械的な確認を約束しているが、"
                 ".github/workflows/feedback-count.yml が無い")
        return
    y = open(wf, encoding="utf-8").read()

    # ご意見フォームとIssue・PRの両方を数えているか（片方だけの監視に戻らないように）。
    for rel in ("agents/feedback_count.py", "agents/issue_count.py"):
        if rel not in y:
            fail("窓口の監視", f"feedback-count.yml が {rel} を実行していない")
        elif not os.path.exists(os.path.join(TOOLS, *rel.split("/"))):
            fail("窓口の監視", f"feedback-count.yml が実行する {rel} が存在しない")

    # 「半日ごと」と書いている以上、cron も1日2回であること。
    m = re.search(r"cron:\s*'([^']+)'", y)
    if not m:
        if claimed:
            fail("窓口の監視", "feedback-count.yml に schedule(cron) が無いのに、"
                              "feedback.html は定期的な確認を約束している")
    elif claimed:
        hours = [h for h in m.group(1).split()[1].split(",") if h.strip()]
        if len(hours) != 2:
            fail("窓口の監視",
                 f"feedback.html は「半日ごと」と書いているが、cron は1日{len(hours)}回"
                 f"（{m.group(1)}）")
    print("  窓口の監視: 開示と実装が一致"
          + ("（半日ごと・ご意見／Issue・PR）" if claimed else "（開示なし）"))


# ------------------------------- 7b. ご意見と対応の記録(⑦応答班)の整合
# 取り決めは agents/FEEDBACK_CHARTER.md。ここで見るのは:
#   ①記録の必須フィールド ②境界時刻(policy_boundary_utc)が無いまま記録が増えていないか
#   (境界時刻より前の投稿は新運用の対象外なので、境界未設定で記録が存在するのは矛盾)。
# 原文の混入は機械では判定できない(それは人間とAIの規律)。
def check_feedback_log():
    p = os.path.join(TOOLS, "feedback_log.json")
    if not os.path.exists(p):
        fail("ご意見の記録", "tools/feedback_log.json が無い")
        return
    log = json.load(open(p, encoding="utf-8"))
    boundary = log.get("policy_boundary_utc")
    entries = log.get("entries", [])
    decisions = {"採用", "一部採用", "不採用", "確認中"}
    for i, e in enumerate(entries):
        miss = [k for k in ("date", "category", "decision", "reason") if not e.get(k)]
        if miss:
            fail("ご意見の記録", f"記録{i}: 必須フィールドが無い {miss}")
        if e.get("decision") not in decisions:
            fail("ご意見の記録", f"記録{i}: 採否の値が不正（{e.get('decision')}）")
    if entries and not boundary:
        fail("ご意見の記録",
             "境界時刻(policy_boundary_utc)が未設定なのに記録が存在する。"
             "新運用は開示改定の公開時刻を記録してからしか始められない(憲章 段階0)")
    if boundary:
        k = os.path.join(ROOT, "kiroku.html")
        if os.path.exists(k) and boundary not in open(k, encoding="utf-8").read():
            fail("ご意見の記録",
                 f"kiroku.html に境界時刻（{boundary}）が表示されていない。再生成が必要")
    print(f"  ご意見の記録: {len(entries)} 件"
          + (f"／境界時刻 {boundary}" if boundary else "／新運用は未開始(境界時刻なし)"))

# ------------------------------------------- 7c. 次の国政選挙の日程(①収集班)
# 日程は tools/election_schedule.json を正本とし、トップページと
# election_mode(選挙期間中の停止スイッチ)がそこから作られる。
# ここで見るのは「日付そのものが正しいか」ではない——それは一次情報を見た人の仕事で、
# ①収集班(agents/watch_election.py)が毎日一次情報と突き合わせている。
# ここで見るのは、正本とページとスイッチが**食い違っていないか**:
#   ①期日を載せるなら出典が要る ②ページが再生成されている ③スイッチが日付と一致している
def collect_election_urls():
    p = os.path.join(TOOLS, "election_schedule.json")
    if not os.path.exists(p):
        return []
    urls = []
    for e in json.load(open(p, encoding="utf-8")).get("elections", []):
        urls += [e.get(k) for k in ("source", "term_end_source", "law_source") if e.get(k)]
    return urls


def _jdate(iso):
    y, m, d = iso.split("-")
    return f"{int(y)}年{int(m)}月{int(d)}日"


def check_election_schedule():
    p = os.path.join(TOOLS, "election_schedule.json")
    if not os.path.exists(p):
        fail("選挙日程", "tools/election_schedule.json が無い")
        return
    schedule = json.load(open(p, encoding="utf-8"))
    elections = schedule.get("elections", [])
    if not elections:
        fail("選挙日程", "election_schedule.json に選挙が1件も無い")
        return

    index = os.path.join(ROOT, "index.html")
    html_txt = open(index, encoding="utf-8").read() if os.path.exists(index) else ""

    for e in elections:
        name = e.get("name", e.get("id", "?"))
        # ① 期日を載せるなら、その根拠になった一次情報が要る。
        #    推測や報道だけで日付を置かない、という約束を機械で縛る。
        if e.get("vote") and not e.get("source"):
            fail("選挙日程", f"{name}: 投票日を載せているのに出典(source)が無い")
        if not e.get("term_end_source"):
            fail("選挙日程", f"{name}: 任期満了日の出典(term_end_source)が無い")
        # ② 正本を書き換えたのにページを再生成していない、を検出する。
        shown = e.get("vote") or e.get("term_end")
        if shown and html_txt and _jdate(shown) not in html_txt:
            fail("選挙日程",
                 f"{name}: {_jdate(shown)} がトップページに出ていない。"
                 "build_site.py で再生成が必要")

    # ③ 停止スイッチが日程と一致しているか（掛け忘れ・戻し忘れの検出）。
    sys.path.insert(0, os.path.join(TOOLS, "agents"))
    try:
        from sync_election_mode import active_election, today_jst
    except Exception as exc:
        fail("選挙日程", f"agents/sync_election_mode.py を読み込めない（{exc}）")
        return
    cfgp = os.path.join(ROOT, "config.json")
    cfg = json.load(open(cfgp, encoding="utf-8")) if os.path.exists(cfgp) else {}
    today = today_jst()
    want = active_election(schedule, today) is not None
    if bool(cfg.get("election_mode")) != want:
        fail("選挙日程",
             f"config.json の election_mode が {bool(cfg.get('election_mode'))} だが、"
             f"日程では {want} であるべき。python agents/sync_election_mode.py を実行する")

    fixed = sum(1 for e in elections if e.get("vote"))
    print(f"  選挙日程: {len(elections)} 件（期日確定 {fixed} 件）"
          f"／election_mode={bool(cfg.get('election_mode'))} は日程と一致")


def check_data_range():
    """フッターの「掲載データの範囲」が、実際のデータと一致しているかを見る。

    件数と日付はビルド時に埋めるので、**データを足してHTMLを作り直さないと古いまま公開される**。
    公開している数字がデータとずれたら止める（この開示は「いつ時点のデータか」という
    利用者の判断の土台なので、ずれたまま出すのは開示が無いより悪い）。
    """
    from _sessions import published_sessions
    sessions = published_sessions()
    n_sp = 0
    for s in sessions:
        p = os.path.join(TOOLS, f"speeches_{s}.json")
        if os.path.exists(p):
            n_sp += len(json.load(open(p, encoding="utf-8"))["items"])
    n_vt = 0
    for s in sessions:
        p = os.path.join(TOOLS, f"{s}_votes.json")
        if os.path.exists(p):
            n_vt += len(json.load(open(p, encoding="utf-8")).get("bills", []))

    pages = [f for f in os.listdir(ROOT) if f.endswith(".html")]
    checked = 0
    for fn in sorted(pages):
        html = open(os.path.join(ROOT, fn), encoding="utf-8").read()
        if 'class="sitefoot"' not in html:
            continue
        m = re.search(r'<p class="sf-data">(.*?)</p>', html, re.S)
        if not m:
            fail("掲載データの範囲", f"{fn}: フッターに掲載データの範囲が無い")
            continue
        line = m.group(1)
        miss = [s for s in sessions if f"第{s}回" not in line]
        if miss:
            fail("掲載データの範囲", f"{fn}: 掲載中の会期が書かれていない（第{'・第'.join(miss)}回）")
        for label, want in (("国会発言", n_sp), ("記名投票", n_vt)):
            m2 = re.search(label + r"\s*([0-9,]+)件", line)
            if not m2:
                fail("掲載データの範囲", f"{fn}: 「{label} N件」が読み取れない")
            elif int(m2.group(1).replace(",", "")) != want:
                fail("掲載データの範囲",
                     f"{fn}: {label}の件数が実データと違う（表示 {m2.group(1)} / 実際 {want}）。"
                     "build_site.py → deploy_to_repo.py で作り直す必要がある")
        checked += 1
    print(f"  掲載データの範囲: {checked}ページ／発言{n_sp}件・記名投票{n_vt}件と一致")

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
    check_vote_triage()
    check_privacy_claims()
    check_search_disclosure()
    check_link_colors()
    check_intake_watch()
    check_feedback_log()
    check_election_schedule()
    check_data_range()
    collect_research_citations()

    if not a.offline:
        print("\n[通信を伴う点検]")
        check_quotes(bp, oneissue, a.quotes_limit)
        check_links(collect_urls(bp, oneissue) + collect_election_urls(), a.links_limit)
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
