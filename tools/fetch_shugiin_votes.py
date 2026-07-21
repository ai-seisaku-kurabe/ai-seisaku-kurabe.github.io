# -*- coding: utf-8 -*-
"""②編集班用: 衆議院の記名投票を、会議録から会派別の賛否に組み立てる。

なぜ必要か:
  「衆議院は起立採決で個人別の賛否が残らない」と説明してきたが、これは**起立採決に
  ついては正しく、記名投票については誤り**だった。予算・不信任案などの重要案件は
  記名投票で行われ、会議録に**賛成者と反対者の氏名が全部載る**。
  予算は年に一度の最重要議案なので、この例外は小さくない。

取れるもの・取れないもの:
  - 取れる … 記名投票が行われた議案（掲載3会期では第217回2件・第219回0件・第221回2件）
  - 取れない … 起立採決の議案（大多数）。会議録に「起立多数」としか残らない。
  参議院と違い、衆議院は会派ごとの投票結果を公表していないため、**氏名から党を引く**。
  引けない議員は数えず、人数を開示する（roster.json / build_roster.py と同じ方法）。

使い方:
    python fetch_shugiin_votes.py 221 2026-01-01 2026-07-20
    → 221_shugiin_votes.json
    python fetch_shugiin_votes.py 221 2026-01-01 2026-07-20 --budget-only
"""
import json, os, re, sys, time, urllib.parse, urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_roster as R          # resolve(): 議員名 → 党（会議録の過去ログから逆引き）

API = "https://kokkai.ndl.go.jp/api/meeting"
UA = {"User-Agent": "seisaku-kurabe/1.0 (+https://ai-seisaku-kurabe.github.io)"}
ROSTER = os.path.join(HERE, "roster.json")

# 会議録の記名投票は次の形で載る:
#   〔事務総長報告〕 投票総数 四百五十九 / 可とする者（白票） 三百五十 / 否とする者（青票） 百九
#   <議案名>を可とする議員の氏名  氏名…  否とする議員の氏名  氏名…
HEAD_YES = re.compile(r"(?P<label>[^\r\n]{4,80}?)を可とする議員の氏名")
HEAD_NO = re.compile(r"否とする議員の氏名")
NAME = re.compile(r"([^\s　、。（）\r\n]{1,10}?(?:　+[^\s　、。（）\r\n]{1,10}?)?)君")
KANSUJI = {"〇": 0, "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9}


def kan2int(s):
    """「三百五十一」→ 351。会議録の数字は漢数字で書かれている。"""
    s = re.sub(r"[^〇零一二三四五六七八九十百千]", "", s)
    total, tmp = 0, 0
    for ch in s:
        if ch in KANSUJI:
            tmp = tmp * 10 + KANSUJI[ch] if tmp and ch == "〇" else KANSUJI[ch]
        elif ch == "十":
            total += (tmp or 1) * 10; tmp = 0
        elif ch == "百":
            total += (tmp or 1) * 100; tmp = 0
        elif ch == "千":
            total += (tmp or 1) * 1000; tmp = 0
    return total + tmp


def list_only(seg):
    """氏名の並びだけを残す。

    並びの後ろには議事が続き、そこにも「○議長（森英介君）」「（逢沢一郎君外十一名提出）」
    のように「君」付きの名前が出るため、そのまま拾うと数え過ぎる
    （実測: 109名の並びが221名に、201名の並びが203名になった）。
    氏名の並びに発言記号「○」と区切り記号「◇」は現れないので、先に来た方で切る。
    数え過ぎは main() の検算（党に集計＋無所属＋特定できず＝投票総数）で検出できる。
    """
    ends = [i for i in (seg.find("○"), seg.find("◇")) if i >= 0]
    return seg[:min(ends)] if ends else seg


def names_in(text):
    """氏名の並びを取り出す。「赤羽　　一嘉君」→「赤羽一嘉」。"""
    out = []
    for m in NAME.finditer(text):
        n = re.sub(r"\s+", "", m.group(1))
        if 2 <= len(n) <= 12:
            out.append(n)
    return out


def meetings(house, dfrom, duntil):
    start = 1
    while True:
        q = urllib.parse.urlencode({"nameOfHouse": house, "nameOfMeeting": "本会議",
                                    "from": dfrom, "until": duntil, "recordPacking": "json",
                                    "maximumRecords": 3, "startRecord": start})
        d = json.load(urllib.request.urlopen(
            urllib.request.Request(f"{API}?{q}", headers=UA), timeout=90))
        recs = d.get("meetingRecord", [])
        for m in recs:
            yield m
        if len(recs) < 3 or start + 3 > d.get("numberOfRecords", 0):
            break
        start += 3
        time.sleep(0.4)


def joined(records):
    """会議録を1本の文字列にしつつ、位置から元の発言に戻れる索引も返す。

    憲法3条は「該当箇所への直接リンク」を求める。会議全体のURLでは、
    読者が数万字の中から投票結果を探すことになり、検証可能とは言えない。
    投票結果が載っている発言そのもののURLを付けるために、位置の対応を保つ。
    """
    parts, index, pos = [], [], 0
    for s in records:
        body = s.get("speech") or ""
        parts.append(body)
        index.append((pos, pos + len(body), s))
        pos += len(body) + 1          # "\n" で連結する分
    return "\n".join(parts), index


def record_at(index, pos):
    for a, b, s in index:
        if a <= pos < b:
            return s
    return None


def parse_votes(full, meeting, index=None):
    """1つの会議録から、記名投票の議案をすべて取り出す。"""
    out = []
    heads = list(HEAD_YES.finditer(full))
    for k, h in enumerate(heads):
        label = re.sub(r"\s+", "", h.group("label"))
        end = heads[k + 1].start() if k + 1 < len(heads) else len(full)
        block = full[h.end():end]
        no = HEAD_NO.search(block)
        yes_names = names_in(list_only(block[:no.start()] if no else block))
        no_names = names_in(list_only(block[no.end():])) if no else []

        # 事務総長報告の集計値。抽出が正しいかを突き合わせる材料になる。
        rep = full[:h.start()]
        m = re.search(r"投票総数\s*([〇零一二三四五六七八九十百千]+)[\s\S]{0,80}?"
                      r"可とする者（白票）\s*([〇零一二三四五六七八九十百千]+)[\s\S]{0,80}?"
                      r"否とする者（青票）\s*([〇零一二三四五六七八九十百千]+)", rep[-1200:])
        reported = {"total": kan2int(m.group(1)), "yes": kan2int(m.group(2)),
                    "no": kan2int(m.group(3))} if m else None
        # 憲法3条: 該当箇所への直接リンク。会議全体のURLだと数万字から探させることになる。
        rec = record_at(index, h.start()) if index else None
        out.append({"label": label, "date": meeting["date"],
                    "url": (rec or {}).get("speechURL") or meeting["meetingURL"],
                    "issueID": meeting["issueID"], "yes_names": yes_names,
                    "no_names": no_names, "reported": reported})
    return out


# 投票者の氏名→党の対応。roster.json は「統一会派の議員」を意味する別物なので、
# そちらに混ぜず、この名簿は独立して持つ（開示文の意味が変わってしまうため）。
NAME_ROSTER = os.path.join(HERE, "shugiin_roster.json")


def resolve_party(name, on_date):
    """氏名から、**その投票日時点の**所属党を引く。

    投票日を上限にするのが要点。上限を置かずに引くと、その後に移籍した議員の票を
    移籍先の党に数えてしまう。第217回（2025年3月）の採決を2026年の所属で数えれば、
    採決の記録として事実と違うものになる。
    そこで投票日以前で最も新しい「党名入りの会派」を採る。

    会派名から引けない議員には3種類ある。
      1. 無所属          … 党が無い。どの党にも数えないのが正しい。
      2. 統一会派のみ    … 過去ログが統一会派の下にしかなく、永久に解決しない。
      3. 発言記録が無い  … 新人など。
    ひとまとめに「特定できず」とすると、1が誤りのように見えるので分ける。
    """
    year, floor = int(on_date[:4]), int(R.LOOKBACK_FROM[:4])
    latest_group = None
    while year >= floor:
        until = on_date if year == int(on_date[:4]) else f"{year}-12-31"
        try:
            # 院で絞る。同姓同名が衆参にいるため、絞らないと別人の会派を拾う。
            # 実例: 鬼木誠は衆議院（自由民主党）と参議院（立憲民主党）の両方にいる。
            # 絞らずに引いた結果、衆院の予算採決で立憲が「分かれた」と表示されていた。
            d = R.api(speaker=name, nameOfHouse="衆議院",
                      **{"from": R.LOOKBACK_FROM, "until": until}, maximumRecords=3)
        except Exception:
            return None
        recs = d.get("speechRecord", [])
        if not recs:
            break                     # これ以上遡っても発言が無い
        if latest_group is None:
            latest_group = (recs[0].get("speakerGroup") or "").strip()
        for r in recs:
            p = R.party_of(r.get("speakerGroup"))
            if p:
                return p
        year -= 1                     # まだ統一会派の下。1年前を見る
        time.sleep(0.15)

    # 投票日より後の記録から補うことはしない。
    # 一度は「初当選者が最初に入る会派はその党だから当てずっぽうではない」として
    # 補完を入れたが、⑧査読班（Gemini・ChatGPT）が独立に、憲法6条「データが無い
    # 項目は捏造せず空欄にし、理由を明記」と、憲法4条「引けない議員は数えず、
    # 人数を開示する」に反すると指摘した。そのとおりなので撤去した。
    # 投票日時点の記録で引けない議員は、数えずに人数を開示する。
    if latest_group is None:
        try:
            d = R.api(speaker=name, nameOfHouse="衆議院",
                      **{"from": R.LOOKBACK_FROM, "until": on_date}, maximumRecords=1)
            recs = d.get("speechRecord", [])
            if recs:
                latest_group = (recs[0].get("speakerGroup") or "").strip()
        except Exception:
            pass
    return "無所属" if latest_group == "無所属" else None


def load_roster():
    """「氏名|投票日」→ 党。

    roster.json（統一会派の名簿）はここでは使わない。あちらは日付を持たず
    「今の所属」しか表せないため、過去の採決に当てると移籍を取り違える。
    採決は投票日時点の所属で数える必要がある。
    """
    try:
        # 「@後」は撤去した補完の名残。読み込まない（古い名簿から復活させないため）。
        return {k: v for k, v in json.load(
            open(NAME_ROSTER, encoding="utf-8")).get("members", {}).items()
            if v and not str(v).endswith("@後")}
    except Exception:
        return {}


def save_roster(resolved):
    """引けた分も引けなかった分も残す。次回の照会を省き、結果を検証可能にする。"""
    json.dump({"generated": time.strftime("%Y-%m-%d"),
               "note": "衆議院の記名投票の投票者名から引いた、投票日時点の所属党。"
                       "鍵は「氏名|投票日」。投票日以前で最も新しい党名入り会派を採る。",
               "members": {k: v for k, v in sorted(resolved.items())}},
              open(NAME_ROSTER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def main():
    if len(sys.argv) < 4:
        raise SystemExit("使い方: python fetch_shugiin_votes.py <会期> <from> <until> [--budget-only]")
    session, dfrom, duntil = sys.argv[1], sys.argv[2], sys.argv[3]
    budget_only = "--budget-only" in sys.argv

    bills = []
    for mt in meetings("衆議院", dfrom, duntil):
        full, index = joined(mt.get("speechRecord", []))
        if "可とする議員の氏名" not in full:
            continue
        for b in parse_votes(full, mt, index):
            bills.append(b)
        time.sleep(0.3)

    if budget_only:
        bills = [b for b in bills if "予算" in b["label"] and "決議案" not in b["label"]]

    print(f"第{session}回国会: 記名投票 {len(bills)} 件")
    cache = load_roster()
    resolved, unknown = dict(cache), set()

    out = []
    for b in bills:
        counts, n_indep, n_unknown = {}, 0, 0
        for stance, names in (("賛成", b["yes_names"]), ("反対", b["no_names"])):
            for n in names:
                key = f"{n}|{b['date']}"
                p = resolved.get(key)
                if p is None:
                    p = resolve_party(n, b["date"])
                    resolved[key] = p
                    time.sleep(0.15)
                if not p:
                    unknown.add(n); n_unknown += 1; continue
                if p == "無所属":
                    n_indep += 1; continue        # 党が無いので、どの党にも数えない
                counts.setdefault(p, {"賛成": 0, "反対": 0})[stance] += 1
        for p, c in counts.items():
            c["stance"] = ("賛成" if c["反対"] == 0 else
                           "反対" if c["賛成"] == 0 else "分かれた")
        rep = b["reported"]
        got = sum(c["賛成"] + c["反対"] for c in counts.values())
        # 検算: 党に数えた票 + 無所属 + 特定できず が、会議録の投票総数と一致するか。
        # 一致しなければ、氏名の取りこぼしか数え過ぎがある。
        ok = rep and got + n_indep + n_unknown == rep["total"]
        print(f"  {b['date']} {b['label'][:44]}")
        print(f"    会議録の集計: 総数{rep['total'] if rep else '?'} "
              f"賛成{rep['yes'] if rep else '?'} 反対{rep['no'] if rep else '?'}")
        print(f"    氏名から抽出: 賛成{len(b['yes_names'])} 反対{len(b['no_names'])}")
        print(f"    内訳: 党に集計{got} + 無所属{n_indep} + 特定できず{n_unknown} "
              f"= {got + n_indep + n_unknown}  [{'検算OK' if ok else '検算が合わない'}]")
        out.append({"id": f"{session}-{b['date'].replace('-','')}-{b['issueID'][-3:]}",
                    "label": b["label"], "date": b["date"], "url": b["url"],
                    "parties": counts, "reported": rep, "counted": got,
                    "independent": n_indep, "unidentified": n_unknown,
                    "reconciled": bool(ok),
                    "unresolved": sorted({n for n in b["yes_names"] + b["no_names"]
                                          if not resolved.get(f"{n}|{b['date']}")})})

    save_roster(resolved)
    path = os.path.join(HERE, f"{session}_shugiin_votes.json")
    json.dump({"session": int(session), "house": "衆議院", "bills": out},
              open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"\n{path} を書き出しました")
    if unknown:
        print(f"党を特定できなかった議員: {len(unknown)}名（数えていません）")


if __name__ == "__main__":
    main()
