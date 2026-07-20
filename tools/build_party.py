# -*- coding: utf-8 -*-
"""政策くらべ v1.1 「政党で選ぶ」= 党タブ主体。
既存 build_guide.py のデータ(46発言+投票)・整形関数を再利用し、行列を転置して党ごとに表示。
各党に『ワンイシュー』(特に重視する1点)を新設。"""
import html, json

# --- 既存ファイルを実行して、データと関数を取り込む(policy_guide.htmlは後で上書き) ---
ns = {}
exec(open("build_guide.py", encoding="utf-8").read(), ns)
esc          = ns["esc"]
clean_quote  = ns["clean_quote"]
votes_html   = ns["votes_html"]
NO_VOTE_BLOCK= ns["NO_VOTE_BLOCK"]
VBASE        = ns.get("VBASE", "https://www.sangiin.go.jp/japanese/touhyoulist/217/")

DOMAIN_ORDER = [
    ("財政",          ns["FISCAL"], ns["FVOTES"], ns["FLABEL"]),
    ("外交・安保",     ns["DIPLO"],  ns["DVOTES"], ns["DLABEL"]),
    ("社会保障",       ns["SOCIAL"], ns["SVOTES"], ns["SLABEL"]),
    ("エネルギー・環境", ns["ENERGY"], ns["EVOTES"], ns["ELABEL"]),
    ("経済・産業",     ns["ECON"],   ns["CVOTES"], ns["CLABEL"]),
    ("憲法",          ns["KENPO"],  None,         None),
]
PARTIES = [("自由民主党","自民"),("立憲民主党","立憲"),("日本維新の会","維新"),
           ("国民民主党","国民"),("公明党","公明"),("日本共産党","共産"),
           ("れいわ新選組","れいわ"),("参政党","参政")]
PARTY_IDMAP = {"自由民主党":"jimin","立憲民主党":"rikken","日本維新の会":"ishin","国民民主党":"kokumin",
               "公明党":"komei","日本共産党":"kyosan","れいわ新選組":"reiwa","参政党":"sansei"}
# 各党のイメージカラー（各党公式サイト基準・報道慣例を参考。build_site.py と同一）
PARTY_COLOR = {"自由民主党":"#E60012","立憲民主党":"#004097","日本維新の会":"#12A150","国民民主党":"#F2B200",
               "公明党":"#F55881","日本共産党":"#D7003A","れいわ新選組":"#E4007F","参政党":"#E8630A"}
def pc_on(hx):
    r,g,b=int(hx[1:3],16),int(hx[3:5],16),int(hx[5:7],16)
    return "#1b2130" if (0.299*r+0.587*g+0.114*b)>150 else "#ffffff"

# 党→領域→(entry, votes, labels)
PIDX = {full: {} for full,_ in PARTIES}
for dname, lst, votes, labels in DOMAIN_ORDER:
    for e in lst:
        if e["party"] in PIDX:
            PIDX[e["party"]][dname] = (e, votes, labels)

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
    e = PIDX[full][ref][0]
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
    vk = entry.get("vkey")
    if votes is not None and vk:
        for i, b in enumerate(votes["bills"]):
            st = next((v["stance"] for name, v in b["parties"].items() if vk in name), None)
            vlist.append({"l": labels[i], "st": st or "—", "u": VBASE + b["id"] + ".htm"})
    CLIP_CAT[cid] = {"party": short, "pc": PARTY_COLOR[full], "dom": dname,
                     "point": entry["point"], "quote": clean_quote(entry["quote"]),
                     "who": entry["who"], "url": entry["url"], "votes": vlist}
    return cid

def domain_row(dname, entry, votes, labels, cid):
    tag = f'<span class="tag">◉ {esc(entry["tag"])}</span>' if entry.get("tag") else ""
    clip = (f'<button class="clip" type="button" data-clip="{cid}" aria-label="この分野をマイノートに保存" '
            f'title="マイノートに保存"><svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true">'
            f'<path d="M6 3.6h12a1 1 0 0 1 1 1v16.1l-7-4.1-7 4.1V4.6a1 1 0 0 1 1-1z"/></svg></button>')
    vblock = NO_VOTE_BLOCK if votes is None else votes_html(entry["vkey"], votes, labels)
    return (f'<article class="drow"><div class="drow-h">'
            f'<span class="dname">{esc(dname)}</span><span class="dh-r">{tag}{clip}</span></div>'
            f'<div class="say"><span class="vlbl gen">言 ／ 国会での発言</span>'
            f'<p class="point">{esc(entry["point"])}</p>{quote_block(entry)}</div>{vblock}</article>')

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
        _rows.append(domain_row(dn, _e, _v, _l, _cid))
    rows = "".join(_rows)
    missing = [dn for dn,_,_,_ in DOMAIN_ORDER if dn not in PIDX[full]]
    miss = (f'<p class="miss">※この党は当会期の {("・".join(missing))} 分野で会派としての代表発言・採決が確認できず、掲載を見送りました。</p>'
            if missing else "")
    panes.append(f'<section class="pane" data-pane="{i}" '
                 f'style="--pc:{PARTY_COLOR[full]};--pc-on:{pc_on(PARTY_COLOR[full])}"{"" if i==0 else " hidden"}>'
                 f'{oneissue_block(full)}{package_block(full)}'
                 f'<div class="pnews" data-pid="{PARTY_IDMAP.get(full,"")}"></div>'
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
.dh-r{ display:flex; align-items:center; gap:8px; flex:none; }
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

HTML = f'''<title>政策くらべ — 政党で選ぶ（比例区）v1.5</title>
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
    <b>データの出どころ：</b>言＝<a class="src" href="https://kokkai.ndl.go.jp/" target="_blank" rel="noopener">国会会議録検索システム</a>第217回国会。
    行＝<a class="src" href="https://www.sangiin.go.jp/japanese/touhyoulist/217/vote_ind.htm" target="_blank" rel="noopener">参議院 記名投票の会派別賛否</a>。憲法分野は記名投票の議案が無く「行」は該当なし。<br>
    <b>賛否は「結果」であり「理由」ではありません：</b>各党は「方向性には賛成だが規定が不十分」等の複雑な理由で反対することもあります。
    賛否だけで是非を判断せず、反対・賛成の<b>理由や討論は原典（会議録・記名投票結果）</b>でご確認ください。<br>
    <b>正直な断り：</b>「ワンイシュー」「力点」は編集要約で党の公式見解そのものではありません。参政党は会派未結成のため会派別の採決記録がありません。判断は必ず原典リンクで裏取りを。
    データの作り方・選定基準・限界は<a class="src" href="about.html">▸ このサイトについて（方法論）</a>で公開しています。
  </p>
</div></div>
<script>{JS}</script>'''

open("policy_guide.html","w",encoding="utf-8").write(HTML)
print("wrote party-major policy_guide.html", len(HTML), "bytes / parties:", len(PARTIES))
