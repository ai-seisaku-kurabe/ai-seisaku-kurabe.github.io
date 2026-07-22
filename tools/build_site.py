# -*- coding: utf-8 -*-
"""デプロイ用一式を site/ に出力してzip化。
- 既存の policy_guide.html / shindan.html / shukei.html を生成→ナビ挿入・相対リンク・Firebase配線
- index.html(トップ), firebase.js, firestore.rules, README.md を新規生成
Firebase未設定でも全ページ動作(送信/集計だけ無効)。設定を firebase.js に貼れば集計有効化。"""
import html, json, os, shutil, re, urllib.parse

def _roster():
    """統一会派の議員名簿。開示文をここから組み立て、実名を埋め込まない。"""
    try:
        d = json.load(open("roster.json", encoding="utf-8"))
    except Exception:
        return {}, []
    return d.get("members", {}), d.get("unresolved", [])

ROSTER_MEMBERS, ROSTER_UNRESOLVED = _roster()

def _shugiin_stat(path="221_shugiin_votes.json"):
    """衆院採決の開示に使う数値。手で書くとデータとずれるので、必ずここから作る。"""
    try:
        b = json.load(open(path, encoding="utf-8"))["bills"][0]
        return {"total": b["reported"]["total"], "unidentified": b["unidentified"],
                "later": b.get("inferred_later", 0), "independent": b["independent"]}
    except Exception:
        return {"total": 0, "unidentified": 0, "later": 0, "independent": 0}

SHUGIIN_STAT = _shugiin_stat()

def roster_note(short=False):
    """発言の収集範囲についての開示。名簿の中身から毎回生成する。

    会派名も議員名も文面に書き込まない。会派は再編され、議員は入れ替わるので、
    写しを作れば必ず実態とずれる（「衆議院には」と書いていた間に、参議院の
    「立憲民主・社民・無所属」が対象に加わって記述が古びた）。
    """
    if not ROSTER_MEMBERS:
        return ""
    n = len(ROSTER_MEMBERS)
    un = ROSTER_UNRESOLVED
    caucuses = sorted({v.get("group", "") for v in ROSTER_MEMBERS.values() if v.get("group")})
    names = "」「".join(esc(c) for c in caucuses)
    body = (f"国会には、会派名だけでは所属党が分からない統一会派があります"
            f"（現在は「{names}」）。そこで<b>同じ議員の過去の発言に付いている会派名</b>から"
            f"所属党を割り出し、{n}名を特定しています。")
    if un:
        body += ("過去の発言記録が無く党を特定できない"
                 f"<b>{len(un)}名（{'・'.join(esc(x) for x in un)}）は掲載していません。</b>")
    body += ("また、統一会派の議員が<b>会派を代表して行った討論は掲載しません</b>。"
             "会派としての合意であり、単独の党の主張ではないためです。")
    return body

ns={}
exec(open("build_shindan.py",encoding="utf-8").read(), ns)   # -> shindan.html, PARTIES, POLICY
exec(open("build_party.py",encoding="utf-8").read(), {})     # -> policy_guide.html
exec(open("build_shukei.py",encoding="utf-8").read(), {})    # -> shukei.html(サンプル)
PARTIES=ns["PARTIES"]; POLICY=ns["POLICY"]

ID={"自由民主党":"jimin","立憲民主党":"rikken","日本維新の会":"ishin","国民民主党":"kokumin",
    "公明党":"komei","日本共産党":"kyosan","れいわ新選組":"reiwa","参政党":"sansei",
    "チームみらい":"mirai","社会民主党":"shamin","none":"none"}
# 各党のイメージカラー（各党公式サイト基準・報道慣例を参考。認識性優先で微調整）
PC={"自由民主党":"#E60012","立憲民主党":"#004097","日本維新の会":"#12A150","国民民主党":"#F2B200",
    "公明党":"#F55881","日本共産党":"#D7003A","れいわ新選組":"#E4007F","参政党":"#E8630A",
    "チームみらい":"#00B8C4","社会民主党":"#0B60A8"}
def on_color(hx):
    r,g,b=int(hx[1:3],16),int(hx[3:5],16),int(hx[5:7],16)
    return "#1b2130" if (0.299*r+0.587*g+0.114*b)>150 else "#ffffff"
def esc(s): return html.escape(str(s))

# ---------- 共通ナビ（スクロールしても常時表示のスティッキーヘッダ） ----------
NAV_CSS=("<style>"
  "html{scroll-padding-top:64px;}"
  ".sitehdr{position:sticky;top:0;z-index:100;background:var(--paper);"
  # .wrap の上・左右パディングを打ち消して画面幅いっぱいのバーにする
  "margin:calc(-1*clamp(20px,5vw,56px)) calc(-1*clamp(16px,5vw,40px)) 26px;"
  "padding:10px clamp(16px,5vw,40px);border-bottom:1px solid var(--line);}"
  ".sitehdr-in{max-width:900px;margin:0 auto;display:flex;align-items:center;gap:12px;}"
  ".brand{font-family:var(--serif);font-weight:600;font-size:15px;color:var(--ink);"
  "text-decoration:none;white-space:nowrap;}.brand span{color:var(--accent);}"
  ".topnav{display:flex;flex-wrap:wrap;gap:6px;margin-left:auto;"
  "font-family:var(--mono);font-size:12px}.topnav a{color:var(--muted);text-decoration:none;"
  "border:1px solid var(--line);border-radius:20px;padding:5px 11px}"
  ".topnav a:hover{border-color:var(--accent);color:var(--accent)}"
  ".topnav a.cur{background:var(--accent);color:#fff;border-color:var(--accent)}"
  "@media(max-width:600px){.sitehdr{padding:8px clamp(16px,5vw,40px);}.sitehdr-in{gap:10px;}"
  ".brand{flex:none;font-size:14px;}"
  # スマホは1行のまま横スクロール（縦に伸びてスクロールを邪魔しない）
  ".topnav{flex:1;min-width:0;margin-left:6px;flex-wrap:nowrap;overflow-x:auto;"
  "-webkit-overflow-scrolling:touch;scrollbar-width:none;font-size:11.5px;gap:5px;}"
  ".topnav::-webkit-scrollbar{display:none;}"
  ".topnav a{flex:none;white-space:nowrap;padding:5px 10px;}}"
  "</style>")
def nav(cur):
    # ヘッダーは「情報の入口」だけに絞る。二次的な導線はフッターへ（項目が増えても崩れないように）
    items=[("index.html","トップ"),("guide.html","政党で選ぶ"),("oneissue.html","ワンイシュー"),
           ("shindan.html","政策で照らす"),("news.html","ニュース")]
    a="".join(f'<a href="{h}"{" class=\"cur\"" if h==cur else ""}>{t}</a>' for h,t in items)
    return (NAV_CSS+'<header class="sitehdr"><div class="sitehdr-in">'
            '<a class="brand" href="index.html">AI政策<span>くらべ</span></a>'
            f'<nav class="topnav">{a}</nav></div></header>')
def inject_nav(src, cur):
    return src.replace('<div class="wrap"><div class="doc">',
                       '<div class="wrap">'+nav(cur)+'<div class="doc">', 1)

FB_TAGS=('\n<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-compat.js"></script>'
  '\n<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-firestore-compat.js"></script>'
  '\n<script src="https://www.gstatic.com/firebasejs/10.12.0/firebase-app-check-compat.js"></script>'
  '\n<script src="firebase.js"></script>')

os.makedirs("site", exist_ok=True)

# ---------- guide.html ----------
guide=open("policy_guide.html",encoding="utf-8").read()
guide=inject_nav(guide,"guide.html")
open("site/guide.html","w",encoding="utf-8").write(guide)

# ---------- shindan.html (ナビ + Firebase送信) ----------
shindan=open("shindan.html",encoding="utf-8").read()
shindan=inject_nav(shindan,"shindan.html")
# compute内 render 呼び出し直後に送信を挿入
shindan=shindan.replace(
  "render(res, pick, ans.filter(a=>a!==0).length);",
  "render(res, pick, ans.filter(a=>a!==0).length);\n"
  "  try{ if(window.KG&&KG.sendResult&&!localStorage.getItem('kg_sent')){ KG.sendResult(pick, ans, wts); localStorage.setItem('kg_sent','1'); } }catch(e){}",1)
shindan=shindan+FB_TAGS
open("site/shindan.html","w",encoding="utf-8").write(shindan)

# ---------- shukei.html (ナビ + Firebaseから実データ描画) ----------
OI_JS=[{"id":ID[p["full"]],"short":p["short"],"oneissue":p["oneissue"]} for p in PARTIES]
OI_JS.append({"id":"none","short":"（特にない）","oneissue":"ワンイシューにこだわらない"})
QS_JS=[q["q"] for q in POLICY]
QSHORT_JS=["消費税減税","防衛費増額","年金改革の支持","脱炭素・GX","憲法改正","財政健全化を優先",
           "日米同盟の強化","原発の活用","外国人受け入れ規制","教育の無償化"]

# 集計スナップショット用のメタ情報（設問・判定・根拠）。研究用に数字の意味を復元できるようにする。
SNAP_META = json.dumps({
    "session": "第221回国会",
    "questions": [{"q": q["q"], "kind": q.get("kind", "core"),
                   "basis": q.get("basis", ""), "basis_url": q.get("basis_url", ""),
                   "stance": q["stance"]} for q in POLICY],
    "caveat": "自己選択サンプルであり、世論調査ではありません。回答した人の傾向を示すだけの参考値です。",
}, ensure_ascii=False)

SHUKEI_JS=("<script>(function(){if(!window.KG)return;"
  f"var OI={json.dumps(OI_JS,ensure_ascii=False)};var QS={json.dumps(QS_JS,ensure_ascii=False)};"
  f"var QSHORT={json.dumps(QSHORT_JS,ensure_ascii=False)};"
  "function esc(s){return String(s).replace(/[&<>]/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]);});}"
  "function render(agg){var total=agg.responses||0;if(!total)return;"
  "document.getElementById('totalN').innerHTML=total.toLocaleString()+'<small> 件の回答</small>';"
  "var ci=OI.map(function(o){return{o:o,n:agg['oi_'+o.id]||0};});ci.sort(function(a,b){return b.n-a.n;});"
  "document.getElementById('cCard').innerHTML=ci.map(function(it){var p=total?Math.round(it.n/total*100):0;"
  "return '<div class=\"crow\"><div class=\"cnm\"><b>'+esc(it.o.short)+'</b><span>'+esc(it.o.oneissue)+"
  "'</span></div><div class=\"cbarwrap\"><div class=\"cbar\" style=\"width:'+p+'%\"></div></div>'+"
  "'<div class=\"cval\">'+p+'%<small>'+it.n+'</small></div></div>';}).join('');"
  "document.getElementById('bCard').innerHTML=QS.map(function(q,i){"
  "var a=agg['p'+i+'_agree']||0,n=agg['p'+i+'_neutral']||0,o=agg['p'+i+'_oppose']||0;var t=a+n+o||1;"
  "var pa=Math.round(a/t*100),pn=Math.round(n/t*100),po=Math.round(o/t*100);"
  "return '<div class=\"bq\"><p class=\"bq-q\"><span class=\"bq-n\">Q'+(i+2)+'</span>'+esc(q)+'</p>'+"
  "'<div class=\"bseg\"><div class=\"sg agree\" style=\"width:'+pa+'%\"></div><div class=\"sg neu\" style=\"width:'+pn+'%\"></div>'+"
  "'<div class=\"sg opp\" style=\"width:'+po+'%\"></div></div><div class=\"bkey\"><span class=\"k agree\">賛成 '+pa+'%</span>'+"
  "'<span class=\"k neu\">どちらでもない '+pn+'%</span><span class=\"k opp\">反対 '+po+'%</span></div></div>';}).join('');"
  "var dc=document.getElementById('dCard');if(dc){var dr=QSHORT.map(function(l,i){return{l:l,n:agg['wt'+i]||0};});"
  "dr.sort(function(a,b){return b.n-a.n;});dc.innerHTML=dr.map(function(it){var p=total?Math.round(it.n/total*100):0;"
  "return '<div class=\"crow\"><div class=\"cnm\"><b>'+esc(it.l)+'</b></div><div class=\"cbarwrap\">'+"
  "'<div class=\"cbar\" style=\"width:'+p+'%\"></div></div><div class=\"cval\">'+p+'%<small>'+it.n+'</small></div></div>';}).join('');}"
  "var d=document.getElementById('demoBadge');if(d)d.style.display='none';}"
  "KG.loadAgg().then(function(agg){if(agg&&agg.responses)render(agg);});})();</script>")
shukei=open("shukei.html",encoding="utf-8").read()
shukei=inject_nav(shukei,"shukei.html")
# shindan/index への相対リンクは既に相対(shindan.html/index.html)
shukei=shukei+FB_TAGS+SHUKEI_JS+("<script>(function(){""var META=" + SNAP_META + ";"
  # GitHub Pages が config.json に10分のキャッシュ(Cache-Control: max-age=600)を付けるため、
  # no-store で毎回取得しないと election_mode の停止スイッチが最大10分効かない。
  "fetch('config.json', { cache: 'no-store' }).then(function(r){return r.json();}).then(function(cfg){""if(!cfg||!cfg.election_mode)return;""var d=document.querySelector('.doc');if(!d)return;""var box=document.createElement('div');box.className='sk-pause';""box.innerHTML='<b>集計の公開を一時停止しています。</b><br>'+ (cfg.election_notice||'');""var keep=d.querySelector('.topnav');""[].slice.call(d.children).forEach(function(el){if(el!==keep&&!el.classList.contains('eyebrow')&&el.tagName!=='H1')el.remove();});""d.appendChild(box);""}).catch(function(){});""var btn=document.getElementById('snapBtn');""if(btn)btn.addEventListener('click',function(){""if(!window.KG||!KG.loadAgg){alert('集計を読み込めません');return;}""KG.loadAgg().then(function(agg){""var snap={captured_at:new Date().toISOString(),session:META.session,""responses:(agg&&agg.responses)||0,questions:META.questions,""aggregate:agg||{},caveat:META.caveat};""var b=new Blob([JSON.stringify(snap,null,1)],{type:'application/json'});""var a=document.createElement('a');a.href=URL.createObjectURL(b);""var t=new Date();a.download='snapshot-'+t.getFullYear()+'-'+String(t.getMonth()+1).padStart(2,'0')+'.json';""a.click();URL.revokeObjectURL(a.href);});});""})();</script>")
open("site/shukei.html","w",encoding="utf-8").write(shukei)

# ---------- index.html ----------
party_cards="".join(
  f'<a class="pcard" href="guide.html" style="--pc:{PC[p["full"]]}">'
  f'<span class="ps"><i class="pdot"></i>{esc(p["short"])}</span>'
  f'<span class="poi">{esc(p["oneissue"])}</span></a>' for p in PARTIES)
INDEX_CSS="""
:root{ --paper:#f3f4f7; --card:#fbfbfd; --ink:#1b2130; --muted:#5c6675; --line:#dcdfe6;
  --accent:#3a4d8f; --accent-soft:#e6e9f4; --shadow:0 1px 2px rgba(20,28,50,.05),0 8px 24px rgba(20,28,50,.05); }
@media(prefers-color-scheme:dark){ :root{ --paper:#12151d; --card:#191d27; --ink:#e7eaf1; --muted:#98a1b2;
  --line:#282e3b; --accent:#8ea2e6; --accent-soft:#222a40; --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);} }
:root[data-theme="dark"]{ --paper:#12151d;--card:#191d27;--ink:#e7eaf1;--muted:#98a1b2;--line:#282e3b;--accent:#8ea2e6;--accent-soft:#222a40; }
:root[data-theme="light"]{ --paper:#f3f4f7;--card:#fbfbfd;--ink:#1b2130;--muted:#5c6675;--line:#dcdfe6;--accent:#3a4d8f;--accent-soft:#e6e9f4; }
*{box-sizing:border-box;}
.wrap{ --serif:"Hiragino Mincho ProN","Yu Mincho",YuMincho,"Noto Serif JP",serif;
  --sans:"Hiragino Kaku Gothic ProN","Yu Gothic",YuGothic,"Noto Sans JP",Meiryo,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  background:var(--paper);color:var(--ink);font-family:var(--sans);line-height:1.7;
  -webkit-font-smoothing:antialiased;padding:clamp(20px,5vw,56px) clamp(16px,5vw,40px);}
.doc{max-width:900px;margin:0 auto;}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.16em;text-transform:uppercase;color:var(--accent);margin:0 0 12px;}
h1{font-family:var(--serif);font-weight:600;font-size:clamp(26px,5vw,42px);line-height:1.28;text-wrap:balance;margin:0 0 14px;}
.lede{color:var(--muted);font-size:15px;max-width:62ch;margin:0 0 26px;}
.lede b{color:var(--ink);}
.nav2{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-bottom:34px;}
@media(max-width:640px){.nav2{grid-template-columns:1fr;}}
.big{position:relative;display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--line);
  border-radius:16px;padding:22px 44px 22px 22px;box-shadow:var(--shadow);transition:transform .1s,border-color .15s;}
.big:hover{transform:translateY(-2px);border-color:var(--accent);}
.big .k{font-family:var(--mono);font-size:11px;letter-spacing:.1em;color:var(--accent);text-transform:uppercase;}
.big .t{font-family:var(--serif);font-size:21px;font-weight:600;margin:8px 0 4px;}
.big .s{font-size:12.5px;color:var(--muted);line-height:1.7;}
.big .arw{position:absolute;right:18px;top:50%;transform:translateY(-50%);font-family:var(--mono);
  font-size:18px;color:var(--line);transition:.15s;}
.big:hover .arw{color:var(--accent);right:14px;}
.big.primary{margin-bottom:14px;padding:24px 26px;border:2px solid var(--accent);background:var(--accent-soft);
  display:flex;flex-direction:column;align-items:flex-start;}
.big.primary .t{font-size:clamp(22px,4vw,27px);color:var(--accent);margin:6px 0 6px;}
.big.primary .s{font-size:13.5px;}
.big.primary .go{margin-top:16px;font-family:var(--mono);font-size:13.5px;font-weight:700;color:#fff;
  background:var(--accent);border-radius:24px;padding:11px 24px;transition:.15s;}
.big.primary:hover .go{padding-left:28px;padding-right:28px;}
.sec{font-family:var(--serif);font-size:20px;font-weight:600;margin:0 0 4px;}
.sec-s{color:var(--muted);font-size:13px;margin:0 0 16px;}
.pgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
@media(max-width:600px){.pgrid{grid-template-columns:1fr;}}
.pcard{position:relative;display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--line);
  border-left:4px solid var(--pc,var(--accent));border-radius:14px;padding:15px 34px 15px 18px;transition:border-color .15s,transform .1s;}
.pcard:hover{border-color:var(--pc,var(--accent));transform:translateY(-2px);box-shadow:var(--shadow);}
.pcard::after{content:"›";position:absolute;right:15px;top:50%;transform:translateY(-50%);
  font-size:22px;line-height:1;color:var(--line);transition:.15s;}
.pcard:hover::after{color:var(--pc,var(--accent));right:11px;}
.ps{display:flex;align-items:center;gap:8px;font-family:var(--serif);font-weight:600;font-size:16px;}
.pdot{flex:none;width:10px;height:10px;border-radius:50%;background:var(--pc,var(--accent));}
.poi{display:block;font-size:12px;color:var(--muted);margin-top:3px;}
.note{margin-top:28px;font-size:12px;color:var(--muted);line-height:1.85;}
"""
INDEX=f'''<title>AI政策くらべ — 中身で選ぶ投票ガイド</title>
<style>{INDEX_CSS}</style>
<div class="wrap">{nav("index.html")}<div class="doc">
  <p class="eyebrow">比例区・投票ガイド</p>
  <h1>知名度でなく、中身で選ぶ。</h1>
  <p class="lede">各党が国会で<b>何を論じ、どう投票したか（言と行）</b>を基に、政策で投票先を考えるためのサイトです。
  国会会議録と参議院の記名投票という<b>一次情報</b>にもとづき、<b>点数化も格付けもしません</b>。</p>
  <p class="lede" style="margin-top:-14px"><b>AIの役割：</b>AIは膨大な国会の記録を<b>集めて整理し、並べる</b>ところまでを担います。
  「どの党が優れているか」といった<b>評価はしません</b>。判断はあなたに返します。
  そのために守っているルールは<a class="src" href="about.html" style="color:var(--accent);text-decoration:none">▸ 全文公開</a>しています。</p>
  <a class="big primary" href="shindan.html">
    <span class="k">▶ まずはこちらから</span><div class="t">政策で照らす</div>
    <div class="s">あなたの考えと、各党の言と行（実績）を照らし合わせ、どこが交差しどこがズレるかを表示（重視する争点は加重）。所要2〜3分・登録不要。</div>
    <span class="go">照らしてみる →</span></a>
  <div class="nav2">
    <a class="big" href="guide.html"><span class="k">見る</span><div class="t">政党で選ぶ</div>
      <div class="s">各党のワンイシューと6分野の言と行を、原典リンク付きで確認</div><span class="arw">→</span></a>
    <a class="big" href="shukei.html"><span class="k">集計</span><div class="t">みんなの結果</div>
      <div class="s">「政策で照らす」に答えた人の傾向（参考値・自己選択サンプル）</div><span class="arw">→</span></a>
  </div>
  <p class="sec">各政党の政策パッケージ</p>
  <p class="sec-s">カードを押すと、その党の全分野の言と行（政党で選ぶ）へ進みます。</p>
  <div class="pgrid">{party_cards}</div>
  <p class="note">出典：国会会議録検索システム／参議院 記名投票結果（第217回国会）。
  各党の立場や要約は編集判断を含みます。必ず原典リンクで裏取りしてください。<br>
  データの作り方・編集の判断・限界（点数化しない理由など）は
  <a class="src" href="about.html" style="color:var(--accent);text-decoration:none">▸ このサイトについて（方法論）</a>で公開しています。</p>
</div></div>'''
open("site/index.html","w",encoding="utf-8").write(INDEX)

# ---------- feedback.html (Netlify Forms) ----------
FEEDBACK_CSS = """
form.fb{ display:flex; flex-direction:column; gap:16px; max-width:620px; margin-top:8px; }
form.fb label{ font-size:13.5px; font-weight:600; color:var(--ink); display:flex; flex-direction:column; gap:6px; }
form.fb textarea, form.fb input[type=email], form.fb select{ font:inherit; font-size:14px; color:var(--ink);
  background:var(--card); border:1px solid var(--line); border-radius:10px; padding:11px 13px; width:100%; }
form.fb textarea{ resize:vertical; min-height:130px; }
form.fb .req{ color:#c1704f; font-weight:700; font-size:11px; margin-left:4px; }
.fb-hp{ position:absolute; left:-9999px; height:0; overflow:hidden; }
.fb-btn{ align-self:flex-start; font:inherit; font-weight:600; font-size:15px; cursor:pointer;
  border:1px solid var(--accent); background:var(--accent); color:#fff; border-radius:12px; padding:12px 30px; }
.fb-btn:hover{ opacity:.92; }
.fb-btn:disabled{ opacity:.5; cursor:not-allowed; }
.fb-thanks{ background:var(--accent-soft); border:1px solid var(--line); border-radius:14px; padding:22px 24px;
  font-size:14px; line-height:1.8; }
.fb-note{ font-size:12px; color:var(--muted); line-height:1.9; margin-top:22px; }
a.src{ color:var(--accent); text-decoration:none; } a.src:hover{ text-decoration:underline; }
.fb-msg{ font-size:13px; color:var(--muted); margin:0; min-height:1.2em; }
.fb-msg.err{ color:#c1704f; font-weight:600; }
.fb-count{ font-size:11.5px; color:var(--muted); align-self:flex-end; }
"""
FEEDBACK_FORM = ('  <p class="eyebrow">ご意見・お問い合わせ</p>'
  '<h1>このサイトへのご意見をお寄せください</h1>'
  '<p class="lede">誤りの指摘・機能の要望・感想など、なんでも歓迎です。いただいた声は<b>サイトの改善に活用</b>します。</p>'
  '<div id="fbWrap">'
  '<form class="fb" id="fbForm">'
  '<label>ご意見<span class="req">必須</span>'
  # 例文は置かない。例を示すと、その種類の意見しか来なくなる（誤りの指摘に寄った例を
  # 出していたため、感想や要望が送りにくくなっていた）。
  '<textarea id="fbText" maxlength="2000" required></textarea></label>'
  '<span class="fb-count" id="fbCount">0 / 2000 字</span>'
  '<button class="fb-btn" id="fbBtn" type="submit">送信する</button>'
  '<p class="fb-msg" id="fbMsg"></p>'
  '</form></div>'
  '<p class="fb-note">'
  # ⑦応答班: 「運営者だけが読む」から「補助AIも読む・要旨を公開することがある」への開示改定。
  # 公開の約束の変更なのでPR必須。適用は掲載後に届いたご意見のみ(境界時刻はfeedback_log.json)。
  '・<b>いただいた本文は、そのままの形では公開しません。</b>読むのは運営者と、'
  '運営者の作業を補助するAI（Claude）です。AIが読む際、本文は外部のAI事業者'
  '（Anthropic）のAPIに送信され、同社の定めに従って一定期間保持されることがあります'
  '（<a class="src" href="https://www.anthropic.com/legal/privacy" target="_blank" rel="noopener">同社のプライバシーポリシー</a>）。<br>'
  '・<b>採否の記録として、運営者が書き直した要旨を公開することがあります。</b>'
  'ご意見がどう扱われたかは<a class="src" href="kiroku.html">ご意見と対応の記録</a>に残します。'
  '要旨には、送った方や第三者の推測につながる要素は入れません。<br>'
  '・<b>原文は、採否の決定と記録への反映が済み次第、保存先から削除します</b>'
  '（遅くとも受信から30日以内）。<br>'
  '・この取り扱いは、<b>この説明の掲載後に送られたご意見</b>に適用します。'
  '掲載前に届いたご意見は、従来どおり運営者だけが読み、公開せず、AIにも渡しません。<br>'
  '・<b>お名前・メールアドレス・電話番号などは書かないでください。</b>'
  'このフォームは本文と送信元のページ名しか保存せず、連絡先を受け取る作りになっていません。'
  'そのため<b>個別の返信はできません</b>。<br>'
  '・連続送信対策として Google の reCAPTCHA を利用しており、送信時の接続情報は Google に渡ります。<br>'
  '・公開の場で議論したい場合や、返信のやり取りが必要な場合は'
  '<a class="src" href="https://github.com/ai-seisaku-kurabe/ai-seisaku-kurabe.github.io/issues/new" '
  'target="_blank" rel="noopener">GitHub の Issue</a>をお使いください（GitHubのアカウントが必要です）。<br>'
  '・<b>このサイトのソースコードは公開しています。</b>掲載データ・生成スクリプト・'
  '運用ルールのすべてを<a class="src" href="https://github.com/ai-seisaku-kurabe/ai-seisaku-kurabe.github.io" target="_blank" rel="noopener">'
  'リポジトリ</a>で確認でき、誤りがあればIssueやPull Requestで直接指摘できます。</p>'
  '<div class="fb-thanks" style="margin-top:22px">''<b>権利に関する申出も、この窓口で受け付けます。</b><br>''国会での発言の著作権は、<b>発言した議員ご本人</b>に帰属します。''このサイトは発言の一部を引用し、全文は会議録の原典リンクに委ねる形で掲載しています。''掲載のしかたについて<b>削除・訂正のご要望がある場合</b>は、上のIssueか''リポジトリ経由でお知らせください。確認のうえ対応します。''詳しくは<a class="src" href="about.html">このサイトについて</a>の「出典と権利」をご覧ください。</div>')
FEEDBACK_JS = FB_TAGS + """
<script>(function(){
  var wrap=document.getElementById('fbWrap'), form=document.getElementById('fbForm'),
      ta=document.getElementById('fbText'), btn=document.getElementById('fbBtn'),
      msg=document.getElementById('fbMsg'), cnt=document.getElementById('fbCount');
  var LIMIT=2000, WAIT=60*1000, KEY='kg_fb_last', sending=false;
  var cfg=null, cfgReady=false;
  if(!form || !ta) return;
  function say(t, err){ msg.textContent=t; msg.className = err ? 'fb-msg err' : 'fb-msg'; }
  function done(html){ wrap.innerHTML='<div class="fb-thanks">'+html+'</div>'; }
  function stopped(){ return !!(cfg && cfg.feedback_enabled === false); }
  ta.addEventListener('input', function(){ cnt.textContent = ta.value.length + ' / ' + LIMIT + ' 字'; });
  // 受付の停止スイッチ（config.json を書き換えるだけで効く。再ビルド不要）。
  // 取得が終わるまでは送信ボタンを無効にし、submit 側でも cfg を確認してから送信する。
  btn.disabled = true;
  say('設定を確認しています…');
  // GitHub Pages が config.json に10分のキャッシュ(Cache-Control: max-age=600)を付けるため、
  // no-store で毎回取得しないと停止スイッチが最大10分効かない。
  fetch('config.json', { cache: 'no-store' }).then(function(r){ return r.json(); }).then(function(c){
    cfg = c;
  }).catch(function(){
    cfg = null;
  }).then(function(){
    cfgReady = true;
    if(stopped()){
      done('<b>ご意見の受付を一時停止しています。</b><br>' + (cfg.feedback_notice || ''));
      return;
    }
    btn.disabled = false;
    say('');
  });
  form.addEventListener('submit', function(e){
    e.preventDefault();
    if(sending) return;
    if(!cfgReady){ say('設定を確認しています。しばらくお待ちください。', true); return; }
    if(stopped()){
      done('<b>ご意見の受付を一時停止しています。</b><br>' + (cfg.feedback_notice || ''));
      return;
    }
    var t=(ta.value||'').trim();
    if(!t){ say('本文が空です。', true); return; }
    if(t.length > LIMIT){ say(LIMIT+'字までです（現在 '+t.length+' 字）。', true); return; }
    var last = Number(localStorage.getItem(KEY) || 0);
    if(Date.now() - last < WAIT){
      say('続けて送信することはできません。1分ほどおいてからお試しください。', true); return;
    }
    if(!window.KG || !KG.enabled() || !KG.sendFeedback){
      say('送信できませんでした。下の GitHub の Issue からお送りください。', true); return;
    }
    sending=true; btn.disabled=true; say('送信しています…');
    KG.sendFeedback(t, 'feedback').then(function(){
      localStorage.setItem(KEY, String(Date.now()));
      done('<b>お送りいただき、ありがとうございます。</b><br>'
         + 'いただいた内容はサイトの改善に使わせていただきます。個別の返信はできません。');
    }).catch(function(){
      sending=false; btn.disabled=false;
      say('送信できませんでした。時間をおいて試すか、下の GitHub の Issue からお送りください。', true);
    });
  });
})();</script>"""
FEEDBACK = (f'<title>ご意見・お問い合わせ — AI政策くらべ</title>\n<style>{INDEX_CSS}{FEEDBACK_CSS}</style>\n'
  f'<div class="wrap">{nav("feedback.html")}<div class="doc">' + FEEDBACK_FORM + '</div></div>' + FEEDBACK_JS)
open("site/feedback.html","w",encoding="utf-8").write(FEEDBACK)

# ---------- oneissue.html (ワンイシュー深掘り) ----------
OISPEECH = json.load(open("oneissue_speech.json",encoding="utf-8")) if os.path.exists("oneissue_speech.json") else {}
# 各党のワンイシュー→関連する採決(実績)を引く分野の投票データ
VKEY={"自由民主党":"自由民主党","立憲民主党":"立憲民主","日本維新の会":"日本維新の会",
  "国民民主党":"国民民主","公明党":"公明党","日本共産党":"日本共産党","れいわ新選組":"れいわ","参政党":None,
  "チームみらい":None,"社会民主党":None}
REFVOTE={"自由民主党":("diplo_votes.json","外交・安保"),"立憲民主党":("votes_data.json","財政"),
  "日本維新の会":("votes_data.json","財政"),"国民民主党":("votes_data.json","財政"),
  "公明党":("ss_votes.json","社会保障"),"日本共産党":("diplo_votes.json","外交・安保"),
  "れいわ新選組":("votes_data.json","財政"),"参政党":(None,None),
  "チームみらい":(None,None),"社会民主党":(None,None)}
_vcache={}
def load_votes(fn):
    if fn not in _vcache:
        _vcache[fn]=(json.load(open(fn,encoding="utf-8")).get("bills",[]) if os.path.exists(fn) else [])
    return _vcache[fn]
SANGIIN="https://www.sangiin.go.jp/japanese/touhyoulist/217/"
def oi_speeches(full):
    recs=OISPEECH.get(full,[])
    hd='<div class="oi-hd"><span class="oi-tag gen">言</span>この争点に関わる国会発言</div>'
    if not recs: return hd+'<p class="oi-none">この会期では関連発言を十分に取得できませんでした。</p>'
    out=[]
    for r in recs:
        q=re.sub(r'^○[^　]{1,14}　','',r["text"]).strip()
        out.append(f'<div class="oi-sp"><p class="oi-q">「{esc(q)}…」</p>'
          f'<p class="oi-cite">{esc(r["who"])}／{esc(r["meeting"])}（{esc(r["date"])}）'
          f' <a class="src" href="{esc(r["url"])}" target="_blank" rel="noopener">原文→</a></p></div>')
    return hd+"".join(out)
def oi_records(full):
    fn,dom=REFVOTE[full]; vk=VKEY[full]
    hd='<div class="oi-hd"><span class="oi-tag gyo">行</span>関連する採決での立場（実績）'
    if not fn or not vk:
        return hd+'</div><p class="oi-none">この党は第217回国会の参議院で会派を構成しておらず、この会期の会派別記名投票記録がありません（第219回・第221回の賛否は「政党で選ぶ」のページで確認できます）。</p>'
    rows=[]
    for b in load_votes(fn):
        pe=next((v for k,v in b["parties"].items() if vk in k), None)
        if not pe: continue
        st=pe.get("stance","")
        cls="ag" if st=="賛成" else ("op" if st=="反対" else "nu")
        rows.append(f'<a class="oi-vote" href="{SANGIIN}{esc(b["id"])}.htm" target="_blank" rel="noopener">'
          f'<span class="oi-vst {cls}">{esc(st or "―")}</span>'
          f'<span class="oi-vlb">{esc(b["label"])}</span></a>')
        if len(rows)>=5: break
    if not rows:
        return hd+'</div><p class="oi-none">この分野で該当する記名採決が見つかりませんでした。</p>'
    return (hd+f'<span class="oi-dom">{esc(dom)}分野の記名投票より</span></div>'
      f'<div class="oi-votes">'+"".join(rows)+"</div>"
      f'<p class="oi-cav">※賛否は採決の<b>結果</b>で、反対・賛成の<b>理由や背景</b>は含みません'
      f'（「方向性は賛成だが規定が不十分で反対」等もあります）。討論は各リンク先の原典でご確認ください。</p>')
# 各党のワンイシューが属する争点テーマ（絞り込み用・格付けではなく分類のみ）
THEME={"自由民主党":"外交・安保","立憲民主党":"税・財政","日本維新の会":"税・財政",
  "国民民主党":"税・財政","公明党":"くらし・社会保障","日本共産党":"外交・安保",
  "れいわ新選組":"税・財政","参政党":"税・財政",
  "チームみらい":"くらし・社会保障","社会民主党":"外交・安保"}
THEME_ORDER=["税・財政","外交・安保","くらし・社会保障"]
# ワンイシューに対応するニュース分野と、会議録検索に渡すキーワード
ONEISSUE_DOMAIN = {"自由民主党":"外交・安保","立憲民主党":"財政","日本維新の会":"財政",
  "国民民主党":"財政","公明党":"社会保障","日本共産党":"外交・安保",
  "れいわ新選組":"財政","参政党":"財政",
  "チームみらい":"経済・産業","社会民主党":"憲法"}
ONEISSUE_KEYWORD = {"自由民主党":"抑止力","立憲民主党":"説明責任","日本維新の会":"歳出改革",
  "国民民主党":"手取り","公明党":"処遇改善","日本共産党":"軍事費",
  "れいわ新選組":"消費税","参政党":"消費税",
  "チームみらい":"デジタル","社会民主党":"憲法"}
def oneissue_links(full):
    """その争点のニュースと、当サイト内の発言一覧への入口。"""
    dom = ONEISSUE_DOMAIN.get(full, "財政")
    pid = ID.get(full, "")
    qs = urllib.parse.quote(dom) + ("&party=" + pid if pid else "")
    return (f'<div class="oi-more2">'
            f'<a href="news.html?domain={qs}">▸ この争点のニュース（{esc(dom)}）</a>'
            f'<a href="speeches.html?domain={qs}">▸ この党のこの分野の発言をもっと見る</a>'
            f'</div>')

oi_index="".join(
  f'<a class="oi-ix" href="#{ID[p["full"]]}" data-theme="{THEME[p["full"]]}" style="--pc:{PC[p["full"]]}">'
  f'<span class="oi-ix-p"><i class="pdot"></i>{esc(p["short"])}</span>'
  f'<span class="oi-ix-i">{esc(p["oneissue"])}</span></a>' for p in PARTIES)
oi_sections="".join(
  f'<section class="oi-sec" id="{ID[p["full"]]}" data-theme="{THEME[p["full"]]}" style="--pc:{PC[p["full"]]};--pc-on:{on_color(PC[p["full"]])}">'
  f'<div class="oi-sec-top"><span class="oi-badge">{esc(p["short"])}</span>'
  f'<a class="oi-up" href="#oi-top">一覧へ ↑</a></div>'
  f'<h2 class="oi-issue">{esc(p["oneissue"])}</h2>'
  f'<p class="oi-why2">{esc(p["why"])}</p>'
  f'{oi_speeches(p["full"])}{oi_records(p["full"])}'
  f'{oneissue_links(p["full"])}</section>'
  for p in PARTIES)
OI_CSS="""
.oi-lede{color:var(--muted);font-size:15px;max-width:64ch;margin:0 0 24px;}
.oi-lede b{color:var(--ink);}
.oi-ixgrid{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0 0 10px;}
@media(max-width:600px){.oi-ixgrid{grid-template-columns:1fr;}}
.oi-ix{display:block;text-decoration:none;color:inherit;background:var(--card);border:1px solid var(--line);
  border-left:4px solid var(--pc,var(--accent));border-radius:12px;padding:12px 15px;transition:border-color .15s,transform .1s;}
.oi-ix:hover{border-color:var(--pc,var(--accent));transform:translateY(-1px);}
.oi-ix-p{display:flex;align-items:center;gap:7px;font-family:var(--serif);font-weight:600;font-size:15px;}
.oi-ix-i{display:block;font-size:12.5px;color:var(--muted);margin-top:2px;}
.pdot{flex:none;width:9px;height:9px;border-radius:50%;background:var(--pc,var(--accent));}
.oi-ixhint{font-size:12px;color:var(--muted);margin:0 0 8px;}
.oi-filter{display:flex;align-items:center;flex-wrap:wrap;gap:7px;margin:0 0 14px;}
.oi-filter-l{font-family:var(--mono);font-size:11px;letter-spacing:.08em;color:var(--muted);margin-right:2px;}
.oi-fchip{font:inherit;font-size:12.5px;cursor:pointer;background:transparent;color:var(--muted);
  border:1px solid var(--line);border-radius:20px;padding:5px 13px;transition:.13s;}
.oi-fchip:hover{border-color:var(--accent);color:var(--ink);}
.oi-fchip.on{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:600;}
.oi-ix.dim,.oi-sec.dim{opacity:.28;filter:saturate(.3);transition:opacity .2s,filter .2s;}
.oi-ix,.oi-sec{transition:opacity .2s,filter .2s;}
.oi-sec{border-top:3px solid var(--pc,var(--line));padding-top:22px;margin-top:34px;scroll-margin-top:70px;}
.oi-sec-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;}
.oi-badge{display:inline-block;font-family:var(--mono);font-size:12px;letter-spacing:.06em;
  background:var(--pc,var(--accent));color:var(--pc-on,#fff);border-radius:20px;padding:4px 13px;font-weight:600;}
.oi-up{font-family:var(--mono);font-size:11px;color:var(--muted);text-decoration:none;}
.oi-up:hover{color:var(--accent);}
.oi-issue{font-family:var(--serif);font-weight:600;font-size:clamp(19px,3.4vw,25px);line-height:1.4;margin:2px 0 8px;text-wrap:balance;}
.oi-why2{color:var(--muted);font-size:13.5px;line-height:1.85;margin:0 0 4px;max-width:66ch;}
.oi-hd{display:flex;align-items:center;gap:9px;font-family:var(--serif);font-weight:600;font-size:15px;
  margin:22px 0 12px;flex-wrap:wrap;}
.oi-tag{font-family:var(--mono);font-size:12.5px;width:26px;height:26px;display:inline-flex;align-items:center;
  justify-content:center;border-radius:8px;font-weight:700;flex:none;}
.oi-tag.gen{background:#e7edff;color:#3a4d8f;}.oi-tag.gyo{background:#eae4d8;color:#7a5c2e;}
@media(prefers-color-scheme:dark){.oi-tag.gen{background:#232c48;color:#9fb2ee;}.oi-tag.gyo{background:#332c1f;color:#c9ab6f;}}
.oi-dom{font-family:var(--mono);font-size:11px;color:var(--muted);font-weight:400;}
.oi-sp{background:var(--card);border:1px solid var(--line);border-left:3px solid var(--pc,var(--accent));
  border-radius:0 10px 10px 0;padding:12px 16px;margin:0 0 10px;}
.oi-q{font-size:14px;line-height:1.85;margin:0 0 6px;}
.oi-cite{font-family:var(--mono);font-size:11.5px;color:var(--muted);margin:0;}
.oi-votes{display:flex;flex-direction:column;gap:7px;}
.oi-vote{display:flex;align-items:center;gap:11px;text-decoration:none;color:inherit;
  background:var(--card);border:1px solid var(--line);border-radius:10px;padding:9px 13px;}
.oi-vote:hover{border-color:var(--accent);}
.oi-vst{flex:none;font-family:var(--mono);font-size:11.5px;font-weight:700;border-radius:6px;padding:3px 9px;}
.oi-vst.ag{background:#e3f0e4;color:#2f7d43;}.oi-vst.op{background:#f6e4dc;color:#b25334;}
.oi-vst.nu{background:var(--accent-soft);color:var(--muted);}
@media(prefers-color-scheme:dark){.oi-vst.ag{background:#1e3327;color:#7fc891;}.oi-vst.op{background:#3a271f;color:#e0a086;}}
.oi-vlb{font-size:13.5px;}
.oi-none{font-size:13px;color:var(--muted);background:var(--card);border:1px dashed var(--line);
  border-radius:10px;padding:12px 15px;margin:0;}
.oi-cav{font-size:12px;color:var(--muted);line-height:1.7;margin:9px 2px 0;}
.oi-cav b{color:var(--ink);}
.oi-more2{display:flex;flex-wrap:wrap;gap:16px;margin-top:16px;padding-top:12px;
  border-top:1px dotted var(--line);}
.oi-more2 a{font-family:var(--mono);font-size:12px;color:var(--muted);text-decoration:none;}
.oi-more2 a:hover{color:var(--pc,var(--accent));}
.oi-newshd{font-family:var(--mono);font-size:11px;letter-spacing:.1em;color:var(--muted);text-transform:uppercase;margin:20px 0 4px;}
.oi-news{display:block;text-decoration:none;color:var(--ink);font-size:13px;line-height:1.6;
  padding:7px 0;border-top:1px solid var(--line);}
.oi-news:hover{color:var(--accent);}
.oi-news span{display:block;font-family:var(--mono);font-size:11px;color:var(--muted);}
"""
OI_NEWS_JS=('<script>(function(){function esc(s){return String(s).replace(/[&<>]/g,function(c){'
  'return({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]);});}'
  'fetch("news.json").then(function(r){return r.json();}).then(function(nd){var P=nd.parties||{};'
  'document.querySelectorAll(".pnews").forEach(function(el){var id=el.getAttribute("data-pid");'
  'var items=P[id]||[];if(!items.length)return;'
  'el.innerHTML=\'<div class="oi-newshd">この党の関連ニュース</div>\'+items.map(function(it){'
  'return \'<a class="oi-news" href="\'+it.u+\'" target="_blank" rel="noopener">\'+esc(it.t)+'
  '\'<span>\'+esc(it.s||"")+\'</span></a>\';}).join("");});}).catch(function(){});})();</script>')
OI_FILTER_JS=('<script>(function(){var chips=document.querySelectorAll(".oi-fchip");'
  'chips.forEach(function(c){c.addEventListener("click",function(){'
  'chips.forEach(function(x){x.classList.remove("on");});c.classList.add("on");'
  'var th=c.getAttribute("data-fth");'
  'document.querySelectorAll(".oi-ix,.oi-sec").forEach(function(el){'
  'var m=(th==="all"||el.getAttribute("data-theme")===th);el.classList.toggle("dim",!m);});'
  '});});})();</script>')
ONEISSUE=(f'<title>ワンイシュー — 各党が最も重視する一点 ｜ AI政策くらべ</title>\n'
  f'<style>{INDEX_CSS}{OI_CSS}</style>\n'
  f'<div class="wrap">{nav("oneissue.html")}<div class="doc" id="oi-top">'
  '<p class="eyebrow">ワンイシュー</p>'
  '<h1>各党が、いちばん譲れない一点。</h1>'
  '<p class="oi-lede">政党には、あらゆる分野を扱う<b>包括政党</b>もあれば、特定の一点に力を集中する党もあります。'
  '前者ではワンイシューが「政権運営の基本姿勢」に近く、後者では「この1点を問う」という<b>争点そのもの</b>になりがちです。'
  'その<b>性質の違い</b>も含めて、各党が特に重視する「一点」を、<b>国会発言（言）</b>と<b>採決での立場（行）</b>から見比べられます。'
  '<b>どちらが良いという評価はしません。</b>要約は編集判断を含み、点数化・格付けもしません。必ず原典リンクで裏取りを。</p>'
  '<div class="oi-filter"><span class="oi-filter-l">争点で見る</span>'
  '<button type="button" class="oi-fchip on" data-fth="all">すべて</button>'
  + "".join(f'<button type="button" class="oi-fchip" data-fth="{esc(t)}">{esc(t)}</button>' for t in THEME_ORDER)
  + '</div>'
  f'<div class="oi-ixgrid">{oi_index}</div>'
  '<p class="oi-ixhint">▸ 気になる党を押すと、その党の発言・実績へ移動します。争点で絞り込むと、同じ土俵で戦う党が見えます。</p>'
  + oi_sections +
  '<p class="note" style="margin-top:34px">出典：国会会議録検索システム（発言）／参議院 記名投票結果 第217回国会（採決）。'
  '「ワンイシュー」は各党の国会での言動をもとに編集部が要約したものです。採決は各党のワンイシューに関連の深い分野のものを表示しています。'
  'データの作り方・選定基準・限界は<a class="src" href="about.html">▸ このサイトについて（方法論）</a>で公開しています。</p>'
  '</div></div>'+OI_FILTER_JS)
open("site/oneissue.html","w",encoding="utf-8").write(ONEISSUE)

# ---------- about.html (このサイトについて＝方法論・透明性) ----------
# ---------- 監査結果の読み込み（about.html と research.html が数字を流し込む） ----------
# 本文に数字を手で書くと、設問や掲載会期を変えたときにページだけが古いまま残る。
def _audit_load():
    """照合の全数検査（agents/audit_matching.py）の結果を読む。

    ページに出る数字はすべてこのJSONから流し込む。本文に数字を手で書くと、
    設問や政党を変えたときにページだけが古いまま残るため。
    """
    p = "state/matching_audit.json"
    if not os.path.exists(p):
        raise SystemExit("state/matching_audit.json がありません。"
                         "先に python agents/audit_matching.py を実行してください。")
    return json.load(open(p, encoding="utf-8"))

AUDIT = _audit_load()

def _qaudit_load():
    """設問の来歴の洗い出し（agents/audit_questions.py）の結果を読む。"""
    p = "state/question_audit.json"
    if not os.path.exists(p):
        raise SystemExit("state/question_audit.json がありません。"
                         "先に python agents/audit_questions.py を実行してください。")
    return json.load(open(p, encoding="utf-8"))

QAUDIT = _qaudit_load()

def _rcaudit_load():
    """記名投票がどれだけを覆っているかの測定（agents/audit_rollcall.py）の結果を読む。"""
    p = "state/rollcall_audit.json"
    if not os.path.exists(p):
        raise SystemExit("state/rollcall_audit.json がありません。"
                         "先に python agents/audit_rollcall.py を実行してください。")
    return json.load(open(p, encoding="utf-8"))

RCAUDIT = _rcaudit_load()

def _xaudit_load():
    """「言」の抽出でどれだけ選んでいるかの測定（agents/audit_extraction.py）の結果を読む。"""
    p = "state/extraction_audit.json"
    if not os.path.exists(p):
        raise SystemExit("state/extraction_audit.json がありません。"
                         "先に python agents/audit_extraction.py を実行してください。")
    return json.load(open(p, encoding="utf-8"))

XAUDIT = _xaudit_load()

def _saudit_load():
    """各党が会議録で何に触れたかの配分の測定（agents/audit_saliency.py）の結果を読む。"""
    p = "state/saliency_audit.json"
    if not os.path.exists(p):
        raise SystemExit("state/saliency_audit.json がありません。"
                         "先に python agents/audit_saliency.py を実行してください。")
    return json.load(open(p, encoding="utf-8"))

SALIENCY = _saudit_load()

ABOUT_CSS="""
.ab-lede{color:var(--muted);font-size:15.5px;line-height:1.85;max-width:64ch;margin:0 0 8px;}
.ab-lede b{color:var(--ink);}
.ab-sec{border-top:1px solid var(--line);padding-top:24px;margin-top:30px;}
.ab-k{font-family:var(--mono);font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--accent);margin:0 0 7px;}
.ab-h{font-family:var(--serif);font-weight:600;font-size:clamp(18px,3.2vw,23px);line-height:1.4;margin:0 0 12px;text-wrap:balance;}
.ab-b{font-size:14px;line-height:1.95;color:var(--ink);max-width:70ch;margin:0 0 12px;}
.ab-b a.src{color:var(--accent);text-decoration:none;} .ab-b a.src:hover{text-decoration:underline;}
.ab-list{list-style:none;padding:0;margin:4px 0 0;display:flex;flex-direction:column;gap:10px;}
.ab-list li{position:relative;padding-left:20px;font-size:14px;line-height:1.85;color:var(--ink);max-width:70ch;}
.ab-list li::before{content:"";position:absolute;left:2px;top:9px;width:7px;height:7px;border-radius:2px;background:var(--accent);}
.ab-list b{font-weight:700;}
.ab-two{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:6px;}
@media(max-width:640px){.ab-two{grid-template-columns:1fr;}}
.ab-card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px 18px;}
.ab-card.do{border-top:3px solid #2f8f7f;} .ab-card.dont{border-top:3px solid #c1704f;}
.ab-card h3{font-family:var(--mono);font-size:12px;letter-spacing:.06em;margin:0 0 10px;}
.ab-card.do h3{color:#2f8f7f;} .ab-card.dont h3{color:#c1704f;}
.ab-card ul{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:8px;}
.ab-card li{font-size:13.5px;line-height:1.7;color:var(--ink);padding-left:16px;position:relative;}
.ab-card li::before{position:absolute;left:0;top:0;} .ab-card.do li::before{content:"○";color:#2f8f7f;} .ab-card.dont li::before{content:"×";color:#c1704f;}
.rulebook{counter-reset:rb;list-style:none;padding:18px 20px;margin:8px 0 0;display:flex;flex-direction:column;gap:11px;
  background:var(--card);border:1px solid var(--line);border-radius:14px;}
.rulebook li{counter-increment:rb;position:relative;padding-left:34px;font-size:13.5px;line-height:1.85;color:var(--ink);}
.rulebook li::before{content:counter(rb);position:absolute;left:0;top:2px;width:22px;height:22px;
  display:flex;align-items:center;justify-content:center;font-family:var(--mono);font-size:11px;font-weight:700;
  background:var(--accent);color:#fff;border-radius:7px;}
.rulebook b{font-weight:700;}
.ab-limit{background:var(--card);border:1px solid var(--line);border-left:3px solid #c1704f;border-radius:0 12px 12px 0;padding:13px 18px;margin:10px 0;}
.ab-limit p{margin:0;font-size:13.5px;line-height:1.8;color:var(--ink);} .ab-limit b{font-weight:700;}
.ab-cta{display:flex;gap:12px;flex-wrap:wrap;margin:34px 0 0;}
.ab-cta a{text-decoration:none;font-family:var(--mono);font-size:13px;font-weight:600;border-radius:22px;padding:10px 20px;}
.ab-cta a.p{background:var(--accent);color:#fff;} .ab-cta a.s{border:1px solid var(--line);color:var(--accent);}
.ab-cta a:hover{opacity:.92;}
"""
ABOUT=(f'<title>このサイトについて（方法論と透明性）｜ AI政策くらべ</title>\n'
  f'<style>{INDEX_CSS}{ABOUT_CSS}</style>\n'
  f'<div class="wrap">{nav("about.html")}<div class="doc">'
  '<p class="eyebrow">このサイトについて</p>'
  '<h1>つくり方と、あえて「しない」こと。</h1>'
  '<p class="ab-lede">このサイトが信頼できる判断材料であるために、'
  '<b>データの作り方・編集の判断・限界</b>を包み隠さず公開します。'
  'ここに書いたことは、すべて各ページの原典リンクから誰でも検証できます。</p>'

  '<section class="ab-sec"><p class="ab-k">01 ／ 目的</p>'
  '<h2 class="ab-h">「評価」ではなく「検証可能性のインフラ」を提供する</h2>'
  '<p class="ab-b">目的は、知名度や雰囲気ではなく<b>中身（各党が国会で何を論じ、どう投票したか）</b>で'
  '投票先を考えられるようにすることです。私たちは<b>正解を出しません</b>。'
  '一次情報を整理して並べるところまでを担い、評価と判断は有権者に委ねます。</p></section>'

  '<section class="ab-sec"><p class="ab-k">02 ／ 「言」の作り方</p>'
  '<h2 class="ab-h">国会会議録から、原文のまま引用する</h2>'
  '<ul class="ab-list">'
  '<li>出典は<a class="src" href="https://kokkai.ndl.go.jp/" target="_blank" rel="noopener">国会会議録検索システム</a>（第217回・第219回・第221回国会）。API経由で発言を取得します。</li>'
  '<li><b>質問側の議員の発言のみ</b>を対象とし、<b>答弁側（大臣・副大臣・政府参考人・参考人など）は除外</b>します。政府答弁は「その党の主張」ではないためです。</li>'
  '<li>各争点の<b>キーワード周辺</b>を抜き出し、挨拶や定型の前置きは避けます。<b>引用は原文のまま</b>で、こちらで言葉を補ったり推測で書き換えたりしません。</li>'
  '<li>すべての発言に、<b>その発言の該当箇所へ直接ジャンプする原文リンク</b>を付けています（会議録のトップではなく、当該発言まで一発で飛べます）。要約を信じる必要はなく、原典で直接確認できます。</li>''<li><b>会議録そのものにも、作られる過程があります。</b>衆議院の会議録は2011年から音声認識をもとに作成され、認識結果を記録部の職員が確認・修正して確定させています。「一次情報」は生の音声そのものではなく、この工程を経たものです。私たちはその確定した会議録を、書き換えずに引用しています。</li></ul></section>'

  '<section class="ab-sec"><p class="ab-k">03 ／ 「行」の作り方</p>'
  '<h2 class="ab-h">参議院の記名投票から、会派ごとの賛否を取る</h2>'
  '<ul class="ab-list">'
  '<li>出典は<a class="src" href="https://www.sangiin.go.jp/japanese/touhyoulist/217/vote_ind.htm" target="_blank" rel="noopener">参議院 記名投票結果</a>。各法案ページの会派別の賛成・反対をそのまま集計します。</li>'
  '<li><b>発言（言）は衆議院・参議院の両方</b>から採っています。国会会議録検索システムが両院を収録しているためで、''引用にはどちらの議院・どの委員会かを明記しています。''<b>統一会派の扱い。</b>' + roster_note() + '（この仕組みが無かったため、立憲民主党と公明党の「言」は長く参議院のものだけでした。''<b>「発言をもっと見る」の一覧は2026年7月20日に、「政党で選ぶ」の各分野の発言は7月21日に</b>、それぞれ両院から採るようになりました。''訂正が2段階になったのは、一覧とガイドで発言を集める仕組みが別々だったためです。''「両院から」という記載が事実と違っていたことをおわびし、訂正します。）</li>''<li><b>採決（行）は、参議院が中心です。</b>衆議院の本会議は原則として起立採決で、その議案は会派別・個人別の賛否が記録に残りません。''<b>ただし予算などの重要案件は記名投票で行われ、賛成者と反対者の氏名が会議録に全部載ります。</b>''以前ここに「衆議院は個人別の賛否が残らない」と書いていましたが、これは起立採決については正しく、記名投票については誤りでした。おわびして訂正します。''現在は<b>予算の記名投票（第217回・第221回）だけ</b>を財政分野に載せています。''委員長解任決議案も記名投票ですが、予算審議の進め方をめぐる案件であり、政策的な立場として並べると誤読を招くため入れていません。</li>''<li><b>衆院の賛否は、氏名から所属党を引いて数えています。</b>参議院と違い衆議院は会派ごとの投票結果を公表しておらず、会議録に載るのは氏名だけだからです。''無所属の議員はどの党にも数えません。過去の発言記録から所属党を特定できない議員も数に入れておらず、''第221回の予算では<b>' + f"{SHUGIIN_STAT['total']}票のうち{SHUGIIN_STAT['unidentified']}票" + '</b>がこれに当たります。''補いはしません（採決より後の記録から推測すると、データが無い箇所を埋めることになるためです）。''同姓同名が衆参にいるため、照会は衆議院に限っています。''各党の賛成・反対の数は<b>特定できた分の集計</b>であり、議員の総数とは一致しません。''抽出が正しいかは、会議録が報告している投票総数と突き合わせて確認しています。</li>''<li>憲法分野は記名投票の議案が無く「行」は該当なしとしています。</li></ul></section>'

  '<section class="ab-sec"><p class="ab-k">04 ／ 「編集判断」の中身</p>'
  '<h2 class="ab-h">どこに人の手が入るかを、隠さない</h2>'
  '<p class="ab-b">「どの発言・どの採決を選ぶか」「ワンイシューを1点にどう絞るか」は、'
  '一次情報をもとにした<b>編集の判断</b>です。ここに偏りが入り得ることは事実です。'
  'だからこそ、その判断を検証可能にするために、次のことを徹底しています。</p>'
  '<ul class="ab-list">'
  '<li><b>引用は原文</b>・<b>必ず原典リンク</b>。編集要約を信じなくても、元の発言・採決に当たれます。</li>'
  '<li><b>点数化・格付けをしない</b>。「良い/悪い」の結論を出さないので、評価の偏りが入り込む余地を最小化しています。'
  'この判断の根拠にした先行事例（米GovTrackのランキング撤回など）は'
  '<a class="src" href="research.html">▸ 先行研究と、この設計の根拠</a>にまとめています。</li>'
  '<li>AI（Claude）は、膨大な会議録の<b>収集・整理・要約</b>に使っています。'
  '「どの党が優れているか」といった<b>評価の結論をAIに出させることはしていません</b>。'
  'AIの政治的判断が測定条件で揺れることを示した研究が、この判断の根拠です'
  '（<a class="src" href="research.html">先行研究</a>の01）。</li>'
  '<li><b>更新は、AIが自分で公開しています。</b>人が1件ずつ目を通してから公開しているわけでは'
  'ありません。代わりに、公開の前に<b>機械による点検</b>を必ず通しています——引用が会議録の原文と'
  '一致するか、一次情報へのリンクが実際に到達するか、使わないと決めた評価語が混じっていないか。'
  '1件でも不合格があれば公開しません。<b>ただし、この方法論そのもの（下の運用ルール）と、'
  'どの党・どの会期を載せるかの方針を変えるときだけは、人の承認を経ます。</b></li>'
  '<li><b>分野の並び順は、読みやすさのための編集判断</b>であり、重要度の順位ではありません。'
  '関心が集まりやすい分野を上に置いていますが、どの分野が大切かを決めるのは有権者です。</li></ul></section>'

  '<section class="ab-sec"><p class="ab-k">05 ／ 運用ルール（AIへの指示に相当）</p>'
  '<h2 class="ab-h">私たちがAIを動かしている「ルールそのもの」</h2>'
  '<p class="ab-b">「AIの要約自体が偏っているのでは」という疑念に応えるため、発言の収集・引用・要約で'
  '<b>必ず守っている運用ルール（AIに与えている指示に相当するもの）</b>を、そのまま公開します。'
  'このルールから外れた記載を見つけたら、それは私たちの誤りです。'
  '<a class="src" href="feedback.html">ご指摘ください</a>。</p>'
  '<ol class="rulebook">'
  '<li>発言は国会会議録検索システムのAPIから取得する。対象は<b>質問側の議員の発言のみ</b>とし、'
  '答弁側（大臣・副大臣・大臣政務官・政府参考人・参考人など）は除外する。</li>'
  '<li>引用は<b>原文のまま</b>。語を補ったり推測で書き換えたりしない。定型の挨拶・前置きは引用に含めない。'
  '中略は「…」で示し、<b>各断片は原文と同じ順序</b>で並べる（順序を入れ替えると意味が変わるため）。'
  '<b>引用への補足の挿入は禁止</b>——「（米国防次官が）」のような括弧書きの説明を混ぜない。'
  '文脈の補足が要る場合は、引用ではなく編集テキスト（力点）に書く。</li>'
  '<li>すべての発言・採決に、<b>一次情報の該当箇所への直接リンク</b>を付す。</li>'
  '<li>採決は<b>記名投票の記録</b>をそのまま用いる。参議院は会派別の賛否が公表されているのでそれを用いる。衆議院は会派別の公表が無いため、会議録に載る<b>賛成者・反対者の氏名</b>を用い、氏名から所属党を引く（引けない議員と無所属は数えず、人数を開示する）。<b>起立採決の議案は個人別の賛否が残らないため扱わない。</b></li>'
  '<li><b>点数化・格付け・ランキング・「平均からの乖離」を出力しない。</b>'
  'あわせて、編集テキスト（力点・ワンイシューの説明・政策パッケージ）に'
  '<b>価値判断や感情を含む語を使わない</b>（素晴らしい／優れた／無責任／暴走／ばらまき／選ぶべき など）。'
  '禁止語は機械的に検査している。<b>引用（原文）は対象外</b>——原文に何が書かれていても改変しないため。</li>'
  '<li>データが無い項目は<b>捏造せず空欄にし、理由を明記</b>する。</li>'
  '<li>「ワンイシュー」「力点」などの要約は<b>編集判断であると明示</b>し、党の公式見解とは称さない。</li>'
  '<li>AIは<b>収集・整理・要約</b>に用い、「どの党が優れているか」等の<b>評価の結論は出力しない</b>。'
  '公開の前に機械的検証（引用の原文照合・リンク到達性・禁止語）を必ず通し、'
  'この運用ルールと掲載方針の変更は人の承認を経る。</li>'
  '</ol></section>'

  '<section class="ab-sec"><p class="ab-k">06 ／ どの党を掲載するか</p>'
  '<h2 class="ab-h">掲載の基準と、掲載していない党</h2>'
  '<p class="ab-b">「どの党を載せるか」は、決め方を示さないと恣意的になります。'
  'そこで基準を先に決めて公開し、それに当てはめています。'
  '<b>掲載しない党についても、その理由をここに書きます。</b></p>'
  '<ol class="rulebook">'
  '<li><b>参議院で会派を構成していること。</b>会派を構成していないと、記名投票に会派別の賛否が'
  '記録されず、「行」を示せないためです。</li>'
  '<li><b>「言」と「行」の両方を、原典付きで示せること。</b>どちらか一方しか示せない党を'
  '同じ形式で並べると、比較しているように見えて実は比較になりません。</li>'
  '<li><b>政党であること。</b>「各派に属しない議員」のような、政党ではない集まりは対象外です。</li>'
  '</ol>'
  '<div class="ab-limit"><p><b>現在、基準を満たさず掲載していない会派：</b><br>'
  '・<b>日本保守党</b>（参院2名）… 参議院の会派としての採決記録はありますが、'
  '国会会議録で会派としての発言を確認できませんでした。「行」だけを載せると'
  '全分野が空欄の党ができてしまうため、掲載を見送っています。<br>'
  '・<b>沖縄の風</b>（参院2名）… 特定地域を基盤とする会派のため、'
  '全国比例区の選択肢を比べる本サイトの趣旨とは性質が異なると判断しました。<br>'
  '・<b>各派に属しない議員</b>（参院6名）… 政党ではないため対象外です。<br>'
  'いずれも<b>評価による除外ではありません。</b>基準を満たすデータが揃えば掲載します。</p></div>'
  '</section>'

  '<section class="ab-sec"><p class="ab-k">07 ／ あえて「しない」こと</p>'
  '<h2 class="ab-h">やらないと決めていること</h2>'
  '<div class="ab-two">'
  '<div class="ab-card do"><h3>すること</h3><ul>'
  '<li>一次情報（言と行）を原典リンク付きで並べる</li>'
  '<li>データが無い所は「空欄＋理由」を明示する</li>'
  '<li>賛成派・反対派の対立軸を両論で示す</li></ul></div>'
  '<div class="ab-card dont"><h3>しないこと</h3><ul>'
  '<li>政党の点数化・ランキング・格付け</li>'
  '<li>「平均からの乖離＝極端さ」の表示（中道＝正解という価値判断を持ち込まないため）</li>'
  '<li>言と行のズレを一律に「矛盾」と断じること</li></ul></div></div></section>'

  '<section class="ab-sec"><p class="ab-k">08 ／ このツールの限界</p>'
  '<h2 class="ab-h">正直な、弱点の開示</h2>'
  '<div class="ab-limit"><p><b>賛否は「結果」であって「理由」ではありません。</b>'
  '各党は「方向性には賛成だが規定・予算規模が不十分だから反対」といった複雑な理由で票を投じることがあります。'
  '賛否だけで是非を判断せず、討論は原典でご確認ください。</p></div>'
  '<div class="ab-limit"><p><b>実績ベースは、小さな政党・新しい勢力に構造的に不利です。</b>'
  '議席が少ないほど発言や採決に関わる機会も少なくなります。'
  'データが無い所は捏造せず空欄にします（例：参政党は第217回国会では会派未結成のため賛否記録がありません。第221回国会では会派を結成し記録があります）。</p></div>'
  '<div class="ab-limit"><p><b>「政策で照らす」は、争点によって性質が違います。</b>'
  '消費税・防衛費など既存の争点は<b>参院採決ベース</b>、原発・外国人受け入れ・教育無償化など新しい争点は<b>各党の公約ベース</b>で立場を推定しています。'
  '過去の実績と未来の方針が混在している点にご留意ください。</p></div>'
  '<div class="ab-limit"><p><b>会期によって、拾える議案の量が違います。</b>'
  '「政党で選ぶ」では第217回・第219回・第221回国会の参院記名投票を並べています。'
  'このうち<b>第219回は約3週間の臨時国会</b>で、記名投票31件のうち10件が人事の同意案件、4件がNHKの決算でした。'
  '政策の議案は財政（補正予算・地方交付税・租税特別措置）と社会保障（医療法・高次脳機能障害者支援法）に偏り、'
  '<b>外交・安保／エネルギー・環境／経済・産業には該当する議案がありません</b>。'
  '該当が無い分野は、埋めずに「この会期では該当する議案がありません」と表示しています。</p></div>'
  '<div class="ab-limit"><p><b>会期を跨ぐと、会派の構成も変わります。</b>'
  '例えば社会民主党は第219回国会では立憲民主党などとの統一会派（立憲民主・社民・無所属）に属しており、'
  '会派としての単独の賛否が記録に残りません。'
  '統一会派の賛否を1党の賛否として載せることはせず、その旨を表示しています。</p></div>'
  '<div class="ab-limit"><p><b>「中立」とは名乗りません。</b>私たちは特定の政党に肩入れせず、評価も格付けもしません（<b>非党派的</b>であろうとしています）。ただしそれは「どの立場からも等距離である」という意味ではありません。6つの分野の区切り方、「政策で照らす」の設問、どの党を載せるかの線引きは、いずれも<b>何を争点とみなすかを形づくる行為</b>です。投票支援ツールの研究では、よくできたツールも非党派的ではありえるが政治的に中立ではない、と指摘されています（<a class="src" href="research.html">▸ 先行研究</a>の03）。原典リンクを付けても、この点は解消されません。</p></div>''<div class="ab-limit"><p><b>一致度の計算方法は、ひとつの選び方にすぎません。</b>「政策で照らす」は、各設問の立場を+1／0／−1で表して一致した数を数え、重視した争点を3倍にしています。<b>別の計算方法を使えば、別の結果になりえます。</b>海外の投票支援ツールの研究では、利用者の過半数が、計算モデルを変えれば違う助言を受け取っていたという報告があります（<a class="src" href="research.html">▸ 先行研究</a>の03）。一致度は「答え」ではなく、ひとつの見方です。</p></div>''<div class="ab-limit"><p><b>記名投票は、採決の全体ではありません。</b>'
  'ただし、どの程度なのかを数えました。'
  '<b>参議院の本会議で議決された' + str(RCAUDIT["total"]["decided"]) + '件のうち'
  + str(RCAUDIT["total"]["named"]) + '件（' + str(RCAUDIT["total"]["named_pct"])
  + '％）は、誰がどう投じたかが残る採決</b>でした'
  '（参議院は押しボタン式の投票が原則です）。'
  'このサイトは以前「記名投票にかけられるのはごく一部だ」という趣旨を書いていましたが、'
  '<b>参議院についてはそれは誤りだったので訂正しました。</b>'
  '残る限界は次のとおりです。'
  '①同じ議案でも<b>衆議院は' + str(RCAUDIT["total"]["shugiin_decided"]) + '件中'
  + str(RCAUDIT["total"]["shugiin_named"]) + '件（'
  + str(RCAUDIT["total"]["shugiin_named_pct"]) + '％）しか個人別の記録が残りません</b>'
  '（起立採決と「異議の有無」が原則のため）。'
  '②記名投票' + str(RCAUDIT["total"]["named"]) + '件のうち'
  + str(RCAUDIT["total"]["named_unanimous"]) + '件は<b>全会一致</b>で、党の違いは読み取れません。'
  '③数えたのは<b>本会議だけ</b>で、委員会での採決は個人別・会派別に残りません。'
  '④党議拘束の下では、記録に残る賛否は議員個人の考えの表明ではなく、政党としての行動です。'
  'つまり「行」は各党の行動の全体像ではなく、<b>記録に残った一部</b>です。'
  '数え方と内訳は<a class="src" href="research.html">▸ 先行研究と、この設計の根拠</a>の04にあります。</p></div>''<div class="ab-limit"><p><b>これは3つの会期の断面です。</b>今後の会期で更新していきます。</p></div>''<div class="ab-limit"><p><b>先行研究が指摘していて、まだ解けていない問題があります。</b>設問の選び方が一致度を左右すること、一致度の計算式そのものが編集判断であること、記名投票が代表的な標本ではないことなど、現時点で手当てできていない点を<a class="src" href="research.html">▸ 先行研究と、この設計の根拠</a>の03に、根拠となる文献とともに列挙しています。</p></div></section>'

  '<section class="ab-sec"><p class="ab-k">09 ／ 出典と権利</p>''<h2 class="ab-h">誰の著作物を、どう使っているか</h2>''<p class="ab-b">このサイトは、国会の一次情報を引用して成り立っています。''その権利が誰にあり、こちらがどう扱っているかを明示します。</p>''<ul class="ab-list">''<li><b>国会での発言の著作権は、発言した議員ご本人に帰属します。</b>''国立国会図書館は、会議録検索システムの利用条件で「発言の著作権は個々の発言者に帰属する」ことと、''<b>データベース自体の著作権は同館にある</b>ことを明示しています。''会議録は公開情報ですが、権利が消えているわけではありません。</li>''<li><b>引用として使っています。</b>発言は全文を載せず一部を抜き出し、''かならず「 」で括って本文と区別し、<b>発言者名・議院名・会議名・日付・原典への直リンク</b>を添えています。''全文は原典でお読みいただく形にしています。''こちらで言葉を補ったり書き換えたりせず、掲載中の引用はすべて機械的に原文と照合しています。</li>''<li><b>採決の記録は、参議院・衆議院が公表しているものを用いています。</b>''両院ともオープンデータとしての利用許諾は与えておらず、''著作権法上認められた範囲での利用と出所の明示を求めています。''こちらは元のページの配列をそのまま再現せず、分野別・政党別という自前の軸で集計し直したうえで、''各議案の原典ページにリンクしています。</li>''<li><b>データの取得は、提供元の求める間隔を守って行っています。</b>''会議録検索システムのAPIへは、連続した多重リクエストを避けて取得しています。</li>''<li><b>削除・訂正の申出を受け付けます。</b>掲載のしかたについてご要望のある権利者の方は、''<a class="src" href="feedback.html">ご意見の窓口</a>からお知らせください。確認のうえ対応します。</li>''<li>利用者の情報の扱いは<a class="src" href="privacy.html">▸ プライバシーポリシー</a>にまとめています。</li>''</ul></section>''<section class="ab-sec"><p class="ab-k">10 ／ 誤りの指摘と修正</p>'
  '<h2 class="ab-h">間違いは、直します</h2>'
  '<p class="ab-b">すべての記載は原典リンクから検証できます。'
  '事実誤認・要約の偏り・見落としにお気づきの際は、ぜひご指摘ください。'
  '内容を確認し、必要なら修正します。</p>'
  '<p class="ab-b"><b>ご意見フォームで送られた原文は、そのままの形では公開しません。</b>'
  '読むのは運営者と、運営者の作業を補助するAI（Claude）です。'
  '採否の記録として、運営者が書き直した要旨と理由を'
  '<a class="src" href="kiroku.html">ご意見と対応の記録</a>で公開することがあります。'
  '運営者が受け取るのは<b>本文と送信元のページ名だけ</b>で、'
  'お名前・メールアドレスは受け取りません。連続送信対策として Google の reCAPTCHA を利用しており、'
  '送信時の接続情報は Google に渡ります。そのため個別の返信はできません。'
  '詳しい取り扱いは<a class="src" href="feedback.html">ご意見のページ</a>と'
  '<a class="src" href="privacy.html">プライバシーポリシー</a>に記載しています。'
  '公開の場で記録を残して議論したい場合は、GitHub の Issue をお使いください。</p>'
  '<div class="ab-cta">'
  '<a class="p" href="feedback.html">誤りを指摘・意見を送る</a>'
  '<a class="s" href="guide.html">「政党で選ぶ」を見る</a></div></section>'

  '<p class="note" style="margin-top:36px">運営：個人（AIをパートナーとした非営利の試み）。'
  '本サイトは特定の政党・団体とは無関係で、広告・献金・アフィリエイトはありません。</p>'
  '</div></div>')
open("site/about.html","w",encoding="utf-8").write(ABOUT)

# ---------- research.html (先行研究と設計の根拠) ----------
# 方針: about.html が「何をする/しないか（ルールそのもの）」、こちらが「なぜそう決めたか（外部の根拠）」。
# 内容を写し合わない（写しを作ると原本とずれるため、about 側からはリンクのみ）。
# class="cite" のURLは③検証班(verify_content.py)がCIで到達性を確認する。
# class="cite unv" は未確認文献＝到達性チェックの対象外。必ず「未確認」と明示すること。
RESEARCH_CSS="""
.rs-lede{color:var(--muted);font-size:15.5px;line-height:1.85;max-width:64ch;margin:0 0 8px;}
.rs-lede b{color:var(--ink);}
.rs-item{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:15px 18px;margin:12px 0;}
.rs-item.keep{border-left:3px solid #2f8f7f;}
.rs-item.drop{border-left:3px solid #c1704f;}
.rs-item.open{border-left:3px solid #b08d20;}
.rs-item h3{font-family:var(--serif);font-weight:600;font-size:15.5px;line-height:1.55;margin:0 0 8px;color:var(--ink);}
.rs-f{font-size:13.5px;line-height:1.9;color:var(--ink);margin:0 0 9px;}
.rs-f b{font-weight:700;}
.rs-do{font-size:13.5px;line-height:1.9;color:var(--ink);margin:0;padding:9px 12px;
  background:var(--paper);border-radius:9px;}
.rs-do span{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;color:var(--muted);
  display:block;margin-bottom:3px;}
.rs-src{border-top:1px dashed var(--line);margin-top:11px;padding-top:8px;font-size:12px;
  line-height:1.8;color:var(--muted);}
.rs-src a.cite{color:var(--accent);text-decoration:none;}
.rs-src a.cite:hover{text-decoration:underline;}
.rs-src a.cite.unv{color:var(--muted);text-decoration:underline dotted;}
.rs-unv{background:var(--card);border:1px dashed var(--line);border-radius:14px;padding:15px 18px;margin:12px 0;}
.rs-unv ul{list-style:none;padding:0;margin:6px 0 0;display:flex;flex-direction:column;gap:9px;}
.rs-unv li{font-size:13px;line-height:1.85;color:var(--ink);padding-left:18px;position:relative;}
.rs-unv li::before{content:"?";position:absolute;left:0;top:0;font-family:var(--mono);
  font-size:11px;font-weight:700;color:#b08d20;}
.rs-item.meas{border-left:3px solid #3b6ea5;}
.rs-tw{overflow-x:auto;margin:12px 0;}
.rs-tbl{border-collapse:collapse;font-size:12.5px;min-width:520px;width:100%;}
.rs-tbl th,.rs-tbl td{border-bottom:1px solid var(--line);padding:7px 10px;text-align:left;
  line-height:1.6;white-space:nowrap;}
.rs-tbl th{font-size:11px;color:var(--muted);font-weight:600;vertical-align:bottom;}
.rs-tbl td.n{font-family:var(--mono);font-size:12px;}
.rs-note{font-size:12px;line-height:1.85;color:var(--muted);margin:8px 0 0;}
"""

def _cite(label, url, unverified=False):
    """引用リンク。unverified=True は到達性チェックの対象外（未確認文献）。"""
    cls = "cite unv" if unverified else "cite"
    return ('<a class="' + cls + '" href="' + url + '" target="_blank" rel="noopener">'
            + label + '</a>')


def _audit_table(a):
    """党ごとの検査結果の表。順位表に見えないよう、一致度の平均は出さない。"""
    rows = "".join(
        '<tr><td>' + r["short"] + '</td>'
        '<td class="n">' + str(r["stance_nonzero"]) + '/' + str(a["questions"]) + '</td>'
        '<td class="n">' + str(r["shown_share"]) + '%</td>'
        '<td class="n">' + str(r["tied_share"]) + '%</td>'
        '<td class="n">' + str(r["top_share_balanced"]) + '%</td></tr>'
        for r in sorted(a["by_party"], key=lambda r: -r["shown_share"]))
    return ('<div class="rs-tw"><table class="rs-tbl">'
            '<thead><tr><th>党</th><th>立場を示した設問</th><th>1位に出る割合</th>'
            '<th>同率1位に含まれる割合</th><th>賛否が釣り合った回答で1位</th></tr></thead>'
            '<tbody>' + rows + '</tbody></table></div>')

def _saliency_short(full):
    """党の正式名→短縮名（PARTIES から）。"""
    for p in PARTIES:
        if p["full"] == full:
            return p["short"]
    return full

def _saliency_table(s):
    """各党が会議録で触れたテーマの上位。★＝6分野に収まらない横断争点。
    順位・格付けに見えないよう、割合は「話題の配分」であることを列見出しで明示する。"""
    rows = ""
    for e in s["by_party"]:
        short = _saliency_short(e["party"])
        if e["reserved"]:
            rows += ('<tr><td>' + esc(short) + '</td><td class="n">' + str(e["total"])
                     + '</td><td colspan="3">資料不足のため保留</td></tr>')
            continue
        cells = "".join(
            '<td class="n">' + esc(t["theme"]) + ('★' if t["cross"] else '')
            + ' ' + str(t["share"]) + '%</td>'
            for t in e["top"][:3])
        cells += '<td class="n"></td>' * (3 - len(e["top"][:3]))
        rows += ('<tr><td>' + esc(short) + '</td><td class="n">' + str(e["total"])
                 + '</td>' + cells + '</tr>')
    return ('<div class="rs-tw"><table class="rs-tbl">'
            '<thead><tr><th>党</th><th>対象の発言数</th>'
            '<th>触れた話題 1位</th><th>2位</th><th>3位</th></tr></thead>'
            '<tbody>' + rows + '</tbody></table></div>'
            '<p class="rs-note">★＝6分野に収まらない横断争点。'
            '「%」は、その党が<b>いずれかの話題に触れた質問側発言</b>のうち、その話題に触れた割合'
            '（1つの発言が複数の話題に当たりうるので、合計は100%を超えます）。'
            '<b>党の重点や本質を表すものではなく、会議録での話題の配分の粗い目安</b>です。</p>')

def _rs(kind, title, finding, did, srcs):
    """先行研究の1項目。

    kind = keep（採り入れた）/ drop（採らなかった）/ open（未手当て）/
           meas（自分で測った＝先行研究の指摘を数字で確かめた結果）。
    """
    lab = {"keep": "このサイトでどうしたか", "drop": "このサイトでどうしたか",
           "open": "現状", "meas": "測った結果"}[kind]
    return ('<div class="rs-item ' + kind + '"><h3>' + title + '</h3>'
            '<p class="rs-f">' + finding + '</p>'
            '<p class="rs-do"><span>' + lab + '</span>' + did + '</p>'
            '<p class="rs-src">出典：' + srcs + '</p></div>')

RESEARCH=(f'<title>先行研究と、この設計の根拠｜ AI政策くらべ</title>\n'
  f'<style>{INDEX_CSS}{ABOUT_CSS}{RESEARCH_CSS}</style>\n'
  f'<div class="wrap">{nav("research.html")}<div class="doc">'
  '<p class="eyebrow">先行研究</p>'
  '<h1>なぜ、この作りにしたのか。</h1>'
  '<p class="rs-lede">投票支援ツールも、議会記録の可視化も、AIの政治利用も、'
  'すでに30年以上の研究と実践の蓄積があります。'
  'このページでは、その先行研究を私たちなりに整理し、'
  '<b>どれを採り入れ、どれを採らなかったか、そしてどこがまだ手当てできていないかを、根拠とともに公開します。</b>'
  'このサイトの設計は思いつきではありませんが、正解でもありません。'
  '何を根拠にそう決めたかを見せることが、その判断を検証可能にする唯一の方法だと考えています。</p>'

  '<section class="ab-sec"><p class="ab-k">00 ／ このページの読み方</p>'
  '<h2 class="ab-h">出典のルール</h2>'
  '<ul class="ab-list">'
  '<li>本文で引く文献は、<b>実際にたどり着けたURLを持つものだけ</b>です。'
  'すべての引用リンクは、公開のたびに<b>到達できるかを機械的に検査</b>しています。</li>'
  '<li>心当たりはあるが確認できていない文献は、本文に混ぜず'
  '<b>末尾の「未確認」にまとめ、未確認と明記</b>します。'
  'これは「データが無い所は捏造せず空欄にし、理由を明記する」という'
  '<a class="src" href="about.html">運用ルール</a>の6番を、このページにも適用したものです。</li>'
  '<li>ここに挙げた研究の<b>良し悪しを論じてはいません</b>。'
  '「この設計にどう使ったか」だけを書いています。'
  '採らなかった手法も、その研究が劣っているという意味ではありません。</li>'
  '<li>調査はAI（Claude）に文献を集めさせ、URLの到達性と記述の対応を人が確認する手順で作っています。'
  '見落としや読み違いがあれば<a class="src" href="feedback.html">ご指摘ください</a>。</li>'
  '</ul></section>'

  '<section class="ab-sec"><p class="ab-k">01 ／ 採り入れたこと</p>'
  '<h2 class="ab-h">先行研究が、この設計を支持している点</h2>'

  + _rs("keep",
    "点数化・格付けをしない",
    "議会記録から機械的に算出した定量スコアであっても、集計期間の取り方ひとつで結論が反転しうる。"
    "米 <b>GovTrack は2024年7月、単年度の議員ランキング（レポートカード）を撤回</b>した。"
    "投入する共同提案データの年数によってスコアが変動し、単年ランキングが複数年分析と著しく異なる結果を出していたためである。"
    "英 <b>mySociety も2024年に投票サマリの方式を全面改訂</b>し、非拘束的動議によるゲーミング、欠席の扱い、"
    "弱い投票の重み付けといった問題を自ら列挙した。"
    "「機械的に算出したから中立」は成立しない。",
    "点数もランキングも出しません。賛否と発言を、原典リンク付きでそのまま並べるところで止めています。"
    "重み付けの設計に固有の恣意性を、そもそも背負わない作りです。",
    _cite("GovTrack 撤回告知（2024-07-26）", "https://www.govtrack.us/posts/434/2024-07-26_we-retracted-our-single-year-legislator-report-cards-after-warning-about-their-unreliability")
    + " ／ " + _cite("mySociety 2024年 投票記録の方式改訂", "https://research.mysociety.org/html/2024-voting-records/"))

  + _rs("keep",
    "「平均からの乖離＝極端さ」を出さない",
    "議員や政党を1本の軸の上に配置する手法（DW-NOMINATE など）について、"
    "<b>取り出される次元が時代を通じて一貫したイデオロギー的意味を持つとは限らない</b>こと、"
    "議員の座標がイデオロギーだけでなく政党組織からの圧力や選挙区の要求など複数の要因の関数であることが指摘されている。",
    "軸の上に配置することはしません。尺度化した時点で、それは格付けになります。"
    "採決は「どの党がどの議案に賛成・反対したか」という生のかたちのまま示します。",
    _cite("Caughey &amp; Schickler (2016) Substance and Change in Congressional Ideology: NOMINATE and Its Alternatives (Studies in American Political Development 30)", "https://devincaughey.github.io/files/caughey_schickler_2016_nominate/caughey_schickler_2016_nominate.pdf"))

  + _rs("keep",
    "AIに評価の結論を出力させない",
    "大規模言語モデルの政治的傾向を測った研究は複数あり、"
    "多くが「中道左派寄り」と報告している。"
    "ただし、より重要なのは方向ではなく<b>安定性</b>である。"
    "<b>これらの測定は強制選択形式に依存しており、選択を強制しない場合や言い換えを与えた場合にモデルの回答は変わる</b>、"
    "という批判が示された。"
    "つまり「AIはどちら寄りか」以前に、<b>AIの政治的判断は測定条件で揺れるため、評価器として使えない</b>。",
    "AIは会議録の収集・整理・要約の下書きに使い、"
    "「どの党が優れているか」「この賛否は矛盾か」といった評価の結論は出力させません。"
    "採決の理由をAIに生成させる案も、この理由で採用しませんでした。",
    _cite("R&ouml;ttger et al. (2024) Political Compass or Spinning Arrow? (ACL 2024)", "https://aclanthology.org/2024.acl-long.816/")
    + " ／ " + _cite("Rozado (2024) The political preferences of LLMs (PLOS ONE)", "https://journals.plos.org/plosone/article/file?id=10.1371%2Fjournal.pone.0306621&amp;type=printable"))

  + _rs("keep",
    "政党の立場を、党の自己申告ではなく議会記録から取る",
    "多くの投票支援ツールは、政党や候補者にアンケートで立場を答えてもらう方式を採る。"
    "この方式は、<b>政党が有利になるように回答を選ぶ戦略的操作</b>のリスクを構造的に負う。"
    "政党ポジションの推定手法（自己申告・専門家によるコーディング・議会記録）の妥当性は、"
    "投票支援ツール研究で長く論じられてきた論点である。",
    "各党の立場は、国会での発言と参議院の記名投票という<b>すでに記録に残ってしまったもの</b>から取ります。"
    "こちらから各党にアンケートを送ることはしていません。",
    _cite("Gemenis (2013) Estimating parties' policy positions through voting advice applications (Acta Politica 48)", "https://link.springer.com/article/10.1057/ap.2012.36"))

  + _rs("keep",
    "根拠へのリンクを、要約ではなく該当箇所まで張る",
    "欧州の代表的な投票支援ツール群を、欧州委員会の「信頼できるAIのための倫理ガイドライン」に照らして評価した研究は、"
    "<b>多くの要件でスコアが低い</b>とし、改善が必要な点として"
    "「推薦が主観的であることの透明性」「ユーザー目線でのアルゴリズム文書化」"
    "「基礎にある価値と前提の開示」を挙げた。",
    "すべての発言・採決に、会議録や参議院の<b>当該箇所へ直接ジャンプするリンク</b>を付けています。"
    "編集した要約を信じなくても、元に当たれます。運用ルールと掲載基準も全文公開しています。",
    _cite("Stockinger, Maas, Talvitie &amp; Dignum (2024) Trustworthiness of voting advice applications in Europe (Ethics and Information Technology)", "https://link.springer.com/article/10.1007/s10676-024-09790-6"))

  + _rs("keep",
    "熟議の場を作ろうとせず、情報の整理に絞る",
    "参加型プラットフォーム Decidim をカタルーニャの自治体で検証した研究は、"
    "実証的に確認できた達成が<b>熟議や主権の市民への移転ではなく、透明性・情報の整理・市民提案の収集</b>に"
    "現れたと報告している。",
    "このサイトは議論の場を持ちません。一次情報を整理して並べ、判断は有権者に返します。"
    "設計として狭いのは、意図的なものです。",
    _cite("Borge, Balcells &amp; Padr&oacute;-Solanet (2023) Democratic Disruption or Continuity? (American Behavioral Scientist)", "https://journals.sagepub.com/doi/abs/10.1177/00027642221092798"))

  + _rs("keep",
    "選挙が近づいたら、集計の公開を止める",
    "公職選挙法第138条の3は「何人も、選挙に関し、公職に就くべき者を予想する人気投票の経過又は結果を公表してはならない」と定め、"
    "比例代表の選挙については政党を予想するものを含む。罰則は第242条の2にある。"
    "立法趣旨は、選挙人が誤った予断を抱くことを防ぐことにあると説明されている。",
    "「みんなの結果」の公開と保存を、設定ひとつで停止できるようにしてあります。"
    "停止中は、この条文を根拠として明示した通知だけが残ります。"
    "<b>集計の公開が本条に当たるかどうかは、私たちの解釈であって確定した見解ではありません。</b>"
    "安全側に倒して止める設計にしています。",
    _cite("e-Gov 法令検索 公職選挙法", "https://laws.e-gov.go.jp/law/325AC1000000100"))

  + _rs("keep",
    "「ワンイシュー」は、政党が“何を強調するか”に注目する",
    "政党競争の顕出性理論（saliency theory, Budge &amp; Farlie 1983）は、"
    "<b>政党は同じ争点で賛否を戦わせるより、自分が得意な争点を選んで強調し、他を強調しないことで競う</b>、"
    "と説く。各国の公約を分析する Manifesto Project も、この「強調の違い」を数える発想に立っている。"
    "「その党が最も強調している1争点」に注目することには、こうした理論的な下敷きがある。",
    "各党の「ワンイシュー」を示す機能は、この<b>顕出性理論から示唆を得たもの</b>です。"
    "ただし<b>顕出性理論そのものの実装ではありません</b>——発言量などを体系的に計量したのではなく、"
    "一次情報にもとづく<b>編集判断による入口</b>です（04も参照）。"
    "そのうえで、混同を避けるために3つを分けています。"
    "<b>①強調（ワンイシュー＝どの争点を前面に出すか）②賛否（「政策で照らす」の設問＝その争点にどう立つか）"
    "③重視度（「◎ 特に重視」＝あなたがどの争点を重く見るか）。</b>"
    "とくに③の重みづけは、<b>あなたが判断材料に重みを置くための操作であって、投票行動を予測する係数ではありません。</b>",
    _cite("Manifesto Project（MARPOR・顕出性理論にもとづく公約分析）", "https://manifesto-project.wzb.eu/"))

  + '</section>'

  '<section class="ab-sec"><p class="ab-k">02 ／ 採らなかったこと</p>'
  '<h2 class="ab-h">先行研究にはあるが、この設計では使わない手法</h2>'

  + _rs("drop",
    "記名投票からの尺度化（NOMINATE、ベイズIRT など）",
    "記名投票を統計モデルにかけて議員・政党を空間上に配置する手法は、政治学で確立した道具である。"
    "一方で、推定結果の差の大部分が<b>モデルの識別制約という分析者の選択</b>に由来することが指摘されている。",
    "使いません。「この党は中道からどれだけ離れている」という表示は、"
    "中道が正解だという価値判断を持ち込みます。手法として否定するのではなく、"
    "<b>このサイトの目的に対して使わない</b>という判断です。",
    _cite("voteview: NOMINATE と IDEAL の比較", "https://legacy.voteview.com/pdf/nominatevideal.pdf"))

  + _rs("drop",
    "AIによる立場の自動分類を、そのまま表示すること",
    "日本語の議会発言から政党の賛否を当てる課題は、<b>NTCIR QA Lab-PoliInfo として10年近く共有タスク化</b>され、"
    "公開データセットと評価指標がある。ただし<b>対象は都議会・市町村議会であって、国会ではない</b>。"
    "報告される精度は0.97〜0.99と高いが、<b>主催者自身が「議員が冒頭で立場を明言する表層表現を拾っているだけで、"
    "本来の目的に合っていない」と自己批判</b>し、後の回では該当表現を伏せている。"
    "また、<b>政党名という手がかりだけでモデルのラベルが偏る</b>ことを示した実証研究もある。",
    "AIが判定した立場を、検証なしに有権者へ提示することはしません。"
    "「政策で照らす」の各党の立場は、参議院の採決か各党の公約から人が判断し、"
    "設問ごとに<b>何にもとづく判断かを表示</b>しています。"
    "高い精度が報告されていても、それが表層的な言い回しを拾った結果でありうることは、"
    "この判断を裏づける材料だと考えています（03も参照）。",
    _cite("NTCIR-15 QA Lab-PoliInfo-2 概要", "https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings15/pdf/ntcir/01-NTCIR15-OV-QALAB-KimuraY.pdf")
    + " ／ " + _cite("NTCIR-17 PoliInfo-4 概要", "https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings17/pdf/ntcir/01-NTCIR17-OV-QALAB-OgawaY.pdf"))

  + _rs("drop",
    "AIに合意や結論の文章を作らせること",
    "AIが人々の意見を統合して共通の立場を書く実験（DeepMind の Habermas Machine）は、"
    "AI生成の集団声明が人間の書いたものより明確・低バイアスと評価されたと報告し、Science に掲載された。"
    "一方で、<b>AIによる合意生成には「何を合意とみなすか」「誰を包摂するか」といった規範判断が"
    "不可避に埋め込まれる</b>という批判がある。",
    "採決の理由の要約も、各党の主張の統合も、AIには書かせません。"
    "「ワンイシュー」や分野の要約は人の編集判断であることを明示し、党の公式見解とは称していません。",
    _cite("Tessler et al. (2024) AI can help humans find common ground in democratic deliberation (Science 386, eadq2852)", "https://www.science.org/doi/10.1126/science.adq2852"))

  + _rs("drop",
    "利用者に合わせて、見せる情報を変えること",
    "AIによる説得力の研究は動いている領域である。"
    "個人情報にアクセスできる GPT-4 が人間より説得的だったとする研究がある一方、"
    "<b>マイクロターゲティングの上乗せ効果は検出できなかった</b>とする研究もあり、争いがある。"
    "大規模な追試では、説得力の源泉は個人化よりもポストトレーニングとプロンプト設計にあり、"
    "<b>説得力を高める手法は事実正確性を下げる</b>方向に働くことも報告された。",
    "利用者の回答や属性によって、表示する発言・採決を変えることはしません。"
    "誰が見ても同じものが並びます。「政策で照らす」の結果表示も、"
    "一致した争点を挙げるだけで、投票先の推薦はしません。",
    _cite("Salvi et al. (2025) On the conversational persuasiveness of GPT-4 (Nature Human Behaviour)", "https://www.nature.com/articles/s41562-025-02194-6")
    + " ／ " + _cite("Hackenburg &amp; Margetts (2024) Evaluating the persuasive influence of political microtargeting with LLMs (PNAS)", "https://www.pnas.org/doi/10.1073/pnas.2403116121")
    + " ／ " + _cite("Hackenburg et al. (2025) The levers of political persuasion with conversational AI (Science)", "https://www.science.org/doi/10.1126/science.aea3884"))

  + '</section>'

  '<section class="ab-sec"><p class="ab-k">03 ／ まだ手当てできていないこと</p>'
  '<h2 class="ab-h">先行研究が指摘していて、このサイトが解けていない問題</h2>'
  '<p class="ab-b">ここが、このページで最も重要な部分です。'
  '調査は自分の設計を正当化するためではなく、<b>弱点を先に見つけるため</b>に行っています。'
  '以下は、先行研究に照らして、現時点で解けていないと私たちが考えている点です。</p>'

  + _rs("open",
    "設問の選び方が、一致度を左右する",
    "投票支援ツール批判の最も基礎的な研究は、<b>ステートメント（設問）の選択が、"
    "利用者と政党の一致度に深甚な影響を与える</b>ことを実証した。"
    "これは点数化するかどうかとは独立に、マッチング機能を持つ限り必ず生じる。"
    "ドイツの Wahl-O-Mat は、混成チームが80〜100案を作り、全政党に回答させたうえで38問に絞る"
    "多段階の編集過程を公開している。",
    "設問の来歴は<b>04で洗い出して公開しました</b>"
    "（採決から判定した設問が" + str(QAUDIT["by_basis"]["採決"]) + "問、"
    "公約・発言から判定した設問が" + str(QAUDIT["by_basis"]["公約・発言"]) + "問、"
    "設問になりえた記名投票は" + str(QAUDIT["pool_total"]) + "件）。"
    "<b>ただし手続きそのものは、いまも踏んでいません。</b>"
    "設問は運営者が選んだもので、Wahl-O-Mat のように全政党に回答させて絞り込む多段階の過程はありません。"
    "選定の基準も、選んだ時点では文書になっていませんでした。"
    "<b>来歴を数えたことは、選び方が妥当であることの証明にはなりません。</b>"
    "設問数が少ないことも、この問題を緩和しません（1問あたりの影響が大きくなります）。",
    _cite("Walgrave, Nuytemans &amp; Pepermans (2009) Voting Aid Applications and the Effect of Statement Selection (West European Politics)", "https://medialibrary.uantwerpen.be/oldcontent/container2608/files/Walgrave%20et%20al%202009%20-%20voting%20aid%20applications.pdf")
    + " ／ " + _cite("Wahl-O-Mat（連邦政治教育センター）", "https://www.wahl-o-mat.de/"))

  + _rs("open",
    "一致度の計算式そのものが、編集判断である",
    "助言は採用する空間モデルに強く依存する。"
    "オランダ StemWijzer を対象にした研究は、<b>利用者の過半数が、別の空間モデルを使っていれば"
    "別の助言を受け取っていた</b>ことを示した。"
    "次元の取り方、距離の測り方、重み付けの与え方によって結果は変わる。",
    "「政策で照らす」は、各設問の立場を+1／0／−1で表し、単純な一致数を数え、"
    "重視した争点を3倍にしています。<b>これは数ある計算方法のひとつにすぎず、"
    "別の計算法なら別の結果になりえます。</b>"
    "この点は<b>04でありうる回答すべてを計算して測りました</b>"
    "（割り方を変えると" + str(AUDIT["flip_rate"]["proximity"]) + "%の入力で1位の党が変わります）。"
    "測っても<b>どの式が妥当かは決まらない</b>ので、この項目は解決済みにしていません。"
    "（なお国内の投票マッチング型サービスを調べた範囲では、<b>算出式を公開しているものは確認できませんでした</b>。公開していること自体は前進ですが、公開すれば恣意性が消えるわけではありません。）",
    _cite("Louwerse &amp; Rosema (2014) The design effects of voting advice applications (Acta Politica)", "https://link.springer.com/article/10.1057/ap.2013.30"))

  + _rs("open",
    "マッチングの仕組みが、特定の立場を押し上げる可能性がある",
    "ドイツの投票支援ツール Voteswiper を2025年連邦議会選挙で分析した研究は、"
    "<b>中道的な立場の利用者が極右政党にマッチしやすく、ツールがポピュリスト政党・極右政党を"
    "不均衡に利しうる</b>と報告している。設問の作り方と一致度の計算のしかたから生じる効果であり、"
    "運営者がどの党を支持するかとは関係なく起きる。",
    "<b>04で、ありうる回答すべてについてどの党が1位に出るかを数えました。</b>"
    "仕組みの癖（立場を示した設問が少ない党ほど1位に出やすい）は、そこで数字になっています。"
    "ただし<b>この研究の指摘そのものは、まだ検証できていません。</b>"
    "「ポピュリスト政党・極右政党を利する」かどうかを測るには、"
    "各党を左右のような軸のどこに置くかを先に決める必要があり、"
    "<b>このサイトは政党を軸の上に配置しません</b>（それ自体が格付けになるため）。"
    "偏りの向きまでは、この設計では測れません。"
    "設計上どの党にも肩入れしていないことは、結果が偏らないことを意味しません。",
    _cite("Fr&ouml;hle et al. (2026) From Swipes to Votes (Policy &amp; Internet 18-1, DOI 10.1002/poi3.70028)", "https://doi.org/10.1002/poi3.70028")
    + "（本文は取得できず、抄録での確認）")

  + _rs("open",
    "「中立」は名乗れない。名乗れるのは「非党派的」まで",
    "投票支援ツールの哲学的検討は、よく設計されたツールは<b>非党派的（non-partisan）ではありうるが、"
    "政治的に中立（politically neutral）ではない</b>と論じる。"
    "ツールは開発者の前提に基づいて政治情報を構造化し、"
    "<b>争点と政党の選択を通じて、選挙のアジェンダそのものを形成する</b>からである。"
    "これは原典リンクを付けても解消されない。",
    "このサイトの6つの分野の区切り方、11問の設問、掲載する10党の線引きは、"
    "いずれもアジェンダを形づくる行為です。掲載基準と掲載しない会派の理由は公開していますが、"
    "<b>「中立」という言葉の使い方は、この指摘に照らして 検討中です。</b>"
    "現時点の私たちの立場は「評価をしない」「特定の党に肩入れしない」であって、"
    "「どの立場からも等距離である」ではありません。",
    _cite("Fossen &amp; Anderson (2014) What's the point of voting advice applications? (Electoral Studies 36)", "https://www.sciencedirect.com/science/article/pii/S0261379414000419"))

  + _rs("open",
    "並べるだけでも、読み手の推論は歪む",
    "日本の有権者を対象にしたサーベイ実験は、<b>ある政党に目立つ「看板政策」があると、"
    "有権者はその党の他の政策についての立場まで、看板政策から推し量って判断してしまう</b>ことを示した。"
    "情報を評価せずに並べても、受け取る側で推論が働く。",
    "このサイトには<b>「ワンイシュー」という、各党の力点を1つに絞って示す機能があります。</b>"
    "編集判断であることは明示していますが、<b>それが他の分野の読まれ方まで方向づける可能性は"
    "説明していません。</b>点数化しないことでは、この歪みは防げません。",
    _cite("秦正樹・Song Jaehyun (2020)「争点を束ねれば『イデオロギー』になる？」『年報政治学』2020-I", "https://www.jstage.jst.go.jp/article/nenpouseijigaku/71/1/71_1_58/_pdf"))

  + _rs("open",
    "記名投票は、代表的な標本ではない",
    "強い党議拘束の下では、議員個人の投票は本人の選好の表明ではなく、政党としての行動である。"
    "また、どの議案を記名投票にかけるかに偏りがあれば、"
    "<b>記録に残った投票は議会の行動の代表的な標本ではなくなる</b>。",
    "<b>ここには、私たちの側の事実誤りがありました。</b>"
    "この項目には以前「記名投票にかけられる議案は参議院の採決全体のごく一部だ」と書いていましたが、"
    "04で数えたところ<b>参議院の本会議で議決された議案の"
    + str(RCAUDIT["total"]["named_pct"]) + "％が記名投票</b>でした。"
    "『ごく一部』は誤りだったので訂正します。"
    "<b>ただし、この研究の指摘そのものが消えたわけではありません。</b>"
    "党議拘束の下で政党としての行動を見ているという点は変わらず、"
    "本会議の外（委員会での採決）や、衆議院のほとんどの議決は、"
    "いまも個人別・会派別には残りません。"
    "「行」は各党の行動の全体像ではなく、記録に残った一部です。",
    _cite("Hix, Noury &amp; Roland (2018) Is there a selection bias in roll call votes? Evidence from the European Parliament", "https://ideas.repec.org/p/ehl/lserod/87696.html"))

  + _rs("open",
    "「みんなの結果」は世論ではない",
    "投票支援ツールの利用者データを使った分析には、"
    "<b>ツールを使うことを選んだ人だけが集まるという自己選択バイアス</b>がかかる。"
    "利用者は高学歴・若年・政治的関心の高い層に偏りやすいことが指摘されている。",
    "集計ページに「これは世論調査ではない」旨は書いていますが、"
    "<b>回答者がどう偏っているかの説明としては不十分</b>です。"
    "母集団はこのサイトを見に来て、最後まで答えた人に限られます。",
    _cite("Pianzola (2014) Selection biases in Voting Advice Application research (Electoral Studies 36)", "https://doi.org/10.1016/j.electstud.2014.04.012"))

  + _rs("open",
    "「有権者が判断できるようになる」効果は、自明ではない",
    "9カ国22研究・73,673名を統合したメタ分析は、投票支援ツールが"
    "<b>投票参加に与える効果（OR=1.87）と投票先に与える効果（OR=1.44）には強い証拠がある</b>一方、"
    "<b>政治知識の向上については信頼区間が0をまたぐ穏当な証拠にとどまる</b>と報告した。",
    "このサイトは「判断材料を提供する」と述べていますが、"
    "<b>この種のツールで政治知識が増えるという証拠は、実は強くありません。</b>"
    "効果を主張しないという形で扱っていますが、目的の書き方としては再検討の余地があります。",
    _cite("Munzert &amp; Ramirez-Ruiz (2021) Meta-Analysis of the Effects of Voting Advice Applications (Political Communication 38-6)", "https://www.tandfonline.com/doi/abs/10.1080/10584609.2020.1843572"))

  + _rs("open",
    "AIによる立場判定の精度を、測っていない",
    "日本語の議会発言を対象にした共有タスクは存在するが、<b>その対象は地方議会であって国会ではない</b>。"
    "国会の発言について、抽出や分野への割り当ての精度を測れる公開ベンチマークは、今回の調査では見つからなかった。",
    "このサイトは、AIに立場を自動判定させて表示する作りにはしていません（02を参照）。"
    "ただし発言の抽出・分野への割り当てにはAIが関与しています。"
    "<b>その工程の精度を、数値で測ってはいません。</b>"
    "現状は全件の引用を原文と機械照合することで担保していますが、これは「引用が正確か」を見ているだけで、"
    "<b>「拾うべき発言を拾えているか」は測れていません</b>。国会向けの物差しが無いことは言い訳になりません。"
    "せめて<b>どれだけ選んでいるかは04で数えました</b>"
    "（表示している発言は、条件を通った候補の中央値" + str(XAUDIT["total"]["median_candidates_per_shown_cell"])
    + "件のうちの1件）。ただし精度そのものは、これでも測れていません。",
    _cite("NTCIR-15 QA Lab-PoliInfo-2 データセット", "https://github.com/poliinfo2/NTCIR15-QA-Lab-PoliInfo-2-Dataset")
    + " ／ " + _cite("Kaneko, Asano &amp; Miwa (2026) Extracting ideological dimensions from legislative speeches in the Japanese Diet (Social Science Japan Journal 29-1)", "https://academic.oup.com/ssjj/article/29/1/jyag001/8507400"))

  + _rs("open",
    "責任者と連絡先が、明示されていない",
    "アムステルダムとヘルシンキが2020年に公開した公的AI登録簿は、"
    "行政が使うアルゴリズムについて<b>使用データ／用途／人間がどう関与するか／リスク評価／"
    "責任者と連絡先／フィードバック経路</b>の開示を項目としている。",
    "6項目のうち、<b>使用データ／用途／人の関与／限界（リスク）／フィードバック経路の5つは公開しています。</b>"
    "残る「責任者と連絡先」について、<b>運営主体は明示することにしました</b>——"
    "このサイトは<b>「AI政策くらべ」として、個人が非営利で運営</b>しています。"
    "連絡の窓口は、<a class=\"src\" href=\"feedback.html\">ご意見フォーム</a>"
    "（GitHubのアカウントは不要です）と、GitHubのIssuesです。"
    "一方で<b>運営者の氏名や個人の連絡先（メール・住所）は、公開しません。</b>"
    "個人が運営しているためで、その分の説明責任は"
    "「誰が見ても同じ一次情報が並び、作り方をすべて公開する」ことで果たす方針です。"
    "組織としての責任者名を出せないことは、この登録簿の水準には届いていません。",
    _cite("Amsterdam AI Register（OECD.AI）", "https://oecd.ai/en/dashboards/policy-initiatives/amsterdams-ai-register-8123")
    + " ／ " + _cite("Public AI Registers（Amsterdam Open Research）", "https://openresearch.amsterdam/en/page/73074/public-ai-registers"))

  + _rs("open",
    "6つの分野の枠が、少数政党の「際立ち」を埋もれさせているかもしれない",
    "政治学のニッチ政党研究は、<b>ニッチ政党を「主流政党が無視する、左右の軸に乗らない"
    "少数の争点に特化した政党」</b>と定義する。挑戦者政党が既存の政党システムを揺るがすのは、"
    "<b>大政党が見落としている新しい争点</b>を持ち込むからだ、という研究もある。"
    "つまり、少数政党を少数政党たらしめているのは、<b>ふつうの分野分けに収まらない争点</b>であることが多い。",
    "このサイトは、各党の言と行を<b>6つの分野（財政・外交安保・社会保障・エネルギー環境・"
    "経済産業・憲法）に振り分けて</b>並べています。しかしこの6分野は、<b>まさに大政党が争う"
    "主流の争点軸</b>でもあります。そのため、少数政党の看板になっている争点"
    "（たとえば外国人政策、放送の受信料、デジタル・ガバナンス改革など、6分野に素直に収まらないもの）は、"
    "<b>「他党と同じ6分野」の中に均され、その党を際立たせている当のものが見えにくくなる</b>おそれがあります。"
    "分野の分け方自体が編集判断であることは04で書いていますが、"
    "<b>その分け方が、特定の党の争点を構造的に不利にしていないかは、まだ確かめていません。</b>"
    "たとえばドイツの海賊党は、デジタルの権利や<b>政治の透明化</b>という、"
    "左右の軸にも経済・社会文化の軸にも乗りにくい争点を掲げました"
    "（このサイトの6分野にも素直には収まりません）。"
    "海外では、こうした争点の党が議席や政権入りに至った例（チェコの海賊党）もあれば、"
    "定着できずに消えた例（ドイツの海賊党）もあります。"
    "<b>ここで言いたいのは党の成否ではなく、6分野という枠の側が、"
    "そもそもこうした争点を置きにくいということ</b>です。"
    "さらに、日本の有権者研究は、<b>若い世代では「保守／革新」という左右の対立軸そのものが"
    "共有されなくなっている</b>と報告しています。"
    "もしそうなら、主流の争点軸にならった分野分けは、世代によって効き方が変わることになります。"
    "<b>→ この弱点は、04で実際に測りました。</b>6分野の外の争点（外国人・移民、デジタル）が、"
    "参政党やチームみらいの最大の強調として現れ、6分野だけでは埋もれることを数字で確認しています。",
    _cite("Wagner（ニッチ政党／著者公開）", "https://www.wagnermarkus.net/uploads/7/2/9/8/72983017/niche_parties_chapter_web.pdf")
    + " ／ " + _cite("Meyer &amp; Miller (2015) The niche party concept and its measurement (Party Politics 21-2)", "https://pmc.ncbi.nlm.nih.gov/articles/PMC5180693/")
    + " ／ " + _cite("De Vries &amp; Hobolt (2020) Political Entrepreneurs (Princeton University Press)", "https://press.princeton.edu/books/hardcover/9780691194752/political-entrepreneurs")
    + " ／ " + _cite("ドイツ海賊党（Wikipedia）", "https://en.wikipedia.org/wiki/Pirate_Party_Germany")
    + " ／ " + _cite("遠藤晶久・ウィリー・ジョウ (2019)『イデオロギーと日本政治』新泉社", "https://www.shinsensha.com/books/2188/"))

  + _rs("open",
    "「政策で照らす」は賛否を測るが、争点には「賛否で表せないもの」がある",
    "政治学は争点を2種類に分ける。<b>位置争点</b>（目的そのものについて賛成・反対が割れる争点）と、"
    "<b>valence 争点</b>（目的には皆が賛成で、どの党が上手に実現できるかという能力で競う争点）だ。"
    "「汚職を減らす」「経済を成長させる」のように、<b>誰も反対しない争点</b>がこれにあたる。",
    "「政策で照らす」の設問は、すべて<b>賛成／どちらでもない／反対</b>という位置争点の形をしています。"
    "ところが、各党のワンイシューとしてこのサイトが記録している"
    "「手取りを増やす」「行政の透明化」「身を切る改革」などは、<b>誰も正面から反対しない valence 争点</b>で、"
    "賛否では表せません（透明化に「反対」する人はいません。競争は能力と優先順位です）。"
    "<b>照合の軸が位置争点ひとつであることは、valence で競うワンイシュー政党を、"
    "構造的にうまく表現できないことを意味します。</b>"
    "設問によっては賛否から立場を一意に導けないことは既に開示していますが、"
    "その背景にこの区別があることは、まだ十分に説明できていません。",
    _cite("Stokes (1963) Spatial Models of Party Competition (American Political Science Review 57-2)", "https://doi.org/10.2307/1952828"))

  + '</section>'

  # ---- 03の指摘のうち、測れるものを実際に測った結果。数字はすべて state/matching_audit.json から。
  + '<section class="ab-sec"><p class="ab-k">04 ／ 自分たちで測ったこと</p>'
  '<h2 class="ab-h">「政策で照らす」の照合を、ありうる回答すべてで検査した</h2>'
  '<p class="ab-b">03に挙げた指摘のうち2つ——<b>算出式の選び方が結果を左右する</b>と、'
  '<b>照合の仕組み自体が特定の立場を押し上げうる</b>——は、'
  '「そうかもしれません」と書くだけでは確かめたことになりません。'
  'このサイトの「政策で照らす」は、入力できる回答が有限です'
  '（' + str(AUDIT["questions"]) + '問 × 賛成／どちらでもない／反対の3択、それぞれに「◎重視する」の有無）。'
  'だから標本を取る必要がなく、<b>ありうる入力を全部計算できます</b>。'
  '<b>' + f'{AUDIT["total_inputs"]:,}' + '通り</b>すべてについて一致度を計算し、'
  'どの党が1位に出るかを数えました。'
  '検査するプログラムと結果の数値は、'
  '<a class="src" href="https://github.com/ai-seisaku-kurabe/ai-seisaku-kurabe.github.io/blob/main/tools/agents/audit_matching.py" target="_blank" rel="noopener">'
  'audit_matching.py</a> と '
  '<a class="src" href="https://github.com/ai-seisaku-kurabe/ai-seisaku-kurabe.github.io/blob/main/tools/state/matching_audit.json" target="_blank" rel="noopener">'
  'matching_audit.json</a> にあります。このページの数字は、そのファイルから直接流し込んでいます。</p>'

  + _audit_table(AUDIT)
  + '<p class="rs-note">※「1位に出る割合」は、'
  + f'{AUDIT["total_inputs"]:,}' + '通りの入力のうち、その党が結果の先頭に表示される割合です。'
  '党の優劣ではなく、<b>照合の仕組みの癖</b>を測った数字です。'
  '「賛否が釣り合った回答」は、賛成と反対を同じ数だけ選んだ回答'
  '（' + f'{AUDIT["balanced_inputs"]:,}' + '通り）に限った場合の割合です。</p>'

  + _rs("meas",
    "分かったこと①：立場を示した設問が少ない党ほど、1位に出やすい",
    "現行の計算式は、<b>その党が賛成か反対かをはっきり示している設問だけを分母にする</b>。"
    "そのため中立・不明の設問が多い党ほど分母が小さくなり、少ない一致で高い割合が出る。"
    "設問の数を増やしても、この性質は消えない。",
    "検査の結果、<b>立場を示した設問が" + str(min(r["stance_nonzero"] for r in AUDIT["by_party"]))
    + "問の党と、" + str(max(r["stance_nonzero"] for r in AUDIT["by_party"]))
    + "問の党が、同じ土俵で比べられていること</b>が数字で確認できました。"
    + (lambda m: "立場を示した設問がいちばん少ない党（" + m["short"] + "・"
       + str(m["stance_nonzero"]) + "問）は、割合で出す現行式では"
       + str(m["top_share"]["current"]) + "%の入力で単独1位になりますが、"
       + "割らずに点数を合計する式にすると" + str(m["top_share"]["proximity"]) + "%まで下がります。"
       )(min(AUDIT["by_party"], key=lambda r: (r["stance_nonzero"], r["short"])))
    + "これは公約や発言で立場を確認できなかった党を「中立(0)」にするという、"
    "捏造しないための扱いから生じています。"
    "<b>直し方は決まっていません。</b>中立を不一致として数えれば分母は揃いますが、"
    "今度は「立場を確認できなかったこと」を「あなたと違うこと」として計算することになり、"
    "別の歪みが入ります。現時点では、この癖があることを数字で開示することまでが対応です。",
    "この検査は先行研究の追試ではなく、このサイト自身の測定です。"
    "着想の元は " + _cite("Fr&ouml;hle et al. (2026) From Swipes to Votes (Policy &amp; Internet 18-1)",
                          "https://doi.org/10.1002/poi3.70028") + " です。")

  + _rs("meas",
    "分かったこと②：割合にするか、点数の合計にするかで、1位の党が変わる",
    "先行研究は、助言が空間モデルに依存することを指摘してきた。"
    "そこで現行式のほかに、<b>近接性（距離）型・方向性（スカラー積）型・点数合計型</b>でも同じ検査を回した。"
    "検査の途中で分かったことがひとつある。<b>賛成・どちらでもない・反対の3択では、"
    "この3つはまったく同じ順位を出す</b>（|u−p| = 1 − u×p が恒等的に成り立つため）。"
    "つまり本当の分かれ目は近接性か方向性かではなく、"
    "<b>その党が立場を示した設問の数で割るかどうか</b>だった。",
    "割らない式に替えると、<b>" + str(AUDIT["flip_rate"]["proximity"])
    + "%の入力で1位の党が変わりました。</b>"
    "「◎重視する」の3倍を外すだけでも、<b>" + str(AUDIT["flip_rate"]["current_noweight"])
    + "%の入力で1位が変わります。</b>"
    "どちらの式が正しいとは言えません。言えるのは、"
    "<b>結果は回答だけで決まっているのではなく、私たちが選んだ計算方法にも左右されている</b>ということです。"
    "この数字を出したので、「別の計算法なら別の結果になりえます」は"
    "推測ではなく測定された事実として書けるようになりました。",
    _cite("Louwerse &amp; Rosema (2014) The design effects of voting advice applications (Acta Politica)",
          "https://link.springer.com/article/10.1057/ap.2013.30"))

  + _rs("meas",
    "分かったこと③：一度も1位に表示されない党があった（修正しました）",
    "検査で、<b>" + ("・".join("＝".join(p) for p in AUDIT["identical_stance_pairs"])
                     if AUDIT["identical_stance_pairs"] else "同じ立場の組")
    + " が" + str(AUDIT["questions"]) + "問すべてで同じ立場</b>だと分かった。"
    "立場が同じなら一致度は必ず等しくなり、どちらが上に出るかは"
    "<b>同点のときの並べ替え規則だけで決まる</b>。"
    "当時の規則は「判定に使われた設問数が多い順、それも同じなら元の並び順」だったため、"
    "片方は<b>どんな回答をしても結果の先頭に出てこなかった</b>。",
    "これは先行研究からの指摘ではなく、<b>この検査で見つけた自分たちの欠陥</b>です。"
    "並べ替えの規則が、利用者には優劣に見えていました。"
    "<b>同じ一致度の党は「同率」として明示し、区別できないことをその場で伝える形に直しました。</b>"
    "結果の画面には「一致度が同じ党がいくつあるか」「この設問数では区別できないこと」"
    "「上下の並びは優劣ではないこと」が出ます。"
    "同じ見落としが再び入らないよう、③検証班の機械チェックにも項目を足しました。",
    "この項目に対応する先行研究はありません。全数検査から出た結果です。")

  + _rs("meas",
    "分かったこと④：設問がどこから来たかを数えた（手続きは踏んでいないままです）",
    "投票支援ツール批判の最も基礎的な研究は、<b>設問の選択が一致度に深甚な影響を与える</b>ことを実証した。"
    "そこで、良い設問かどうかではなく（それは機械には決められない）、"
    "<b>設問が何から作られ、何が使われなかったか</b>を数えた。",
    "「政策で照らす」の" + str(QAUDIT["questions"]) + "問のうち、"
    "<b>" + str(QAUDIT["by_basis"]["採決"]) + "問</b>は参議院の記名採決での賛否から立場を判定し、"
    "<b>" + str(QAUDIT["by_basis"]["公約・発言"]) + "問</b>は各党の公約と国会での発言から判定しています"
    "（採決の賛否だけでは賛成・反対の理由を一意に決められない設問があるためです）。"
    "掲載している" + str(len(QAUDIT["pool"])) + "会期の記名投票は"
    + "・".join("第" + s + "回" + str(v["roll_calls"]) + "件" for s, v in QAUDIT["pool"].items())
    + "の<b>あわせて" + str(QAUDIT["pool_total"]) + "件</b>あり、"
    "設問の根拠としてリンクしているのは<b>" + str(len(QAUDIT["vote_ids_used"])) + "件</b>です。"
    "<b>残りは検討して外したのではなく、多くは検討そのものをしていません。</b>"
    "選定の基準は、選んだ時点で文書になっていませんでした。"
    "ここに出しているのは事後に洗い出した記録で、当時の議事録ではありません。"
    "<b>Wahl-O-Mat のような多段階の手続きは、いまも踏んでいません。</b>"
    "この開示は問題を解消するものではなく、問題の大きさを見えるようにするものです。"
    "設問の直前にも、同じ内容の短い説明を置きました。",
    _cite("Walgrave, Nuytemans &amp; Pepermans (2009) Voting Aid Applications and the Effect of Statement Selection (West European Politics)",
          "https://medialibrary.uantwerpen.be/oldcontent/container2608/files/Walgrave%20et%20al%202009%20-%20voting%20aid%20applications.pdf")
    + " ／ " + _cite("Wahl-O-Mat（連邦政治教育センター）", "https://www.wahl-o-mat.de/"))

  + _rs("meas",
    "分かったこと⑤：「記名投票はごく一部」は、参議院については私たちの誤りだった",
    "記名投票を材料にする研究は、<b>どの議案を記名投票にかけるかに偏りが乗る</b>ことを指摘してきた。"
    "このサイトの「行」は参議院の記名投票だけでできているので、この指摘は設計の根幹に当たる。"
    "参議院の議案情報は<b>議案ごとに採決方法（押しボタン／記名／起立／異議の有無）を公表している</b>ため、"
    "程度は数えられる。"
    + "・".join("第" + s + "回" + str(v["bills_listed"]) + "件"
                for s, v in RCAUDIT["sessions"].items())
    + "の明細を集めて数えた。",
    "<b>参議院の本会議で議決された" + str(RCAUDIT["total"]["decided"]) + "件のうち、"
    + str(RCAUDIT["total"]["named"]) + "件（" + str(RCAUDIT["total"]["named_pct"])
    + "％）が、誰がどう投じたかの残る採決でした。</b>"
    "私たちはこのページに「記名投票は参議院の採決全体のごく一部」と書いていましたが、"
    "<b>これは誤りだったので訂正しました。</b>"
    "一方で、同じ議案を衆議院がどう採決したかを見ると、"
    + str(RCAUDIT["total"]["shugiin_decided"]) + "件中"
    + str(RCAUDIT["total"]["shugiin_named"]) + "件（"
    + str(RCAUDIT["total"]["shugiin_named_pct"]) + "％）しか個人別の記録が残っていません。"
    "<b>「一部しか残らない」のは衆議院の側でした。</b>"
    "残る限界は3つあります。"
    "①記名投票" + str(RCAUDIT["total"]["named"]) + "件のうち"
    + str(RCAUDIT["total"]["named_unanimous"]) + "件は<b>全会一致</b>で、"
    "党の違いは読み取れません（差が出るのは"
    + str(RCAUDIT["total"]["named_majority"]) + "件）。"
    "②数えたのは<b>本会議だけ</b>で、委員会での採決は個人別・会派別に残りません。"
    "③党議拘束の下では、投票は議員本人の選好ではなく政党としての行動です。"
    "この記名投票は<b><a href=\"votes.html\">採決一覧</a>で全件を並べています</b>"
    "（「政党で選ぶ」に各分野で載せているのは、この中から選んだ代表例です）。"
    "なお、記名投票の一覧と議案情報は出どころが違うため件数が少しずれます"
    "（人事案件や決算の件名の付け方が資料によって異なるためで、差は"
    + "・".join("第" + s + "回" + str(v["crosscheck"]["vote_list"]) + "件と"
                + str(v["crosscheck"]["bill_index"]) + "件"
                for s, v in RCAUDIT["sessions"].items() if v.get("crosscheck"))
    + "）。",
    _cite("Hix, Noury &amp; Roland (2018) Is there a selection bias in roll call votes? Evidence from the European Parliament",
          "https://ideas.repec.org/p/ehl/lserod/87696.html")
    + " ／ " + _cite("参議院 議案情報（第217回国会）",
                     "https://www.sangiin.go.jp/japanese/joho1/kousei/gian/217/gian.htm"))

  + _rs("meas",
    "分かったこと⑥：発言は「候補のうち1件」で、その選択の度合いを数えた",
    "「言」の各発言は、会議録を争点キーワードで検索し、答弁側・手続き的発言・"
    "統一会派の代表討論などを除いたうえで、<b>最初に条件を満たした1件</b>を採ったものである。"
    "国会向けの精度の物差し（拾うべき発言を拾えたか）は無く、正解を作ればそれ自体が編集判断になる。"
    "そこで精度の代わりに、<b>どれだけ選んでいるか</b>を数えた。"
    "各党×分野×会期について、同じ検索と同じ除外条件を通る発言が何件あるかを、"
    "各会期の会期期間にわたって数えた。",
    "<b>条件を通った候補の発言は、掲載" + str(len(XAUDIT["windows"]))
    + "会期であわせて" + f'{XAUDIT["total"]["candidate_total"]:,}' + "件</b>ありました。"
    "このサイトが見せているのは、そのうち<b>各枠1件だけ</b>です。"
    "表示している枠あたりの候補は<b>中央値" + str(XAUDIT["total"]["median_candidates_per_shown_cell"])
    + "件、最も多い枠で" + str(XAUDIT["total"]["max_candidates"]) + "件</b>で、"
    "<b>" + str(XAUDIT["total"]["shown_cells_with_multiple_candidates"]) + "／"
    + str(XAUDIT["total"]["shown_cells_counted"]) + "枠で候補が2件以上</b>ありました。"
    "<b>つまり表示している発言は「多くのうちの1つ」で、別の1件を選べば違って見えます。</b>"
    "どれが最も代表的かを決める物差しは無いので、これは精度の測定ではありません。"
    "測れたのは選択の度合いだけで、<b>「拾うべきものを拾えているか」は依然として測れていません。</b>"
    "並べている発言が力点の要約でなく一次情報への入口であること、"
    "各分野の全発言は<a class=\"src\" href=\"speeches.html\">発言一覧</a>から辿れることが、"
    "この選択への歯止めです。",
    _cite("NTCIR-15 QA Lab-PoliInfo-2 データセット", "https://github.com/poliinfo2/NTCIR15-QA-Lab-PoliInfo-2-Dataset"))

  + _rs("meas",
    "分かったこと⑦：6分野の外にある争点も測ってみた──そして党の最大の強調に出た",
    "顕出性理論（政党は「どの争点を強調するか」で競う）に立つなら、"
    "各党が国会で<b>どの話題にどれだけ触れたか</b>は数えられる。"
    "03の弱点で「6分野は主流の争点軸なので、それに収まらない少数政党の看板争点が埋もれるおそれがある。"
    "だが確かめていない」と書いた。<b>そこで、実際に測った。</b>",
    "6分野の検索に加えて、<b>6分野に収まらない横断争点</b>"
    "（" + "・".join(SALIENCY["cross_themes"]) + "）の検索語を足し、"
    "各党の質問側発言が各話題にどれだけ触れたかを、掲載"
    + str(len(SALIENCY["sessions"])) + "会期ぶん機械的に数えました。"
    "その結果、<b>6分野に収まらない争点が、いくつかの党では最大の強調として現れました。</b>"
    # 見出しには、その話題の発言数が十分ある（n>=15）ものだけを出す。少数の発言による
    # 大きな割合（例：社民の外国人8件で28.6%）を先頭に置くと、ノイズを事実のように見せてしまう。
    + "".join(
        "<b>" + _saliency_short(c["party"]) + "＝" + esc(c["theme"]) + "（"
        + str(c["share"]) + "％、" + str(c["n"]) + "件）</b>、"
        for c in sorted([x for x in SALIENCY["cross_signal"] if x["n"] >= 15],
                        key=lambda x: -x["share"])[:3])
    + "といった具合です（発言数が少ない党は割合が不安定なので、見出しには発言数の多いものだけを挙げました）。"
    "<b>固定した6分野だけでは、まさにこれらの党を際立たせている争点が、"
    "「他党と同じ6分野」の中に埋もれる</b>——弱点2番を、数字で確かめたことになります。"
    + _saliency_table(SALIENCY)
    + "<b>強い限界があります。</b>"
    "①検索語の選び方は編集判断です（横断争点の語の一覧は"
    "<a href=\"https://github.com/ai-seisaku-kurabe/ai-seisaku-kurabe.github.io/blob/main/tools/agents/audit_saliency.py\" target=\"_blank\" rel=\"noopener\">audit_saliency.py</a>"
    "で公開し、訂正を受け付けます）。"
    "②<b>国会の質問側発言だけ</b>が対象で、公約・演説・記者会見・SNSは含みません。"
    "会議録に出ない強調は測れません。"
    "③発言が少ない党（社民" + str(next((e["total"] for e in SALIENCY["by_party"]
                                       if e["party"] == "社会民主党"), "-"))
    + "件、チームみらい" + str(next((e["total"] for e in SALIENCY["by_party"]
                                    if e["party"] == "チームみらい"), "-"))
    + "件）は割合が不安定です。"
    "④これは<b>話題の配分の粗い目安であって、党の重点や本質を断定するものではありません。</b>"
    "だからこのサイトは、この数字を各党のラベルとして掲げることはしていません。",
    _cite("Manifesto Project（MARPOR・顕出性にもとづく公約分析）", "https://manifesto-project.wzb.eu/"))

  + '</section>'

  '<section class="ab-sec"><p class="ab-k">05 ／ 未確認</p>'
  '<h2 class="ab-h">まだ確かめられていないこと</h2>'
  '<p class="ab-b">調査の過程で手がかりは得たものの、'
  '一次資料に当たれていない、または記述が食い違っているものです。'
  '<b>確認できるまで、本文の根拠には使いません。</b>'
  'ここに挙げておくのは、何を確かめていないかも含めて検証可能にするためです。</p>'
  '<div class="rs-unv"><ul>'
  '<li><b>2026年の公職選挙法改正の中身。</b>''<b>この改正法が存在することは確認できました</b>——''「公職選挙法及び特定電気通信による情報の流通によって発生する権利侵害等への対処に関する法律の一部を改正する法律」''（2026年7月17日公布・法律第58号、議員立法）です''（' + _cite("内閣法制局 公布された法律の一覧", "https://www.clb.go.jp/recent-laws/promulgation_law/id=5122") + '）。''選挙運動で使うAI生成物に表示を義務づける内容と報じられていますが、''<b>どの条文が、何を対象に、いつから適用されるのかを、私たちは条文で確認できていません。</b>''公布からまもなく、法令データベースにまだ収録されていないためです。''確認できるまで、このサイトが対象になる／ならないとは書きません''（なお、このサイトは画像も映像も生成していません）。</li>'
  '<li><b>投票支援ツールと分極化の関係。</b>ツールが投票選択を分極化させる方向を示唆する研究の存在を検索結果で確認しましたが、'
  '本文を読めていません。他の研究と結論が食い違う可能性があります。</li>'
  '</ul></div></section>'

  '<section class="ab-sec"><p class="ab-k">06 ／ この調査の作り方と限界</p>'
  '<h2 class="ab-h">誰が、どうやって調べたか</h2>'
  '<ul class="ab-list">'
  '<li>文献の収集はAI（Claude）に行わせました。'
  '<b>AIは存在しない論文や著者名を作り出すことがあります。</b>'
  'これはこのサイトが最も避けなければならない種類の誤りなので、'
  '「実際にたどり着けたURLを持つ文献だけを本文に書く」「それ以外は未確認として分ける」という'
  '手順を先に決めてから調査させています。</li>'
  '<li>本文の引用リンクは、公開のたびに<b>到達性を機械的に検査</b>しています。'
  'ただし到達できることは、その文献が主張の根拠として適切であることまでは保証しません。</li>'
  '<li>英語圏の研究に偏っています。日本の議会を対象にした研究は、'
  '今回の調査では十分に拾えていません。</li>'
  '<li>ここに挙げたのは、<b>この設計の判断に実際に関わった文献だけ</b>です。'
  '分野の網羅ではありません。</li></ul>'
  '<div class="ab-cta">'
  '<a class="p" href="about.html">つくり方と、あえて「しない」こと</a>'
  '<a class="s" href="feedback.html">誤りを指摘する</a></div></section>'

  '<p class="note" style="margin-top:36px">このページは、サイトの設計判断の根拠を示すものです。'
  'データの作り方そのものは<a class="src" href="about.html">サイトについて</a>で公開しています。</p>'
  '</div></div>')
open("site/research.html","w",encoding="utf-8").write(RESEARCH)

# ---------- privacy.html (プライバシーポリシー) ----------
# 個人情報保護法21条は「あらかじめ利用目的を公表している場合」を個別通知の例外にしている。
# 何を集め、何を集めていないか、どこへ通信が出るかを1枚にまとめて公表する。
PRIVACY=(f'<title>プライバシーポリシー ｜ AI政策くらべ</title>'
  f'<style>{INDEX_CSS}{ABOUT_CSS}</style>'
  f'<div class="wrap">{nav("privacy.html")}<div class="doc">'
  '<p class="eyebrow">プライバシーポリシー</p>'
  '<h1>何を集め、何を集めていないか。</h1>'
  '<p class="ab-lede">このサイトは<b>個人が非営利で運営</b>しています。'
  '広告・献金・アフィリエイトはありません。'
  '利用者を識別する情報は集めていません。'
  'ここでは、扱っている情報と、外部に出る通信を明示します。</p>'

  '<section class="ab-sec"><p class="ab-k">01 ／ 利用者について集めていないもの</p>'
  '<h2 class="ab-h">氏名・連絡先・回答の履歴は保存しません</h2>'
  '<ul class="ab-list">'
  '<li><b>氏名・メールアドレス・電話番号・住所などは取得していません。</b>'
  '会員登録もログインもありません。</li>'
  '<li><b>「政策で照らす」の回答は、個別の記録として保存していません。</b>'
  '送信されるのは各選択肢の<b>件数を1つ増やす操作だけ</b>で、'
  '「誰がどう答えたか」の組み合わせは保存されず、復元もできません。'
  '「みんなの結果」で公開しているのは、その加算の結果である割合だけです。</li>'
  '<li><b>「ご意見」フォームは、これとは別の仕組みで、送っていただいた本文を'
  '1件ずつ個別に保存します。</b>受け取るのは本文と送信元のページ名だけで、'
  'お名前・メールアドレス・IPアドレスなどは受け取っていないため、'
  '<b>個別の返信はできません。</b>'
  '本文を読むのは運営者と、運営者の作業を補助するAI（Claude）です。'
  'AIが読む際、本文は外部のAI事業者（Anthropic）のAPIに送信され、'
  '同社の定めに従って一定期間保持されることがあります'
  '（<a class="src" href="https://www.anthropic.com/legal/privacy" target="_blank" rel="noopener">Anthropic プライバシーポリシー</a>）。'
  '原文はそのままの形では公開せず、採否の記録として<b>運営者が書き直した要旨</b>を'
  '<a class="src" href="kiroku.html">ご意見と対応の記録</a>で公開することがあります。'
  '原文は、採否の決定と記録への反映が済み次第削除します（<b>遅くとも受信から30日以内</b>）。'
  'この取り扱いは、この記載の掲載後に送られたご意見に適用します。'
  '掲載前に届いたご意見は、従来どおり運営者だけが読み、公開せず、AIにも渡しません。'
  '詳しくは<a class="src" href="feedback.html">ご意見のページ</a>をご覧ください。</li>'
  '<li><b>「マイノート」で保存した内容は、お使いの端末の中だけに残ります。</b>'
  'ブラウザのローカルストレージに保存され、こちらへは送信されません。'
  'ブラウザのデータを消すと、保存内容も消えます。</li>'
  '<li><b>アクセス解析ツールを入れていません。</b>'
  'Google Analytics などの計測タグは設置していません。</li>'
  '<li><b>このサイト自身は、Cookieを設定していません。</b>'
  'ただし下記の外部サービスがCookieや類似の技術を用いる場合があります。</li>'
  '</ul></section>'

  '<section class="ab-sec"><p class="ab-k">02 ／ 外部に出る通信</p>'
  '<h2 class="ab-h">閲覧すると、次の事業者と通信が発生します</h2>'
  '<p class="ab-b">サイトの表示や集計のために外部サービスを利用しており、'
  '<b>閲覧時にIPアドレスなどの通信情報が各社に送られることがあります。</b>'
  '各社での取扱いは、それぞれのポリシーによります。</p>'
  '<ul class="ab-list">'
  '<li><b>GitHub Pages（GitHub, Inc.）</b>… このサイトの配信元です。'
  '<a class="src" href="https://docs.github.com/ja/site-policy/privacy-policies/github-general-privacy-statement" target="_blank" rel="noopener">プライバシーに関する声明</a></li>'
  '<li><b>Firebase / Cloud Firestore（Google LLC）</b>… 「政策で照らす」の件数の加算、'
  '「みんなの結果」の読み取り、「ご意見」フォームの本文の保存に使っています。'
  '<a class="src" href="https://policies.google.com/privacy?hl=ja" target="_blank" rel="noopener">プライバシー ポリシー</a></li>'
  '<li><b>reCAPTCHA v3（Google LLC）</b>… 集計や「ご意見」フォームへの不正な水増し・連続送信を防ぐため、'
  'Firebase App Check と組み合わせて使っています。'
  '<a class="src" href="https://policies.google.com/privacy?hl=ja" target="_blank" rel="noopener">プライバシー ポリシー</a></li>'
  '<li>ニュースの見出しは<b>このサイト内のファイルから読み込んで</b>います（表示するだけでは外部通信は発生しません）。'
  '見出しや「最新ニュース」のリンクを<b>押したとき</b>に、それぞれの配信元・検索サービスへ移動します。</li>'
  '<li>発言や採決の<b>原典リンクを押したとき</b>は、国立国会図書館や各議院のサイトへ移動します。</li>'
  '</ul></section>'

  '<section class="ab-sec"><p class="ab-k">03 ／ 公人の情報の扱い</p>'
  '<h2 class="ab-h">議員の氏名・発言・投票行動を掲載しています</h2>'
  '<ul class="ab-list">'
  '<li>掲載しているのは、<b>国会会議録と各議院が公表している記録</b>に載っている'
  '氏名・所属会派・発言・採決での賛否です。<b>すべて公開されている一次情報</b>で、'
  '独自に調べた私生活の情報は一切扱いません。</li>'
  '<li>利用目的は、<b>有権者が投票の判断材料として、各党の言動を原典に当たって確認できるようにすること</b>だけです。'
  '他の目的には使わず、第三者に提供もしません。</li>'
  '<li>掲載内容についてのご指摘・削除や訂正のご要望は'
  '<a class="src" href="feedback.html">ご意見の窓口</a>で受け付けます。'
  '権利関係は<a class="src" href="about.html">このサイトについて</a>の「出典と権利」に記載しています。</li>'
  '</ul></section>'

  '<section class="ab-sec"><p class="ab-k">04 ／ 問い合わせと改定</p>'
  '<h2 class="ab-h">窓口と、変更したときの扱い</h2>'
  '<ul class="ab-list">'
  '<li>お問い合わせ・苦情の受付は<a class="src" href="feedback.html">ご意見のページ</a>からお願いします。</li>'
  '<li>この内容を変更したときは、このページを更新します。'
  '<b>変更の履歴は、公開しているリポジトリのコミット履歴から誰でも確認できます。</b></li>'
  '</ul>'
  '<div class="ab-cta">'
  '<a class="p" href="about.html">つくり方と、あえて「しない」こと</a>'
  '<a class="s" href="feedback.html">問い合わせる</a></div></section>'
  '</div></div>')
open("site/privacy.html","w",encoding="utf-8").write(PRIVACY)

# ---------- kiroku.html (ご意見と対応の記録・⑦応答班) ----------
# ご意見フォームは匿名・連絡先なしで個別返信ができない。その代わりに、届いたご意見が
# どう扱われたか(要旨・採否・理由)をこのページで公開する。取り決めは agents/FEEDBACK_CHARTER.md。
# 元データ= feedback_log.json。要旨は運営者が書き直したものだけ(原文をJSONに書いてはならない)。
# パスはスクリプト位置基準で解決し、無ければ即エラーにする(カレントディレクトリ依存で
# 黙って空データにフォールバックすると、記録が欠けたページを公開しうる — ⑧査読の指摘)。
_FBLOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback_log.json")
FBLOG = json.load(open(_FBLOG_PATH, encoding="utf-8"))
FBLOG_DECISIONS = {"採用", "一部採用", "不採用", "確認中"}
for _e in FBLOG["entries"]:
    _miss = [k for k in ("date", "category", "decision", "reason") if not _e.get(k)]
    if _miss:
        raise SystemExit(f"feedback_log.json: 必須フィールドが無い記録がある {_miss}")
    if _e["decision"] not in FBLOG_DECISIONS:
        raise SystemExit(f"feedback_log.json: 採否は {sorted(FBLOG_DECISIONS)} のどれか（{_e['decision']}）")

def _fblog_rows():
    if not FBLOG["entries"]:
        return ('<div class="mn-empty" style="background:var(--card);border:1px dashed var(--line);'
                'border-radius:14px;padding:26px 22px;font-size:14px;color:var(--muted);'
                'line-height:1.9;text-align:center;">まだ記録はありません。</div>')
    rows = []
    for e in sorted(FBLOG["entries"], key=lambda x: x["date"], reverse=True):
        summary = e.get("summary") or "（推測につながる要素を落としきれないため、要旨の掲載はありません）"
        link = (f'<a class="src" href="{e["link"]}">▸ 対応した変更</a>' if e.get("link") else "")
        rows.append(
            '<li><b>' + e["date"] + '</b>　' + e["category"] + '　'
            '<b>' + e["decision"] + '</b><br>'
            '要旨: ' + summary + '<br>'
            '理由: ' + e["reason"] + (('<br>' + link) if link else "") + '</li>')
    return '<ul class="ab-list">' + "".join(rows) + '</ul>'

_fb_boundary = FBLOG.get("policy_boundary_utc")
_fb_boundary_html = (
    ('この運用は、<b>' + _fb_boundary + '（UTC）以降</b>に届いたご意見に適用しています。'
     'それより前に届いたご意見は、従来の取り扱い（運営者だけが読み、公開せず、AIにも渡さない）のままです。')
    if _fb_boundary else
    'この運用の適用開始日時は、取り扱いの説明（ご意見のページ・プライバシーポリシー）の公開後に確定し、'
    'ここに記載します。<b>確定するまで、届いたご意見を新しい運用で扱うことはありません。</b>')

KIROKU = (f'<title>ご意見と対応の記録 ｜ AI政策くらべ</title>'
  f'<style>{INDEX_CSS}{ABOUT_CSS}</style>'
  f'<div class="wrap">{nav("kiroku.html")}<div class="doc">'
  '<p class="eyebrow">ご意見と対応の記録</p>'
  '<h1>いただいたご意見が、どう扱われたか。</h1>'
  '<p class="ab-lede">ご意見フォームは連絡先を受け取らないため、個別の返信ができません。'
  'その代わりに、サイトの変更につながりうるご意見について、'
  '<b>要旨・採否・理由</b>をこのページに残します。</p>'

  '<section class="ab-sec"><p class="ab-k">01 ／ このページのルール</p>'
  '<h2 class="ab-h">何を載せ、何を載せないか</h2>'
  '<ul class="ab-list">'
  '<li><b>原文は公開しません。</b>載せるのは運営者が書き直した要旨だけです。'
  '要旨には、送った方や第三者の推測につながる要素（固有名詞・地域・所属・具体的な事情）を入れません。'
  '落としきれない場合は、要旨を載せず分類と採否だけを記録します。</li>'
  '<li><b>採否の理由は、掲載基準・運用ルールへの当てはめだけを書きます。</b>'
  'ご意見やその送り主を評価する言葉は使いません。</li>'
  '<li><b>同じ趣旨のご意見が何件届いたかは、採否の根拠にしません。</b>'
  '件数で判断すると、数を装った投稿で結論を動かせてしまうためです。</li>'
  '<li><b>採否の初期値は不採用です。</b>サイトの目的に照らして改善だと積極的に説明でき、'
  '公開前の機械検証を通るものだけを採用します。</li>'
  '<li><b>AIは変更を完結させません。</b>補助AI（Claude）が行うのは分類・事実確認・'
  '修正案や採否案の下書きまでで、内容に関わる採否の決定は運営者が行い、'
  'すべての変更はPull Requestと機械検証を経て公開されます。'
  '取り決めの全文は<a class="src" href="https://github.com/ai-seisaku-kurabe/ai-seisaku-kurabe.github.io/blob/main/tools/agents/FEEDBACK_CHARTER.md" target="_blank" rel="noopener">リポジトリで公開</a>しています。</li>'
  '<li><b>掲載済みの要旨の削除・ぼかしのご要望は、'
  '<a class="src" href="feedback.html">ご意見フォーム</a>で受け付けます。</b>'
  '公開している情報を減らす方向のご要望には、本人確認なしで原則応じます。</li>'
  '</ul></section>'

  '<section class="ab-sec"><p class="ab-k">02 ／ 適用の範囲</p>'
  '<h2 class="ab-h">いつからのご意見が対象か</h2>'
  '<p class="ab-b">' + _fb_boundary_html + '</p></section>'

  '<section class="ab-sec"><p class="ab-k">03 ／ 記録</p>'
  '<h2 class="ab-h">要旨と採否</h2>'
  + _fblog_rows() +
  '</section>'
  '<div class="ab-cta">'
  '<a class="p" href="feedback.html">ご意見を送る</a>'
  '<a class="s" href="about.html">サイトについて</a></div>'
  '</div></div>')
open("site/kiroku.html","w",encoding="utf-8").write(KIROKU)

# ---------- mynote.html (マイ政策ノート＝クリップした言と行を分野別に比較) ----------
MYNOTE_CSS="""
.mn-lede{color:var(--muted);font-size:14.5px;line-height:1.85;max-width:64ch;margin:0 0 22px;}
.mn-lede b{color:var(--ink);}
.mn-empty{background:var(--card);border:1px dashed var(--line);border-radius:14px;padding:26px 22px;
  font-size:14px;color:var(--muted);line-height:1.9;text-align:center;}
.mn-empty a{color:var(--accent);text-decoration:none;font-weight:600;}
.mn-group{margin:0 0 30px;}
.mn-dom{font-family:var(--serif);font-weight:600;font-size:19px;margin:0 0 12px;
  padding-bottom:8px;border-bottom:1px solid var(--line);}
.mn-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;}
@media(max-width:640px){.mn-grid{grid-template-columns:1fr;}}
.mn-card{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--pc,var(--accent));
  border-radius:12px;padding:14px 16px;display:flex;flex-direction:column;gap:9px;}
.mn-top{display:flex;align-items:center;justify-content:space-between;}
.mn-badge{font-family:var(--mono);font-size:12px;font-weight:700;color:var(--pc,var(--accent));}
.mn-x{background:none;border:none;cursor:pointer;color:var(--muted);font-size:18px;line-height:1;padding:2px 6px;border-radius:6px;}
.mn-x:hover{color:#c1704f;background:var(--accent-soft);}
.mn-point{font-size:13.5px;line-height:1.8;color:var(--ink);margin:0;}
.mn-q{margin:0;padding:9px 12px;border-left:3px solid var(--pc,var(--accent));background:var(--paper);
  border-radius:0 8px 8px 0;font-size:13px;line-height:1.75;}
.mn-q cite{display:block;font-style:normal;font-family:var(--mono);font-size:10.5px;color:var(--muted);margin-top:6px;}
.mn-q .src{color:var(--accent);text-decoration:none;}
.mn-votes{background:var(--paper);border:1px solid var(--line);border-radius:10px;padding:9px 11px;}
.mn-vl{display:block;font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.1em;color:var(--muted);margin-bottom:6px;}
.mn-vrow{display:flex;flex-wrap:wrap;gap:6px;}
.mn-v{display:inline-flex;align-items:center;gap:4px;font-size:10.5px;color:var(--muted);text-decoration:none;
  border:1px solid var(--line);border-radius:8px;padding:3px 8px;}
.mn-v b{font-size:11px;}
.mn-v.yes{color:#2f8f7f;border-color:#2f8f7f66;} .mn-v.no{color:#c1704f;border-color:#c1704f66;}
.mn-actions{margin-top:8px;}
.mn-clear{font-family:var(--mono);font-size:12px;color:var(--muted);background:none;border:1px solid var(--line);
  border-radius:20px;padding:7px 15px;cursor:pointer;}
.mn-clear:hover{border-color:#c1704f;color:#c1704f;}
"""
MYNOTE_JS=("<script>(function(){"
  "function esc(s){return String(s).replace(/[&<>\"]/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;','\\\"':'&quot;'}[c]);});}"
  "function get(){try{return JSON.parse(localStorage.getItem('kg_notes')||'{}');}catch(e){return {};}}"
  "function save(o){localStorage.setItem('kg_notes',JSON.stringify(o));}"
  "var ORD=['経済・産業','財政','社会保障','外交・安保','エネルギー・環境','憲法'];"
  "function scls(st){return st==='賛成'?'yes':(st==='反対'?'no':'na');}"
  "function render(){var notes=get(),ids=Object.keys(notes);"
  "var root=document.getElementById('noteRoot'),empty=document.getElementById('noteEmpty'),act=document.getElementById('noteActions');"
  "if(!ids.length){empty.hidden=false;root.innerHTML='';act.hidden=true;return;}"
  "empty.hidden=true;act.hidden=false;var g={};"
  "ids.forEach(function(id){var it=notes[id];it._id=id;(g[it.dom]=g[it.dom]||[]).push(it);});"
  "var order=ORD.filter(function(d){return g[d];}).concat(Object.keys(g).filter(function(d){return ORD.indexOf(d)<0;}));"
  "root.innerHTML=order.map(function(dom){var items=g[dom].map(function(it){"
  "var votes=(it.votes||[]).map(function(v){return '<a class=\"mn-v '+scls(v.st)+'\" href=\"'+v.u+'\" target=\"_blank\" rel=\"noopener\">'+esc(v.l)+' <b>'+esc(v.st)+'</b></a>';}).join('');"
  "return '<div class=\"mn-card\" style=\"--pc:'+esc(it.pc)+'\"><div class=\"mn-top\"><span class=\"mn-badge\">'+esc(it.party)+'</span>'"
  "+'<button class=\"mn-x\" data-id=\"'+esc(it._id)+'\" title=\"削除\" aria-label=\"削除\">×</button></div>'"
  "+'<p class=\"mn-point\">'+esc(it.point)+'</p>'"
  "+'<blockquote class=\"mn-q\">「'+esc(it.quote)+'」<cite>— '+esc(it.who)+'議員　<a class=\"src\" href=\"'+esc(it.url)+'\" target=\"_blank\" rel=\"noopener\">議事録原文→</a></cite></blockquote>'"
  "+(votes?'<div class=\"mn-votes\"><span class=\"mn-vl\">行 ／ 参院採決</span><div class=\"mn-vrow\">'+votes+'</div></div>':'')+'</div>';}).join('');"
  "return '<section class=\"mn-group\"><h2 class=\"mn-dom\">'+esc(dom)+'</h2><div class=\"mn-grid\">'+items+'</div></section>';}).join('');"
  "root.querySelectorAll('.mn-x').forEach(function(b){b.addEventListener('click',function(){var n=get();delete n[b.dataset.id];save(n);render();if(window.KGNOTE)KGNOTE.refresh();});});}"
  "var cl=document.getElementById('noteClear');if(cl)cl.addEventListener('click',function(){if(confirm('保存した項目をすべて消しますか？')){localStorage.removeItem('kg_notes');render();if(window.KGNOTE)KGNOTE.refresh();}});"
  "render();})();</script>")
MYNOTE=(f'<title>マイノート — 保存した言と行の比較 ｜ AI政策くらべ</title>\n'
  f'<style>{INDEX_CSS}{MYNOTE_CSS}</style>\n'
  f'<div class="wrap">{nav("mynote.html")}<div class="doc">'
  '<p class="eyebrow">マイノート</p>'
  '<h1>あなたが選んだ「言と行」。</h1>'
  '<p class="mn-lede">「政党で選ぶ」で保存した項目を、<b>分野ごとに並べて比較</b>できます。'
  'データはこの端末内にだけ保存され（ログイン不要）、外部には送信されません。'
  '各分野カードの<b>しおりアイコン</b>で追加・解除できます。</p>'
  '<div class="mn-empty" id="noteEmpty" hidden>まだ保存された項目がありません。<br>'
  '<a href="guide.html">政党で選ぶ</a>で、各分野カードの右上にある「しおり」を押すと、ここに集まります。</div>'
  '<div id="noteRoot"></div>'
  '<div class="mn-actions" id="noteActions" hidden><button class="mn-clear" id="noteClear">すべて消す</button></div>'
  '</div></div>'+MYNOTE_JS)
open("site/mynote.html","w",encoding="utf-8").write(MYNOTE)

# ---------- news.html (政策ニュース・アーカイブ＝分野タグ付きで蓄積) ----------
NEWS_DOMAINS = ["経済・産業","財政","社会保障","外交・安保","エネルギー・環境","憲法"]
PJS = {ID[p["full"]]: {"n": p["short"], "c": PC[p["full"]]} for p in PARTIES}
NEWS_CSS="""
.nw-lede{color:var(--muted);font-size:14.5px;line-height:1.85;max-width:66ch;margin:0 0 20px;}
.nw-lede b{color:var(--ink);}
.nw-filters{display:flex;flex-direction:column;gap:8px;margin:0 0 16px;}
.nw-row{display:flex;align-items:center;flex-wrap:wrap;gap:7px;}
.nw-lbl{font-family:var(--mono);font-size:11px;letter-spacing:.08em;color:var(--muted);min-width:3.5em;}
.nw-chip{font:inherit;font-size:12.5px;cursor:pointer;background:transparent;color:var(--muted);
  border:1px solid var(--line);border-radius:20px;padding:5px 13px;transition:.13s;}
.nw-chip:hover{border-color:var(--accent);color:var(--ink);}
.nw-chip.on{background:var(--accent);color:#fff;border-color:var(--accent);font-weight:600;}
.nw-chip.on[data-pc]{background:var(--pc);border-color:var(--pc);}
.nw-count{font-family:var(--mono);font-size:12px;color:var(--muted);margin:0 0 14px;}
.nw-list{display:flex;flex-direction:column;gap:10px;}
.nw-item{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:13px 16px;
  display:flex;flex-direction:column;gap:7px;}
.nw-item:hover{border-color:var(--accent);}
.nw-t{font-size:14.5px;line-height:1.65;color:var(--ink);text-decoration:none;font-weight:600;}
.nw-t:hover{color:var(--accent);text-decoration:underline;}
.nw-meta{display:flex;align-items:center;flex-wrap:wrap;gap:7px;}
.nw-date,.nw-src{font-family:var(--mono);font-size:11px;color:var(--muted);}
.nw-tag{font-family:var(--mono);font-size:10.5px;font-weight:700;letter-spacing:.04em;
  background:var(--accent-soft);color:var(--accent);border-radius:6px;padding:3px 8px;}
.nw-pty{font-family:var(--mono);font-size:10.5px;font-weight:700;border-radius:6px;padding:3px 8px;
  background:var(--pc,var(--accent));color:#fff;}
.nw-cta{display:block;text-decoration:none;color:inherit;background:transparent;
  border:1px solid var(--line);border-left:3px solid var(--accent);border-radius:0 12px 12px 0;
  padding:14px 18px;margin:0 0 18px;transition:border-color .15s;}
.nw-cta:hover{border-color:var(--accent);}
.nw-cta-l{display:block;font-family:var(--mono);font-size:11px;letter-spacing:.08em;color:var(--muted);}
.nw-cta-t{display:block;font-size:14px;font-weight:600;color:var(--ink);margin-top:5px;line-height:1.6;}
.nw-cta:hover .nw-cta-t{color:var(--accent);}
.nw-pager{display:flex;align-items:center;justify-content:center;gap:14px;margin:22px 0 0;}
.nw-pg{font:inherit;font-size:13px;cursor:pointer;background:transparent;color:var(--ink);
  border:1px solid var(--line);border-radius:20px;padding:8px 18px;transition:.13s;}
.nw-pg:hover:not(:disabled){border-color:var(--accent);color:var(--accent);}
.nw-pg:disabled{opacity:.35;cursor:not-allowed;}
.nw-pgi{font-family:var(--mono);font-size:12.5px;color:var(--muted);font-variant-numeric:tabular-nums;}
.nw-empty a{color:var(--accent);text-decoration:none;font-weight:600;}
.nw-empty{background:var(--card);border:1px dashed var(--line);border-radius:12px;
  padding:24px;text-align:center;color:var(--muted);font-size:13.5px;}
"""
NEWS_JS=("<script>(function(){"
  f"var PTY={json.dumps(PJS,ensure_ascii=False)};"
  "function esc(s){return String(s).replace(/[&<>\"]/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;','\\\"':'&quot;'}[c]);});}"
  "var ALL=[],fd='all',fp='all',PAGE=10,page=1;"
  "function render(){var L=ALL.filter(function(x){"
  "return (fd==='all'||(x.d||[]).indexOf(fd)>=0)&&(fp==='all'||(x.p||[]).indexOf(fp)>=0);});"
  "var total=L.length,pages=Math.max(1,Math.ceil(total/PAGE));if(page>pages)page=pages;""var from=(page-1)*PAGE;var slice=L.slice(from,from+PAGE);""document.getElementById('nwCount').textContent=total?(total+' 件中 '+(from+1)+'〜'+(from+slice.length)+' 件目'):'0 件';""var cta=document.getElementById('nwCta'),ctaT=document.getElementById('nwCtaT');""if(cta){if(fd==='all'){cta.href='guide.html';""ctaT.textContent='各党が国会で何を論じ、どう投票したかを、原典リンク付きで確かめる →';}""else{cta.href='guide.html?domain='+encodeURIComponent(fd);""ctaT.textContent='「'+fd+'」について、各党が国会で何を論じ、どう投票したかを確かめる →';}}"
  "var root=document.getElementById('nwList');"
  "var pg=document.getElementById('nwPager');""if(!total){var wider=(fp!=='all'&&fd!=='all')?('<div class=\"nw-empty\">この党のこの分野の見出しは、まだ蓄積されていません。<br>'+'<a href=\"#\" id=\"nwWiden\">▸ 「'+fd+'」の見出しをすべて見る</a></div>'):'<div class=\"nw-empty\">条件に合う見出しがありません。</div>';root.innerHTML=wider;pg.innerHTML='';var w=document.getElementById('nwWiden');if(w)w.addEventListener('click',function(e){e.preventDefault();fp='all';page=1;document.querySelectorAll('.nw-chip').forEach(function(c){if(c.getAttribute('data-g')==='p'){if(c.getAttribute('data-v')==='all'){c.classList.add('on');}else{c.classList.remove('on');}}});render();});return;}""pg.innerHTML = pages>1 ? ('<button class=\"nw-pg\" data-go=\"prev\"'+(page<=1?' disabled':'')+'>← 前の10件</button>'""+'<span class=\"nw-pgi\">'+page+' / '+pages+' ページ</span>'""+'<button class=\"nw-pg\" data-go=\"next\"'+(page>=pages?' disabled':'')+'>次の10件 →</button>') : '';"
  "root.innerHTML=slice.map(function(x){"
  "var tags=(x.d||[]).map(function(d){return '<span class=\"nw-tag\">'+esc(d)+'</span>';}).join('');"
  "var pts=(x.p||[]).map(function(p){var m=PTY[p];return m?'<span class=\"nw-pty\" style=\"--pc:'+m.c+'\">'+esc(m.n)+'</span>':'';}).join('');"
  "return '<div class=\"nw-item\"><a class=\"nw-t\" href=\"'+x.u+'\" target=\"_blank\" rel=\"noopener\">'+esc(x.t)+'</a>'"
  "+'<div class=\"nw-meta\"><span class=\"nw-date\">'+esc(x.date||'')+'</span>'"
  "+(x.s?'<span class=\"nw-src\">'+esc(x.s)+'</span>':'')+tags+pts+'</div></div>';}).join('');}"
  "document.querySelectorAll('.nw-chip').forEach(function(c){c.addEventListener('click',function(){"
  "var g=c.getAttribute('data-g');"
  "document.querySelectorAll('.nw-chip[data-g=\"'+g+'\"]').forEach(function(x){x.classList.remove('on');});"
  "c.classList.add('on');"
  "if(g==='d'){fd=c.getAttribute('data-v');}else{fp=c.getAttribute('data-v');}page=1;render();});});""document.getElementById('nwPager').addEventListener('click',function(e){""var b=e.target.closest('.nw-pg');if(!b||b.disabled)return;""page += (b.getAttribute('data-go')==='next'?1:-1);render();""document.getElementById('nwList').scrollIntoView({behavior:'smooth',block:'start'});});"
  "var _q=new URLSearchParams(location.search);""var _d=_q.get('domain'),_p=_q.get('party');""if(_d)fd=_d;if(_p)fp=_p;""document.querySelectorAll('.nw-chip').forEach(function(c){""var g=c.getAttribute('data-g'),v=c.getAttribute('data-v');""var want=(g==='d')?fd:fp;""if(v===want){c.classList.add('on');}else{c.classList.remove('on');}});""fetch('news_archive.json').then(function(r){return r.json();}).then(function(d){"
  "ALL=d.items||[];var u=document.getElementById('nwUpd');"
  "if(u&&d.updated)u.textContent=d.updated+' 時点';render();})"
  ".catch(function(){document.getElementById('nwList').innerHTML="
  "'<div class=\"nw-empty\">ニュースを読み込めませんでした。</div>';});})();</script>")
_dchips = "".join(f'<button type="button" class="nw-chip" data-g="d" data-v="{esc(d)}">{esc(d)}</button>'
                  for d in NEWS_DOMAINS)
_pchips = "".join(f'<button type="button" class="nw-chip" data-g="p" data-v="{ID[p["full"]]}" '
                  f'data-pc style="--pc:{PC[p["full"]]}">{esc(p["short"])}</button>' for p in PARTIES)
NEWS=(f'<title>政策ニュース — 分野別のアーカイブ ｜ AI政策くらべ</title>\n'
  f'<style>{INDEX_CSS}{NEWS_CSS}</style>\n'
  f'<div class="wrap">{nav("news.html")}<div class="doc">'
  '<p class="eyebrow">ニュース</p>'
  '<h1>政策ニュース・アーカイブ</h1>'
  '<p class="nw-lede">各党・各争点のニュース見出しを毎日集め、<b>政策分野ごとに分類して蓄積</b>しています。'
  '政策と関係がないと判断した見出しは蓄積していません。分野や政党で絞り込めます。'
  '<b>見出しと出典へのリンクのみ</b>で、本文は転載していません。'
  '見出しの選定はGoogle ニュースの検索結果に依存し、当サイトの評価を含みません。</p>'
  '<div class="nw-filters">'
  '<div class="nw-row"><span class="nw-lbl">分野</span>'
  '<button type="button" class="nw-chip on" data-g="d" data-v="all">すべて</button>' + _dchips + '</div>'
  '<div class="nw-row"><span class="nw-lbl">政党</span>'
  '<button type="button" class="nw-chip on" data-g="p" data-v="all">すべて</button>' + _pchips + '</div>'
  '</div>'
  '<a class="nw-cta" id="nwCta" href="guide.html">''<span class="nw-cta-l">報道の先にある、国会での言と行へ</span>''<span class="nw-cta-t" id="nwCtaT">各党が国会で何を論じ、どう投票したかを、原典リンク付きで確かめる →</span></a>''<p class="nw-count"><b id="nwCount">…</b> ／ <span id="nwUpd">読み込み中</span></p>'
  '<div class="nw-list" id="nwList"></div>'
  '<div class="nw-pager" id="nwPager"></div>'
  '<p class="note" style="margin-top:30px">出典：Google ニュース検索。見出し・媒体名・リンクのみを掲載しています。'
  '分野タグは見出しのキーワードから機械的に付与したもので、記事内容の評価ではありません。'
  '古い見出しは順次アーカイブから外れます。</p>'
  '</div></div>'+NEWS_JS)
open("site/news.html","w",encoding="utf-8").write(NEWS)

# ---------- speeches.html (発言一覧＝党×分野×会期で絞り込み) ----------
# 会議録検索システムはURLで検索条件を渡せない（SPAは無視・シンプル表示はPOST+CSRF）ため、
# 「この分野の発言を探す」を外部に委ねられない。自前で一覧を持ち、各件に原文リンクを付ける。
SPEECH_ITEMS = []
for _ses in ("221", "219", "217"):
    _p = os.path.join("speeches_%s.json" % _ses)
    if os.path.exists(_p):
        _d = json.load(open(_p, encoding="utf-8"))
        for _it in _d["items"]:
            _it["ses"] = _ses
            SPEECH_ITEMS.append(_it)
SPEECH_ITEMS.sort(key=lambda x: (x["ses"] == "217", x["date"]), reverse=False)
SPEECH_ITEMS.sort(key=lambda x: x["date"], reverse=True)
SP_JSON = json.dumps({"items": SPEECH_ITEMS,
                      "parties": {ID[p["full"]]: {"n": p["short"], "c": PC[p["full"]]} for p in PARTIES},
                      "pmap": {p["full"]: ID[p["full"]] for p in PARTIES},
                      "domains": NEWS_DOMAINS}, ensure_ascii=False)
SP_CSS = NEWS_CSS + """
.nw-note{font-size:12.5px;line-height:1.75;color:var(--muted);margin:10px 0 0;
  padding:10px 12px;border-left:2px solid var(--line);background:var(--soft,transparent);}
.nw-note a{color:var(--accent);}
.sp-q{font-size:14px;line-height:1.8;color:var(--ink);margin:0;}
.sp-ctx{font-family:var(--mono);font-size:10.5px;font-weight:700;color:var(--muted);margin:0 0 4px;}
.sp-cite{font-family:var(--mono);font-size:11px;color:var(--muted);margin:5px 0 0;}
.sp-cite a{color:var(--accent);text-decoration:none;margin-left:8px;}
"""
SP_JS = ("<script>(function(){"
  "var D=" + SP_JSON + ";"
  "function esc(s){return String(s).replace(/[&<>\"]/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]);});}"
  "var fd='all',fp='all',fs='all',PAGE=10,page=1;"
  "var q=new URLSearchParams(location.search);"
  "if(q.get('domain'))fd=q.get('domain');"
  "if(q.get('party'))fp=q.get('party');"
  "if(q.get('session'))fs=q.get('session');"
  "document.querySelectorAll('.nw-chip').forEach(function(c){"
  "var g=c.getAttribute('data-g'),v=c.getAttribute('data-v');"
  "var want=(g==='d')?fd:((g==='p')?fp:fs);"
  "if(v===want){c.classList.add('on');}else{c.classList.remove('on');}});"
  "function render(){"
  "var L=D.items.filter(function(x){"
  "return (fd==='all'||x.domain===fd)&&(fp==='all'||D.pmap[x.party]===fp)&&(fs==='all'||x.ses===fs);});"
  "var total=L.length,pages=Math.max(1,Math.ceil(total/PAGE));if(page>pages)page=pages;"
  "var from=(page-1)*PAGE,slice=L.slice(from,from+PAGE);"
  "document.getElementById('nwCount').textContent=total?(total+' 件中 '+(from+1)+'〜'+(from+slice.length)+' 件目'):'0 件';"
  "var root=document.getElementById('nwList'),pg=document.getElementById('nwPager');"
  "if(!total){root.innerHTML='<div class=\"nw-empty\">条件に合う発言がありません。</div>';pg.innerHTML='';return;}"
  "pg.innerHTML= pages>1 ? ('<button class=\"nw-pg\" data-go=\"prev\"'+(page<=1?' disabled':'')+'>← 前の10件</button>'"
  "+'<span class=\"nw-pgi\">'+page+' / '+pages+' ページ</span>'"
  "+'<button class=\"nw-pg\" data-go=\"next\"'+(page>=pages?' disabled':'')+'>次の10件 →</button>') : '';"
  "root.innerHTML=slice.map(function(x){"
  "var m=D.parties[D.pmap[x.party]]||{n:x.party,c:'#888'};"
  "return '<div class=\"nw-item\">'"
  "+'<p class=\"sp-ctx\">第'+x.ses+'回 ｜ '+esc(x.house+x.meeting)+' ｜ '+esc(x.date)+'</p>'"
  "+'<p class=\"sp-q\">「'+esc(x.quote)+'」</p>'"
  "+'<p class=\"sp-cite\">— '+esc(x.who)+'議員'"
  "+'<a href=\"'+x.url+'\" target=\"_blank\" rel=\"noopener\">全文→</a></p>'"
  "+'<div class=\"nw-meta\"><span class=\"nw-tag\">'+esc(x.domain)+'</span>'"
  "+'<span class=\"nw-pty\" style=\"--pc:'+m.c+'\">'+esc(m.n)+'</span></div></div>';}).join('');}"
  "document.querySelectorAll('.nw-chip').forEach(function(c){c.addEventListener('click',function(){"
  "var g=c.getAttribute('data-g');"
  "document.querySelectorAll('.nw-chip').forEach(function(x){if(x.getAttribute('data-g')===g)x.classList.remove('on');});"
  "c.classList.add('on');var v=c.getAttribute('data-v');"
  "if(g==='d')fd=v;else if(g==='p')fp=v;else fs=v;page=1;render();});});"
  "document.getElementById('nwPager').addEventListener('click',function(e){"
  "var b=e.target.closest('.nw-pg');if(!b||b.disabled)return;"
  "page+=(b.getAttribute('data-go')==='next'?1:-1);render();"
  "document.getElementById('nwList').scrollIntoView({behavior:'smooth',block:'start'});});"
  "render();})();</script>")
_sd = "".join(f'<button type="button" class="nw-chip" data-g="d" data-v="{esc(d)}">{esc(d)}</button>' for d in NEWS_DOMAINS)
_sp = "".join(f'<button type="button" class="nw-chip" data-g="p" data-v="{ID[p["full"]]}" '
              f'data-pc style="--pc:{PC[p["full"]]}">{esc(p["short"])}</button>' for p in PARTIES)
SPEECHES = (f'<title>発言一覧 — 党と分野で探す ｜ AI政策くらべ</title>'
  f'<style>{INDEX_CSS}{SP_CSS}</style>'
  f'<div class="wrap">{nav("speeches.html")}<div class="doc">'
  '<p class="eyebrow">発言一覧</p><h1>国会で、誰が何を論じたか。</h1>'
  '<p class="nw-lede">各党が国会で行った発言を、<b>政党・政策分野・会期で絞り込んで</b>探せます。'
  '答弁側（大臣・政府参考人など）と、委員長報告のような手続き的な発言は除いています。'
  '引用は原文のままで、<b>すべてに議事録原文へのリンク</b>を付けています。</p>'
  '<p class="nw-note">収集の範囲について：' + roster_note() + '<a href="about.html">収集ルールの詳細</a></p>'
  '<div class="nw-filters">'
  '<div class="nw-row"><span class="nw-lbl">分野</span>'
  '<button type="button" class="nw-chip on" data-g="d" data-v="all">すべて</button>' + _sd + '</div>'
  '<div class="nw-row"><span class="nw-lbl">政党</span>'
  '<button type="button" class="nw-chip on" data-g="p" data-v="all">すべて</button>' + _sp + '</div>'
  '<div class="nw-row"><span class="nw-lbl">会期</span>'
  '<button type="button" class="nw-chip on" data-g="s" data-v="all">すべて</button>'
  '<button type="button" class="nw-chip" data-g="s" data-v="221">第221回</button>'
  '<button type="button" class="nw-chip" data-g="s" data-v="219">第219回</button>'
  '<button type="button" class="nw-chip" data-g="s" data-v="217">第217回</button></div>'
  '</div>'
  '<p class="nw-count"><b id="nwCount">…</b></p>'
  '<div class="nw-list" id="nwList"></div><div class="nw-pager" id="nwPager"></div>'
  '<p class="note" style="margin-top:30px">出典：国会会議録検索システム（第217回・第219回・第221回国会）。'
  '各党×各分野につき最大5件を機械的に収集したもので、重要度による選定ではありません。'
  '網羅ではないため、全ての発言は会議録検索システムでご確認ください。</p>'
  '</div></div>' + SP_JS)
open("site/speeches.html", "w", encoding="utf-8").write(SPEECHES)


# ---------- votes.html (採決一覧＝会期の記名投票を全件、党の賛否付きで) ----------
# 「言」は発言一覧で党×分野を横断して探せるのに、「行」は guide.html に埋め込まれていて
# 横断できなかった（言と行の非対称）。ここに会期の記名投票を全件並べる。
# guide が各分野に載せているのは、この全件から選んだ代表例である。全件を見せることは、
# 「記名投票にかけられる議案の選ばれ方に偏りが乗る」(research.html 04・⑥) への具体的な歯止めになる。
# 会派の党への対応（VKEY）は会期ごとに異なる。統一会派に属していた党（第217・219回の社民など）は
# 会派としての単独の賛否が残らないので「—」にし、推測で埋めない。
VKEY_BY_SESSION = {
    "221": {"自由民主党":"自由民主党","立憲民主党":"立憲民主","日本維新の会":"日本維新の会",
            "国民民主党":"国民民主","公明党":"公明党","日本共産党":"日本共産党",
            "れいわ新選組":"れいわ","参政党":"参政党","チームみらい":"チームみらい","社会民主党":"社会民主党"},
    "219": {"自由民主党":"自由民主党","立憲民主党":"立憲民主","日本維新の会":"日本維新の会",
            "国民民主党":"国民民主","公明党":"公明党","日本共産党":"日本共産党",
            "れいわ新選組":"れいわ","参政党":"参政党"},
    "217": {"自由民主党":"自由民主党","立憲民主党":"立憲民主","日本維新の会":"日本維新の会",
            "国民民主党":"国民民主","公明党":"公明党","日本共産党":"日本共産党","れいわ新選組":"れいわ"},
}
_STCLS = {"賛成":"yes","反対":"no","分裂":"na"}
VOTE_ITEMS = []
for _ses in ("221", "219", "217"):
    _p = "%s_votes.json" % _ses
    if not os.path.exists(_p):
        continue
    _vk = VKEY_BY_SESSION.get(_ses, {})
    for _b in json.load(open(_p, encoding="utf-8")).get("bills", []):
        _row = []
        for _full, _short in [(p["full"], p["short"]) for p in PARTIES]:
            _key = _vk.get(_full)
            _st = None
            if _key:
                _st = next((v["stance"] for name, v in _b["parties"].items() if _key in name), None)
            _row.append({"n": _short, "c": PC[_full],
                         "st": _st or "—", "cls": _STCLS.get(_st or "", "none")})
        _sm = _b.get("summary", {})
        VOTE_ITEMS.append({
            "ses": _ses, "date": _b.get("date", ""), "label": _b.get("label", ""),
            "url": f'https://www.sangiin.go.jp/japanese/touhyoulist/{_b["id"][:3]}/{_b["id"]}.htm',
            "yes": _sm.get("yes"), "no": _sm.get("no"), "total": _sm.get("total"),
            "parties": _row})
# 新しい会期を上に。会期内は議案IDの新しい順（date は月日だけで年をまたぐ比較に使えない）
VOTE_ITEMS.sort(key=lambda x: (["217", "219", "221"].index(x["ses"]), x.get("date", "")), reverse=True)
VT_JSON = json.dumps({"items": VOTE_ITEMS}, ensure_ascii=False)
VT_CSS = NEWS_CSS + """
.vt-item{padding:13px 0;border-bottom:1px solid var(--line);}
.vt-ctx{font-family:var(--mono);font-size:10.5px;font-weight:700;color:var(--muted);margin:0 0 4px;}
.vt-label{font-size:14px;line-height:1.7;color:var(--ink);margin:0;}
.vt-label a{color:var(--ink);text-decoration:none;border-bottom:1px solid var(--line);}
.vt-label a:hover{color:var(--accent);border-color:var(--accent);}
.vt-sum{font-family:var(--mono);font-size:11px;color:var(--muted);margin:5px 0 0;}
.vt-row{display:flex;flex-wrap:wrap;gap:5px;margin:8px 0 0;}
.vt-p{display:inline-flex;align-items:center;gap:5px;font-size:11px;border:1px solid var(--line);
  border-radius:16px;padding:3px 9px;border-left:3px solid var(--pc,#888);}
.vt-p b{font-weight:700;}
.vt-p.yes{color:#2f8f7f;border-color:#2f8f7f55;} .vt-p.yes b{color:#2f8f7f;}
.vt-p.no{color:#c1704f;border-color:#c1704f55;} .vt-p.no b{color:#c1704f;}
.vt-p.na{color:var(--muted);} .vt-p.none{color:var(--muted);opacity:.55;}
"""
VT_JS = ("<script>(function(){"
  "var D=" + VT_JSON + ";"
  "function esc(s){return String(s).replace(/[&<>\"]/g,function(c){return({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;'}[c]);});}"
  "var fs='all',kw='',PAGE=10,page=1;"
  "var q=new URLSearchParams(location.search);if(q.get('session'))fs=q.get('session');"
  "document.querySelectorAll('.nw-chip').forEach(function(c){"
  "if(c.getAttribute('data-v')===fs)c.classList.add('on');else c.classList.remove('on');});"
  "function render(){"
  "var L=D.items.filter(function(x){return (fs==='all'||x.ses===fs)&&(!kw||x.label.indexOf(kw)>=0);});"
  "var total=L.length,pages=Math.max(1,Math.ceil(total/PAGE));if(page>pages)page=pages;"
  "var from=(page-1)*PAGE,slice=L.slice(from,from+PAGE);"
  "document.getElementById('nwCount').textContent=total?(total+' 件中 '+(from+1)+'〜'+(from+slice.length)+' 件目'):'0 件';"
  "var root=document.getElementById('nwList'),pg=document.getElementById('nwPager');"
  "if(!total){root.innerHTML='<div class=\"nw-empty\">条件に合う採決がありません。</div>';pg.innerHTML='';return;}"
  "pg.innerHTML= pages>1 ? ('<button class=\"nw-pg\" data-go=\"prev\"'+(page<=1?' disabled':'')+'>← 前の10件</button>'"
  "+'<span class=\"nw-pgi\">'+page+' / '+pages+' ページ</span>'"
  "+'<button class=\"nw-pg\" data-go=\"next\"'+(page>=pages?' disabled':'')+'>次の10件 →</button>') : '';"
  "root.innerHTML=slice.map(function(x){"
  "var ps=x.parties.map(function(p){return '<span class=\"vt-p '+p.cls+'\" style=\"--pc:'+p.c+'\">'+esc(p.n)+' <b>'+esc(p.st)+'</b></span>';}).join('');"
  "var sm=(x.total!=null)?('採決 賛成'+x.yes+'／反対'+x.no+'（投票総数'+x.total+'）'):'';"
  "return '<div class=\"vt-item\">'"
  "+'<p class=\"vt-ctx\">第'+x.ses+'回 ｜ '+esc(x.date)+'</p>'"
  "+'<p class=\"vt-label\"><a href=\"'+x.url+'\" target=\"_blank\" rel=\"noopener\">'+esc(x.label)+'</a></p>'"
  "+(sm?'<p class=\"vt-sum\">'+sm+'</p>':'')"
  "+'<div class=\"vt-row\">'+ps+'</div></div>';}).join('');}"
  "document.querySelectorAll('.nw-chip').forEach(function(c){c.addEventListener('click',function(){"
  "document.querySelectorAll('.nw-chip').forEach(function(x){x.classList.remove('on');});"
  "c.classList.add('on');fs=c.getAttribute('data-v');page=1;render();});});"
  "var kb=document.getElementById('vtKw');if(kb)kb.addEventListener('input',function(){kw=kb.value.trim();page=1;render();});"
  "document.getElementById('nwPager').addEventListener('click',function(e){"
  "var b=e.target.closest('.nw-pg');if(!b||b.disabled)return;"
  "page+=(b.getAttribute('data-go')==='next'?1:-1);render();"
  "document.getElementById('nwList').scrollIntoView({behavior:'smooth',block:'start'});});"
  "render();})();</script>")
VOTES = (f'<title>採決一覧 — 参議院の記名投票を全件 ｜ AI政策くらべ</title>'
  f'<style>{INDEX_CSS}{VT_CSS}</style>'
  f'<div class="wrap">{nav("votes.html")}<div class="doc">'
  '<p class="eyebrow">採決一覧</p><h1>参議院で、各党がどう投じたか。</h1>'
  '<p class="nw-lede">掲載している3会期の<b>参議院の記名投票を全件</b>並べ、'
  'それぞれに各党（会派）の賛否を付けました。各議案名は<b>参議院の投票結果ページ</b>に直接リンクしています。'
  '<b>「政党で選ぶ」で各分野に載せているのは、この中から選んだ代表例</b>です。</p>'
  '<p class="nw-note">この一覧に<b>含まれないもの</b>：委員会での採決、衆議院の議決（原則は起立採決で個人別に残りません）、'
  '起立採決になった議案。「行」がどれだけを覆っているかは'
  '<a href="research.html">先行研究の04</a>で数えています。'
  '統一会派に属していた党（第217・219回の社民など）は、会派としての単独の賛否が残らないため「—」です。</p>'
  '<div class="nw-filters">'
  '<div class="nw-row"><span class="nw-lbl">会期</span>'
  '<button type="button" class="nw-chip on" data-v="all">すべて</button>'
  '<button type="button" class="nw-chip" data-v="221">第221回</button>'
  '<button type="button" class="nw-chip" data-v="219">第219回</button>'
  '<button type="button" class="nw-chip" data-v="217">第217回</button></div>'
  '<div class="nw-row"><span class="nw-lbl">議案名で検索</span>'
  '<input type="search" id="vtKw" placeholder="例：予算、年金、防衛" '
  'style="flex:1;min-width:160px;padding:6px 10px;border:1px solid var(--line);border-radius:8px;'
  'background:var(--card);color:var(--ink);font-size:13px"></div>'
  '</div>'
  '<p class="nw-count"><b id="nwCount">…</b></p>'
  '<div class="nw-list" id="nwList"></div><div class="nw-pager" id="nwPager"></div>'
  '<p class="note" style="margin-top:30px">出典：参議院 記名投票結果（第217回・第219回・第221回国会）。'
  '賛否は会派としての結果で、賛成・反対の理由や討論は各議案の原典でご確認ください。'
  '<b>点数化も格付けもしません。</b></p>'
  '</div></div>' + VT_JS)
open("site/votes.html", "w", encoding="utf-8").write(VOTES)


# ---------- 共通フッター（二次導線・全ページ末尾） ----------
FOOTER = ("<style>"
  ".sitefoot{--sf-sans:\"Hiragino Kaku Gothic ProN\",\"Yu Gothic\",YuGothic,\"Noto Sans JP\",Meiryo,sans-serif;"
  "--sf-mono:ui-monospace,\"SF Mono\",Menlo,Consolas,monospace;"
  "background:var(--paper);border-top:1px solid var(--line);"
  "padding:26px clamp(16px,5vw,40px) 40px;font-family:var(--sf-sans);}"
  ".sitefoot-in{max-width:900px;margin:0 auto;display:flex;flex-wrap:wrap;gap:26px;}"
  ".sf-group{display:flex;flex-direction:column;gap:7px;}"
  ".sf-l{font-family:var(--sf-mono);font-size:10.5px;letter-spacing:.12em;color:var(--muted);"
  "text-transform:uppercase;}"
  ".sf-group a{font-size:13px;color:var(--ink);text-decoration:none;}"
  ".sf-group a:hover{color:var(--accent);text-decoration:underline;}"
  ".sf-note{flex:1 1 260px;min-width:220px;font-size:11.5px;line-height:1.85;color:var(--muted);margin:0;}"
  "</style>"
  '<footer class="sitefoot"><div class="sitefoot-in">'
  '<div class="sf-group"><span class="sf-l">さらに詳しく</span>'
  '<a href="speeches.html">発言一覧</a>'
  '<a href="votes.html">採決一覧</a>'
  '<a href="shukei.html">みんなの結果</a>'
  '<a href="mynote.html">マイノート</a></div>'
  '<div class="sf-group"><span class="sf-l">このサイト</span>'
  '<a href="about.html">サイトについて</a>'
  '<a href="research.html">先行研究</a>'
  '<a href="privacy.html">プライバシー</a>'
  '<a href="feedback.html">ご意見</a>'
  '<a href="kiroku.html">ご意見と対応の記録</a></div>'
  '<p class="sf-note">出典：国会会議録検索システム／参議院 記名投票結果'
  '（第217回・第219回・第221回国会）。要約は編集判断を含みます。'
  '<b>点数化も格付けもしません。</b>判断は原典リンクで裏取りしてください。</p>'
  '</div></footer>')

# ---------- 浮遊「マイノート」ボタン（保存が1件以上あるとき全ページ右下に出現・ヘッダには置かない） ----------
FLOATNOTE=("\n<style>"
  ".kgfab{position:fixed;right:16px;bottom:16px;z-index:95;display:inline-flex;align-items:center;gap:8px;"
  "background:var(--accent);color:#fff;text-decoration:none;border-radius:26px;padding:11px 17px;"
  "box-shadow:0 6px 22px rgba(20,28,50,.28);font-family:var(--mono),monospace;font-size:13px;font-weight:700;}"
  ".kgfab svg{fill:#fff;width:15px;height:15px;}"
  "@media(max-width:600px){.kgfab{right:12px;bottom:12px;padding:10px 15px;font-size:12px;}}"
  "</style>"
  '<a class="kgfab" id="kgfab" href="mynote.html" hidden aria-label="マイノートを開く">'
  '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 3.6h12a1 1 0 0 1 1 1v16.1l-7-4.1-7 4.1V4.6a1 1 0 0 1 1-1z"/></svg>'
  '<span>マイノート <b id="kgfabn"></b></span></a>'
  "<script>window.KGNOTE=(function(){"
  "function n(){try{return Object.keys(JSON.parse(localStorage.getItem('kg_notes')||'{}')).length;}catch(e){return 0;}}"
  "function refresh(){var f=document.getElementById('kgfab');if(!f)return;var c=n();"
  "if(c>0){f.hidden=false;document.getElementById('kgfabn').textContent=c;}else{f.hidden=true;}}"
  "if(document.readyState!=='loading')refresh();else document.addEventListener('DOMContentLoaded',refresh);"
  "return {refresh:refresh};})();</script>")

# ---------- firebase.js ----------
FIREBASE_JS='''/* ===== Firebase 設定 =====
   Firebaseコンソール > プロジェクト設定 > 「マイアプリ(ウェブ)」で発行される値を貼り付けてください。
   未設定のままでもサイトは動作します(結果送信と集計だけ無効になります)。 */
var FIREBASE_CONFIG = {
  apiKey: "PASTE_API_KEY",
  authDomain: "PASTE_PROJECT.firebaseapp.com",
  projectId: "PASTE_PROJECT_ID"
};
/* ======================== */
/* App Check（bot・不正投稿対策・任意）。使う場合は reCAPTCHA v3 のサイトキーを入れる。空なら無効。
   ※コンソールで「適用(enforce)」する前に、キーを入れて動作確認すること（順序はREADME参照）。 */
var RECAPTCHA_SITE_KEY = "";
var PARTY_ID = %s;
window.KG = (function(){
  var db=null, ready=false;
  try{
    if(FIREBASE_CONFIG.apiKey && FIREBASE_CONFIG.apiKey.indexOf("PASTE")<0 && window.firebase){
      firebase.initializeApp(FIREBASE_CONFIG);
      try{ if(RECAPTCHA_SITE_KEY && firebase.appCheck){ firebase.appCheck().activate(RECAPTCHA_SITE_KEY, true); } }catch(e){}
      db=firebase.firestore(); ready=true;
    }
  }catch(e){ ready=false; }
  function inc(){ return firebase.firestore.FieldValue.increment(1); }
  return {
    enabled:function(){return ready;},
    sendResult:function(pickFull, answers, weights){
      if(!ready) return;
      var pid = PARTY_ID[pickFull] || "other";
      var upd = { responses: inc() }; upd["oi_"+pid]=inc();
      (answers||[]).forEach(function(a,i){ var k=a>0?"agree":(a<0?"oppose":"neutral"); upd["p"+i+"_"+k]=inc(); });
      (weights||[]).forEach(function(w,i){ if(w>1) upd["wt"+i]=inc(); });  // ◎重視された争点
      db.doc("aggregates/summary").set(upd,{merge:true}).catch(function(){});
    },
    loadAgg: async function(){
      if(!ready) return null;
      try{ var s=await db.doc("aggregates/summary").get(); return s.exists? s.data(): null; }
      catch(e){ return null; }
    },
    sendFeedback: function(text, from){
      if(!ready) return Promise.reject(new Error("not-ready"));
      var t = String(text||"").trim();
      if(!t) return Promise.reject(new Error("empty"));
      if(t.length > 2000) return Promise.reject(new Error("too-long"));
      // 保存するのは本文と送信元ページ名だけ。個人を特定できる情報は受け取らない。
      return db.collection("feedback").add({
        text: t,
        from: String(from||"").slice(0,40),
        at: firebase.firestore.FieldValue.serverTimestamp()
      });
    }
  };
})();''' % json.dumps(ID, ensure_ascii=False)
open("site/firebase.js","w",encoding="utf-8").write(FIREBASE_JS)

# ---------- firestore.rules ----------
RULES='''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 集計カウンター。読み取り自由 / aggregates/summary の更新のみ許可 / 削除禁止。
    // 悪用対策は App Check（reCAPTCHA v3）を 2026-07-20 に適用済み。
    match /aggregates/summary {
      allow read: if true;
      allow create, update: if true;
      allow delete: if false;
    }

    // ご意見。書き込めるが、誰も読めない。
    // 運営者が読む経路は Firebase コンソールと、ルールを迂回できる
    // サービスアカウント（件数の集計）の2つだけ。
    match /feedback/{id} {
      allow create: if request.resource.data.keys().hasOnly(['text','from','at'])
                 && request.resource.data.text is string
                 && request.resource.data.text.size() > 0
                 && request.resource.data.text.size() <= 2000
                 && request.resource.data.from is string
                 && request.resource.data.from.size() <= 40
                 && request.resource.data.at == request.time;
      allow read, update, delete: if false;
    }

    match /{document=**} { allow read, write: if false; }
  }
}'''
open("site/firestore.rules","w",encoding="utf-8").write(RULES)

# ---------- README ----------
README='''# AI政策くらべ（比例区・投票ガイド）デプロイ手順

静的サイト（index / guide / shindan / shukei）＋ Firestore(集計) の構成です。
**Firebase未設定でも全ページ動きます**（結果送信と集計だけ無効）。

## ファイル
- index.html … トップ（政策パッケージ一覧＋各ページへの導線）
- guide.html … 政党で選ぶ（言と行）
- shindan.html … 政策で照らす（旧・相性診断。結果を Firestore に集計送信）
- shukei.html … みんなの結果（Firestore から集計を表示。未設定時はサンプル表示）
- firebase.js … Firebase 設定と集計ロジック（**ここに設定を貼る**）
- firestore.rules … Firestore セキュリティルール

## 集計を有効にする（Firebase）
1. https://console.firebase.google.com/ でプロジェクト作成
2. 「Firestore Database」を作成（本番モード/ロケーションは任意）
3. プロジェクト設定 >「マイアプリ」でウェブアプリ登録 → 表示される `firebaseConfig` の
   apiKey / authDomain / projectId を **firebase.js の FIREBASE_CONFIG に貼り付け**
4. `firestore.rules` の内容を Firestore のルールに貼り付けて公開

## Firebase Hosting で公開
1. Node.js を入れて `npm install -g firebase-tools`
2. `firebase login`
3. このフォルダで `firebase init hosting`（公開ディレクトリはこのフォルダ、SPAは「No」）
4. `firebase deploy`

※ Hostingを使わず、ファイルをそのまま任意の静的ホスティング（Cloudflare Pages等）に置いてもOK。

## 集計のデータ設計（Firestore）
- 単一ドキュメント `aggregates/summary` に件数だけ加算（個人情報は保存しない）
  - responses（総数）, oi_<党id>（ワンイシュー単一選択）, p<0-6>_{agree|neutral|oppose}（各設問の賛否）

## 注意
- 無料枠(Spark): 1日 5万読み取り / 2万書き込み。超過時は課金でなく停止（請求は発生しません）。
- 上記ルールは誰でも書き込み可の簡易版です。悪用（連打・ボット）対策は下記の App Check を推奨。

## 二重カウント防止・App Check（悪用対策）
- **二重カウント防止（設定不要・実装済み）**：同じブラウザからは集計は1回だけ（localStorageに記録）。
  テストで何度も送信したい時は、ブラウザの「サイトデータ削除」かシークレットウィンドウで。
- **App Check（bot対策・任意）**：ボットによる大量の偽投稿を防ぎます。導入手順：
  1. Google reCAPTCHA 管理画面（ https://www.google.com/recaptcha/admin ）で **reCAPTCHA v3** のサイトを登録し、
     **サイトキー**を取得（ドメインに Netlify 等の公開URLのホスト名を追加）
  2. Firebaseコンソール → 「App Check」→ ウェブアプリを登録 → プロバイダに reCAPTCHA v3 を選び、上記サイトキーを設定
  3. `firebase.js` の `RECAPTCHA_SITE_KEY` にそのサイトキーを貼る → 再デプロイ
  4. **動作確認**（診断→集計がこれまで通り増える）ができてから、App Checkの「Cloud Firestore」を **「適用(enforce)」** に切り替える
  - ⚠️ 順序が逆（キー未設定のまま適用）だと、全ての書き込みが失敗します。必ず「キー設定→動作確認→適用」の順で。

## 最新ニュースの表示（news.json）
「政策で照らす」の各設問に、その争点のGoogle News見出しを表示します（同梱の news.json を読むだけ）。
- **手動更新**：`python update_news.py` を実行すると news.json が更新されます。更新後、フォルダを再アップロード。
- **自動更新（GitHub Actions・無料）**：このフォルダをGitHubリポジトリに置くと、同梱の
  `.github/workflows/news.yml` が**毎日自動で** news.json を更新します（Netlify/Cloudflare等をそのリポジトリに
  連携すれば、更新のたび自動で再公開）。※Netlify Dropの手動運用のままなら「手動更新」でOK。
- 見出し＋出典＋リンクのみ表示（本文は転載しません）。
'''
open("site/README.md","w",encoding="utf-8").write(README)

# ---------- news: 生成済みnews.json・更新スクリプト・GitHub Actionsを同梱 ----------
if os.path.exists("news.json"):
    shutil.copy("news.json", "site/news.json")
if os.path.exists("update_news.py"):
    shutil.copy("update_news.py", "site/update_news.py")
WORKFLOW = """name: update-news
on:
  schedule:
    - cron: '0 21 * * *'   # 毎日 JST 6:00 (UTC 21:00) に自動実行
  workflow_dispatch:        # 手動実行も可
permissions:
  contents: write
jobs:
  news:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: python update_news.py
      - run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          git add news.json
          git commit -m "chore: update news.json" || echo "no changes"
          git push
"""
os.makedirs("site/.github/workflows", exist_ok=True)
open("site/.github/workflows/news.yml", "w", encoding="utf-8").write(WORKFLOW)


# ---------- HTMLを完全な文書にする（クローラ・共有カード対策） ----------
SITE_URL = "https://ai-seisaku-kurabe.github.io"
PAGE_DESC = {
 "index.html":   "各党が国会で何を論じ、どう投票したか（言と行）を一次情報で比べる投票ガイド。点数化も格付けもしません。",
 "guide.html":   "政党ごとに、ワンイシューと6分野の「言（国会発言）」「行（参院採決）」を原典リンク付きで確認できます。",
 "oneissue.html":"各党が特に重視する一点（ワンイシュー）を、関連する国会発言と採決の実績から確認できます。",
 "shindan.html": "11問に答えると、あなたの考えと各党の言と行がどこで交差しどこでズレるかを表示します。",
 "news.html":    "各党・各争点のニュース見出しを政策分野別に分類して蓄積しています。見出しと出典リンクのみ。",
 "speeches.html":"国会での発言を、政党・政策分野・会期で絞り込んで探せます。すべて議事録原文へのリンク付き。",
 "votes.html":"参議院の記名投票を掲載3会期分すべて、各党の賛否付きで一覧できます。各議案は投票結果の原典にリンク。",
 "shukei.html":  "「政策で照らす」に回答した人の傾向（参考値・自己選択サンプル）。",
 "about.html":   "データの作り方・編集の判断・限界、そして運用ルールを全文公開しています。",
 "mynote.html":  "保存した各党の言と行を、分野ごとに並べて比較できます。",
 "feedback.html":"誤りの指摘・機能の要望・感想をお寄せください。",
}
def wrap_document(fn, html):
    """<!DOCTYPE>〜<body> で包み、説明文とOGタグを足す。
    これまで<title>から書き始めていたためブラウザ以外では不完全な文書だった。"""
    d = PAGE_DESC.get(fn, PAGE_DESC["index.html"])
    import re as _re
    m = _re.search(r"<title>(.*?)</title>", html, _re.S)
    title = m.group(1) if m else "AI政策くらべ"
    head_extra = ('<meta name="google-site-verification" '
                  'content="5MZhggn_go-F1KWBR-mDVs2F6fG3wO9S0UdiSt53XKM">'
                  f'<meta name="description" content="{esc(d)}">'
                  f'<link rel="canonical" href="{SITE_URL}/{"" if fn=="index.html" else fn}">'
                  f'<meta property="og:type" content="website">'
                  f'<meta property="og:site_name" content="AI政策くらべ">'
                  f'<meta property="og:title" content="{esc(title)}">'
                  f'<meta property="og:description" content="{esc(d)}">'
                  f'<meta property="og:url" content="{SITE_URL}/{"" if fn=="index.html" else fn}">'
                  f'<meta name="twitter:card" content="summary">')
    # 既存の先頭メタ・title・style は head に入れ、残りを body に置く
    idx = html.find('<div class="wrap">')
    head, body = (html[:idx], html[idx:]) if idx > 0 else ("", html)
    return ("<!DOCTYPE html>\n<html lang=\"ja\">\n<head>\n"
            + head + head_extra
            + "\n</head>\n<body>\n"
            + body
            + "\n</body>\n</html>\n")

# ---------- 全HTMLに文字コード・viewportメタを付与（スマホで正しく縮尺・折返しさせる） ----------
META=('<meta charset="utf-8">\n'
      '<meta name="viewport" content="width=device-width, initial-scale=1">\n')
for _fn in os.listdir("site"):
    if _fn.endswith(".html"):
        _p=os.path.join("site",_fn)
        _s=open(_p,encoding="utf-8").read()
        if "name=\"viewport\"" not in _s:
            _s=META+_s
        # 浮遊マイノートボタンを全ページに（マイノート自身を除く）
        if "class=\"sitefoot\"" not in _s:
            _s=_s+FOOTER
        if _fn!="mynote.html" and "id=\"kgfab\"" not in _s:
            _s=_s+FLOATNOTE
        if "<!DOCTYPE" not in _s:
            _s=wrap_document(_fn,_s)
        open(_p,"w",encoding="utf-8").write(_s)


import gen_seo; gen_seo.generate('site')

# ---------- zip ----------
if os.path.exists("seisaku_site.zip"): os.remove("seisaku_site.zip")
shutil.make_archive("seisaku_site","zip","site")
print("built site/:", sorted(os.listdir("site")))
print("zip:", os.path.getsize("seisaku_site.zip"), "bytes")
