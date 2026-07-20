# -*- coding: utf-8 -*-
"""集計スナップショットを archive/ に保存する（研究用の保管）。

App Check を「適用」にしているため、認証のないクライアントからは Firestore を
読めない。そこで **読み取り専用のサービスアカウント** で REST API から取得する
（サーバー側の認証情報は App Check の対象外）。

保存するのは回答だけではない。各党の判定(stance)は新しい採決や公約の確認で
変わるため、**設問・判定・その根拠・集計を一式で**残さないと、後から見た人に
数字の意味が復元できない。

環境変数:
    FIREBASE_SA_KEY   … サービスアカウントのJSON（GitHub Secrets から渡す）
    FIREBASE_PROJECT  … 省略時は 'aipolitics-9c657'

使い方:
    python agents/snapshot_archive.py            # archive/YYYY-MM.json を書き出す
    python agents/snapshot_archive.py --dry-run  # 取得して表示するだけ
"""
import datetime, json, os, sys, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, ".."))
ROOT = os.path.abspath(os.path.join(TOOLS, ".."))
PROJECT = os.environ.get("FIREBASE_PROJECT", "aipolitics-9c657")
DOC = "aggregates/summary"


def access_token(sa_json):
    """サービスアカウントから Firestore 読み取り用のアクセストークンを得る。"""
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    creds = service_account.Credentials.from_service_account_info(
        json.loads(sa_json), scopes=["https://www.googleapis.com/auth/datastore"])
    creds.refresh(Request())
    return creds.token


def decode(v):
    """Firestore REST の型付き値を素の値に直す。"""
    if "integerValue" in v: return int(v["integerValue"])
    if "doubleValue" in v:  return v["doubleValue"]
    if "stringValue" in v:  return v["stringValue"]
    if "booleanValue" in v: return v["booleanValue"]
    return None


def fetch_aggregate(token):
    url = (f"https://firestore.googleapis.com/v1/projects/{PROJECT}"
           f"/databases/(default)/documents/{DOC}")
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    doc = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    return {k: decode(v) for k, v in (doc.get("fields") or {}).items()}


def load_questions():
    """設問・stance・判定根拠を取り込む（数字の意味を復元できるようにするため）。"""
    cwd = os.getcwd()
    os.chdir(TOOLS)
    try:
        ns = {}
        exec(open("build_shindan.py", encoding="utf-8").read(), ns)
        return [{"q": q["q"], "kind": q.get("kind", "core"),
                 "basis": q.get("basis", ""), "basis_url": q.get("basis_url", ""),
                 "stance": q["stance"]} for q in ns["POLICY"]]
    finally:
        os.chdir(cwd)


def election_mode():
    p = os.path.join(ROOT, "config.json")
    if not os.path.exists(p):
        return False
    try:
        return bool(json.load(open(p, encoding="utf-8")).get("election_mode"))
    except Exception:
        return False


def main():
    dry = "--dry-run" in sys.argv

    # 選挙期間中は保存しない（公選法138条の3。公開だけでなく取得も止める）
    if election_mode():
        print("election_mode が true のため、スナップショットの保存を行いません。")
        return

    sa = os.environ.get("FIREBASE_SA_KEY")
    if not sa:
        raise SystemExit("FIREBASE_SA_KEY が設定されていません（GitHub Secrets を確認）。")

    agg = fetch_aggregate(access_token(sa))
    snap = {
        "captured_at": datetime.datetime.now(datetime.timezone(
            datetime.timedelta(hours=9))).isoformat(timespec="seconds"),
        "session": "第221回国会",
        "responses": agg.get("responses", 0),
        "questions": load_questions(),
        "aggregate": agg,
        "caveat": "自己選択サンプルであり、世論調査ではありません。"
                  "回答した人の傾向を示すだけの参考値です。",
    }
    print(f"回答数: {snap['responses']} / 設問 {len(snap['questions'])} 問 / "
          f"集計フィールド {len(agg)} 個")
    if dry:
        print(json.dumps(snap, ensure_ascii=False, indent=1)[:600] + " …")
        return

    os.makedirs(os.path.join(ROOT, "archive"), exist_ok=True)
    name = datetime.datetime.now().strftime("%Y-%m") + ".json"
    path = os.path.join(ROOT, "archive", name)
    json.dump(snap, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"archive/{name} を書き出しました。")


if __name__ == "__main__":
    main()
