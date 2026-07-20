# -*- coding: utf-8 -*-
"""発言一覧ページ用: 各党×各分野の発言を複数件まとめて集める。

国会会議録検索システムは URL で検索条件を渡せない（SPAはパラメータを無視し、
シンプル表示は POST + CSRF）。そのため「この分野の発言を探す」を外部に委ねられず、
自前で一覧を持つことにした。取得は API から、表示は必ず原文リンク付きで行う。

    python fetch_speech_list.py 221 2026-01-01 2026-07-20
    python fetch_speech_list.py 217 2025-01-01 2025-06-30
    → speeches_<会期>.json  [{party, domain, who, quote, url, date, house, meeting}]

ルール（about.html の運用ルールに準拠）:
  - 質問側の議員の発言のみ。答弁側と、委員長報告などの手続き的発言は除く。
  - 引用は原文のまま。争点キーワード周辺を抜き出す。
"""
import json, sys, time

# 既存スクリプトの取得ロジック（fetch/snippet/is_gov/is_procedural/PARTY_KEYS）を再利用する
exec(open("fetch_session_speeches.py", encoding="utf-8").read().split("def main")[0])

PER = 5   # 1つの党×分野あたりの上限

# 一覧用に検索語を増やし、取りこぼしを減らす
LIST_TERMS = {
    "財政":            ["財政健全化", "消費税", "予算", "国債", "税制", "歳出"],
    "外交・安保":      ["抑止力", "防衛力", "日米同盟", "安全保障", "自衛隊", "外交"],
    "社会保障":        ["年金", "医療保険", "介護", "子育て支援", "社会保障", "生活保護"],
    "エネルギー・環境": ["原子力", "再生可能エネルギー", "脱炭素", "電気料金", "環境", "気候変動"],
    "経済・産業":      ["賃上げ", "物価高", "中小企業", "手取り", "雇用", "産業政策"],
    "憲法":            ["憲法改正", "緊急事態条項", "憲法審査会", "立憲主義"],
}
NEW_PARTIES = {"チームみらい": "チームみらい", "社会民主党": "社会民主党"}


def main():
    if len(sys.argv) < 4:
        raise SystemExit("使い方: python fetch_speech_list.py <会期> <from> <until>")
    session, dfrom, duntil = sys.argv[1], sys.argv[2], sys.argv[3]
    PARTY_KEYS.update(NEW_PARTIES)   # 新党2党も party_of() 側で判定する
    rows, seen = [], set()
    count = {}   # (党, 分野) -> 件数

    for dom, terms in LIST_TERMS.items():
        for term in terms:
            try:
                recs = fetch(term, dfrom, duntil)
            except Exception as e:
                print(f"  WARN {dom}/{term}: {e}")
                continue
            for rec in recs:
                if is_gov(rec):
                    continue
                party, via_roster = party_of(rec)
                if party is None:
                    continue
                if count.get((party, dom), 0) >= PER:
                    continue
                body = (rec.get("speech") or "").replace("\r\n", " ").strip()
                if len(body) < 80 or "会議録情報" in body or is_procedural(body):
                    continue
                # 統一会派の議員は、会派を代表した発言を党の主張として扱えない
                if via_roster and is_caucus_rep(body):
                    continue
                text = snippet(body, term)
                if len(text) < 40:
                    continue
                key = rec["speechURL"]
                if key in seen:
                    continue
                seen.add(key)
                rows.append({"party": party, "domain": dom, "who": rec["speaker"],
                             "quote": text, "url": rec["speechURL"], "date": rec["date"],
                             "house": rec.get("nameOfHouse", ""), "meeting": rec["nameOfMeeting"]})
                count[(party, dom)] = count.get((party, dom), 0) + 1
            time.sleep(0.35)
        got = sum(v for (p, d), v in count.items() if d == dom)
        print(f"  [{dom}] {got} 件")

    rows.sort(key=lambda r: (r["domain"], r["party"], r["date"]))
    path = f"speeches_{session}.json"
    json.dump({"session": int(session), "items": rows},
              open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    parties = len({r["party"] for r in rows})
    print(f"\n{path}: {len(rows)} 件（{parties} 党）")


if __name__ == "__main__":
    main()
