# -*- coding: utf-8 -*-
"""統一会派に属する議員の所属政党を、会議録APIの過去ログから逆引きする。

なぜ必要か:
  発言の党判定は会派名の文字列一致で行っている。ところが衆議院には党名を含まない
  統一会派があり（例: 「中道改革連合・無所属」＝立憲民主党・公明党など）、そこに
  属する議員の発言は一件も拾えていなかった。立憲と公明の「言」が参議院のものだけ
  になるという、利用者から見えない偏りが生じていた。

なぜ会議録APIから引くのか:
  衆議院の公式議員一覧は「会派」しか載せておらず（赤羽一嘉も有田芳生も「中道」）、
  党を判別できない。各党の公式サイトは議員名をJavaScriptで描画しており、初期HTMLに
  存在しない。一方、議員は会派が変わっても発言記録は残るため、**同じ議員の過去の
  発言に付いている会派名**を読めば所属党が分かる。すでに引用元として信頼している
  一次情報だけで完結し、外部サイトの改装で壊れない。

設計上の判断:
  - 遡及は広く取り、**日付の降順**で最初に見つかった党名入り会派を採る。
    期間を絞ると精度は上がらずカバレッジだけ落ちる（実測: 2024-10以降に絞ると
    42/44 → 38/44。伊佐進一・國重徹・山本香苗・笠浩史が判定不能になった）。
    古い所属を拾う危険は、期間ではなく「新しい順」で防ぐ。
  - 対象会派はハードコードしない。PARTY_KEYS に一致しない会派をその都度検出する。
  - 過去ログが統一会派の下にしかない新人は、**時間が経っても永久に解決しない**。
    roster_override.json で人間が補う（移籍の承認も同じファイルで行う）。

使い方:
    python build_roster.py              # roster.json を更新し、解決状況を報告
    python build_roster.py --check      # 更新せず、差分だけ見る（CI用）
"""
import collections, datetime, json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROSTER = os.path.join(HERE, "roster.json")
OVERRIDE = os.path.join(HERE, "roster_override.json")
API = "https://kokkai.ndl.go.jp/api/speech?"

# 会派名に含まれていれば、その党の議員だと判定できる文字列
PARTY_KEYS = {
    "自由民主党": "自由民主党", "立憲民主": "立憲民主党", "日本維新の会": "日本維新の会",
    "国民民主": "国民民主党", "公明党": "公明党", "日本共産党": "日本共産党",
    "れいわ": "れいわ新選組", "参政党": "参政党",
    "チームみらい": "チームみらい", "社会民主": "社会民主党", "社民": "社会民主党",
}
LOOKBACK_FROM = "2021-01-01"   # 逆引きの遡及開始。広く取り、降順で最初の一致を採る
SAMPLE_PAGES = 8               # 会派の発言者を洗い出す標本ページ数(×100件)


def api(**kw):
    kw.setdefault("recordPacking", "json")
    url = API + urllib.parse.urlencode(kw)
    return json.load(urllib.request.urlopen(url, timeout=60))


def party_of(group):
    """会派名から党名を引く。判定できなければ None。

    **複数の党名が一致する会派は「判定不能」として扱う。** 第217回の参議院会派
    「立憲民主・社民・無所属」は立憲民主党と社会民主党が同居しており、辞書の
    並び順で先に当たった方を採ると誤って帰属させる（実際に福島みずほ議員の発言が
    立憲民主党として掲載されていた）。**曖昧なら黙って一方に決めず、名簿に回す。**
    2026年に会派が分裂して党名が明確になっているため、名簿の逆引き（新しい順に
    見る）でほとんどが正しく解決する。
    """
    if not group:
        return None
    hit = {name for key, name in PARTY_KEYS.items() if key in group}
    return hit.pop() if len(hit) == 1 else None


# 会派ではないもの。名簿の対象にすると、無所属議員を党に帰属させてしまう。
NOT_A_CAUCUS = ("各派に属しない議員",)

def unmatched_groups(house="衆議院", years=2):
    """党を判定できない会派を検出する（会派名をコードに埋め込まないため）。

    **年ごとに区切って調べる。** APIは新しい順に返し、1回の窓では直近の年で
    埋まってしまう。長い窓を1回で投げると、古い会期の会派（第217回=2025年の
    「立憲民主・社民・無所属」）に到達しない。
    """
    seen = collections.Counter()
    this_year = datetime.date.today().year
    for y in range(this_year, this_year - years - 1, -1):
        for start in range(1, SAMPLE_PAGES * 100, 100):
            try:
                d = api(**{"from": f"{y}-01-01", "until": f"{y}-12-31"},
                        nameOfHouse=house, maximumRecords=100, startRecord=start)
            except Exception as e:
                print(f"  WARN 会派の検出に失敗: {e}")
                break
            recs = d.get("speechRecord", [])
            for r in recs:
                g = r.get("speakerGroup")
                if g and not party_of(g) and g not in NOT_A_CAUCUS:
                    seen[g] += 1
            if len(recs) < 100:
                break
            time.sleep(0.2)
    return seen


def speakers_in(group, years=2):
    """その会派で発言している議員と、その院を洗い出す（年ごとに区切る）。

    院を持ち帰るのは同姓同名を切り分けるため。衆議院の鬼木誠議員（自民）と
    参議院の鬼木誠議員（立憲）のように、名前だけでは別人を取り違える。
    """
    names = collections.Counter()
    houses = collections.defaultdict(collections.Counter)
    this_year = datetime.date.today().year
    for y in range(this_year, this_year - years - 1, -1):
        for start in range(1, SAMPLE_PAGES * 100, 100):
            try:
                d = api(speakerGroup=group, **{"from": f"{y}-01-01", "until": f"{y}-12-31"},
                        maximumRecords=100, startRecord=start)
            except Exception as e:
                print(f"  WARN {group} の発言者取得に失敗: {e}")
                break
            recs = d.get("speechRecord", [])
            for r in recs:
                names[r["speaker"]] += 1
                houses[r["speaker"]][r.get("nameOfHouse") or ""] += 1
            if len(recs) < 100:
                break
            time.sleep(0.2)
    return {n: (houses[n].most_common(1)[0][0] if houses[n] else "") for n in names}


def resolve(name, house=""):
    """議員名から所属党を逆引きする。直近の「党名入り会派」に属していた時点を探す。

    APIは新しい順に返し、1回で取れるのは100件まで。よく発言する議員は直近100件が
    すべて統一会派の下になり、まとめて取ると党名が見つからない（長妻昭は1,303件あり、
    先頭100件が全て2026年だった）。そこで until を年単位で遡らせ、最初に党名入り会派
    が現れた年で止める。ほとんどの議員は1回のリクエストで解決する。
    """
    year = datetime.date.today().year
    floor = int(LOOKBACK_FROM[:4])
    while year >= floor:
        try:
            q = {"speaker": name, "from": LOOKBACK_FROM, "until": f"{year}-12-31",
                 "maximumRecords": 3}
            if house:
                q["nameOfHouse"] = house    # 同姓同名の別人を混ぜないため
            d = api(**q)
        except Exception:
            return None
        recs = d.get("speechRecord", [])
        if not recs:
            return None          # その年以前に発言が無い＝これ以上遡っても出てこない
        for r in recs:
            p = party_of(r.get("speakerGroup"))
            if p:
                return p
        year -= 1                # まだ統一会派の下。1年前を見る
        time.sleep(0.15)
    return None


def load(path, default):
    if not os.path.exists(path):
        return default
    try:
        return json.load(open(path, encoding="utf-8"))
    except Exception:
        return default


def main():
    check_only = "--check" in sys.argv
    prev = load(ROSTER, {}).get("members", {})
    override = load(OVERRIDE, {})

    print("[名簿の解決状況]")
    found = unmatched_groups("衆議院")
    found.update(unmatched_groups("参議院"))   # 第217回の「立憲民主・社民・無所属」

    # 検出は自動、参入は人が承認する。
    # 自動で全部を対象にすると、「無所属」や掲載対象外の党の会派まで拾い、
    # 離党した議員を元の党の発言として扱ってしまう（実測で自由民主党113名を誤って
    # 解決した）。**誤って帰属させるより、載せない方がましである。**
    allowed = set(override.get("_caucuses", {}))
    rejected = set(override.get("_caucuses_rejected", {}))
    groups = collections.Counter({g: n for g, n in found.items() if g in allowed})
    pending = [g for g in found if g not in allowed and g not in rejected]

    if not groups:
        print("  対象会派はありません（承認済みの会派が見つかりませんでした）。")
    else:
        print("  対象会派 : " + " / ".join(f"{g}（{n}件）" for g, n in groups.most_common()))
    if pending:
        print("  ★要承認 : " + " / ".join(f"{g}（{found[g]}件）" for g in pending))
        print("           roster_override.json の _caucuses か _caucuses_rejected に"
              "理由付きで追記してください。")

    members, unresolved = {}, []
    for group in groups:
        for name, house in speakers_in(group).items():
            if name in override:
                p = (override[name].get("party") or "").strip()
                if p:
                    members[name] = {"party": p, "group": group, "source": "override"}
                else:
                    unresolved.append(name)
                continue
            p = resolve(name, house)
            if p:
                members[name] = {"party": p, "group": group, "house": house, "source": "api"}
            else:
                unresolved.append(name)
            time.sleep(0.15)

    # 前回と判定が変わった議員（本当の移籍か、逆引きの誤りか、人間の確認が要る）
    changed = [(n, prev[n]["party"], members[n]["party"]) for n in members
               if n in prev and prev[n]["party"] != members[n]["party"]
               and members[n]["source"] == "api"]

    by_party = collections.Counter(v["party"] for v in members.values())
    print(f"  発言者   : {len(members) + len(unresolved)}名")
    print(f"  解決     : {len(members)}名（"
          + " / ".join(f"{p} {n}" for p, n in by_party.most_common()) + "）")
    print(f"  未解決   : {len(unresolved)}名"
          + (f"（{'・'.join(sorted(unresolved))}）… 掲載対象外" if unresolved else ""))
    print(f"  要確認   : {len(changed)}名"
          + (f" {changed}" if changed else "（前回と所属判定が変わった議員）"))

    if not check_only:
        out = {"generated": datetime.date.today().isoformat(),
               "members": members, "unresolved": sorted(unresolved)}
        json.dump(out, open(ROSTER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"\n  roster.json を書き出しました（{len(members)}名）")

    if changed:
        print("\n  所属判定が変わった議員がいます。本当の移籍なら "
              "roster_override.json に党名を書いて承認してください。")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
