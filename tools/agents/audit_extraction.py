# -*- coding: utf-8 -*-
"""⑨文献調査班／「言」の抽出で、どれだけ選んでいるかを測る（audit_extraction）

このサイトは各党×分野に発言を1件ずつ載せている。その1件は、会議録検索システムを
争点キーワードで検索し、答弁側・手続き的発言・統一会派の代表討論などを除いたうえで、
**最初に条件を満たした1件**を採ったものである（fetch_session_speeches.py）。

先行研究（NTCIR の共有タスクは地方議会が対象で、国会向けの物差しは見つからなかった）
に照らすと、「拾うべき発言を拾えているか」の精度は測れない。正解データが無く、作れば
それ自体が編集判断になるからである。だが**どれだけ選んでいるか**は測れる。

各党×分野×会期について、同じ検索と同じ除外条件を通る発言が何件あるか（＝候補の数）を
数える。私たちが見せているのはそのうち1件なので、「候補 N 件のうち 1 件を表示」という
選択の度合いが数字になる。候補が多い枠ほど、表示している1件は「多くのうちの1つ」であり、
別の1件を選べば違って見えうる。

除外条件は fetch_session_speeches.py から関数ごと読み込む（写しを作らず、判定をずらさない）。
検索の窓は各会期の会期期間（参議院の議案情報で公表されている会期の日程）に固定する。

    cd tools && python agents/audit_extraction.py
    cd tools && python agents/audit_extraction.py --print   # 表示のみ

出力は state/extraction_audit.json。research.html はこの数字を流し込む。
"""
from __future__ import annotations
import argparse, io, json, os, sys, datetime

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, TOOLS)          # fetch_session_speeches.py を関数ごと使う
import fetch_session_speeches as F  # noqa: E402
sys.path.insert(0, HERE)
from _sessions import published_sessions   # noqa: E402

OUT_JSON = os.path.join(TOOLS, "state", "extraction_audit.json")

# 各会期の会期期間（参議院 議案情報のトップに公表されている会期の日程）。
# 検索の窓をここに固定することで、数字が「たまたま指定した期間」に左右されない。
# 会期を足したらここにも足す（③検証班が会期の一致を見る）。
SESSION_WINDOWS = {
    "217": ("2025-01-24", "2025-06-22"),
    "219": ("2025-10-21", "2025-12-17"),
    "221": ("2026-02-18", "2026-07-22"),
}


def candidates(session):
    """会期の各党×分野について、条件を通る候補発言の数を数える。

    fetch_session_speeches.main() の選別と同じ条件を使い、最初の1件で止めずに
    すべて数える。同じ発言（speechURL）は1回だけ数える。
    """
    dfrom, duntil = SESSION_WINDOWS[session]
    # party -> domain -> set(speechURL)
    pool = {p: {d: set() for d in F.DOMAIN_TERMS} for p in F.PARTY_KEYS}
    for dom, terms in F.DOMAIN_TERMS.items():
        for term in terms:
            try:
                recs = F.fetch(term, dfrom, duntil)
            except Exception as e:
                print(f"  WARN {session}/{dom}/{term}: {e}")
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
                text = F.snippet(body, term)
                if len(text) < 40:
                    continue
                pool[p][dom].add(rec.get("speechURL") or rec.get("speechID"))
            import time
            time.sleep(0.4)
    return pool


def load_displayed():
    """実際に表示している党×分野×会期（1件表示している枠）。"""
    shown = {s: {} for s in SESSION_WINDOWS}
    # 第217回はガイド本体（build_party.py の PIDX）に入る。exec せず JSON から拾える
    # 219/221 と違い器が異なるので、生成済みの speeches ファイルがある会期だけを数える。
    for s in ("219", "221"):
        p = os.path.join(TOOLS, f"{s}_speeches.json")
        if os.path.exists(p):
            d = json.load(open(p, encoding="utf-8"))
            shown[s] = {party: set(doms) for party, doms in d.items() if doms}
    # 第217回は 217_speech_meta.json（表示中の発言のメタ）から党×分野を拾う
    meta = os.path.join(TOOLS, "217_speech_meta.json")
    if os.path.exists(meta):
        m = json.load(open(meta, encoding="utf-8"))
        got = {}
        for key in m:                       # キーは "党|分野" 形式
            if "|" in key:
                party, dom = key.split("|", 1)
                got.setdefault(party, set()).add(dom)
        shown["217"] = got
    return shown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="only_print", action="store_true")
    ap.add_argument("--sessions", nargs="*", help="数える会期（既定は掲載中の全会期）")
    args = ap.parse_args()

    want = args.sessions or [s for s in published_sessions() if s in SESSION_WINDOWS]
    shown = load_displayed()

    res = {"generated": datetime.datetime.now().strftime("%Y-%m-%d"),
           "windows": {s: SESSION_WINDOWS[s] for s in want},
           "sessions": {}, "cells": []}
    tot_pool = tot_shown = 0
    ratios = []

    for s in want:
        print(f"[第{s}回 {SESSION_WINDOWS[s][0]}〜{SESSION_WINDOWS[s][1]}]")
        pool = candidates(s)
        s_pool = s_shown = 0
        for party in F.PARTY_KEYS:
            for dom in F.DOMAIN_TERMS:
                n = len(pool[party][dom])
                is_shown = dom in shown.get(s, {}).get(party, set())
                if n == 0 and not is_shown:
                    continue
                res["cells"].append({"session": s, "party": party, "domain": dom,
                                     "candidates": n, "shown": bool(is_shown)})
                s_pool += n
                if is_shown:
                    s_shown += 1
                    if n:
                        ratios.append(n)
        res["sessions"][s] = {"candidate_total": s_pool, "shown": s_shown}
        tot_pool += s_pool
        tot_shown += s_shown
        print(f"  候補 {s_pool} 件 / 表示 {s_shown} 枠")

    ratios.sort()
    med = ratios[len(ratios) // 2] if ratios else 0
    res["total"] = {
        "candidate_total": tot_pool,
        "shown": tot_shown,
        "median_candidates_per_shown_cell": med,
        "max_candidates": max(ratios) if ratios else 0,
        "shown_cells_with_multiple_candidates":
            sum(1 for r in ratios if r > 1),
        "shown_cells_counted": len(ratios),
    }

    print(f"\n■ まとめ（掲載 {len(want)} 会期）")
    print(f"  条件を通った候補発言：あわせて {tot_pool} 件")
    print(f"  そのうち表示しているのは各枠 1 件（表示 {tot_shown} 枠）")
    print(f"  表示している枠あたりの候補：中央値 {med} 件／最多 {res['total']['max_candidates']} 件")
    print(f"  候補が2件以上あった枠：{res['total']['shown_cells_with_multiple_candidates']}"
          f"/{res['total']['shown_cells_counted']} 枠")

    if not args.only_print:
        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        io.open(OUT_JSON, "w", encoding="utf-8").write(
            json.dumps(res, ensure_ascii=False, indent=1))
        print("\nwrote", os.path.relpath(OUT_JSON, TOOLS))


if __name__ == "__main__":
    main()
