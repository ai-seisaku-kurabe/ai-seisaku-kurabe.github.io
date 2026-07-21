# -*- coding: utf-8 -*-
"""⑨文献調査班／「行」がどれだけを覆っているかを測る（audit_rollcall）

Hix, Noury & Roland は、記名投票にかけられる議案の選ばれ方そのものに偏りが乗る
（selection bias in roll call votes）と指摘した。このサイトの「行」は参議院の
記名投票だけでできているので、この指摘は設計の根幹に当たる。

これまでは「記名投票は採決全体の一部です」と<b>程度を示さずに</b>書いていた。
参議院の議案情報は議案ごとに採決方法（押しボタン＝記名／起立／異議なし）を
公表しているので、程度は数えられる。

  ・参議院の本会議で議決された議案のうち、記名投票は何件・何％か
  ・記名投票のうち、賛否が分かれた（多数決）ものと全会一致は何件ずつか
    ＝各党の違いが読み取れる採決は、実際にはもっと少ない
  ・同じ議案を衆議院はどう採決したか（両院の非対称の裏づけ）

材料は fetch_bill_outcomes.py が取った {会期}_bills.json。
出力は state/rollcall_audit.json。research.html はこの数字を流し込む。

使い方:
    cd tools && python agents/audit_rollcall.py
    cd tools && python agents/audit_rollcall.py --print
"""
from __future__ import annotations
import argparse, collections, io, json, os, sys, datetime

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from _sessions import published_sessions   # noqa: E402

OUT_JSON = os.path.join(TOOLS, "state", "rollcall_audit.json")
# 掲載中の会期は build_party.py の sessions_for() が唯一の出どころ。ここに書き持たない。
SESSIONS = published_sessions()

# 「採決方法」欄に現れる値。個人別の賛否が記録に残るのは押しボタン（参議院の電子投票）と
# 記名（木札投票）の2つ。起立と異議の有無は、誰がどう投じたかが残らない。
NAMED = "押しボタン"
NAMED_METHODS = ("押しボタン", "記名")


def summarize(bills, house):
    """本会議で議決された議案を、採決方法・採決態様で数える。"""
    voted = [b for b in bills if (b.get(house) or {}).get("date")]
    method = collections.Counter((b[house].get("method") or "（記載なし）") for b in voted)
    manner = collections.Counter((b[house].get("manner") or "（記載なし）") for b in voted)
    named = [b for b in voted if b[house].get("method") in NAMED_METHODS]
    named_split = collections.Counter((b[house].get("manner") or "（記載なし）") for b in named)
    return {
        "decided": len(voted),
        "by_method": dict(method),
        "by_manner": dict(manner),
        "named": len(named),
        "named_pct": round(len(named) / len(voted) * 100, 1) if voted else None,
        "named_by_manner": dict(named_split),
    }


def crosscheck(session, bills):
    """記名投票の一覧（{会期}_votes.json）と件数が合うかを見る。

    出どころの違う2つの資料が食い違うなら、その差は公表しておく。
    人事案件や決算は資料によって件名の付け方が違うので、完全一致はしない。
    """
    import re, unicodedata
    p = os.path.join(TOOLS, f"{session}_votes.json")
    if not os.path.exists(p):
        return None
    def norm(s):
        s = unicodedata.normalize("NFKC", s)
        return re.sub(r"\s+", "", re.sub(r"\([^)]*\)", "", s)).rstrip("。")
    listed = {norm(b["label"]) for b in json.load(open(p, encoding="utf-8"))["bills"]}
    named = {norm(b["label"]) for b in bills
             if (b.get("sangiin") or {}).get("method") in (NAMED, "記名")}
    return {"vote_list": len(listed), "bill_index": len(named),
            "matched": len(listed & named)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="only_print", action="store_true")
    args = ap.parse_args()

    res = {"generated": datetime.datetime.now().strftime("%Y-%m-%d"), "sessions": {}}
    tot = {"decided": 0, "named": 0, "named_majority": 0, "named_unanimous": 0,
           "shugiin_decided": 0, "shugiin_named": 0}

    for s in SESSIONS:
        p = os.path.join(TOOLS, f"{s}_bills.json")
        if not os.path.exists(p):
            print(f"  （{s}_bills.json が無いので飛ばします。fetch_bill_outcomes.py {s} を実行）")
            continue
        bills = json.load(open(p, encoding="utf-8"))["bills"]
        sg = summarize(bills, "sangiin")
        sh = summarize(bills, "shugiin")
        res["sessions"][s] = {"bills_listed": len(bills), "sangiin": sg, "shugiin": sh,
                              "crosscheck": crosscheck(s, bills)}
        tot["decided"] += sg["decided"]
        tot["named"] += sg["named"]
        tot["named_majority"] += sg["named_by_manner"].get("多数", 0)
        tot["named_unanimous"] += sg["named_by_manner"].get("全会一致", 0)
        tot["shugiin_decided"] += sh["decided"]
        tot["shugiin_named"] += sh["named"]

    if not res["sessions"]:
        raise SystemExit("材料がありません。先に fetch_bill_outcomes.py を実行してください。")

    tot["named_pct"] = round(tot["named"] / tot["decided"] * 100, 1) if tot["decided"] else None
    tot["named_majority_pct"] = (round(tot["named_majority"] / tot["decided"] * 100, 1)
                                 if tot["decided"] else None)
    tot["shugiin_named_pct"] = (round(tot["shugiin_named"] / tot["shugiin_decided"] * 100, 1)
                                if tot["shugiin_decided"] else None)
    res["total"] = tot

    print("■ 参議院 本会議で議決された議案の採決方法")
    for s, v in res["sessions"].items():
        sg = v["sangiin"]
        print(f"  第{s}回: 議決 {sg['decided']}件 ／ 記名（押しボタン） {sg['named']}件"
              f"（{sg['named_pct']}%）")
        print(f"    採決方法の内訳: {sg['by_method']}")
        print(f"    記名のうち: {sg['named_by_manner']}")
    print(f"  {len(res['sessions'])}会期あわせて: 議決 {tot['decided']}件 ／ 記名 {tot['named']}件"
          f"（{tot['named_pct']}%）／ うち賛否が分かれたもの {tot['named_majority']}件"
          f"（{tot['named_majority_pct']}%）")
    print("\n■ 衆議院 本会議（同じ議案の衆議院側）")
    for s, v in res["sessions"].items():
        sh = v["shugiin"]
        print(f"  第{s}回: 議決 {sh['decided']}件 ／ 記名 {sh['named']}件"
              f"（{sh['named_pct']}%）／ 採決方法 {sh['by_method']}")

    if not args.only_print:
        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        io.open(OUT_JSON, "w", encoding="utf-8").write(
            json.dumps(res, ensure_ascii=False, indent=1))
        print("\nwrote", os.path.relpath(OUT_JSON, TOOLS))


if __name__ == "__main__":
    main()
