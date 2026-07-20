# -*- coding: utf-8 -*-
"""更新したページを IndexNow で検索エンジンに通知する。

なぜ必要か:
  このサイトは新規ドメインのため、クローラが来る間隔が長い。ニュースは毎日
  更新されるのに、その事実が伝わるまで数日かかると、内容が古いまま索引される。
  IndexNow は「更新した」とこちら側から知らせる仕組みで、Bing系（ChatGPT の
  取得層を含む）に効く。Google は対応していないので、そちらは sitemap 頼み。

鍵について:
  KEY は秘密情報ではない。<KEY>.txt をサイト直下に置いて公開すること自体が、
  送信者がサイト所有者であることの証明になる（そういう設計の仕組み）。
  したがってリポジトリに含めてよい。

使い方:
    python tools/ping_indexnow.py                      # 既定のページ群を通知
    python tools/ping_indexnow.py news.html index.html # 指定したものだけ
    python tools/ping_indexnow.py --all                # 全ページ
"""
import json, sys, urllib.request, urllib.error

HOST = "ai-seisaku-kurabe.github.io"
KEY = "17b94a7b683221489ce2e2a137ed6a08"
ENDPOINT = "https://api.indexnow.org/indexnow"

# ニュース更新で内容が変わるページ（毎日の通知はこれだけで足りる）
DAILY = ["", "news.html"]

ALL = ["", "guide.html", "oneissue.html", "shindan.html", "news.html",
       "speeches.html", "shukei.html", "about.html", "mynote.html", "feedback.html"]


def ping(paths):
    urls = [f"https://{HOST}/{p}" for p in paths]
    body = json.dumps({
        "host": HOST,
        "key": KEY,
        "keyLocation": f"https://{HOST}/{KEY}.txt",
        "urlList": urls,
    }).encode("utf-8")

    req = urllib.request.Request(
        ENDPOINT, data=body,
        headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        # 422 = 鍵が確認できない / URLがホスト不一致。設定ミスなので黙って流さない
        raise SystemExit(f"IndexNow 送信に失敗しました: {e.code} {e.reason}\n"
                         f"{e.read().decode('utf-8', 'replace')[:300]}")

    # 200=受理, 202=受理(鍵は後で検証)。どちらも成功扱い
    print(f"IndexNow: {code} / {len(urls)} 件を通知しました")
    for u in urls:
        print(f"  {u}")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if "--all" in sys.argv:
        ping(ALL)
    else:
        ping(args or DAILY)
