# -*- coding: utf-8 -*-
"""AI政策くらべ v1.1 「政党で選ぶ」= 党タブ主体。
既存 build_guide.py のデータ(46発言+投票)・整形関数を再利用し、行列を転置して党ごとに表示。
各党に『ワンイシュー』(特に重視する1点)を新設。"""
import html, json, urllib.parse, os

# --- 既存ファイルを実行して、データと関数を取り込む(policy_guide.htmlは後で上書き) ---
ns = {}
exec(open("build_guide.py", encoding="utf-8").read(), ns)
esc          = ns["esc"]
clean_quote  = ns["clean_quote"]
votes_html   = ns["votes_html"]
NO_VOTE_BLOCK= ns["NO_VOTE_BLOCK"]
VBASE        = ns.get("VBASE", "https://www.sangiin.go.jp/japanese/touhyoulist/217/")

# 並び順は読みやすさのための編集判断で、重要度の順位ではない（about.html に明記）。
# 物価高・消費税減税が「経済・産業」と「財政」にまたがるので隣接させて上に置く。
# 憲法は記名投票の議案が無く「行」が空になるため最後。
DOMAIN_ORDER = [
    ("経済・産業",     ns["ECON"],   ns["CVOTES"], ns["CLABEL"]),
    ("財政",          ns["FISCAL"], ns["FVOTES"], ns["FLABEL"]),
    ("社会保障",       ns["SOCIAL"], ns["SVOTES"], ns["SLABEL"]),
    ("外交・安保",     ns["DIPLO"],  ns["DVOTES"], ns["DLABEL"]),
    ("エネルギー・環境", ns["ENERGY"], ns["EVOTES"], ns["ELABEL"]),
    ("憲法",          ns["KENPO"],  None,         None),
]
PARTIES = [("自由民主党","自民"),("立憲民主党","立憲"),("日本維新の会","維新"),
           ("国民民主党","国民"),("公明党","公明"),("日本共産党","共産"),
           ("れいわ新選組","れいわ"),("参政党","参政"),
           ("チームみらい","みらい"),("社会民主党","社民")]
PARTY_IDMAP = {"自由民主党":"jimin","立憲民主党":"rikken","日本維新の会":"ishin","国民民主党":"kokumin",
               "公明党":"komei","日本共産党":"kyosan","れいわ新選組":"reiwa","参政党":"sansei",
               "チームみらい":"mirai","社会民主党":"shamin"}
# 各党のイメージカラー（各党公式サイト基準・報道慣例を参考。build_site.py と同一）
PARTY_COLOR = {"自由民主党":"#E60012","立憲民主党":"#004097","日本維新の会":"#12A150","国民民主党":"#F2B200",
               "公明党":"#F55881","日本共産党":"#D7003A","れいわ新選組":"#E4007F","参政党":"#E8630A",
               "チームみらい":"#00B8C4","社会民主党":"#0B60A8"}
def pc_on(hx):
    r,g,b=int(hx[1:3],16),int(hx[3:5],16),int(hx[5:7],16)
    return "#1b2130" if (0.299*r+0.587*g+0.114*b)>150 else "#ffffff"

# ---- 第221回国会の記名投票（会期併記用） ----------------------------------
# 各分野の代表議案は編集判断で選定。可能な限り第217回と同系統の法案を選び、
# 会期を跨いだ立場の変化が読み取れるようにしている（評価はせず、事実を並べるだけ）。
BILLS221 = {
 "財政": [("221-0407-v001","予算"), ("221-0331-v012","所得税"),
          ("221-0331-v002","交付税"), ("221-0605-v001","補正")],
 "外交・安保": [("221-0626-v001","防衛省設置"), ("221-0619-v001","日比ACSA"),
                ("221-0619-v002","蘭ACSA"), ("221-0610-v003","経済安保")],
 "社会保障": [("221-0529-v005","健康保険"), ("221-0619-v006","社会福祉"),
              ("221-0710-v003","労災保険")],
 "エネルギー・環境": [("221-0717-v005","電気事業"), ("221-0612-v008","PCB処理"),
                      ("221-0515-v006","環境省設置")],
 "経済・産業": [("221-0715-v003","金商法"), ("221-0529-v009","産業競争力"),
                ("221-0612-v009","産業技術力"), ("221-0612-v006","郵便法")],
}
# 第219回（2025年11-12月の臨時国会）。記名投票31件のうち10件が人事同意案件、
# 4件がNHK決算で、政策議案は財政と社会保障に偏る。外交・安保／エネルギー・環境／
# 経済・産業には該当議案が無く、空欄になる（理由は画面に明示する）。
BILLS219 = {
 "財政": [("219-1216-v001","補正予算"), ("219-1216-v002","特会補正"),
          ("219-1216-v008","交付税"), ("219-1128-v010","租特")],
 "社会保障": [("219-1205-v002","医療法"), ("219-1216-v003","高次脳機能障害")],
}
S221 = json.load(open("221_speeches.json", encoding="utf-8"))   # 会期併記用の「言」
S219 = json.load(open("219_speeches.json", encoding="utf-8"))
META217 = json.load(open("217_speech_meta.json", encoding="utf-8"))  # 第217回の議院・会議名


def _load_votes(path, sel):
    """選定した議案だけを、分野ごとに (votes, labels) の形にまとめる。"""
    byid = {b["id"]: b for b in json.load(open(path, encoding="utf-8"))["bills"]}
    out = {}
    for dom, pairs in sel.items():
        bs = [(byid[i], lab) for i, lab in pairs if i in byid]
        out[dom] = ({"bills": [b for b, _ in bs]}, [lab for _, lab in bs])
    return out


V221 = _load_votes("221_votes.json", BILLS221)
V219 = _load_votes("219_votes.json", BILLS219)

# 第221回の会派名（選挙を経て変わった）。参政党はこの会期で会派を結成した。
VKEY221 = {"自由民主党":"自由民主党","立憲民主党":"立憲民主","日本維新の会":"日本維新の会",
           "国民民主党":"国民民主","公明党":"公明党","日本共産党":"日本共産党",
           "れいわ新選組":"れいわ","参政党":"参政党",
           "チームみらい":"チームみらい","社会民主党":"社会民主党"}

# 第219回の会派名。社民は立憲との統一会派「立憲民主・社民・無所属」に属しており、
# 会派としての単独の賛否が記録に残らない。統一会派の賛否を1党の賛否として扱うと
# 事実と違うものを載せることになるため、ここには入れず、理由を画面に出す。
# チームみらいはこの会期にまだ会派が無い。
VKEY219 = {"自由民主党":"自由民主党","立憲民主党":"立憲民主","日本維新の会":"日本維新の会",
           "国民民主党":"国民民主","公明党":"公明党","日本共産党":"日本共産党",
           "れいわ新選組":"れいわ","参政党":"参政党"}

# 会期×党で、既定の説明文では事実と食い違う場合の個別の説明。
# {what} は「賛否記録」「発言記録」のように、行と言で言い分けるために置いている
# （採決用の文言を発言欄に出すと、書いていないことを書いたことになる）。
SESSION_NOTE = {
    ("第219回", "社会民主党"):
        "この会期は立憲民主党などとの統一会派（立憲民主・社民・無所属）に属しており、"
        "会派としての単独の{what}がありません",
}


def session_note(ses, full, what):
    tpl = SESSION_NOTE.get((ses, full))
    return tpl.format(what=what) if tpl else None


def sessions_for(full, dname, entry, votes, labels):
    """掲載する会期を古い順に (表示名, vkey, votes, labels) で返す。

    会期を足すときはここに1行足す。表示側3か所が同じ並びを使うため、
    片方だけ直して会期が食い違う事故が起きない。
    """
    v219, l219 = V219.get(dname, (None, None))
    v221, l221 = V221.get(dname, (None, None))
    return [("第217回", entry.get("vkey"), votes, labels),
            ("第219回", VKEY219.get(full), v219, l219),
            ("第221回", VKEY221.get(full), v221, l221)]

def vote_url(bid):
    """議案IDの先頭3桁が会期番号なので、そこからURLを組み立てる。"""
    return f"https://www.sangiin.go.jp/japanese/touhyoulist/{bid[:3]}/{bid}.htm"

def _chips(vkey, votes, labels):
    if votes is None or not vkey or not votes.get("bills"):
        return None
    out = []
    for i, b in enumerate(votes["bills"]):
        st = next((v["stance"] for name, v in b["parties"].items() if vkey in name), None)
        cls = {"賛成":"yes","反対":"no"}.get(st or "", "na")
        out.append(f'<a class="vchip {cls}" href="{esc(vote_url(b["id"]))}" target="_blank" '
                   f'rel="noopener" title="{esc(b["label"])}：{esc(st or "—")}（原典へ）">'
                   f'{esc(labels[i])}<b>{esc(st or "—")}</b></a>')
    return "".join(out)

def session_quote(ses, who, quote, url, where="", date=""):
    """発言は「いつ・どこで」を先に示す。切り抜きではなく、国会での一場面として読ませるため。"""
    ctx = " ".join(x for x in (where, date) if x)
    head = f'<span class="qctx">{esc(ctx)}</span>' if ctx else ""
    return (f'<div class="vses"><span class="vsl">{ses}</span>'
            f'<div class="qbox">{head}'
            f'<p class="qtext">「{esc(quote)}」</p>'
            f'<p class="qcite">— {esc(who)}議員'
            f'<a class="evq" href="{esc(url)}" target="_blank" rel="noopener">全文→</a></p>'
            f'</div></div>')

def say_block(full, dname, entry):
    """第217回と第221回の発言を並べる。採決と同じく、変化に評価は与えない。"""
    if entry.get("quote"):
        _m = META217.get(f'{full}|{dname}', {})
        rows = [session_quote("第217回", entry["who"], clean_quote(entry["quote"]), entry["url"],
                              f'{_m.get("house","")}{_m.get("meeting","")}', _m.get("date",""))]
    else:
        rows = ['<div class="vses"><span class="vsl">第217回</span>'
                '<span class="vna">この会期にはこの党の会派が存在せず、会派としての発言記録がありません</span></div>']
    for ses, src in (("第219回", S219), ("第221回", S221)):
        e2 = src.get(full, {}).get(dname)
        if e2:
            rows.append(session_quote(ses, e2["who"], e2["quote"], e2["url"],
                                      f'{e2.get("house","")}{e2.get("meeting","")}',
                                      e2.get("date","")))
        else:
            reason = (session_note(ses, full, "発言記録")
                      or "この会期ではこの分野の会派代表発言を確認できませんでした")
            rows.append(f'<div class="vses"><span class="vsl">{ses}</span>'
                        f'<span class="vna">{reason}</span></div>')
    return ('<div class="say"><span class="vlbl gen">言 ／ 国会での発言（会期別）</span>'
            + (f'<p class="point">{esc(entry["point"])}</p>' if entry.get("point") else "")
            + "".join(rows) + '</div>')

# 衆議院の記名投票。予算だけを扱う（fetch_shugiin_votes.py --budget-only）。
# 起立採決の議案は会議録に「起立多数」としか残らないので、財政以外は空欄になる。
# 委員長解任決議案も記名投票だが、予算審議の進め方をめぐる政局案件であり、
# 政策的立場として並べると誤読を招くため入れていない。
# 収集していない会期と、収集した結果0件だった会期を区別する。
# ファイルが無いだけなのに「採決がありません」と書くと、未取得を事実の不在として
# 提示することになる（憲法6条）。0件のときも必ずファイルを作って裏づけを残す。
SHUGIIN = {}
for _s in ("217", "219", "221"):
    _p = f"{_s}_shugiin_votes.json"
    SHUGIIN[f"第{_s}回"] = (json.load(open(_p, encoding="utf-8"))["bills"]
                            if os.path.exists(_p) else None)


def shugiin_rows(full, dname):
    """衆院の賛否。参院と違い会派別の公表が無いため、投票者の氏名から党を引いている。"""
    rows = []
    for ses in ("第217回", "第219回", "第221回"):
        bills = SHUGIIN.get(ses)
        chips, notes = [], []
        if dname == "財政" and bills:
            for b in bills:
                c = b["parties"].get(full)
                if not c:
                    continue
                cls = {"賛成": "yes", "反対": "no"}.get(c["stance"], "na")
                title = (f'{b["label"]}：{c["stance"]}'
                         f'（氏名から党を特定できた分で 賛成{c["賛成"]}・反対{c["反対"]}）')
                chips.append(f'<a class="vchip {cls}" href="{esc(b["url"])}" target="_blank" '
                             f'rel="noopener" title="{esc(title)}">予算<b>{esc(c["stance"])}</b></a>')
                # 憲法4条は「引けない議員と無所属は数えず、人数を開示する」と定める。
                # 方法論のページだけでなく、数字が出ているその場に、議案ごとに書く。
                notes.append(f'※ 投票総数{b["reported"]["total"]}票のうち、'
                             f'氏名から所属党を特定できなかった{b["unidentified"]}票と'
                             f'無所属{b["independent"]}票は、どの党にも数えていません')
        if chips:
            rows.append(f'<div class="vses"><span class="vsl">{ses}</span>'
                        f'<div class="vrow">{"".join(chips)}</div>'
                        f'<span class="vna">{" ／ ".join(notes)}</span></div>')
            continue
        if bills is None:
            reason = "この会期の衆議院の記名投票は、まだ収集していません"
        elif dname != "財政":
            # 「記録が残らない」と断定できるのは、実際に数えたから。掲載3会期の衆院
            # 記名投票は予算2件と委員長解任決議案2件だけで、他分野の議案は無かった。
            reason = ("この3会期の衆議院の記名投票は予算と委員長解任決議案だけで、"
                      "この分野の議案は起立採決のため賛否が記録に残っていません")
        elif not bills:
            reason = "この会期に衆議院の記名投票による予算の採決がありません"
        else:
            # 議席が無かったのか、氏名から特定できなかったのかは、この段では区別できない。
            # 区別できないことを、区別できたように書かない。
            reason = ("この会期の予算の記名投票で、この党の議員の投票を確認できませんでした"
                      "（議席が無かったか、氏名から所属を特定できなかったかのいずれかです）")
        rows.append(f'<div class="vses"><span class="vsl">{ses}</span>'
                    f'<span class="vna">{reason}</span></div>')
    return "".join(rows)


def votes_block(full, dname, entry, votes, labels):
    """各会期の賛否を並べて示す。どちらが良いという評価はしない。"""
    rows = []
    for ses, vk, vv, ll in sessions_for(full, dname, entry, votes, labels):
        chips = _chips(vk, vv, ll)
        if chips:
            rows.append(f'<div class="vses"><span class="vsl">{ses}</span>'
                        f'<div class="vrow">{chips}</div></div>')
            continue
        note = session_note(ses, full, "賛否記録")
        if note:
            reason = note
        elif dname == "憲法":
            reason = "憲法審査会は討議の場で、本会議の記名投票にかかる議案がありません"
        elif not vk:
            reason = "この会期では会派未結成のため、会派別の賛否記録がありません"
        else:
            reason = "この会期では該当する議案がありません"
        rows.append(f'<div class="vses"><span class="vsl">{ses}</span>'
                    f'<span class="vna">{reason}</span></div>')
    return ('<div class="votes"><span class="vlbl">行 ／ 参院 記名投票（会期別）</span>'
            + "".join(rows)
            + '<span class="vlbl">行 ／ 衆院 記名投票（会期別）</span>'
            + shugiin_rows(full, dname) + "</div>")

# 党→領域→(entry, votes, labels)
PIDX = {full: {} for full,_ in PARTIES}
for dname, lst, votes, labels in DOMAIN_ORDER:
    for e in lst:
        if e["party"] in PIDX:
            PIDX[e["party"]][dname] = (e, votes, labels)

# 第217回に会派が無かった党（チームみらい・社民）は上のループで空になる。
# 第221回の発言がある分野については、217側を「該当なし」としてカードを作る。
_DOM_VOTES = {dn: (v, l) for dn, _lst, v, l in DOMAIN_ORDER}
for full, doms in S221.items():
    if full not in PIDX or PIDX[full]:
        continue
    for dname in doms:
        v, l = _DOM_VOTES.get(dname, (None, None))
        PIDX[full][dname] = ({"party": full, "point": "", "who": "", "quote": "",
                              "url": "", "vkey": None, "tag": ""}, v, l)

# ワンイシュー(国会での言動から抽出した具体版)。根拠は ref 領域の実発言にリンク。
ONEISSUE = {
 "自由民主党":  ("防衛力の強化と現実的な政権運営","広範な政権与党で単一争点ではないが、強いて挙げれば抑止力の向上・防衛力強化を前面に。","外交・安保"),
 "立憲民主党":  ("行政・財政の透明化と説明責任","政治とカネや予算・財務の説明責任を追及する姿勢を前面に。","財政"),
 "日本維新の会":("身を切る改革・歳出改革","歳出削減と行財政改革を党是に掲げる。","財政"),
 "国民民主党":  ("手取りを増やす（減税・103万円の壁）","可処分所得の増加を最重要争点に据える。","経済・産業"),
 "公明党":      ("福祉と現場の処遇改善","現場の技能者・生活者の処遇改善を重視する福祉政党。","経済・産業"),
 "日本共産党":  ("軍拡より暮らし（大軍拡・改憲に反対）","軍事費拡大と改憲に一貫して反対し、暮らし・社会保障を優先。","外交・安保"),
 "れいわ新選組":("消費税廃止・積極財政","結党以来の一貫した看板政策。反緊縮で需要を底上げする。","経済・産業"),
 "参政党":      ("消費税減税・インボイス廃止","既存政治への異議として、減税と負担軽減を前面に掲げる。","財政"),
 "チームみらい":("テクノロジーで政治を作り変える","デジタル技術で行政の効率化・政治資金の可視化・プッシュ型支援を進めることを前面に掲げる。","経済・産業"),
 "社会民主党":  ("憲法9条を守り、暮らしを底上げする","護憲と反戦を党是とし、食料品消費税ゼロや最低賃金の引き上げで生活を支えると訴える。","憲法"),
}

# 政策パッケージ要約（2025年参院選の公約等より・編集要約）。url=各党公式サイト。
PACKAGE = {
 "自由民主党": {"url":"https://www.jimin.jp/", "bullets":[
   "物価高対策として国民1人2万円の給付（子ども・住民税非課税世帯に加算）",
   "賃上げと投資による「成長型経済」。消費税は維持",
   "全世代型社会保障、年金制度改革（基礎年金の底上げ）",
   "日米同盟を基軸に防衛力を抜本強化（反撃能力の保有）",
   "原発の再稼働・次世代炉の開発、GXの推進",
   "緊急事態条項などの憲法改正を推進"]},
 "立憲民主党": {"url":"https://cdp-japan.jp/", "bullets":[
   "食料品の消費税を1年間ゼロに＋「食卓おうえん給付金」1人2万円",
   "政治とカネの透明化（企業・団体献金の見直し）",
   "年金の底上げ・子育て支援、大学までの教育無償化をめざす",
   "現実的な安全保障（専守防衛）。防衛費は財源を吟味",
   "原発の新増設は認めず、再エネを重視",
   "選択的夫婦別姓など多様性の尊重"]},
 "日本維新の会": {"url":"https://o-ishin.jp/", "bullets":[
   "「身を切る改革」（議員定数・報酬の削減、行財政改革）",
   "社会保険料を1人あたり年6万円引き下げ、現役世代の負担軽減",
   "幼児〜大学までの教育無償化",
   "年金・医療の抜本改革（積立方式の検討など）",
   "統治機構改革・教育無償化の明記を含む憲法改正",
   "防衛力の強化に前向き、原発の活用も支持"]},
 "国民民主党": {"url":"https://new-kokumin.jp/", "bullets":[
   "「手取りを増やす」、年収の壁（103万円）の引き上げ",
   "ガソリン減税、若者向けの所得税減税",
   "積極財政と金融緩和で賃金上昇を後押し",
   "原発の再稼働・活用を明確に支持",
   "教育・人づくりへの投資（教育国債など）",
   "現実的な安全保障、防衛力の強化"]},
 "公明党": {"url":"https://www.komei.or.jp/", "bullets":[
   "物価高対策として国民1人2万円の一律給付",
   "出産費用の無償化、児童手当の拡充など子育て支援",
   "中小企業支援・賃上げ、生活者目線の福祉",
   "教育の無償化を推進",
   "平和外交、日米同盟と対話を重視",
   "憲法は「加憲」の立場（9条は維持）"]},
 "日本共産党": {"url":"https://www.jcp.or.jp/", "bullets":[
   "消費税を一律5%へ減税、大企業・富裕層への課税を強化",
   "大軍拡に反対し軍事費を削減、憲法9条を守る（改憲反対）",
   "原発ゼロ、再エネの推進",
   "社会保障の拡充（年金・医療・介護）、教育無償化",
   "ジェンダー平等・選択的夫婦別姓",
   "外国人の人権保障"]},
 "れいわ新選組": {"url":"https://reiwa-shinsengumi.com/", "bullets":[
   "消費税廃止・インボイス廃止（積極財政）",
   "全国一律の最低賃金引き上げ、季節ごとの現金給付",
   "奨学金の返済免除、教育の無償化",
   "原発の廃止と再エネ",
   "障害者・弱者支援、社会保障の拡充",
   "非軍事・平和外交（防衛費増や安保法制に反対）"]},
 "チームみらい": {"url":"https://team-mir.ai/", "bullets":[
   "「子育て減税」（子どもの人数に応じて親の所得税率を定率で減税）",
   "社会保険料の引き下げ（消費税減税より優先）",
   "行政の「プッシュ型支援」（申請主義をやめ、支援を自動で届ける）",
   "政治資金の可視化と国会のデジタル化",
   "高等専門学校への設備投資、大学の運営費交付金の拡充",
   "AI・ロボット・自動運転など新産業の育成"]},
 "社会民主党": {"url":"https://sdp.or.jp/", "bullets":[
   "食料品の消費税をゼロに（財源は防衛費の引き下げ・法人税や所得税の累進強化）",
   "憲法9条の改悪に反対（護憲）",
   "原発ゼロ・自然エネルギー100%",
   "働く人の社会保険料を半減、最低賃金は全国一律1500円",
   "包括的差別禁止法・国内人権救済機関の設置",
   "選択的夫婦別姓と同性婚の実現"]},
 "参政党": {"url":"https://www.sanseito.jp/", "bullets":[
   "「日本人ファースト」、行き過ぎた外国人受け入れに反対",
   "消費税減税・インボイス廃止など国民負担の軽減",
   "教育改革（日本の歴史・伝統を重視）、子どもへの給付",
   "「食と健康」（食の安全、オーガニック給食など）",
   "国防の強化・自主憲法の制定",
   "「脱・脱炭素」（再エネ賦課金の見直し、次世代原発）"]},
}

def quote_block(e, ref_note=""):
    note = f'（{esc(ref_note)}）' if ref_note else ""
    return (f'<blockquote>「{esc(clean_quote(e["quote"]))}」'
            f'<cite>— {esc(e["who"])}議員・第217回国会{note}</cite>'
            f'<a class="evq" href="{esc(e["url"])}" target="_blank" rel="noopener">全文→</a></blockquote>')

def oneissue_block(full):
    issue, why, ref = ONEISSUE[full]
    e = PIDX[full].get(ref, (None,))[0]
    if not e or not e.get("quote"):          # 第221回しかない党はそちらを根拠にする
        alt = S221.get(full, {}).get(ref) or next(iter(S221.get(full, {}).values()), None)
        if alt:
            e = {"who": alt["who"], "quote": alt["quote"], "url": alt["url"]}
    pid = PARTY_IDMAP.get(full, "")
    more = (f'<a class="oi-more" href="oneissue.html#{pid}">'
            f'▸ このワンイシューを深掘り（関連する発言・採決の実績を見る）</a>')
    return (f'<div class="oneissue"><span class="oi-label">★ ワンイシュー ― この党が特に重視する1点（要注目）</span>'
            f'<h2 class="oi-title">{esc(issue)}</h2><p class="oi-why">{esc(why)}</p>'
            f'{quote_block(e, ref+"分野の発言")}{more}</div>')

def package_block(full):
    pk = PACKAGE.get(full)
    if not pk: return ""
    lis = "".join(f'<li>{esc(b)}</li>' for b in pk["bullets"])
    return (f'<details class="pkg" open><summary>政策パッケージ（2025年の公約より・要約）</summary>'
            f'<ul class="pkg-list">{lis}</ul>'
            f'<a class="src" href="{esc(pk["url"])}" target="_blank" rel="noopener">公式サイトで全体を見る ↗</a></details>')

# --- マイノート(クリップ)用のデータカタログ。各分野カードを一意IDで保存できるようにする ---
CLIP_CAT = {}
def build_clip(full, short, dname, entry, votes, labels):
    cid = PARTY_IDMAP[full] + "__" + dname
    vlist = []
    for ses, vk, vv, ll in sessions_for(full, dname, entry, votes, labels):
        ses = ses.strip("第回")   # マイノートでは「217」と短く出す
        if vv is None or not vk:
            continue
        for i, b in enumerate(vv["bills"]):
            st = next((v["stance"] for name, v in b["parties"].items() if vk in name), None)
            vlist.append({"l": f"{ses} {ll[i]}", "st": st or "—", "u": vote_url(b["id"])})
    CLIP_CAT[cid] = {"party": short, "pc": PARTY_COLOR[full], "dom": dname,
                     "point": entry["point"], "quote": clean_quote(entry["quote"]),
                     "who": entry["who"], "url": entry["url"], "votes": vlist}
    return cid

# 分野ごとの会議録検索キーワード（発言一覧リンク用）
DOMAIN_SEARCH = {
    "財政": "財政", "外交・安保": "安全保障", "社会保障": "社会保障",
    "エネルギー・環境": "エネルギー", "経済・産業": "経済", "憲法": "憲法",
}
# 会派名は会期で変わるため、検索は会派指定なし（議員名で辿れるよう発言リンクは別途ある）
def domain_links(full, dname):
    """この分野の『もっと見る』導線。いずれも当サイト内で党×分野を保ったまま辿れる。"""
    pid = PARTY_IDMAP.get(full, "")
    qs = urllib.parse.quote(dname) + ("&party=" + pid if pid else "")
    return (f'<div class="dmore">'
            f'<a href="news.html?domain={qs}">▸ この党のこの分野のニュース</a>'
            f'<a href="speeches.html?domain={qs}">▸ この党のこの分野の発言をもっと見る</a>'
            f'</div>')

def domain_row(dname, entry, votes, labels, cid, full):
    tag = f'<span class="tag">◉ {esc(entry["tag"])}</span>' if entry.get("tag") else ""
    clip = (f'<button class="clip" type="button" data-clip="{cid}" aria-label="この分野をマイノートに保存" '
            f'title="マイノートに保存"><svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">'
            f'<path d="M6 3.6h12a1 1 0 0 1 1 1v16.1l-7-4.1-7 4.1V4.6a1 1 0 0 1 1-1z"/></svg></button>')
    vblock = votes_block(full, dname, entry, votes, labels)
    return (f'<article class="drow"><div class="drow-h">'
            f'<span class="dname">{esc(dname)}</span><span class="dh-r">{tag}{clip}</span></div>'
            f'{say_block(full, dname, entry)}{vblock}{domain_links(full, dname)}</article>')

panes, tabs = [], []
for i,(full,short) in enumerate(PARTIES):
    _c=PARTY_COLOR[full]
    tabs.append(f'<button class="dtab{" on" if i==0 else ""}" data-d="{i}" '
                f'style="--pc:{_c};--pc-on:{pc_on(_c)}">{esc(short)}</button>')
    _rows = []
    for dn,_,_,_ in DOMAIN_ORDER:
        if dn not in PIDX[full]: continue
        _e,_v,_l = PIDX[full][dn]
        _cid = build_clip(full, short, dn, _e, _v, _l)
        _rows.append(domain_row(dn, _e, _v, _l, _cid, full))
    rows = "".join(_rows)
    missing = [dn for dn,_,_,_ in DOMAIN_ORDER if dn not in PIDX[full]]
    miss = (f'<p class="miss">※この党は当会期の {("・".join(missing))} 分野で会派としての代表発言・採決が確認できず、掲載を見送りました。</p>'
            if missing else "")
    panes.append(f'<section class="pane" data-pane="{i}" '
                 f'style="--pc:{PARTY_COLOR[full]};--pc-on:{pc_on(PARTY_COLOR[full])}"{"" if i==0 else " hidden"}>'
                 f'{oneissue_block(full)}{package_block(full)}'
                 f'<div class="dgrid">{rows}</div>{miss}</section>')

CSS = """
:root{ --paper:#f3f4f7; --card:#fbfbfd; --ink:#1b2130; --muted:#5c6675; --line:#dcdfe6;
  --accent:#3a4d8f; --accent-soft:#e6e9f4; --answer:#9aa3b2;
  --shadow:0 1px 2px rgba(20,28,50,.05),0 8px 24px rgba(20,28,50,.05); }
@media (prefers-color-scheme:dark){ :root{ --paper:#12151d; --card:#191d27; --ink:#e7eaf1;
  --muted:#98a1b2; --line:#282e3b; --accent:#8ea2e6; --accent-soft:#222a40; --answer:#5c6473;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35); } }
:root[data-theme="dark"]{ --paper:#12151d; --card:#191d27; --ink:#e7eaf1; --muted:#98a1b2;
  --line:#282e3b; --accent:#8ea2e6; --accent-soft:#222a40; --answer:#5c6473;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35); }
:root[data-theme="light"]{ --paper:#f3f4f7; --card:#fbfbfd; --ink:#1b2130; --muted:#5c6675;
  --line:#dcdfe6; --accent:#3a4d8f; --accent-soft:#e6e9f4; --answer:#9aa3b2;
  --shadow:0 1px 2px rgba(20,28,50,.05),0 8px 24px rgba(20,28,50,.05); }
*{ box-sizing:border-box; }
.wrap{ --serif:"Hiragino Mincho ProN","Yu Mincho",YuMincho,"Noto Serif JP",serif;
  --sans:"Hiragino Kaku Gothic ProN","Yu Gothic",YuGothic,"Noto Sans JP",Meiryo,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  background:var(--paper); color:var(--ink); font-family:var(--sans); line-height:1.7;
  -webkit-font-smoothing:antialiased; padding:clamp(20px,5vw,56px) clamp(16px,5vw,40px); }
.doc{ max-width:940px; margin:0 auto; }
.eyebrow{ font-family:var(--mono); font-size:12px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); margin:0 0 12px; }
h1{ font-family:var(--serif); font-weight:600; font-size:clamp(24px,4.4vw,38px); line-height:1.3;
  text-wrap:balance; margin:0 0 14px; }
.lede{ color:var(--muted); font-size:15px; max-width:64ch; margin:0; }
.lede b{ color:var(--ink); }
.rule{ height:1px; background:var(--line); border:0; margin:26px 0; }
.tablabel{ font-family:var(--mono); font-size:11px; letter-spacing:.14em; text-transform:uppercase;
  color:var(--muted); margin:6px 0 8px; }
.dtabs{ display:flex; flex-wrap:wrap; gap:8px; margin:0 0 22px; }
.dtab{ font:inherit; font-size:14.5px; font-weight:600; cursor:pointer; background:transparent;
  color:var(--muted); border:1px solid var(--line); border-radius:22px; padding:8px 18px; transition:.15s; }
.dtab.on{ background:var(--pc,var(--accent)); color:var(--pc-on,#fff); border-color:var(--pc,var(--accent)); }
.dtab:not(.on):hover{ border-color:var(--pc,var(--accent)); color:var(--ink); }
.oneissue{ background:var(--accent-soft); border:1px solid var(--line); border-left:5px solid var(--pc,var(--accent));
  border-radius:0 16px 16px 0; padding:20px 24px; margin-bottom:24px; }
.oi-label{ display:block; font-family:var(--mono); font-size:11.5px; letter-spacing:.06em;
  color:var(--pc,var(--accent)); margin-bottom:8px; font-weight:700; }
.oi-title{ font-family:var(--serif); font-weight:600; font-size:clamp(20px,3.4vw,27px);
  line-height:1.3; margin:0 0 8px; text-wrap:balance; }
.oi-why{ color:var(--muted); font-size:13.5px; margin:0 0 12px; }
.oi-more{ display:inline-block; margin-top:10px; font-family:var(--mono); font-size:12.5px;
  font-weight:600; color:var(--pc,var(--accent)); text-decoration:none; border:1px solid var(--pc,var(--accent));
  border-radius:20px; padding:7px 15px; transition:background .15s,color .15s; }
.oi-more:hover{ background:var(--pc,var(--accent)); color:var(--pc-on,#fff); }
.pkg{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 20px;
  margin-bottom:22px; box-shadow:var(--shadow); }
.pkg>summary{ font-family:var(--sans); font-weight:700; font-size:13px; color:var(--muted); cursor:pointer;
  list-style:none; letter-spacing:.02em; }
.pkg>summary::-webkit-details-marker{ display:none; }
.pkg>summary::before{ content:"▾ "; color:var(--accent); }
.pkg:not([open])>summary::before{ content:"▸ "; }
.pkg-list{ margin:12px 0 10px; padding-left:1.15em; display:grid; gap:7px; }
.pkg-list li{ font-size:13.5px; line-height:1.7; color:var(--ink); }
.pkg-list li::marker{ color:var(--accent); }
.pnews:empty{ display:none; }
.pnews{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:14px 18px;
  margin-bottom:22px; box-shadow:var(--shadow); }
.pnews-h{ font-family:var(--mono); font-size:11px; color:var(--muted); margin-bottom:8px; }
.pnewsitem{ display:block; text-decoration:none; color:var(--ink); font-size:13px; line-height:1.55;
  padding:7px 0; border-bottom:1px solid var(--line); }
.pnewsitem:last-child{ border-bottom:0; }
.pnewsitem:hover{ color:var(--accent); }
.pnews-s{ display:block; font-size:10.5px; color:var(--muted); margin-top:2px; }
.dgrid{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }
@media (max-width:660px){ .dgrid{ grid-template-columns:1fr; }
  /* スマホでは長文の本文・引用を少し大きく（読みやすさ優先） */
  .point{ font-size:14.5px; line-height:1.75; }
  blockquote{ font-size:14.5px; line-height:1.8; } }
.drow{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px;
  box-shadow:var(--shadow); display:flex; flex-direction:column; gap:10px; }
.drow-h{ display:flex; align-items:center; justify-content:space-between; gap:8px; }
.dmore{ display:flex; flex-wrap:wrap; gap:14px; margin-top:11px; padding-top:10px;
  border-top:1px dotted var(--line); }
.dmore a{ font-family:var(--mono); font-size:11.5px; color:var(--muted); text-decoration:none; }
.dmore a:hover{ color:var(--pc,var(--accent)); }
.dh-r{ display:flex; align-items:center; gap:8px; flex:none; }
.drow.dfocus{ border-color:var(--pc,var(--accent)); box-shadow:0 0 0 2px var(--accent-soft); }
.clip{ background:none; border:none; cursor:pointer; padding:2px; line-height:0; color:var(--line);
  transition:color .15s,transform .1s; -webkit-tap-highlight-color:transparent; }
.clip svg{ fill:none; stroke:currentColor; stroke-width:2; }
.clip:hover{ color:var(--muted); transform:translateY(-1px); }
.clip.on{ color:var(--pc,var(--accent)); }
.clip.on svg{ fill:currentColor; stroke:currentColor; }
.cliphint{ font-size:12px; color:var(--muted); margin:0 2px 20px; display:flex; align-items:center; gap:5px; flex-wrap:wrap; }
.clip-ic{ display:inline-flex; color:var(--muted); vertical-align:middle; }
.clip-ic svg{ fill:none; stroke:currentColor; stroke-width:2; }
.dname{ font-family:var(--serif); font-weight:600; font-size:16px; }
.tag{ font-family:var(--sans); font-size:11px; font-weight:600; color:var(--accent);
  background:var(--accent-soft); border-radius:20px; padding:3px 10px; white-space:nowrap; }
.point{ font-size:13px; margin:0; color:var(--ink); }
blockquote{ margin:0; padding:10px 13px; border-left:3px solid var(--accent); background:var(--paper);
  border-radius:0 8px 8px 0; font-size:13px; line-height:1.7; }
.oneissue blockquote{ background:var(--card); }
blockquote cite{ display:block; font-style:normal; font-family:var(--mono); font-size:10.5px;
  color:var(--muted); margin-top:6px; }
blockquote .evq{ font-family:var(--mono); font-size:11px; color:var(--accent); text-decoration:none;
  margin-left:8px; white-space:nowrap; }
blockquote .evq:hover{ text-decoration:underline; }
.say{ display:flex; flex-direction:column; gap:10px; }
.votes{ margin-top:auto; background:var(--paper); border:1px solid var(--line);
  border-radius:10px; padding:11px 13px; }
.vses{ display:flex; align-items:flex-start; gap:9px; padding:5px 0; }
.vses + .vses{ border-top:1px dotted var(--line); }
.vses .qbox{ flex:1; min-width:0; }
.qctx{ display:block; font-family:var(--mono); font-size:10.5px; font-weight:700;
  color:var(--muted); letter-spacing:.02em; margin-bottom:3px; }
.qtext{ margin:0; font-size:13.5px; line-height:1.75; color:var(--ink);
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical; overflow:hidden; }
.qcite{ margin:4px 0 0; font-family:var(--mono); font-size:10.5px; color:var(--muted); }
.qcite .evq{ margin-left:8px; }
.vsl{ flex:none; font-family:var(--mono); font-size:10px; font-weight:700; color:var(--muted);
  background:var(--card); border:1px solid var(--line); border-radius:6px; padding:3px 7px; margin-top:1px; }
.vlbl{ display:block; font-family:var(--mono); font-size:10px; letter-spacing:.1em;
  font-weight:700; color:var(--muted); margin-bottom:7px; }
.vlbl.gen{ color:var(--accent); }
.vrow{ display:flex; flex-wrap:wrap; gap:6px; }
.vchip{ display:inline-flex; flex-direction:column; align-items:center; gap:1px; font-size:10px;
  color:var(--muted); text-decoration:none; border:1px solid var(--line); border-radius:8px;
  padding:4px 8px; line-height:1.25; }
.vchip b{ font-size:11.5px; font-weight:700; }
.vchip.yes{ color:#2f8f7f; border-color:#2f8f7f66; background:#2f8f7f18; }
.vchip.yes b{ color:#2f8f7f; }
.vchip.no{ color:#c1704f; border-color:#c1704f66; background:#c1704f18; }
.vchip.no b{ color:#c1704f; }
.vchip.na b{ color:var(--muted); }
.vna{ font-size:11.5px; color:var(--muted); }
.miss{ font-size:12px; color:var(--muted); margin:16px 2px 0; }
.note{ margin-top:26px; font-size:12.5px; color:var(--muted); line-height:1.9; }
.note b{ color:var(--ink); }
a.src{ color:var(--accent); text-decoration:none; } a.src:hover{ text-decoration:underline; }
:focus-visible{ outline:2px solid var(--accent); outline-offset:2px; border-radius:4px; }
"""

JS = """
(function(){
  var tabs=document.querySelectorAll('.dtab'), panes=document.querySelectorAll('.pane');
  tabs.forEach(function(t){ t.addEventListener('click',function(){
    tabs.forEach(function(x){x.classList.remove('on');}); t.classList.add('on');
    panes.forEach(function(p){ p.hidden=(p.dataset.pane!==t.dataset.d); });
    window.scrollTo({top:0,behavior:'smooth'});
  }); });
})();
// ニュースページから ?domain=<分野> で来たとき、その分野のカードへ案内する
(function(){
  var d=new URLSearchParams(location.search).get('domain');
  if(!d) return;
  function focus(){
    var pane=document.querySelector('.pane:not([hidden])'); if(!pane) return;
    var row=[].slice.call(pane.querySelectorAll('.drow')).filter(function(r){
      var n=r.querySelector('.dname'); return n && n.textContent.trim()===d; })[0];
    if(!row) return;
    row.classList.add('dfocus');
    row.scrollIntoView({behavior:'smooth', block:'center'});
  }
  setTimeout(focus, 300);
  // 政党タブを切り替えても、同じ分野を追いかける
  document.querySelectorAll('.dtab').forEach(function(t){
    t.addEventListener('click', function(){
      document.querySelectorAll('.drow.dfocus').forEach(function(r){r.classList.remove('dfocus');});
      setTimeout(focus, 120);
    });
  });
})();
// 各党の最新ニュース(news.json の parties)を各党ペインに表示（同一フォルダ読み込み・無ければ何もしない）
fetch('news.json').then(function(r){return r.ok?r.json():null;}).then(function(nd){
  if(!nd||!nd.parties) return;
  function esc(s){return String(s).replace(/[&<>]/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]);});}
  document.querySelectorAll('.pnews').forEach(function(box){
    var list=nd.parties[box.dataset.pid]||[];
    if(!list.length) return;
    box.innerHTML='<div class="pnews-h">この党の最新ニュース'+(nd.updated?'（'+nd.updated+' 時点）':'')+'</div>'+
      list.map(function(h){return '<a class="pnewsitem" href="'+h.u+'" target="_blank" rel="noopener">'+
        esc(h.t)+'<span class="pnews-s">'+esc(h.s||'')+'</span></a>';}).join('');
  });
}).catch(function(){});
// マイノート(クリップ): 各分野カードのしおりで localStorage(kg_notes) に保存/解除
var CLIP = __CLIP__;
(function(){
  function get(){ try{ return JSON.parse(localStorage.getItem('kg_notes')||'{}'); }catch(e){ return {}; } }
  function save(o){ localStorage.setItem('kg_notes', JSON.stringify(o)); if(window.KGNOTE) KGNOTE.refresh(); }
  var notes=get();
  document.querySelectorAll('.clip').forEach(function(b){
    var id=b.dataset.clip;
    if(notes[id]) b.classList.add('on');
    b.addEventListener('click', function(e){
      e.preventDefault(); e.stopPropagation();
      var n=get();
      if(n[id]){ delete n[id]; b.classList.remove('on'); }
      else if(CLIP[id]){ n[id]=CLIP[id]; b.classList.add('on'); }
      save(n);
    });
  });
})();
"""
JS = JS.replace("__CLIP__", json.dumps(CLIP_CAT, ensure_ascii=False))

HTML = f'''<title>AI政策くらべ — 政党で選ぶ（比例区）v1.5</title>
<style>{CSS}</style>
<div class="wrap"><div class="doc">
  <p class="eyebrow">比例区・投票ガイド ／ v1.5「政党で選ぶ」</p>
  <h1>まず政党を選ぶ。その党の「ワンイシュー」と、全政策の言と行を見る</h1>
  <p class="lede">タブで政党を選ぶと、その党が<b>特に重視する1点（ワンイシュー）</b>と、
  財政・外交・社会保障などの各分野での<b>言（国会発言）と行（参院採決）</b>が出ます。
  一致か乖離かは判定せず、<b>点数も格付けもしません</b>。発言も採決も全て原典リンク付き。</p>
  <hr class="rule">
  <p class="tablabel">▼ 政党を選ぶ</p>
  <div class="dtabs">{''.join(tabs)}</div>
  <p class="cliphint">各分野カード右上の<span class="clip-ic"><svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true"><path d="M6 3.6h12a1 1 0 0 1 1 1v16.1l-7-4.1-7 4.1V4.6a1 1 0 0 1 1-1z"/></svg></span>しおりで保存すると、右下の「マイノート」で党を横断して比較できます。</p>
  {''.join(panes)}
  <p class="note">
    <b>ワンイシューについて：</b>各党が特に重視する1点を、国会での言動から<b>編集の判断</b>で1つに絞ったものです（根拠となる実発言にリンク）。
    この項目への共感を第1問に、他の政策との整合も合わせて「どの党が自分に近いか」を照らし合わせる「政策で照らす」も用意しています。<br>
    <b>データの出どころ：</b>言＝<a class="src" href="https://kokkai.ndl.go.jp/" target="_blank" rel="noopener">国会会議録検索システム</a>（第217回・第219回・第221回の3会期を併記）。
    行＝参議院 記名投票の会派別賛否（<a class="src" href="https://www.sangiin.go.jp/japanese/touhyoulist/217/vote_ind.htm" target="_blank" rel="noopener">第217回</a>・<a class="src" href="https://www.sangiin.go.jp/japanese/touhyoulist/219/vote_ind.htm" target="_blank" rel="noopener">第219回</a>・<a class="src" href="https://www.sangiin.go.jp/japanese/touhyoulist/221/vote_ind.htm" target="_blank" rel="noopener">第221回</a>の3会期を併記）。憲法分野は記名投票の議案が無く「行」は該当なし。<br>
    <b>会期を並べている理由：</b>同じ党でも会期によって賛否が変わることがあります。どちらが良いという評価はせず、事実として並べています。第217回と第221回の間に選挙があり、会派の構成も変わりました。<br>
    <b>衆参の扱いが異なります：</b>発言（言）は<b>衆議院・参議院の両方</b>から採っています（引用に議院と委員会を明記）。一方、採決（行）は<b>参議院のみ</b>です。衆議院の本会議は原則として起立採決で、会派別・個人別の賛否が公式記録に残らないためです。<br><b>賛否は「結果」であり「理由」ではありません：</b>各党は「方向性には賛成だが規定が不十分」等の複雑な理由で反対することもあります。
    賛否だけで是非を判断せず、反対・賛成の<b>理由や討論は原典（会議録・記名投票結果）</b>でご確認ください。<br>
    <b>正直な断り：</b>「ワンイシュー」「力点」は編集要約で党の公式見解そのものではありません。参政党は第217回国会では会派未結成のため賛否記録がありませんが、第221回国会では会派を結成しており賛否が記録されています。判断は必ず原典リンクで裏取りを。
    データの作り方・選定基準・限界は<a class="src" href="about.html">▸ このサイトについて（方法論）</a>で公開しています。
  </p>
</div></div>
<script>{JS}</script>'''

open("policy_guide.html","w",encoding="utf-8").write(HTML)
print("wrote party-major policy_guide.html", len(HTML), "bytes / parties:", len(PARTIES))
