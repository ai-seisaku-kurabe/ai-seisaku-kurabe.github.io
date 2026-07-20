# -*- coding: utf-8 -*-
"""参議院の記名投票を「会期まるごと」取得する（②編集班が新会期を足すときの入口）。

fetch_votes.py は第217回の4法案を手書きで指定していたが、
新会期を取り込むには一覧から全件を拾う必要があるためこちらを使う。

    python fetch_session_votes.py 219
    → 219_votes.json （bills[] に id/label/date/summary/parties）

取得するのは会派別の賛成票・反対票のみ。解釈も選別もしない（それは編集の仕事）。
"""
import json, re, sys, time, urllib.request

UA = {"User-Agent": "seisaku-kurabe/1.0 (+https://tsuruwa2.netlify.app)"}
BASE = "https://www.sangiin.go.jp/japanese/touhyoulist/{n}/"


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def bill_list(n):
    """一覧ページから (議案ID, 案件名) を順に拾う。"""
    html_ = get(BASE.format(n=n) + "vote_ind.htm")
    out, seen = [], set()
    for href, bid, txt in re.findall(
            r'<a[^>]+href="([^"]*?(\d{3}-\d{4}-v\d{3})\.htm)"[^>]*>(.*?)</a>',
            html_, re.S | re.I):
        if bid in seen:
            continue
        seen.add(bid)
        label = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", txt)).strip()
        label = re.sub(r"^日程第[０-９0-9一二三四五六七八九十]+\s*", "", label)  # 「日程第１　」を落とす
        out.append((bid, label))
    return out


def parse_parties(html_):
    out = {}
    for m in re.finditer(
            r'<h4 class="party">([^<(]+)\(\s*(\d+)\s*名\)</h4>.*?'
            r'<dt class="party">\s*賛成票\s*(\d+)\s*反対票\s*(\d+)', html_, flags=re.S):
        name, n, y, no = m.group(1).strip(), int(m.group(2)), int(m.group(3)), int(m.group(4))
        out[name] = {"n": n, "yes": y, "no": no,
                     "stance": "賛成" if y > no else ("反対" if no > y else "分裂")}
    return out


def parse_summary(html_):
    m = re.search(r"投票総数\s*(\d+).*?賛成票\s*(\d+).*?反対票\s*(\d+)",
                  re.sub(r"<[^>]+>", " ", html_), flags=re.S)
    return {"total": int(m.group(1)), "yes": int(m.group(2)), "no": int(m.group(3))} if m else {}


def main():
    if len(sys.argv) < 2:
        raise SystemExit("使い方: python fetch_session_votes.py <会期番号>")
    n = sys.argv[1]
    bills = bill_list(n)
    print(f"第{n}回国会: 記名投票 {len(bills)} 件を取得します")
    data = {"session": int(n), "bills": []}
    for i, (bid, label) in enumerate(bills, 1):
        try:
            raw = get(BASE.format(n=n) + bid + ".htm")
        except Exception as e:
            print(f"  [{i}/{len(bills)}] {bid} 取得失敗: {e}")
            continue
        m = re.match(r"\d{3}-(\d{2})(\d{2})-", bid)
        data["bills"].append({
            "id": bid, "label": label,
            "date": f"{m.group(1)}/{m.group(2)}" if m else "",
            "summary": parse_summary(raw), "parties": parse_parties(raw),
        })
        if i % 10 == 0 or i == len(bills):
            print(f"  [{i}/{len(bills)}] 取得済み")
        time.sleep(0.4)

    out = f"{n}_votes.json"
    json.dump(data, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    ok = sum(1 for b in data["bills"] if b["parties"])
    print(f"\n{out} を書き出しました（会派別賛否を取得できたのは {ok}/{len(data['bills'])} 件）")


if __name__ == "__main__":
    main()
