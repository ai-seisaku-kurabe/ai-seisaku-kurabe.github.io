# -*- coding: utf-8 -*-
"""各争点・各党のGoogle Newsから見出しを取得する。

出力は2つ:
  news.json         … 直近の見出し（各設問・各党ページに表示する分。従来どおり）
  news_archive.json … 蓄積アーカイブ。政策分野タグを付け、政策と無関係な見出しは捨てる。

GitHub Actions で毎日自動実行される（.github/workflows/news.yml）。
見出し・出典・リンクのみを扱い、本文は一切転載しない。
"""
import urllib.request, urllib.parse, re, json, html, datetime, time, os

# 「政策で照らす」の設問(POLICY)と同じ順・同じ話題
NEWS_QUERY = ["消費税 減税", "防衛費 増額", "年金制度改革", "GX 脱炭素 政策",
              "憲法改正 緊急事態条項", "財政健全化 プライマリーバランス", "日米同盟 安全保障",
              "原発 再稼働", "外国人 受け入れ 政策", "教育 無償化"]

PARTY_QUERY = [
    ("jimin", "自民党 政策"), ("rikken", "立憲民主党 政策"), ("ishin", "日本維新の会 政策"),
    ("kokumin", "国民民主党 政策"), ("komei", "公明党 政策"), ("kyosan", "日本共産党 政策"),
    ("reiwa", "れいわ新選組 政策"), ("sansei", "参政党 政策"),
]
PARTY_NAME = {"jimin": "自民", "rikken": "立憲", "ishin": "維新", "kokumin": "国民",
              "komei": "公明", "kyosan": "共産", "reiwa": "れいわ", "sansei": "参政"}

PER_TOPIC = 3     # news.json（各ページ表示用）に載せる件数
PER_FETCH = 8     # 取得件数。余りはアーカイブにだけ入れる

# ---- 政策分野タグ（サイトの6分野と揃える。ここに当たらない見出しは蓄積しない） ----
DOMAIN_KEYWORDS = {
    "財政": ["消費税", "増税", "減税", "税制", "国債", "財政", "歳出", "歳入", "予算",
             "プライマリーバランス", "インボイス", "補正予算", "税収", "給付金"],
    "外交・安保": ["防衛", "安全保障", "自衛隊", "米軍", "日米", "外交", "北朝鮮", "ミサイル",
                   "台湾", "ウクライナ", "条約", "同盟", "中国", "ロシア", "有事", "抑止"],
    "社会保障": ["年金", "医療", "介護", "子育て", "少子化", "保険", "福祉", "生活保護",
                 "高齢者", "児童手当", "出産", "待機児童", "障害者", "社会保障"],
    "エネルギー・環境": ["原発", "原子力", "再稼働", "再エネ", "再生可能エネルギー", "脱炭素",
                         "電力", "気候", "環境", "GX", "カーボン", "電気料金", "太陽光"],
    "経済・産業": ["賃上げ", "物価", "景気", "雇用", "中小企業", "産業", "投資", "円安",
                   "最低賃金", "労働", "経済対策", "半導体", "農業", "手取り"],
    "憲法": ["憲法", "改憲", "九条", "緊急事態条項", "国民投票", "憲法審査会"],
}

KEEP_DAYS = 180    # これより古い見出しはアーカイブから落とす
MAX_ITEMS = 900    # 上限（静的配信なのでファイルを太らせない）
ARCHIVE_PATH = "news_archive.json"


def clean_title(t, src):
    t = html.unescape(t).strip()
    for sep in (" - ", " | ", "｜"):
        if src and t.endswith(sep + src):
            t = t[: -len(sep + src)]
    return t.strip()


def fetch(term, n=PER_FETCH):
    q = urllib.parse.quote(term)
    url = f"https://news.google.com/rss/search?q={q}&hl=ja&gl=JP&ceid=JP:ja"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    xml = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    out = []
    for it in re.findall(r"<item>(.*?)</item>", xml, re.S)[:n]:
        tm = re.search(r"<title>(.*?)</title>", it, re.S)
        lm = re.search(r"<link>(.*?)</link>", it, re.S)
        sm = re.search(r"<source[^>]*>(.*?)</source>", it, re.S)
        src = html.unescape(sm.group(1)).strip() if sm else ""
        if tm and lm:
            out.append({"t": clean_title(tm.group(1), src), "u": lm.group(1).strip(), "s": src})
    return out


def tag_domains(title):
    """見出しから政策分野を判定する。1つも当たらなければ「政策と無関係」とみなす。"""
    return [d for d, kws in DOMAIN_KEYWORDS.items() if any(k in title for k in kws)]


def load_archive():
    if os.path.exists(ARCHIVE_PATH):
        try:
            return json.load(open(ARCHIVE_PATH, encoding="utf-8")).get("items", [])
        except Exception as e:
            print("WARN archive load:", e)
    return []


def main():
    today = datetime.date.today().isoformat()
    collected = []   # アーカイブ候補

    topics = {}
    for i, term in enumerate(NEWS_QUERY):
        try:
            items = fetch(term)
        except Exception as e:
            items = []; print("WARN topic", i, term, e)
        topics[str(i)] = [{k: v for k, v in x.items()} for x in items[:PER_TOPIC]]
        for x in items:
            collected.append({**x, "topic": term, "party": None})
        time.sleep(0.5)

    parties = {}
    for pid, term in PARTY_QUERY:
        try:
            items = fetch(term)
        except Exception as e:
            items = []; print("WARN party", pid, term, e)
        parties[pid] = [{k: v for k, v in x.items()} for x in items[:PER_TOPIC]]
        for x in items:
            collected.append({**x, "topic": None, "party": pid})
        time.sleep(0.5)

    # 従来どおりの表示用
    json.dump({"updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
               "topics": topics, "parties": parties},
              open("news.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("wrote news.json  headlines:",
          sum(len(v) for v in topics.values()) + sum(len(v) for v in parties.values()))

    # ---- アーカイブ（タグ付け＋無関係を除外＋重複排除＋古いものを整理） ----
    archive = load_archive()
    by_url = {it["u"]: it for it in archive}
    added = skipped = 0
    for c in collected:
        doms = tag_domains(c["t"])
        if not doms:            # 政策と関係ない見出しは蓄積しない
            skipped += 1; continue
        u = c["u"]
        if u in by_url:         # 既出。分野タグと党だけ育てる
            ex = by_url[u]
            ex["d"] = sorted(set(ex.get("d", [])) | set(doms))
            if c["party"] and c["party"] not in (ex.get("p") or []):
                ex["p"] = sorted(set(ex.get("p") or []) | {c["party"]})
            continue
        by_url[u] = {"t": c["t"], "u": u, "s": c["s"], "d": doms,
                     "p": [c["party"]] if c["party"] else [], "date": today}
        added += 1

    items = list(by_url.values())
    limit = (datetime.date.today() - datetime.timedelta(days=KEEP_DAYS)).isoformat()
    items = [x for x in items if x.get("date", today) >= limit]
    items.sort(key=lambda x: (x.get("date", ""), x.get("t", "")), reverse=True)
    items = items[:MAX_ITEMS]

    json.dump({"updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
               "domains": list(DOMAIN_KEYWORDS.keys()),
               "parties": PARTY_NAME, "items": items},
              open(ARCHIVE_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {ARCHIVE_PATH}  total:{len(items)} (+{added} 新規 / {skipped} 件は政策と無関係で除外)")


if __name__ == "__main__":
    main()
