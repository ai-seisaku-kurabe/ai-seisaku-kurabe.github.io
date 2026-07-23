# -*- coding: utf-8 -*-
"""選挙期間の停止スイッチ(election_mode)を、日程データから機械的に切り替える。

なぜ機械にやらせるか:
  公職選挙法第138条の3(人気投票の経過・結果の公表禁止)を踏まえて、
  公示日から投票日までは「みんなの結果」の公開を止める運用にしている。
  これまでは人が config.json を手で書き換えていたが、
  **掛け忘れ・戻し忘れが、そのまま法的リスクになる**。

  ここでやるのは日付の比較だけで、判断は一切していない。
  「いつからいつまでが選挙期間か」は tools/election_schedule.json に
  人が一次情報を見て書いた日付であり、このスクリプトはそれを読むだけ。
  期日が入っていなければ、何もしない(勝手に止めも動かしもしない)。

使い方:
    python agents/sync_election_mode.py            # 必要なら config.json を書き換える
    python agents/sync_election_mode.py --check    # 食い違っていたら異常終了(検証用)
    python agents/sync_election_mode.py --date 2028-07-05   # その日だとどうなるかを試す
"""
import argparse, datetime, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(TOOLS, ".."))
SCHEDULE = os.path.join(TOOLS, "election_schedule.json")
CONFIG = os.path.join(ROOT, "config.json")
JST = datetime.timezone(datetime.timedelta(hours=9))


def today_jst():
    return datetime.datetime.now(JST).date()


def parse(d):
    return datetime.date.fromisoformat(d) if d else None


def load_schedule():
    return json.load(open(SCHEDULE, encoding="utf-8"))


def active_election(schedule, today):
    """今日が選挙期間(公示日〜投票日)に入っている選挙を返す。無ければ None。

    公示日だけが分かっていて投票日が未記入のときは「期間中」とみなす。
    止めすぎる側に倒すのは、止め忘れの方が取り返しがつかないため。
    """
    for e in schedule.get("elections", []):
        koji, vote = parse(e.get("koji")), parse(e.get("vote"))
        if not koji or today < koji:
            continue
        if vote is None or today <= vote:
            return e
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="書き換えず、食い違っていたら異常終了する")
    ap.add_argument("--date", help="この日付だとどうなるかを試す(YYYY-MM-DD)")
    a = ap.parse_args()

    today = parse(a.date) if a.date else today_jst()
    schedule = load_schedule()
    hit = active_election(schedule, today)
    want = hit is not None

    cfg = json.load(open(CONFIG, encoding="utf-8"))
    now = bool(cfg.get("election_mode"))

    where = f"（{hit['name']}／公示 {hit.get('koji')}・投票 {hit.get('vote') or '未記入'}）" if hit else ""
    print(f"{today} 時点: election_mode は {want} であるべき{where}／config.json は {now}")

    if want == now:
        print("  一致しています。変更はありません。")
        return 0

    if a.check:
        print("  ❌ 食い違っています。python agents/sync_election_mode.py を実行してください。")
        return 1

    cfg["election_mode"] = want
    # 既存のキー順と体裁を保つため、json.dump のまま書き戻す(手で書いた注記も残る)。
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"  config.json の election_mode を {now} → {want} に変更しました。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
