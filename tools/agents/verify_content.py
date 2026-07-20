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

def check_quotes(bp, oneissue, limit=None):
    """掲載中の引用が原文に実在するかをAPIで直接照合する。"""
    clean = bp["clean_quote"]
    targets = []   # (どこ, 話者, 表示テキスト, URL)
    for full, doms in bp["PIDX"].items():
        for dname, (entry, _v, _l) in doms.items():
            targets.append((f"guide/{full}/{dname}", entry.get("who"),
                            clean(entry["quote"]), entry.get("url")))
    for full, recs in oneissue.items():
        for r in recs:
            targets.append((f"oneissue/{full}", r.get("who"), r.get("text"), r.get("url")))

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

def check_links(urls, limit=None):
    if limit: urls = urls[:limit]
    bad = 0
    for u in urls:
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=25) as r:
                if r.status >= 400:
                    fail("リンク", f"{r.status} {u}"); bad += 1
        except urllib.error.HTTPError as e:
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
    ("about.html",    ["第221回国会では会派を結成"],                "会派構成の変化を反映"),
    ("oneissue.html", ["会派を構成しておらず"],                     "ワンイシュー側の空白明示"),
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

    if not a.offline:
        print("\n[通信を伴う点検]")
        check_quotes(bp, oneissue, a.quotes_limit)
        check_links(collect_urls(bp, oneissue), a.links_limit)
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
