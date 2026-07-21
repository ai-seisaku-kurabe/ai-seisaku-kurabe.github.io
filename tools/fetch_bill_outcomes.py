# -*- coding: utf-8 -*-
"""参議院の議案情報から、会期の全議案の「本会議でどう採決されたか」を取る。

記名投票（押しボタン）の一覧（fetch_session_votes.py）だけでは、
<b>記名投票にならなかった議案</b>が見えない。つまり「行」がどれだけを覆っているかを
測れない。議案情報の各明細ページには

    参議院本会議経過  議決日 … 議決 可決  採決態様 多数  採決方法 押しボタン

という欄があり、採決方法（押しボタン／起立／異議なし）まで公表されている。
これを会期ぶん集めると、記名投票の割合を数えられる。衆議院側の欄も同じ形なので、
両院の非対称（衆院は起立が原則）も同じ材料で確かめられる。

    python fetch_bill_outcomes.py 217
    → 217_bills.json

取得するのは公表されている事実だけ。解釈も選別もしない（それは編集の仕事）。
"""
import json, re, sys, time, urllib.request

UA = {"User-Agent": "seisaku-kurabe/1.0 (+https://ai-seisaku-kurabe.github.io)"}
BASE = "https://www.sangiin.go.jp/japanese/joho1/kousei/gian/{n}/"
WAIT = 0.4          # 提供元に負荷をかけない間隔（他の取得スクリプトと同じ）


def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")


def flat(html_):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html_)).replace(" ", " ")


def section(text, start, ends):
    i = text.find(start)
    if i < 0:
        return ""
    j = len(text)
    for e in ends:
        k = text.find(e, i + len(start))
        if 0 <= k < j:
            j = k
    return text[i + len(start):j]


def field(sec, name):
    """「議決 可決」のように、見出しの直後の語を取る。空欄なら None。"""
    m = re.search(name + r"\s*([^\s]+)", sec)
    if not m:
        return None
    v = m.group(1).strip()
    return None if v in ("", "議決", "採決態様", "採決方法", "&nbsp;") else v


def parse_bill(html_):
    t = flat(html_)
    body = t[t.find("議案審議情報"):] if "議案審議情報" in t else t
    out = {
        "label": field(body, "件名") or "",
        "kind": field(body, "種別") or "",
    }
    # 件名は空白を含むので、見出し間を取り直す
    m = re.search(r"件名\s*(.+?)\s*種別", body)
    if m:
        out["label"] = m.group(1).strip()
    m = re.search(r"種別\s*(.+?)\s*提出回次", body)
    if m:
        out["kind"] = m.group(1).strip()

    for house, head in (("sangiin", "参議院本会議経過"), ("shugiin", "衆議院本会議経過")):
        sec = section(body, head, ["委員会等経過", "その他", "議案要旨", "本会議経過"])
        out[house] = {
            "date": field(sec, "議決日"),
            "result": field(sec, r"議決(?!日)"),
            "manner": field(sec, "採決態様"),
            "method": field(sec, "採決方法"),
        }
    return out


def main():
    n = sys.argv[1] if len(sys.argv) > 1 else "217"
    base = BASE.format(n=n)
    idx = get(base + "gian.htm")
    links = sorted(set(re.findall(r'href="\./meisai/(m\d+\.htm)"', idx)))
    print(f"第{n}回国会：明細ページ {len(links)} 件")

    bills = []
    for i, ln in enumerate(links, 1):
        try:
            b = parse_bill(get(base + "meisai/" + ln))
        except Exception as e:                      # 1件の失敗で会期全体を落とさない
            print(f"  [{i}/{len(links)}] {ln} 取得失敗: {e}")
            continue
        b["page"] = ln
        bills.append(b)
        if i % 20 == 0 or i == len(links):
            print(f"  [{i}/{len(links)}] 取得済み", flush=True)
        time.sleep(WAIT)

    out = {"session": n, "bills": bills}
    fn = f"{n}_bills.json"
    open(fn, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
    voted = [b for b in bills if b["sangiin"]["date"]]
    print(f"\n{fn} を書き出しました（{len(bills)}件／参院本会議で議決 {len(voted)}件）")


if __name__ == "__main__":
    main()
