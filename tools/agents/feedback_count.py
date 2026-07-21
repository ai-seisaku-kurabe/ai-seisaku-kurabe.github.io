# -*- coding: utf-8 -*-
"""ご意見の新着件数だけを数える（本文は取得しない）。

App Check を「適用」にしているため、認証のないクライアントからは Firestore を読めない。
サービスアカウントで REST API の集計クエリ（COUNT）を叩く。

**本文は取得しない。** GitHub Actions のログや成果物に意見の中身が残ると、
非公開にした意味がなくなるため、取得するのは件数だけにする。

総件数の差分では数えない。読んだ意見をコンソールから削除すると総件数が減り、
差分がマイナスになって新着を検知できなくなる。「前回確認した時刻より後に届いた件数」
を数えるので、削除の影響を受けない。

環境変数:
    FIREBASE_SA_KEY   … サービスアカウントのJSON（GitHub Secrets から渡す）
    FIREBASE_PROJECT  … 省略時は 'aipolitics-9c657'

使い方:
    python agents/feedback_count.py            # 数えて state を更新する
    python agents/feedback_count.py --dry-run  # 数えるだけ（state を更新しない）
"""
import datetime, json, os, sys, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, ".."))
PROJECT = os.environ.get("FIREBASE_PROJECT", "aipolitics-9c657")
STATE = os.path.join(TOOLS, "state", "feedback_state.json")


def access_token(sa_json):
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    creds = service_account.Credentials.from_service_account_info(
        json.loads(sa_json), scopes=["https://www.googleapis.com/auth/datastore"])
    creds.refresh(Request())
    return creds.token


def count_since(token, since_iso):
    """since_iso より後に届いた件数を返す。本文は取得しない。"""
    url = (f"https://firestore.googleapis.com/v1/projects/{PROJECT}"
           f"/databases/(default)/documents:runAggregationQuery")
    body = {"structuredAggregationQuery": {
        "structuredQuery": {
            "from": [{"collectionId": "feedback"}],
            "where": {"fieldFilter": {
                "field": {"fieldPath": "at"},
                "op": "GREATER_THAN",
                "value": {"timestampValue": since_iso}}}},
        "aggregations": [{"alias": "n", "count": {}}]}}
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    rows = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    for row in rows:
        r = row.get("result")
        if r:
            return int(r["aggregateFields"]["n"]["integerValue"])
    return 0


def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except Exception:
            pass
    # 初回は7日前を起点にする（全期間だと過去のぶんが一度に新着として出るため）
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    return {"last_checked": since.strftime("%Y-%m-%dT%H:%M:%SZ"), "last_new": 0}


def main():
    dry = "--dry-run" in sys.argv
    sa = os.environ.get("FIREBASE_SA_KEY")
    if not sa:
        raise SystemExit("FIREBASE_SA_KEY が設定されていません（GitHub Secrets を確認）。")

    state = load_state()
    since = state["last_checked"]
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    n = count_since(access_token(sa), since)
    line = (f"ご意見の新着 {n} 件（{since} 以降）" if n
            else f"ご意見の新着はありません（{since} 以降）")
    print(line)
    print("※本文は取得していません。読むには Firebase コンソールを開いてください。")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### " + line + "\n\n本文は取得していません。\n")

    if dry:
        return
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump({"last_checked": now, "last_new": n, "checked_at": now},
              open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"state を更新しました: {STATE}")


if __name__ == "__main__":
    main()
