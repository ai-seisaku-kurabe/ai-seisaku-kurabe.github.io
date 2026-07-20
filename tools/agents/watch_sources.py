# -*- coding: utf-8 -*-
"""①収集班 — 一次情報に「掲載していない新しいデータ」が出ていないかを見張る。

この班は判断も要約もしない。差分を見つけて知らせるだけ。
サイト最大のリスクは「第217回国会の一断面のまま古びること」なので、
新しい会期・新しい採決・新しい発言が出たことに、人が気づく前に気づくのが仕事。

点検項目:
  1. 参議院の記名投票 … 掲載済み会期より新しい会期に採決記録が出ていないか
  2. 国会会議録     … 掲載データの締め日より後の発言が各会派に蓄積されていないか

使い方:
    python agents/watch_sources.py                 # 差分を報告
    python agents/watch_sources.py --update-state  # 現状を「確認済み」として記録
    python agents/watch_sources.py --fail-on-new   # 新データがあれば異常終了（CI通知用）
"""
import argparse, json, os, re, sys, time
import urllib.error, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
STATE_PATH = os.path.join(HERE, "..", "state", "sources_state.json")
UA = {"User-Agent": "seisaku-kurabe-watch/1.0 (+https://ai-seisaku-kurabe.github.io)"}
SANGIIN = "https://www.sangiin.go.jp/japanese/touhyoulist/{n}/vote_ind.htm"
KOKKAI = "https://kokkai.ndl.go.jp/api/speech"

# 掲載中の会派キー（会議録の speakerGroup 部分一致用）
GROUPS = ["自由民主党", "立憲民主", "日本維新の会", "国民民主", "公明党", "日本共産党", "れいわ"]

DEFAULT_STATE = {
    "covered_session": 217,          # サイトが掲載している会期
    "speech_until": "2025-06-30",    # 掲載データの締め日
    "known_sessions": {"217": 136},  # 会期 -> 記名投票件数
}

def load_state():
    if os.path.exists(STATE_PATH):
        return json.load(open(STATE_PATH, encoding="utf-8"))
    return dict(DEFAULT_STATE)

def save_state(state):
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    json.dump(state, open(STATE_PATH, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "ignore")

# ------------------------------------------------ 1. 参議院 記名投票の新会期
def scan_sessions(start, lookahead=4):
    """掲載会期から先を順に見て、記名投票が存在する会期を拾う。"""
    found = {}
    for n in range(start, start + lookahead + 1):
        try:
            status, html = http_get(SANGIIN.format(n=n))
        except urllib.error.HTTPError:
            continue
        except Exception:
            continue
        if status != 200:
            continue
        bills = set(re.findall(r"(\d{3}-\d{4}-v\d{3})\.htm", html))
        found[str(n)] = len(bills)
        time.sleep(0.3)
    return found

# ---------------------------------------------------- 2. 会議録の新規発言
def count_speeches(group, date_from, date_until):
    q = urllib.parse.urlencode({
        "any": group, "from": date_from, "until": date_until,
        "recordPacking": "json", "maximumRecords": 1,
    })
    try:
        d = json.loads(http_get(f"{KOKKAI}?{q}")[1])
        return int(d.get("numberOfRecords") or 0)
    except Exception:
        return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-state", action="store_true",
                    help="今回の結果を『確認済み』として state に保存する")
    ap.add_argument("--fail-on-new", action="store_true",
                    help="新データがあれば終了コード1（CIで通知したいとき）")
    ap.add_argument("--until", default=None, help="会議録チェックの終端日(既定=今日)")
    a = ap.parse_args()

    import datetime
    until = a.until or datetime.date.today().isoformat()
    state = load_state()
    news = []   # 新しく見つかったもの

    print("①収集班 — 一次情報の差分を確認します\n")

    # 1. 記名投票
    print("[参議院 記名投票]")
    sessions = scan_sessions(int(state["covered_session"]))
    known = {str(k): v for k, v in (state.get("known_sessions") or {}).items()}
    for n, cnt in sorted(sessions.items(), key=lambda x: int(x[0])):
        prev = known.get(n)
        mark = ""
        if int(n) > int(state["covered_session"]) and cnt > 0:
            news.append(f"第{n}回国会に記名投票 {cnt} 件（サイトは第{state['covered_session']}回まで）")
            mark = "  ← 未掲載"
        elif prev is not None and cnt != prev:
            news.append(f"第{n}回国会の記名投票が {prev} → {cnt} 件に増加")
            mark = f"  ← {prev}件から増加"
        print(f"  第{n}回: {cnt} 件{mark}")

    # 2. 会議録
    print(f"\n[国会会議録 {state['speech_until']} より後の発言]")
    after = (datetime.date.fromisoformat(state["speech_until"])
             + datetime.timedelta(days=1)).isoformat()
    total = 0
    for g in GROUPS:
        c = count_speeches(g, after, until)
        if c is None:
            print(f"  {g}: 取得失敗")
            continue
        total += c
        print(f"  {g}: {c:,} 件")
        time.sleep(0.25)
    if total > 0:
        news.append(f"会議録に {after} 以降の発言が計 {total:,} 件（掲載データは {state['speech_until']} まで）")

    # 報告
    print("\n" + "=" * 60)
    if news:
        print("🔔 未掲載の新しい一次情報があります:")
        for n in news:
            print(f"   ・{n}")
        print("\n   → ②編集班の出番です。新会期のデータを取り込み、")
        print("     ルールに沿った下書きPRを作成してください（公開は人の承認後）。")
    else:
        print("✅ 新しい一次情報はありません。掲載内容は最新です。")
    print("=" * 60)

    if a.update_state:
        state["known_sessions"] = {**known, **sessions}
        save_state(state)
        print(f"state を更新しました: {os.path.normpath(STATE_PATH)}")

    sys.exit(1 if (news and a.fail_on_new) else 0)

if __name__ == "__main__":
    main()
