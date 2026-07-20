# -*- coding: utf-8 -*-
"""参議院 記名投票ページから会派別賛否を抽出（言と行 の「行」データ）"""
import urllib.request, re, json, time

BILLS = [
    ("217-0331-v001", "令和7年度 一般会計予算（修正議決）"),
    ("217-0331-v008", "所得税法等改正案"),
    ("217-0331-v011", "地方交付税法等改正案"),
    ("217-0516-v002", "特別会計法改正案"),
]
BASE = "https://www.sangiin.go.jp/japanese/touhyoulist/217/"

def parse(html_):
    # 会派ブロック: <h4 class="party">名(N名)</h4> ... <dt class="party">賛成票 X 反対票 Y</dt>
    out = {}
    for m in re.finditer(
        r'<h4 class="party">([^<(]+)\(\s*(\d+)\s*名\)</h4>.*?'
        r'<dt class="party">\s*賛成票\s*(\d+)\s*反対票\s*(\d+)', html_, flags=re.S):
        name, n, y, no = m.group(1).strip(), int(m.group(2)), int(m.group(3)), int(m.group(4))
        stance = "賛成" if y > no else ("反対" if no > y else "分裂")
        out[name] = {"n": n, "yes": y, "no": no, "stance": stance}
    return out

def summary(html_):
    m = re.search(r'投票総数\s*(\d+).*?賛成票\s*(\d+).*?反対票\s*(\d+)', re.sub(r'<[^>]+>', ' ', html_), flags=re.S)
    return {"total": int(m.group(1)), "yes": int(m.group(2)), "no": int(m.group(3))} if m else {}

data = {"bills": []}
for bid, label in BILLS:
    raw = urllib.request.urlopen(BASE + bid + ".htm", timeout=30).read().decode("utf-8")
    data["bills"].append({"id": bid, "label": label,
                          "summary": summary(raw), "parties": parse(raw)})
    time.sleep(0.4)

json.dump(data, open("votes_data.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
# コンソール確認（会派短縮）
def short(n):
    for k in ["自由民主党","立憲民主","公明党","日本維新の会","国民民主","日本共産党",
              "れいわ","参政党","社会民主","無所属","各派"]:
        if k in n: return k
    return n
for b in data["bills"]:
    s = b["summary"]
    print(f'\n[{b["label"]}] 賛{s.get("yes")}/否{s.get("no")}')
    for name, v in b["parties"].items():
        print(f'  {short(name):<10} {v["stance"]:<4} (賛{v["yes"]}/否{v["no"]}/{v["n"]}名)')
