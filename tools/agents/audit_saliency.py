# -*- coding: utf-8 -*-
"""⑨文献調査班／各党が会議録で「何に触れたか」の配分を測る（audit_saliency）

顕出性理論（Budge &amp; Farlie 1983／Manifesto Project）は、政党は賛否で対立するより
「どの争点を強調するか」で競う、と説く。このサイトは各党の言と行を固定6分野に振り分けて
並べているが、少数政党の看板争点は6分野の外にあることが多い（research.html の弱点2-2）。

そこで、6分野に加えて<b>6分野に収まらない横断争点</b>も検索語に足し、各党の質問側発言が
どのテーマにどれだけ触れたかを機械的に数える。これは「強調」の粗い目安であって、
党の重点や本質を断定するものではない。MARPOR が公約を数えるのと同じ発想を、
国会会議録の発言に適用したもの。

**この検査は判定しない。数えて開示するだけ（③検証班・他の監査と同じ）。**

限界（結果と一緒に必ず開示する）:
- 検索語の選び方は編集判断。語の一覧を公開し、訂正を受け付ける。
- 国会の質問側発言だけが対象（答弁側・手続き的発言・統一会派の代表討論は除外）。
  公約・演説・SNS は含まない。会議録に出ない強調は測れない。
- 1つの発言が複数テーマに当たりうる（割合の合計は100%を超えうる）。
- 発言が少ない党は不安定なので、閾値未満は「資料不足（判断保留）」にして順位を出さない。

    cd tools && python agents/audit_saliency.py
    cd tools && python agents/audit_saliency.py --print
出力は state/saliency_audit.json。research.html がこの数字を流し込む。
"""
from __future__ import annotations
import argparse, io, json, os, sys, time, datetime

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)
import fetch_session_speeches as F   # noqa: E402
sys.path.insert(0, HERE)
from _sessions import published_sessions   # noqa: E402
from audit_extraction import SESSION_WINDOWS   # 会期の窓は1か所（audit_extraction）に置く  # noqa: E402

OUT_JSON = os.path.join(TOOLS, "state", "saliency_audit.json")
MIN_SPEECHES = 10   # これ未満の党は「資料不足」にして順位を出さない（判断保留）

# 6分野に収まらない「横断争点」の検索語。**この一覧は編集判断であり、公開して訂正を受ける。**
# 掲載10党のうち、その争点を前面に出す党が国会で使う語を中心に選んだ。
CROSS_TERMS = {
    "外国人・移民":       ["外国人", "移民", "入管", "在留資格"],
    "放送・受信料":       ["受信料", "ＮＨＫ", "放送法"],
    "デジタル・行政改革": ["デジタル", "マイナンバー", "行政のデジタル", "ＤＸ"],
    "政治改革・透明化":   ["政治資金", "議員定数", "世襲", "政治改革"],
    "地方分権":           ["地方分権", "道州制", "地方主権"],
}


def all_themes():
    """6分野（F.DOMAIN_TERMS）＋横断争点（CROSS_TERMS）。値は (検索語list, 6分野か)。"""
    out = {d: (terms, True) for d, terms in F.DOMAIN_TERMS.items()}
    for d, terms in CROSS_TERMS.items():
        out[d] = (terms, False)
    return out


def gather(session, themes):
    """会期の各党×テーマで、条件を通る質問側発言（speechURL）を集める。

    fetch_session_speeches.main() と同じ選別。1つの発言は複数テーマに入りうる。
    """
    dfrom, duntil = SESSION_WINDOWS[session]
    pool = {p: {t: set() for t in themes} for p in F.PARTY_KEYS}
    for theme, (terms, _is6) in themes.items():
        for term in terms:
            try:
                recs = F.fetch(term, dfrom, duntil)
            except Exception as e:
                print(f"  WARN {session}/{theme}/{term}: {e}")
                continue
            for rec in recs:
                if F.is_gov(rec):
                    continue
                p, via_roster = F.party_of(rec)
                if p is None or p not in pool:
                    continue
                body = (rec.get("speech") or "").replace("\r\n", " ").strip()
                if len(body) < 80 or "会議録情報" in body or F.is_procedural(body):
                    continue
                if via_roster and F.is_caucus_rep(body):
                    continue
                pool[p][theme].add(rec.get("speechURL") or rec.get("speechID"))
            time.sleep(0.4)
    return pool


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="only_print", action="store_true")
    args = ap.parse_args()

    sessions = [s for s in published_sessions() if s in SESSION_WINDOWS]
    themes = all_themes()
    is6 = {t: v[1] for t, v in themes.items()}

    # party -> theme -> set(speechURL)（全会期を統合）
    merged = {p: {t: set() for t in themes} for p in F.PARTY_KEYS}
    for s in sessions:
        print(f"[第{s}回 {SESSION_WINDOWS[s][0]}〜{SESSION_WINDOWS[s][1]}]")
        g = gather(s, themes)
        for p in F.PARTY_KEYS:
            for t in themes:
                merged[p][t] |= g[p][t]
        print(f"  第{s}回 集計済み")

    res = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d"),
        "sessions": sessions,
        "windows": {s: SESSION_WINDOWS[s] for s in sessions},
        "themes": list(themes.keys()),
        "cross_themes": list(CROSS_TERMS.keys()),
        "cross_terms": CROSS_TERMS,
        "min_speeches": MIN_SPEECHES,
        "by_party": [],
        "cross_signal": [],     # 横断争点が上位に出た（党, テーマ, 割合）
    }

    for p in F.PARTY_KEYS:
        # その党が「いずれかのテーマ」に触れた distinct 発言（分母）
        union = set().union(*merged[p].values()) if merged[p] else set()
        total = len(union)
        shares = []
        for t in themes:
            n = len(merged[p][t])
            if n:
                shares.append({"theme": t, "n": n,
                               "share": round(n / total * 100, 1) if total else 0.0,
                               "cross": not is6[t]})
        shares.sort(key=lambda x: -x["n"])
        held = total < MIN_SPEECHES
        entry = {"party": p, "total": total, "reserved": held, "top": shares[:6]}
        res["by_party"].append(entry)
        if not held:
            for sh in shares[:3]:
                if sh["cross"]:
                    res["cross_signal"].append(
                        {"party": p, "theme": sh["theme"], "share": sh["share"], "n": sh["n"]})

    res["parties_reserved"] = [e["party"] for e in res["by_party"] if e["reserved"]]

    # ------------------------------------------------------------ 表示
    print("\n■ 各党が会議録で触れたテーマの配分（質問側発言・全会期）")
    print("  ※「割合」は、その党がいずれかのテーマに触れた発言のうち、当該テーマに触れた割合")
    for e in res["by_party"]:
        if e["reserved"]:
            print(f"  {e['party']}: 発言 {e['total']}件 → 資料不足（判断保留、{MIN_SPEECHES}件未満）")
            continue
        tops = "／".join(f"{s['theme']}{s['share']}%{'★' if s['cross'] else ''}" for s in e["top"][:4])
        print(f"  {e['party']}: 発言 {e['total']}件 → {tops}")
    print("\n■ 6分野に収まらない横断争点が、その党の上位3テーマに入った例（★）")
    if res["cross_signal"]:
        for c in sorted(res["cross_signal"], key=lambda x: -x["share"]):
            print(f"  {c['party']}：{c['theme']} {c['share']}%（{c['n']}件）")
    else:
        print("  なし（横断争点は、どの党でも上位3テーマに入らなかった）")

    if not args.only_print:
        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        io.open(OUT_JSON, "w", encoding="utf-8").write(
            json.dumps(res, ensure_ascii=False, indent=1))
        print("\nwrote", os.path.relpath(OUT_JSON, TOOLS))


if __name__ == "__main__":
    main()
