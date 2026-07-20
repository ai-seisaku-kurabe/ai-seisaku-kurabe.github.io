# -*- coding: utf-8 -*-
"""生成した site/*.html だけをリポジトリ直下へ反映する（安全な配布）。

なぜ専用スクリプトが必要か:
  build_site.py は firebase.js を「プレースホルダ版」で生成する。
  それをリポジトリに配ると本番のFirebase設定(apiKey/appId)が消え、
  集計もApp Checkも壊れる。news.json も GitHub Actions が自動更新するので
  ローカルのスナップショットで上書きしてはいけない。
  → このスクリプトは *.html 以外を一切コピーしないことで、事故を構造的に防ぐ。

使い方:
    python build_site.py        # site/ を生成
    python deploy_to_repo.py    # site/*.html だけを ../ へコピー
    cd .. && git diff           # 差分を確認してからコミット
"""
import os, shutil, filecmp

HERE = os.path.dirname(os.path.abspath(__file__))
SRC  = os.path.join(HERE, "site")
DEST = os.path.abspath(os.path.join(HERE, ".."))

# 絶対に配布しないファイル（本番設定・自動更新対象）
NEVER_COPY = {"firebase.js", "news.json", "firestore.rules"}

def main():
    if not os.path.isdir(SRC):
        raise SystemExit("site/ がありません。先に `python build_site.py` を実行してください。")

    changed, same, skipped = [], [], []
    for name in sorted(os.listdir(SRC)):
        if name in NEVER_COPY:
            skipped.append(name); continue
        if not name.endswith(".html"):
            skipped.append(name); continue
        s, d = os.path.join(SRC, name), os.path.join(DEST, name)
        if os.path.exists(d) and filecmp.cmp(s, d, shallow=False):
            same.append(name); continue
        shutil.copy2(s, d)
        changed.append(name)

    print("反映しました:", ", ".join(changed) if changed else "(変更なし)")
    print("変更なし    :", len(same), "件")
    print("配布しない  :", ", ".join(skipped) if skipped else "(なし)")
    print("\n次: cd .. && git diff で差分を確認してからコミットしてください。")
    print("※ firebase.js / news.json は意図的にコピーしていません。")

if __name__ == "__main__":
    main()
