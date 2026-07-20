# -*- coding: utf-8 -*-
"""②編集班用: 指定期間の「言」（各党×各分野の代表発言）を会議録から集める。

発言は衆参両院から取る（会議録検索システムは両院を収録している）。
ただし党の判定は会派名の文字列一致で行うため、党名を含まない統一会派は拾えない。
現に衆議院の「中道改革連合・無所属」（立憲民主党・公明党などの統一会派）が漏れており、
この2党の発言は参議院のものだけになっている。about.html で開示済み。
議員名から党を引く方式に変えれば拾えるが、統一会派を代表した発言を1党の主張として
扱ってよいかという別の判断が要るため、結論が出るまでは対象外にしている。
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
import json, re, sys, time, unicodedata, urllib.parse, urllib.request

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
}

# 委員長報告・趣旨説明・議事進行など、党の立場を示さない手続き的発言
PROCEDURAL = ["委員会におきまして", "質疑を終局", "可決すべきもの", "御報告いたします",
              "報告いたします", "趣旨を説明", "趣旨説明", "議事日程", "審査の経過",
              "採決の結果", "全会一致をもって", "異議ないものと認めます"]

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
    """争点キーワードの周辺を抜き出す。挨拶・定型の前置きを避けるため。"""
    b = re.sub(r"^○[^　]{1,14}　", "", body).strip()
    i = b.find(term)
    if i < 0:
        i = 0
        parts = b.split("。")
        b = ("。".join(parts[1:]) if len(parts) > 2 else b).strip()
    seg = b[max(0, i - 30):max(0, i - 30) + 150]
    d = seg.find("。")
    if 0 <= d < 45:
        seg = seg[d + 1:]
    return re.sub(r"\s+", " ", seg).strip()[:130]

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
                grp = rec.get("speakerGroup") or ""
                hit = [p for p in need if PARTY_KEYS[p] in grp]
                if not hit:
                    continue
                body = (rec.get("speech") or "").replace("\r\n", " ").strip()
                if len(body) < 80 or "会議録情報" in body or is_procedural(body):
                    continue
                text = snippet(body, term)
                if len(text) < 40:
                    continue
                p = hit[0]
                out[p][dom] = {"who": rec["speaker"], "quote": text, "url": rec["speechURL"],
                               "date": rec["date"], "house": rec.get("nameOfHouse", ""),
                               "meeting": rec["nameOfMeeting"], "term": term}
                need.discard(p)
            time.sleep(0.4)
        got = [p for p in PARTY_KEYS if dom in out[p]]
        print(f"  取得: {len(got)}/8 党" + ("" if len(got) == 8 else f"  未取得={[p for p in PARTY_KEYS if dom not in out[p]]}"))

    path = f"{session}_speeches.json"
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    total = sum(len(v) for v in out.values())
    print(f"\n{path} を書き出しました（{total} 件 / 最大 {len(PARTY_KEYS)*len(DOMAIN_TERMS)} 件）")

if __name__ == "__main__":
    main()
