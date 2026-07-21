# -*- coding: utf-8 -*-
"""⑨文献調査班／設問の来歴を洗い出す（audit_questions）

Walgrave, Nuytemans & Pepermans (2009) は、投票支援ツールの<b>設問の選択そのものが</b>
利用者と政党の一致度に深甚な影響を与えることを実証した。点数化するかどうかとは独立に、
マッチング機能を持つ限り必ず生じる問題である。

このスクリプトは「良い設問か」を判定しない（それは編集の仕事で、機械には決められない）。
機械にできるのは、<b>設問が何から作られ、何が使われなかったか</b>を数えることである。

  ・「政策で照らす」の各設問が、採決にもとづくのか公約・発言にもとづくのか
  ・設問の根拠として実際にリンクしている参議院の記名投票は何件か
  ・同じ会期に記名投票にかけられた議案は全部で何件か（＝設問になりえた母集団）

出力は state/question_audit.json。research.html はこの数字を流し込む。

使い方:
    cd tools && python agents/audit_questions.py
    cd tools && python agents/audit_questions.py --print   # 表示のみ
"""
from __future__ import annotations
import argparse, io, json, os, re, sys, datetime

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from _sessions import published_sessions   # noqa: E402

OUT_JSON = os.path.join(TOOLS, "state", "question_audit.json")

# 掲載中の会期は build_party.py の sessions_for() が唯一の出どころ。ここに書き持たない。
SESSIONS = published_sessions()
VOTE_URL = re.compile(r"sangiin\.go\.jp/japanese/touhyoulist/(\d{3})/(\d{3}-\d{4}-v\d{3})\.htm")


def load_policy():
    """build_shindan.py の定義部分だけを読む（import すると shindan.html を書き出すため）。"""
    src_path = os.path.join(TOOLS, "build_shindan.py")
    src = io.open(src_path, encoding="utf-8").read()
    cut = src.find("\nDATA = {")      # basis と短ラベルを付けるループまでを取り込む
    ns: dict = {}
    exec(compile(src[:cut if cut > 0 else len(src)], src_path, "exec"), ns)
    return ns["POLICY"], ns["PARTIES"]


def vote_ids(text):
    return set(m.group(2) for m in VOTE_URL.finditer(text or ""))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="only_print", action="store_true")
    args = ap.parse_args()

    policy, parties = load_policy()

    # ---- 各設問が何にもとづいているか
    items, used = [], set()
    for q in policy:
        srcs = (q.get("basis_url") or "") + " " + " ".join(u for _, u in q.get("links", []))
        ids = vote_ids(srcs)
        used |= ids
        items.append({
            "short": q.get("short", ""),
            "q": q["q"],
            "basis_kind": "採決" if q.get("basis_url") else "公約・発言",
            "basis": q.get("basis", ""),
            "vote_ids": sorted(ids),
            "neutral_parties": sum(1 for p in parties if q["stance"].get(p["full"], 0) == 0),
        })

    # ---- 母集団：同じ会期に記名投票にかけられた議案
    pool = {}
    for s in SESSIONS:
        p = os.path.join(TOOLS, f"{s}_votes.json")
        if not os.path.exists(p):
            print(f"  （{s}_votes.json が無いので母集団に数えません）")
            continue
        bills = json.load(open(p, encoding="utf-8")).get("bills", [])
        pool[s] = {"roll_calls": len(bills),
                   "used_as_basis": sum(1 for b in bills if b["id"] in used)}

    res = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d"),
        "questions": len(policy),
        "by_basis": {
            "採決": sum(1 for i in items if i["basis_kind"] == "採決"),
            "公約・発言": sum(1 for i in items if i["basis_kind"] == "公約・発言"),
        },
        "vote_ids_used": sorted(used),
        "pool": pool,
        "pool_total": sum(v["roll_calls"] for v in pool.values()),
        "items": items,
    }

    print(f"設問 {res['questions']} 問")
    print(f"  採決にもとづく判定: {res['by_basis']['採決']}問"
          f"／公約・発言にもとづく判定: {res['by_basis']['公約・発言']}問")
    for s, v in pool.items():
        print(f"  第{s}回 記名投票 {v['roll_calls']}件 → 設問の根拠に使ったのは {v['used_as_basis']}件")
    print(f"  設問の根拠としてリンクしている記名投票: {len(used)}件")
    for i in items:
        print(f"   ・{i['short'] or i['q'][:14]}（{i['basis_kind']}"
              f"／中立の党 {i['neutral_parties']}）")

    if not args.only_print:
        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        io.open(OUT_JSON, "w", encoding="utf-8").write(
            json.dumps(res, ensure_ascii=False, indent=1))
        print("\nwrote", os.path.relpath(OUT_JSON, TOOLS))


if __name__ == "__main__":
    main()
