# -*- coding: utf-8 -*-
"""robots.txt と sitemap.xml を生成する。

検索エンジンやAIのクローラに、サイトの存在と構造を知らせるためのファイル。
これが無いと、新しいサイトは見つけてもらえるまで時間がかかる。
build_site.py から呼ばれる（site/ に出力し、deploy_to_repo.py がリポジトリ直下へ配る）。
"""
import datetime
import os

SITE_URL = "https://ai-seisaku-kurabe.github.io"

PAGES = ["", "guide.html", "oneissue.html", "shindan.html", "news.html",
         "speeches.html", "shukei.html", "about.html", "mynote.html", "feedback.html"]


def generate(outdir="site"):
    os.makedirs(outdir, exist_ok=True)

    robots = "\n".join([
        "User-agent: *",
        "Allow: /",
        "",
        f"Sitemap: {SITE_URL}/sitemap.xml",
        "",
    ])
    with open(os.path.join(outdir, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(robots)

    today = datetime.date.today().isoformat()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in PAGES:
        lines.append(f"  <url><loc>{SITE_URL}/{u}</loc><lastmod>{today}</lastmod></url>")
    lines.append("</urlset>")
    lines.append("")
    with open(os.path.join(outdir, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"robots.txt / sitemap.xml を生成しました（{len(PAGES)} ページ）")


if __name__ == "__main__":
    generate()
