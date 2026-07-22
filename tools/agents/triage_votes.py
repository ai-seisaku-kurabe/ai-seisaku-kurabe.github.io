# -*- coding: utf-8 -*-
"""記名投票の全件トリアージ＝判定表 vote_triage.json の生成。

「政策で照らす」の設問開示にあった「多くは検討そのものをしていません」を
解消するため、掲載会期の参議院記名投票の全件に設問候補性の判定を付ける。
取り決めは agents/TRIAGE_CRITERIA.md、コード定義は tools/vote_triage_criteria.json、
人間の判定(AI下書き→PR承認)は tools/triage_overrides.json。

機械段(このスクリプト)が判定するもの:
  USED       … 設問の根拠・参考に使用(state/question_audit.json の vote_ids_used)
  PERSONNEL  … 件名に「任命に関する件」
  ACCOUNTS   … 件名に 決算/調書/計算書/財産目録/放送法第七十条
  PROCEDURAL … 件名に 参議院規則/規程案/証人等の旅費
  NO_DIFF    … 全会派の反対が0票(全会一致)
  AMBIGUOUS  … 件名が「令和○年度…予算」(予算への賛否は両方向の理由から生じる。
               このサイトが設問「財政健全化」で採決を根拠にしていないのと同じ理由)
残りは triage_overrides.json の人間判定、無ければ CANDIDATE(候補として成立するが未採用)。
「反対が少ないから除外」のような弁別力の数値足切りは置かない(TRIAGE_CRITERIA.md 原則5)。

実行: tools/ から `python agents/triage_votes.py`
"""
import json
import os
import re
import sys
from datetime import date

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from _sessions import published_sessions, TOOLS

ACCOUNT_KEYS = ("歳入歳出決算", "使用総調書", "経費増額調書", "計算書", "財産目録", "放送法第七十条")
PROC_KEYS = ("参議院規則", "規程案", "証人等の旅費")
BUDGET_RE = re.compile(r"^令和.+年度.*予算")


def load(name):
    return json.load(open(os.path.join(TOOLS, name), encoding="utf-8"))


def machine_code(label, parties, used_ids, vid):
    """機械段の判定。順序は criteria の precedence と同じ。該当なしなら None。"""
    if vid in used_ids:
        return "USED"
    if "任命に関する件" in label:
        return "PERSONNEL"
    if any(k in label for k in ACCOUNT_KEYS):
        return "ACCOUNTS"
    if any(k in label for k in PROC_KEYS):
        return "PROCEDURAL"
    if parties and all(v.get("no", 0) == 0 for v in parties.values()):
        return "NO_DIFF"
    if BUDGET_RE.match(label) and "法律案" not in label:
        return "AMBIGUOUS"
    return None


def main():
    criteria = load("vote_triage_criteria.json")
    codes = set(criteria["codes"])
    overrides = load("triage_overrides.json")["items"]
    used_ids = set(load(os.path.join("state", "question_audit.json"))["vote_ids_used"])

    sessions = published_sessions()
    items, errors, conflicts = [], [], []
    seen_used = set()
    for ses in sessions:
        for b in load(f"{ses}_votes.json")["bills"]:
            vid, label = b["id"], b["label"]
            mc = machine_code(label, b.get("parties", {}), used_ids, vid)
            ov = overrides.get(vid)
            if mc:
                code, note, rep = mc, None, None
                if mc == "AMBIGUOUS":
                    note = ("予算への賛否は「規模が大きすぎる」「小さすぎる」の両方向の理由から"
                            "生じるため、単一の立場として読み替えません。")
                if ov:
                    conflicts.append(f"{vid}: 機械判定 {mc} があるため overrides({ov['code']}) は無視")
            elif ov:
                code, note, rep = ov["code"], ov.get("note"), ov.get("rep")
                if code not in codes:
                    errors.append(f"{vid}: 不明なコード {code}")
            else:
                code, note, rep = "CANDIDATE", None, None
            if code == "USED":
                seen_used.add(vid)
            row = {"id": vid, "code": code}
            if note:
                row["note"] = note
            if rep:
                row["rep"] = rep
            items.append(row)

    ids = {r["id"] for r in items}
    for vid in used_ids - seen_used:
        errors.append(f"設問根拠の採決 {vid} が母集団にありません")
    for vid in set(overrides) - ids:
        errors.append(f"overrides の {vid} は母集団にありません")
    by_id = {r["id"]: r for r in items}
    for r in items:
        if r["code"] == "REPRESENTED":
            t = by_id.get(r.get("rep"))
            if not t:
                errors.append(f"{r['id']}: 代表採決 {r.get('rep')} が存在しません")
            elif t["code"] == "REPRESENTED":
                errors.append(f"{r['id']}: 代表採決 {t['id']} も REPRESENTED(連鎖は不可)")

    counts = {}
    for r in items:
        counts[r["code"]] = counts.get(r["code"], 0) + 1

    out = {
        "criteria_version": criteria["criteria_version"],
        "generated": date.today().isoformat(),
        "sessions": sessions,
        "total": len(items),
        "counts": counts,
        "items": items,
    }
    path = os.path.join(TOOLS, "vote_triage.json")
    json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(f"母集団 {len(items)} 件(会期 {'/'.join(sessions)})")
    for c in criteria["precedence"]:
        if c in counts:
            print(f"  {c:<11} {counts[c]:>3} 件  {criteria['codes'][c]['name']}")
    for msg in conflicts:
        print("注意:", msg)
    if errors:
        for msg in errors:
            print("エラー:", msg)
        raise SystemExit(1)
    print(f"→ {path}")


if __name__ == "__main__":
    main()
