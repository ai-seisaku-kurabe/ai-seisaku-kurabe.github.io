# -*- coding: utf-8 -*-
"""デプロイ用一式を site/ に出力してzip化。
- 既存の policy_guide.html / shindan.html / shukei.html を生成→ナビ挿入・相対リンク・Firebase配線
- index.html(トップ), firebase.js, firestore.rules, README.md を新規生成
Firebase未設定でも全ページ動作(送信/集計だけ無効)。設定を firebase.js に貼れば集計有効化。"""
import html, json, os, shutil, re, urllib.parse

ns={}
exec(open("build_shindan.py",encoding="utf-8").read(), ns)   # -> shindan.html, PARTIES, POLICY
exec(open("build_party.py",encoding="utf-8").read(), {})     # -> policy_guide.html
exec(open("build_shukei.py",encoding="utf-8").read(), {})    # -> shukei.html(サンプル)
PARTIES=ns["PARTIES"]; POLICY=ns["POLICY"]

ID={"自由民主党":"jimin","立憲民主党":"rikken","日本維新の会":"ishin","国民民主党":"kokumin",
    "公明党":"komei","日本共産党":"kyosan","れいわ新選組":"reiwa","参政党":"sansei","none":"none"}
# 各党のイメージカラー（各党公式サイト基準・報道慣例を参考。認識性優先で微調整）
PC={"自由民主党":"#E60012","立憲民主党":"#004097","日本維新の会":"#12A150","国民民主党":"#F2B200",
    "公明党":"#F55881","日本共産党":"#D7003A","れいわ新選組":"#E4007F","参政党":"#E8630A"}
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
    items=[("index.html","トップ"),("guide.html","政党で選ぶ"),("oneissue.html","ワンイシュー"),
           ("shindan.html","政策で照らす"),("news.html","ニュース"),
           ("shukei.html","みんなの結果"),
           ("about.html","サイトについて"),("feedback.html","ご意見")]
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
shukei=shukei+FB_TAGS+SHUKEI_JS
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
"""
FEEDBACK_FORM = ('  <p class="eyebrow">ご意見・お問い合わせ</p>'
  '<h1>このサイトへのご意見をお寄せください</h1>'
  '<p class="lede">誤りの指摘・機能の要望・感想など、なんでも歓迎です。いただいた声は<b>サイトの改善に活用</b>します。</p>'
  '<div class="fb-thanks" style="margin-bottom:22px">'
  '<b>ご意見の受付方法が変わりました。</b><br>'
  'ホスティングの移行にともない、これまでの送信フォームが使えなくなりました。'
  '現在は<b>GitHubのIssue</b>で受け付けています。'
  '<p style="margin:16px 0 0">'
  '<a class="fb-btn" style="text-decoration:none;display:inline-block" '
  'href="https://github.com/ai-seisaku-kurabe/ai-seisaku-kurabe.github.io/issues/new" '
  'target="_blank" rel="noopener">▸ ご意見を投稿する（GitHub）</a></p></div>'
  '<p class="fb-note">・GitHubのアカウントが必要です。お持ちでない方向けの入力フォームは準備中です。<br>'
  '・<b>このサイトのソースコードは公開しています。</b>掲載データ・生成スクリプト・'
  '運用ルールのすべてを<a class="src" href="https://github.com/ai-seisaku-kurabe/ai-seisaku-kurabe.github.io" target="_blank" rel="noopener">'
  'リポジトリ</a>で確認でき、誤りがあればIssueやPull Requestで直接指摘できます。<br>'
  '・いただいた内容はサイト改善の目的でのみ利用します。</p>')
FEEDBACK_JS = ""   # フォーム送信は廃止（GitHub Issue へ誘導）
FEEDBACK = (f'<title>ご意見・お問い合わせ — AI政策くらべ</title>\n<style>{INDEX_CSS}{FEEDBACK_CSS}</style>\n'
  f'<div class="wrap">{nav("feedback.html")}<div class="doc">' + FEEDBACK_FORM + '</div></div>' + FEEDBACK_JS)
open("site/feedback.html","w",encoding="utf-8").write(FEEDBACK)

# ---------- oneissue.html (ワンイシュー深掘り) ----------
OISPEECH = json.load(open("oneissue_speech.json",encoding="utf-8")) if os.path.exists("oneissue_speech.json") else {}
# 各党のワンイシュー→関連する採決(実績)を引く分野の投票データ
VKEY={"自由民主党":"自由民主党","立憲民主党":"立憲民主","日本維新の会":"日本維新の会",
  "国民民主党":"国民民主","公明党":"公明党","日本共産党":"日本共産党","れいわ新選組":"れいわ","参政党":None}
REFVOTE={"自由民主党":("diplo_votes.json","外交・安保"),"立憲民主党":("votes_data.json","財政"),
  "日本維新の会":("votes_data.json","財政"),"国民民主党":("votes_data.json","財政"),
  "公明党":("ss_votes.json","社会保障"),"日本共産党":("diplo_votes.json","外交・安保"),
  "れいわ新選組":("votes_data.json","財政"),"参政党":(None,None)}
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
        return hd+'</div><p class="oi-none">参政党は第217回国会の参議院で会派を構成しておらず、この会期の会派別記名投票記録がありません（第221回では会派を結成しており、政党で選ぶのページで賛否を確認できます）。</p>'
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
  "れいわ新選組":"税・財政","参政党":"税・財政"}
THEME_ORDER=["税・財政","外交・安保","くらし・社会保障"]
# ワンイシューに対応するニュース分野と、会議録検索に渡すキーワード
ONEISSUE_DOMAIN = {"自由民主党":"外交・安保","立憲民主党":"財政","日本維新の会":"財政",
  "国民民主党":"財政","公明党":"社会保障","日本共産党":"外交・安保",
  "れいわ新選組":"財政","参政党":"財政"}
ONEISSUE_KEYWORD = {"自由民主党":"抑止力","立憲民主党":"説明責任","日本維新の会":"歳出改革",
  "国民民主党":"手取り","公明党":"処遇改善","日本共産党":"軍事費",
  "れいわ新選組":"消費税","参政党":"消費税"}
def oneissue_links(full):
    """その争点のニュースと、会議録での発言検索への入口。"""
    dom = ONEISSUE_DOMAIN.get(full, "財政")
    kw = ONEISSUE_KEYWORD.get(full, "")
    q = urllib.parse.urlencode({"keyword": kw, "from": "2026-01-01", "until": "2026-07-20"})
    return (f'<div class="oi-more2">'
            f'<a href="news.html?domain={urllib.parse.quote(dom)}">▸ この争点のニュース（{esc(dom)}）</a>'
            f'<a href="https://kokkai.ndl.go.jp/#/result?{q}" target="_blank" rel="noopener">'
            f'▸ この争点の発言を会議録で探す（「{esc(kw)}」）</a></div>')

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
  '<li>出典は<a class="src" href="https://kokkai.ndl.go.jp/" target="_blank" rel="noopener">国会会議録検索システム</a>（第217回国会）。API経由で発言を取得します。</li>'
  '<li><b>質問側の議員の発言のみ</b>を対象とし、<b>答弁側（大臣・副大臣・政府参考人・参考人など）は除外</b>します。政府答弁は「その党の主張」ではないためです。</li>'
  '<li>各争点の<b>キーワード周辺</b>を抜き出し、挨拶や定型の前置きは避けます。<b>引用は原文のまま</b>で、こちらで言葉を補ったり推測で書き換えたりしません。</li>'
  '<li>すべての発言に、<b>その発言の該当箇所へ直接ジャンプする原文リンク</b>を付けています（会議録のトップではなく、当該発言まで一発で飛べます）。要約を信じる必要はなく、原典で直接確認できます。</li></ul></section>'

  '<section class="ab-sec"><p class="ab-k">03 ／ 「行」の作り方</p>'
  '<h2 class="ab-h">参議院の記名投票から、会派ごとの賛否を取る</h2>'
  '<ul class="ab-list">'
  '<li>出典は<a class="src" href="https://www.sangiin.go.jp/japanese/touhyoulist/217/vote_ind.htm" target="_blank" rel="noopener">参議院 記名投票結果</a>。各法案ページの会派別の賛成・反対をそのまま集計します。</li>'
  '<li><b>発言（言）は衆議院・参議院の両方</b>から採っています。国会会議録検索システムが両院を収録しているためで、''引用にはどちらの議院・どの委員会かを明記しています。</li>''<li>一方、<b>採決（行）は参議院のみ</b>です。衆議院の本会議は原則として起立採決で、会派別・個人別の賛否が公式記録に残らないためです。''この<b>衆参の非対称</b>は、データの制約であって編集方針ではありません。</li>''<li>憲法分野は記名投票の議案が無く「行」は該当なしとしています。</li></ul></section>'

  '<section class="ab-sec"><p class="ab-k">04 ／ 「編集判断」の中身</p>'
  '<h2 class="ab-h">どこに人の手が入るかを、隠さない</h2>'
  '<p class="ab-b">「どの発言・どの採決を選ぶか」「ワンイシューを1点にどう絞るか」は、'
  '一次情報をもとにした<b>編集の判断</b>です。ここに偏りが入り得ることは事実です。'
  'だからこそ、その判断を検証可能にする3点を徹底しています。</p>'
  '<ul class="ab-list">'
  '<li><b>引用は原文</b>・<b>必ず原典リンク</b>。編集要約を信じなくても、元の発言・採決に当たれます。</li>'
  '<li><b>点数化・格付けをしない</b>。「良い/悪い」の結論を出さないので、評価の偏りが入り込む余地を最小化しています。</li>'
  '<li>AI（Claude）は、膨大な会議録の<b>収集・整理・要約の下書き</b>に使っています。'
  '「どの党が優れているか」といった<b>評価の結論をAIに出させることはしていません</b>。</li></ul></section>'

  '<section class="ab-sec"><p class="ab-k">05 ／ 運用ルール（AIへの指示に相当）</p>'
  '<h2 class="ab-h">私たちがAIを動かしている「ルールそのもの」</h2>'
  '<p class="ab-b">「AIの要約自体が偏っているのでは」という疑念に応えるため、発言の収集・引用・要約で'
  '<b>必ず守っている運用ルール（AIに与えている指示に相当するもの）</b>を、そのまま公開します。'
  'このルールから外れた記載を見つけたら、それは私たちの誤りです。'
  '<a class="src" href="feedback.html">ご指摘ください</a>。</p>'
  '<ol class="rulebook">'
  '<li>発言は国会会議録検索システムのAPIから取得する。対象は<b>質問側の議員の発言のみ</b>とし、'
  '答弁側（大臣・副大臣・大臣政務官・政府参考人・参考人など）は除外する。</li>'
  '<li>引用は<b>原文のまま</b>。語を補ったり推測で書き換えたりしない。定型の挨拶・前置きは引用に含めない。</li>'
  '<li>すべての発言・採決に、<b>一次情報の該当箇所への直接リンク</b>を付す。</li>'
  '<li>採決は<b>参議院の記名投票の会派別賛否</b>をそのまま用いる。衆議院は個人別賛否が残らないため扱わない。</li>'
  '<li><b>点数化・格付け・ランキング・「平均からの乖離」を出力しない。</b></li>'
  '<li>データが無い項目は<b>捏造せず空欄にし、理由を明記</b>する。</li>'
  '<li>「ワンイシュー」「力点」などの要約は<b>編集判断であると明示</b>し、党の公式見解とは称さない。</li>'
  '<li>AIは<b>収集・整理・要約の下書き</b>に用い、「どの党が優れているか」等の<b>評価の結論は出力しない</b>。</li>'
  '</ol></section>'

  '<section class="ab-sec"><p class="ab-k">06 ／ あえて「しない」こと</p>'
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

  '<section class="ab-sec"><p class="ab-k">07 ／ このツールの限界</p>'
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
  '<div class="ab-limit"><p><b>これは第217回国会という一断面です。</b>今後の会期で更新していきます。</p></div></section>'

  '<section class="ab-sec"><p class="ab-k">08 ／ 誤りの指摘と修正</p>'
  '<h2 class="ab-h">間違いは、直します</h2>'
  '<p class="ab-b">すべての記載は原典リンクから検証できます。'
  '事実誤認・要約の偏り・見落としにお気づきの際は、ぜひご指摘ください。'
  '内容を確認し、必要なら修正します。</p>'
  '<div class="ab-cta">'
  '<a class="p" href="feedback.html">誤りを指摘・意見を送る</a>'
  '<a class="s" href="guide.html">「政党で選ぶ」を見る</a></div></section>'

  '<p class="note" style="margin-top:36px">運営：個人（AIをパートナーとした非営利の試み）。'
  '本サイトは特定の政党・団体とは無関係で、広告・献金・アフィリエイトはありません。</p>'
  '</div></div>')
open("site/about.html","w",encoding="utf-8").write(ABOUT)

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
  "var ORD=['財政','外交・安保','社会保障','エネルギー・環境','経済・産業','憲法'];"
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
NEWS_DOMAINS = ["財政","外交・安保","社会保障","エネルギー・環境","経済・産業","憲法"]
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
  "var pg=document.getElementById('nwPager');""if(!total){root.innerHTML='<div class=\"nw-empty\">条件に合う見出しがありません。</div>';pg.innerHTML='';return;}""pg.innerHTML = pages>1 ? ('<button class=\"nw-pg\" data-go=\"prev\"'+(page<=1?' disabled':'')+'>← 前の10件</button>'""+'<span class=\"nw-pgi\">'+page+' / '+pages+' ページ</span>'""+'<button class=\"nw-pg\" data-go=\"next\"'+(page>=pages?' disabled':'')+'>次の10件 →</button>') : '';"
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
    }
  };
})();''' % json.dumps(ID, ensure_ascii=False)
open("site/firebase.js","w",encoding="utf-8").write(FIREBASE_JS)

# ---------- firestore.rules ----------
RULES='''rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 集計カウンターのみ公開。読み取り自由 / aggregates/summary の更新のみ許可 / 削除禁止。
    match /aggregates/summary {
      allow read: if true;
      allow create, update: if true;   // ※テスト用。悪用対策は App Check の追加を推奨(README参照)
      allow delete: if false;
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
        if _fn!="mynote.html" and "id=\"kgfab\"" not in _s:
            _s=_s+FLOATNOTE
        open(_p,"w",encoding="utf-8").write(_s)

# ---------- zip ----------
if os.path.exists("seisaku_site.zip"): os.remove("seisaku_site.zip")
shutil.make_archive("seisaku_site","zip","site")
print("built site/:", sorted(os.listdir("site")))
print("zip:", os.path.getsize("seisaku_site.zip"), "bytes")
