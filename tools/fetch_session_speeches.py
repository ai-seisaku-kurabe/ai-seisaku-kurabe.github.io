# -*- coding: utf-8 -*-
"""②編集班用: 指定期間の「言」（各党×各分野の代表発言）を会議録から集める。

発言は衆参両院から取る（会議録検索システムは両院を収録している）。
党の判定は party_of() に任せる。会派名に党名が入っていればそれを使い、
党名を含まない統一会派（衆議院の「中道改革連合・無所属」＝立憲民主党・公明党など）は
roster.json の名簿で補う。名簿で補った議員については、会派を代表した発言を除外する
（会派としての合意であって、単独の党の主張ではないため）。
この判定を使っていなかった間、立憲民主党と公明党の「言」は参議院のものだけだった。
どちらの院の発言かは house に記録し、サイト上でも明示する。
（採決は参院のみ。衆院は起立採決が原則で会派別の賛否が記録に残らないため。）

「行」（採決）は会期を併記できたのに「言」が第217回のままだと、
発言は1年前・投票は最新という非対称が生じる。それを埋めるための取得スクリプト。

    python fetch_session_speeches.py 221 2026-01-01 2026-07-20
    → 221_speeches.json  {党: {分野: {who, quote, url, date, meeting}}}

ルール（about.html の運用ルールに従う）:
  - 質問側の議員の発言のみ。答弁側（大臣・政府参考人など）は除外する。
  - 引用は原文のまま。争点キーワード周辺を抜き出し、挨拶・前置きは含めない。
  - 選定は編集判断であり、公開前に ③検証班（verify_content.py）で原文照合する。
"""
import quote
import json, os, re, sys, time, unicodedata, urllib.parse, urllib.request

API = "https://kokkai.ndl.go.jp/api/speech"
UA = {"User-Agent": "seisaku-kurabe/1.0 (+https://ai-seisaku-kurabe.github.io)"}
GOV = ["大臣", "副大臣", "大臣政務官", "政府参考人", "参考人", "公述人", "委員長",
       "会長", "局長", "長官", "主査", "議長", "副議長", "事務総長"]

# 掲載6分野と、その分野を代表する検索語（先頭から順に試す）
DOMAIN_TERMS = {
    "財政":            ["財政健全化", "消費税", "予算", "国債"],
    "外交・安保":      ["抑止力", "防衛力", "日米同盟", "安全保障"],
    "社会保障":        ["年金", "医療保険", "介護", "子育て支援"],
    "エネルギー・環境": ["原子力", "再生可能エネルギー", "脱炭素", "電気料金"],
    "経済・産業":      ["賃上げ", "物価高", "中小企業", "手取り"],
    "憲法":            ["憲法改正", "緊急事態条項", "憲法審査会"],
}
# 会派名の部分一致キー（会期で会派名が変わっても当たるように短めに取る）
PARTY_KEYS = {
    "自由民主党": "自由民主党", "立憲民主党": "立憲民主", "日本維新の会": "日本維新の会",
    "国民民主党": "国民民主", "公明党": "公明党", "日本共産党": "日本共産党",
    "れいわ新選組": "れいわ", "参政党": "参政党",
    # 第221回で会派を持つようになった党。以前は対象から漏れていて、この2党だけ
    # 別ファイルに手作業で足す運用になっており、取り直すたびに9件消えていた。
    # 正規の対象に入れて解消済み（別ファイルは廃止）。
    # 社民は会派名が「社会民主党」（第221回）と「社民」（第217回の統一会派内）の
    # 二通りある。片方だけだと「立憲民主・社民・無所属」で立憲だけが一致し、
    # 社民の議員を立憲として掲載してしまう（実際に福島みずほ議員で起きた）。
    "チームみらい": "チームみらい", "社会民主党": ("社会民主党", "社民"),
}

# 委員長報告・趣旨説明・議事進行など、党の立場を示さない手続き的発言
# 「趣旨を御説明」は実データで確認した定型句。「趣旨を説明」とは一致しないため別に持つ。
PROCEDURAL = ["委員会におきまして", "質疑を終局", "可決すべきもの", "御報告いたします",
              "報告いたします", "趣旨を説明", "趣旨説明", "趣旨を御説明", "提出者を代表",
              "議事日程", "審査の経過",
              "採決の結果", "全会一致をもって", "異議ないものと認めます"]

# 統一会派を代表した発言。会派の合意であって単独の党の主張ではないため、
# 名簿で党を補った議員についてはこれを収集しない。
# 実データの型: 「私は、会派を代表して、」「会派を代表し、」「中道改革連合・無所属を代表し、」
# 会派名と「を代表」の間に「・無所属」などが挟まるため、直前の語を固定しない。
# 冒頭に議長の指名や自己紹介が入るので、先頭固定ではなく冒頭160字を探す。
CAUCUS_REP = re.compile(r"を代表(し|いたし)")

def is_caucus_rep(body):
    return bool(CAUCUS_REP.search(body[:160]))

# 統一会派の議員名簿（build_roster.py が生成）。会派名から党を判定できない議員を補う。
def _load_roster():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "roster.json")
    if not os.path.exists(p):
        return {}
    try:
        return {k: v["party"] for k, v in json.load(open(p, encoding="utf-8"))["members"].items()}
    except Exception:
        return {}

ROSTER = _load_roster()

def party_of(rec):
    """発言者の党を決める。戻り値は (党名, 名簿で補ったか)。判定できなければ (None, False)。

    会派名に党名が入っていればそれを使う。入っていない統一会派の場合だけ名簿を引く。
    名簿で補った議員には、会派を代表した発言の除外を追加で適用する（単独会派の
    代表討論まで巻き添えで消さないため、この限定が要る）。
    """
    grp = rec.get("speakerGroup") or ""
    hit = {party for party, key in PARTY_KEYS.items()
           if any(k in grp for k in ((key,) if isinstance(key, str) else key))}
    if len(hit) == 1:
        return hit.pop(), False
    # 会派名だけでは決められない場合（党名が無い／複数の党名が同居している）は名簿に回す。
    # 第217回の参議院会派「立憲民主・社民・無所属」は立憲と社民が同居しており、
    # 辞書順で先に当たった方を採っていたため、福島みずほ議員の発言が立憲民主党として
    # 掲載されていた。**曖昧なまま一方に決めるより、載せない方がましである。**
    p = ROSTER.get(rec.get("speaker") or "")
    return (p, True) if p else (None, False)

def is_gov(rec):
    blob = (rec.get("speakerPosition") or "") + (rec.get("speech") or "")[:22]
    return any(m in blob for m in GOV)

def is_procedural(body):
    """委員長報告などの手続き的発言を除く。党の政策的立場を示さないため。"""
    return any(m in body for m in PROCEDURAL)

def fetch(term, date_from, date_until, n=90):
    q = urllib.parse.urlencode({"any": term, "from": date_from, "until": date_until,
                                "recordPacking": "json", "maximumRecords": n})
    req = urllib.request.Request(f"{API}?{q}", headers=UA)
    return json.loads(urllib.request.urlopen(req, timeout=40).read()
                      .decode("utf-8")).get("speechRecord", [])

def snippet(body, term):
    """争点キーワードを含む文を、文の切れ目で抜き出す（切り出しは quote.py に集約）。"""
    return quote.condense(quote.snippet(body, term))


def main():
    if len(sys.argv) < 4:
        raise SystemExit("使い方: python fetch_session_speeches.py <会期> <from> <until>")
    session, dfrom, duntil = sys.argv[1], sys.argv[2], sys.argv[3]
    out = {p: {} for p in PARTY_KEYS}

    for dom, terms in DOMAIN_TERMS.items():
        print(f"[{dom}]")
        need = {p for p in PARTY_KEYS}
        for term in terms:
            if not need:
                break
            try:
                recs = fetch(term, dfrom, duntil)
            except Exception as e:
                print(f"  WARN {term}: {e}"); continue
            for rec in recs:
                if is_gov(rec):
                    continue
                # 会派名の文字列一致だけでは、党名を含まない統一会派に属する議員を
                # 全部取りこぼす（衆議院の「中道改革連合・無所属」に立憲・公明が入る）。
                # party_of() は名簿で党を補う。発言一覧（fetch_speech_list.py）は
                # 先にこちらへ移っており、ガイドの「言」だけが取り残されていた。
                p, via_roster = party_of(rec)
                if p is None or p not in need:
                    continue
                body = (rec.get("speech") or "").replace("\r\n", " ").strip()
                if len(body) < 80 or "会議録情報" in body or is_procedural(body):
                    continue
                # 統一会派を代表した発言は、会派の合意であって1党の主張ではない
                if via_roster and is_caucus_rep(body):
                    continue
                text = snippet(body, term)
                if len(text) < 40:
                    continue
                out[p][dom] = {"who": rec["speaker"], "quote": text, "url": rec["speechURL"],
                               "date": rec["date"], "house": rec.get("nameOfHouse", ""),
                               "meeting": rec["nameOfMeeting"], "term": term}
                need.discard(p)
            time.sleep(0.4)
        got = [p for p in PARTY_KEYS if dom in out[p]]
        miss = [p for p in PARTY_KEYS if dom not in out[p]]
        print(f"  取得: {len(got)}/{len(PARTY_KEYS)} 党" + (f"  未取得={miss}" if miss else ""))

    path = f"{session}_speeches.json"
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    total = sum(len(v) for v in out.values())
    print(f"\n{path} を書き出しました（{total} 件 / 最大 {len(PARTY_KEYS)*len(DOMAIN_TERMS)} 件）")

if __name__ == "__main__":
    main()
