# -*- coding: utf-8 -*-
"""各争点のGoogle Newsから見出しを取得し news.json を生成する。
ローカルで手動実行しても、GitHub Actionsで毎日自動実行してもよい（どちらも無料）。
サイトは同一フォルダの news.json を読むだけ（CORSの問題なし）。"""
import urllib.request, urllib.parse, re, json, html, datetime, time

# 診断の設問(POLICY)と同じ順・同じ話題
NEWS_QUERY = ["消費税 減税", "防衛費 増額", "年金制度改革", "GX 脱炭素 政策",
              "憲法改正 緊急事態条項", "財政健全化 プライマリーバランス", "日米同盟 安全保障",
              "原発 再稼働", "外国人 受け入れ 政策", "教育 無償化"]
PER_TOPIC = 3  # 1話題あたりの見出し数

def clean_title(t, src):
    t = html.unescape(t).strip()
    for sep in (" - ", " | ", "｜"):
        if src and t.endswith(sep + src):
            t = t[: -len(sep + src)]
    return t.strip()

def fetch(term):
    q = urllib.parse.quote(term)
    url = f"https://news.google.com/rss/search?q={q}&hl=ja&gl=JP&ceid=JP:ja"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    xml = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    out = []
    for it in re.findall(r"<item>(.*?)</item>", xml, re.S)[:PER_TOPIC]:
        tm = re.search(r"<title>(.*?)</title>", it, re.S)
        lm = re.search(r"<link>(.*?)</link>", it, re.S)
        sm = re.search(r"<source[^>]*>(.*?)</source>", it, re.S)
        src = html.unescape(sm.group(1)).strip() if sm else ""
        if tm and lm:
            out.append({"t": clean_title(tm.group(1), src), "u": lm.group(1).strip(), "s": src})
    return out

# 各政党の政策関連ニュース(政策広報)
PARTY_QUERY = [
    ("jimin", "自民党 政策"), ("rikken", "立憲民主党 政策"), ("ishin", "日本維新の会 政策"),
    ("kokumin", "国民民主党 政策"), ("komei", "公明党 政策"), ("kyosan", "日本共産党 政策"),
    ("reiwa", "れいわ新選組 政策"), ("sansei", "参政党 政策"),
]

topics = {}
for i, term in enumerate(NEWS_QUERY):
    try:
        topics[str(i)] = fetch(term)
    except Exception as e:
        topics[str(i)] = []
        print("WARN topic", i, term, e)
    time.sleep(0.5)

parties = {}
for pid, term in PARTY_QUERY:
    try:
        parties[pid] = fetch(term)
    except Exception as e:
        parties[pid] = []
        print("WARN party", pid, term, e)
    time.sleep(0.5)

data = {"updated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "topics": topics, "parties": parties}
json.dump(data, open("news.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("wrote news.json  topics:", len(topics), " parties:", len(parties),
      " total headlines:", sum(len(v) for v in topics.values()) + sum(len(v) for v in parties.values()))
