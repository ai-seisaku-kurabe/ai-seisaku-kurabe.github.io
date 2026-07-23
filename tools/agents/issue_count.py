# -*- coding: utf-8 -*-
"""⑥運用班: GitHub の Issue / Pull Request の未対応件数を数える。

**なぜ必要か。** サイトは「掲載のしかたについて削除・訂正のご要望がある場合は、
Issue かリポジトリ経由でお知らせください。確認のうえ対応します」と案内している。
ところが定期確認があったのはご意見フォーム（Firestore）だけで、Issue の側は
GitHub の通知に気づけるかどうかに委ねられていた。権利に関する申出という
いちばん時間に敏感な窓口だけ機械の監視が無い、という約束と実態のずれだったので、
ご意見フォームと同じ頻度で数える。

**数えるのは件数と番号だけ。** 表題や本文は取得しない。Issue は公開情報だが、
第三者が書いた文をリポジトリの state に写して増やす必要はない。件数が動けば
人が GitHub を見にいく、という合図として使えれば足りる。

未対応 = open の Issue と Pull Request。閉じられたものは扱いが済んだとみなす。
「前回確認した時刻より後に作られた件数」も併せて記録する（すぐ閉じられた申出も
履歴に残るようにするため）。

環境変数:
    GITHUB_REPOSITORY … "owner/repo"（Actions が自動で入れる。省略時は本リポジトリ）
    GITHUB_TOKEN      … あれば認証付きで叩く（レート制限を避けるためだけ。公開
                        リポジトリなので無くても動く）

使い方:
    python agents/issue_count.py            # 数えて state を更新する
    python agents/issue_count.py --dry-run  # 数えるだけ（state を更新しない）
"""
import datetime, json, os, sys, urllib.error, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, ".."))
REPO = os.environ.get("GITHUB_REPOSITORY") or "ai-seisaku-kurabe/ai-seisaku-kurabe.github.io"
STATE = os.path.join(TOOLS, "state", "issue_state.json")
API = "https://api.github.com"


def get(path):
    req = urllib.request.Request(
        API + path,
        headers={"Accept": "application/vnd.github+json",
                 "User-Agent": "ai-seisaku-kurabe-issue-count"})
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        return json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        # 失敗は握りつぶさない。⑥運用班は「知らせるだけ」だが、黙って0件を返すと
        # 「未対応なし」と区別がつかず、監視が無いのと同じになる。
        raise SystemExit(f"GitHub API が {e.code} を返した（{path}）: {e.reason}")


def split(items):
    """Issue と Pull Request を分ける（/issues は PR も返す）。"""
    issues = [i for i in items if "pull_request" not in i]
    prs = [i for i in items if "pull_request" in i]
    return issues, prs


def load_state():
    if os.path.exists(STATE):
        try:
            data = json.load(open(STATE, encoding="utf-8"))
            if isinstance(data.get("last_checked"), str):
                return data
        except Exception:
            pass
    # 初回（または壊れた state）は7日前を起点にする。feedback_count.py と同じ扱い。
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    return {"last_checked": since.strftime("%Y-%m-%dT%H:%M:%SZ")}


def main():
    dry = "--dry-run" in sys.argv
    state = load_state()
    since = state["last_checked"]
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    open_items = get(f"/repos/{REPO}/issues?state=open&per_page=100")
    open_issues, open_prs = split(open_items)

    # 新着は作成日時で数える（sort=created の降順なので、前回時刻より古いものが出たら打ち切る）。
    recent = get(f"/repos/{REPO}/issues?state=all&sort=created&direction=desc&per_page=100")
    new_items = []
    for it in recent:
        if it.get("created_at", "") <= since:
            break
        new_items.append(it)
    new_issues, new_prs = split(new_items)

    line = (f"未対応 Issue {len(open_issues)} 件 / PR {len(open_prs)} 件"
            f"（{since} 以降の新着: Issue {len(new_issues)} 件 / PR {len(new_prs)} 件）")
    print(line)
    print("※表題・本文は取得していません。中身は GitHub で確認してください。")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### " + line + "\n\n表題・本文は取得していません。\n")

    if dry:
        return
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump({"last_checked": now,
               "open_issues": len(open_issues),
               "open_prs": len(open_prs),
               "open_numbers": sorted(i["number"] for i in open_items),
               "new_since_last": len(new_items),
               "checked_at": now},
              open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"state を更新しました: {STATE}")


if __name__ == "__main__":
    main()
