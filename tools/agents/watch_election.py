# -*- coding: utf-8 -*-
"""①収集班 — 次の国政選挙の日程が動いていないかを見張る。

この班は判断も要約もしない。**日付をここから書き込むこともしない。**
気づいて知らせるだけで、tools/election_schedule.json に期日を書くのは人の仕事。
理由は、選挙期日を1日読み違えたまま公開すると、
(a) サイトが事実の誤りを載せ、(b) election_mode の切替まで誤作動するため。
機械が拾った日付をそのまま公開に通す設計にはしない。

見るもの:
  1. 期限（通信なし・絶対に見落とさない線）
     掲載中の任期満了日と公職選挙法の定めから、
     「この日を過ぎて期日が未記入なのはおかしい」を機械的に判定する。
  2. 参議院「参議院議員通常選挙一覧」（一次情報）
     掲載中の任期満了日がこの表と一致するかを毎回照合し、
     新しい回次の行が増えていれば知らせる。
  3. 総務省の報道資料・選挙のページ
     選挙期日に関わる新しい見出し・リンクが出ていないかを見る。
     ここは取りこぼさない側に倒してあるので、空振り（選挙と無関係な新着）もある。
     空振りの害は「CIが赤くなる」だけで、見落としの害より小さい。

使い方:
    python agents/watch_election.py                 # 差分を報告
    python agents/watch_election.py --update-state  # 現状を「確認済み」として記録
    python agents/watch_election.py --fail-on-new   # 新しい動きがあれば異常終了（CI用）
    python agents/watch_election.py --offline       # 期限の点検だけ行う
"""
import argparse, datetime, json, os, re, sys, urllib.error, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, ".."))
SCHEDULE = os.path.join(TOOLS, "election_schedule.json")
STATE_PATH = os.path.join(TOOLS, "state", "election_state.json")
UA = {"User-Agent": "seisaku-kurabe-watch/1.0 (+https://ai-seisaku-kurabe.github.io)"}
JST = datetime.timezone(datetime.timedelta(hours=9))

SANGIIN_LIST = "https://www.sangiin.go.jp/japanese/san60/s60_shiryou/senkyoichiran.htm"
SOUMU_PAGES = [
    # 解散・選挙期日は、まずここに報道資料として出る（当月分の一覧）。
    ("総務省 報道資料一覧", "https://www.soumu.go.jp/menu_news/s-news/index.html"),
    # 選挙が行われると、この一覧に新しい回次が並ぶ（事後の裏取り）。
    ("総務省 選挙の結果", "https://www.soumu.go.jp/senkyo/senkyo_s/data/index.html"),
]
# 選挙期日に関わりうる見出しだけを拾う。広めに取り、精度は人が担保する。
KEYWORDS = ("総選挙", "通常選挙", "選挙期日", "衆議院議員選挙", "参議院議員選挙", "解散")

# 公職選挙法第32条: 通常選挙は任期が終わる日の前30日以内。期日は少なくとも17日前に公示。
SANGIIN_WINDOW_DAYS = 30
SANGIIN_KOJI_DAYS = 17

notes = []      # 人に知らせること（新しい動き）
problems = []   # 掲載が古い・食い違っている（放置できない）


def parse(d):
    return datetime.date.fromisoformat(d) if d else None


def today_jst():
    return datetime.datetime.now(JST).date()


def load_state():
    if os.path.exists(STATE_PATH):
        return json.load(open(STATE_PATH, encoding="utf-8"))
    return {"seen_headlines": [], "sangiin_rows": [], "checked": None}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    json.dump(state, open(STATE_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def http_get(url, encoding=None):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        raw = r.read()
    if encoding:
        return raw.decode(encoding, "ignore")
    ct = r.headers.get("Content-Type", "") if hasattr(r, "headers") else ""
    m = re.search(r"charset=([\w-]+)", ct, re.I) or \
        re.search(rb"charset=[\"']?([\w-]+)", raw[:3000], re.I)
    enc = m.group(1) if m else "utf-8"
    if isinstance(enc, bytes):
        enc = enc.decode()
    return raw.decode(enc, "ignore")


# --------------------------------------------------- 1. 期限（通信なし）
def check_deadlines(schedule, today):
    for e in schedule.get("elections", []):
        name = e.get("name", e.get("id"))
        koji, vote, term_end = parse(e.get("koji")), parse(e.get("vote")), parse(e.get("term_end"))

        if vote and vote < today:
            problems.append(f"{name}: 投票日({vote})が過ぎています。"
                            "次の選挙の枠に書き換えてください（election_schedule.json）")
            continue
        if term_end and term_end < today and not vote:
            problems.append(f"{name}: 任期満了日({term_end})を過ぎているのに期日が未記入です。"
                            "掲載が古くなっています")
            continue
        if e.get("house") != "参議院" or vote or not term_end:
            continue
        # 参議院の通常選挙は実施の窓が法律で決まっているので、そこから逆算できる。
        latest_vote = term_end - datetime.timedelta(days=SANGIIN_WINDOW_DAYS)
        latest_koji = latest_vote - datetime.timedelta(days=SANGIIN_KOJI_DAYS)
        if today >= latest_vote:
            problems.append(
                f"{name}: 公職選挙法第32条第1項の期間（{latest_vote}〜{term_end}）に入っているのに"
                "投票日が未記入です。一次情報を確認して election_schedule.json に書いてください")
        elif today >= latest_koji and not koji:
            notes.append(
                f"{name}: 遅くとも {latest_koji} ごろには期日が公示されます"
                "（同条第3項＝17日前まで）。総務省の告示を確認してください")


# ------------------------------------- 2. 参議院の一覧と任期満了日を照合する
WAREKI = {"令和": 2018, "平成": 1988, "昭和": 1925}


def to_iso(wareki_date):
    m = re.match(r"(令和|平成|昭和)(元|\d+)年(\d+)月(\d+)日", wareki_date)
    if not m:
        return None
    era, y, mo, d = m.groups()
    year = WAREKI[era] + (1 if y == "元" else int(y))
    return f"{year:04d}-{int(mo):02d}-{int(d):02d}"


def scan_sangiin(schedule, state):
    html = http_get(SANGIIN_LIST)
    text = re.sub(r"<[^>]+>", "|", html)
    rows = re.findall(
        r"第([０-９0-9]+)回\|+((?:令和|平成|昭和)[元\d]+年\d+月\d+日)\|+"
        r"((?:令和|平成|昭和)[元\d]+年\d+月\d+日)\|+((?:令和|平成|昭和)[元\d]+年\d+月\d+日)",
        re.sub(r"\s+", "", text))
    if not rows:
        problems.append("参議院の通常選挙一覧を読めませんでした（表の形が変わった可能性）")
        return
    zen = str.maketrans("０１２３４５６７８９", "0123456789")
    parsed = [{"kai": int(k.translate(zen)), "vote": to_iso(v),
               "term_start": to_iso(s), "term_end": to_iso(t)} for k, v, s, t in rows]
    term_ends = {r["term_end"] for r in parsed}

    # 掲載している任期満了日が、一次情報の表に存在するか（毎回の裏取り）
    for e in schedule.get("elections", []):
        if e.get("house") == "参議院" and e.get("term_end") not in term_ends:
            problems.append(
                f"{e.get('name')}: 掲載している任期満了日 {e.get('term_end')} が"
                "参議院の一覧に見当たりません。出典を確認してください")

    latest = max(parsed, key=lambda r: r["kai"])
    known = state.get("sangiin_rows", [])
    known_kai = max([r.get("kai", 0) for r in known], default=0)
    if latest["kai"] > known_kai:
        notes.append(f"参議院の一覧に第{latest['kai']}回が現れました"
                     f"（選挙期日 {latest['vote']}／任期満了 {latest['term_end']}）。"
                     "election_schedule.json の更新が要ります")
    state["sangiin_rows"] = parsed[-3:]
    print(f"  参議院の一覧: 第{latest['kai']}回まで（任期満了日 {len(term_ends)} 件を照合）")


# ------------------------------------------- 3. 総務省に新しい見出しが出たか
def scan_soumu(state):
    seen = set(state.get("seen_headlines", []))
    found = []
    for label, url in SOUMU_PAGES:
        try:
            html = http_get(url, encoding="cp932")
        except Exception as exc:
            notes.append(f"{label}: 取得できませんでした（{exc}）")
            continue
        for href, inner in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
            txt = re.sub(r"<[^>]+>", "", inner).strip()
            txt = re.sub(r"\s+", " ", txt)
            if len(txt) < 5 or not any(k in txt for k in KEYWORDS):
                continue
            found.append(f"{txt} <{urllib.parse.urljoin(url, href)}>")
    fresh = [f for f in dict.fromkeys(found) if f not in seen]
    for f in fresh:
        notes.append(f"総務省に選挙関連の見出しがあります（新規）: {f}")
    state["seen_headlines"] = sorted(seen | set(found))
    print(f"  総務省: 選挙関連の見出し {len(set(found))} 件（うち新規 {len(fresh)} 件）")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-state", action="store_true", help="現状を確認済みとして記録する")
    ap.add_argument("--fail-on-new", action="store_true", help="新しい動きがあれば異常終了する")
    ap.add_argument("--offline", action="store_true", help="通信を伴う点検を省く")
    ap.add_argument("--date", help="この日付として点検する(YYYY-MM-DD)")
    a = ap.parse_args()

    schedule = json.load(open(SCHEDULE, encoding="utf-8"))
    state = load_state()
    today = parse(a.date) if a.date else today_jst()

    print(f"①収集班 — 次の国政選挙の日程を点検します（{today} 時点）\n")
    for e in schedule.get("elections", []):
        status = f"投票 {e['vote']}" if e.get("vote") else "期日未定"
        print(f"  掲載中: {e.get('name')} … {status}／任期満了 {e.get('term_end')}")
    print()

    check_deadlines(schedule, today)
    if not a.offline:
        scan_sangiin(schedule, state)
        scan_soumu(state)
    else:
        print("  [--offline のため 一次情報の照合は省略]")

    print("\n" + "=" * 60)
    for p in problems:
        print(f"❌ {p}")
    for n in notes:
        print(f"🔔 {n}")
    if not problems and not notes:
        print("✅ 新しい動きはありません。掲載中の日程は一次情報と一致しています。")
    print("=" * 60)

    if a.update_state:
        state["checked"] = today.isoformat()
        save_state(state)
        print("現状を確認済みとして記録しました。")

    if problems:
        return 1
    if a.fail_on_new and notes:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
