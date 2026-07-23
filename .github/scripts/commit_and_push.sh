#!/usr/bin/env bash
# 定期ジョブの成果を main に反映する。
#
# なぜ共通化したか:
#   各ワークフローが「git add → commit → git push」を各自書いていたため、
#   **実行中に別の push で main が動くと push が弾かれ、その回の更新が捨てられていた**。
#   2026-07-23 の update-news が実際にこれで失敗し、その日のニュース更新が失われた
#   （生成もコミットも成功していたのに、push だけが rejected になった）。
#   このリポジトリは複数の作業が並行して main を進めるので、衝突は今後も起きる。
#   直し漏れが出ないよう、反映の手順はこの1本だけを直せばよい形にしている。
#
# 使い方:
#   bash .github/scripts/commit_and_push.sh "<コミットメッセージ>" <パス>...
#
# 変更が無ければ何もせず正常終了する。3回試しても push できなければ異常終了する
# （黙って捨てない＝失敗はジョブの赤として残す）。
set -uo pipefail

if [ "$#" -lt 2 ]; then
  echo "使い方: commit_and_push.sh \"<message>\" <path>..." >&2
  exit 2
fi

msg="$1"; shift
branch="${TARGET_BRANCH:-main}"

git config user.name "github-actions"
git config user.email "actions@github.com"

git add -- "$@"
if git diff --cached --quiet; then
  echo "変更なし。コミットしません。"
  exit 0
fi

git commit -m "$msg" || { echo "コミットに失敗しました" >&2; exit 1; }

for i in 1 2 3; do
  # 先に取り込んでから押す。--autostash は、スクリプトが残した未ステージの
  # 生成物で rebase が止まらないようにするため。
  if git pull --rebase --autostash origin "$branch" && git push origin "HEAD:$branch"; then
    echo "反映しました（$i 回目）。"
    exit 0
  fi
  echo "push が弾かれました（実行中に $branch が動いた可能性）。再試行 $i/3"
  sleep 5
done

echo "3回試しても push できませんでした。成果はコミット済みなので、次回の実行か手動で反映してください。" >&2
exit 1
