# -*- coding: utf-8 -*-
"""みんなの結果(集計)ページ v0.1  B=各政策の賛否割合 / C=ワンイシュー共感ランキング
現時点はサンプル(ダミー)データで表示レイアウトを確認する用。後でFirestoreの集計値に差し替える。"""
import html, json
ns={}
exec(open("build_shindan.py",encoding="utf-8").read(), ns)
PARTIES=ns["PARTIES"]; POLICY=ns["POLICY"]
def esc(s): return html.escape(str(s))

RESPONSES = 1000  # サンプル総回答数
# C: ワンイシュー共感(単一選択・必須なので合計はほぼ100%)
C_SAMPLE = {"れいわ新選組":210,"国民民主党":180,"日本維新の会":120,"参政党":110,
            "自由民主党":110,"日本共産党":95,"立憲民主党":85,"公明党":40,"__none":50}
# B: 各設問の 賛成/どちらでもない/反対 (合計=RESPONSES)。設問数(POLICY)に合わせる。
B_SAMPLE = [
 (640,180,180),(470,250,280),(300,330,370),(420,330,250),(380,260,360),(400,300,300),(520,260,220),
 (480,200,320),(420,240,340),(700,180,120)]
# D: 各設問を「◎特に重視」と選んだ人数(複数選択可なので合計はRESPONSESを超えうる)
QSHORT = ["消費税減税","防衛費増額","年金改革の支持","脱炭素・GX","憲法改正","財政健全化を優先",
          "日米同盟の強化","原発の活用","外国人受け入れ規制","教育の無償化"]
D_SAMPLE = [460,380,300,180,260,240,210,320,350,300]

short={p["full"]:p["short"] for p in PARTIES}
oneissue={p["full"]:p["oneissue"] for p in PARTIES}

# C rows (降順)
c_items=[]
for full,n in sorted(C_SAMPLE.items(), key=lambda kv:-kv[1]):
    if full=="__none":
        nm,oi="（特にない）","ワンイシューにこだわらない"
    else:
        nm,oi=short[full],oneissue[full]
    pct=round(n/RESPONSES*100)
    c_items.append(
        f'<div class="crow"><div class="cnm"><b>{esc(nm)}</b><span>{esc(oi)}</span></div>'
        f'<div class="cbarwrap"><div class="cbar" style="width:{pct}%"></div></div>'
        f'<div class="cval">{pct}%<small>{n}</small></div></div>')

# B rows
b_items=[]
for i,q in enumerate(POLICY):
    a,nn,o=B_SAMPLE[i]
    pa,pn,po=[round(x/RESPONSES*100) for x in (a,nn,o)]
    b_items.append(
        f'<div class="bq"><p class="bq-q"><span class="bq-n">Q{i+2}</span>{esc(q["q"])}</p>'
        f'<div class="bseg">'
        f'<div class="sg agree" style="width:{pa}%" title="賛成 {pa}%"></div>'
        f'<div class="sg neu" style="width:{pn}%" title="どちらでもない {pn}%"></div>'
        f'<div class="sg opp" style="width:{po}%" title="反対 {po}%"></div></div>'
        f'<div class="bkey"><span class="k agree">賛成 {pa}%</span>'
        f'<span class="k neu">どちらでもない {pn}%</span>'
        f'<span class="k opp">反対 {po}%</span></div></div>')

# D行(重視ランキング・降順)
d_items=[]
for i in sorted(range(len(QSHORT)), key=lambda i:-D_SAMPLE[i]):
    n=D_SAMPLE[i]; pct=round(n/RESPONSES*100)
    d_items.append(
        f'<div class="crow"><div class="cnm"><b>{esc(QSHORT[i])}</b></div>'
        f'<div class="cbarwrap"><div class="cbar" style="width:{pct}%"></div></div>'
        f'<div class="cval">{pct}%<small>{n}</small></div></div>')

CSS="""
:root{ --paper:#f3f4f7; --card:#fbfbfd; --ink:#1b2130; --muted:#5c6675; --line:#dcdfe6;
  --accent:#3a4d8f; --accent-soft:#e6e9f4; --pos:#2f8f7f; --neg:#c1704f; --neu:#9aa3b2;
  --shadow:0 1px 2px rgba(20,28,50,.05),0 8px 24px rgba(20,28,50,.05); }
@media (prefers-color-scheme:dark){ :root{ --paper:#12151d; --card:#191d27; --ink:#e7eaf1;
  --muted:#98a1b2; --line:#282e3b; --accent:#8ea2e6; --accent-soft:#222a40; --neu:#5c6473;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35); } }
:root[data-theme="dark"]{ --paper:#12151d; --card:#191d27; --ink:#e7eaf1; --muted:#98a1b2;
  --line:#282e3b; --accent:#8ea2e6; --accent-soft:#222a40; --neu:#5c6473;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35); }
:root[data-theme="light"]{ --paper:#f3f4f7; --card:#fbfbfd; --ink:#1b2130; --muted:#5c6675;
  --line:#dcdfe6; --accent:#3a4d8f; --accent-soft:#e6e9f4; --neu:#9aa3b2;
  --shadow:0 1px 2px rgba(20,28,50,.05),0 8px 24px rgba(20,28,50,.05); }
*{ box-sizing:border-box; }
.wrap{ --serif:"Hiragino Mincho ProN","Yu Mincho",YuMincho,"Noto Serif JP",serif;
  --sans:"Hiragino Kaku Gothic ProN","Yu Gothic",YuGothic,"Noto Sans JP",Meiryo,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  background:var(--paper); color:var(--ink); font-family:var(--sans); line-height:1.7;
  -webkit-font-smoothing:antialiased; padding:clamp(20px,5vw,56px) clamp(16px,5vw,40px); }
.doc{ max-width:800px; margin:0 auto; }
.eyebrow{ font-family:var(--mono); font-size:12px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); margin:0 0 12px; }
h1{ font-family:var(--serif); font-weight:600; font-size:clamp(24px,4.4vw,36px); line-height:1.3;
  text-wrap:balance; margin:0 0 14px; }
.lede{ color:var(--muted); font-size:14.5px; margin:0 0 8px; }
.demo{ display:inline-block; font-family:var(--mono); font-size:11.5px; color:#a4700f;
  background:rgba(200,140,20,.12); border:1px solid rgba(200,140,20,.4); border-radius:8px;
  padding:6px 12px; margin:6px 0 4px; }
.n{ font-family:var(--mono); font-variant-numeric:tabular-nums; }
.rule{ height:1px; background:var(--line); border:0; margin:24px 0; }
.sec{ font-family:var(--serif); font-size:19px; font-weight:600; margin:0 0 4px; }
.sec-s{ color:var(--muted); font-size:13px; margin:0 0 18px; }
.card{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:20px 22px;
  box-shadow:var(--shadow); margin-bottom:18px; }
.total{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:clamp(26px,4vw,34px);
  font-weight:600; color:var(--accent); }
.total small{ font-size:14px; color:var(--muted); font-weight:400; }
/* C */
.crow{ display:grid; grid-template-columns:150px 1fr 62px; gap:12px; align-items:center; margin-bottom:11px; }
.cnm b{ font-family:var(--serif); font-weight:600; font-size:14px; display:block; }
.cnm span{ font-size:10.5px; color:var(--muted); display:block; line-height:1.4; }
.cbarwrap{ background:var(--line); border-radius:6px; height:14px; overflow:hidden; }
.cbar{ height:100%; background:var(--accent); border-radius:6px; }
.cval{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-weight:600; text-align:right; }
.cval small{ display:block; font-size:10px; color:var(--muted); font-weight:400; }
@media(max-width:560px){ .crow{ grid-template-columns:120px 1fr 52px; } }
/* B */
.bq{ margin-bottom:18px; }
.bq-q{ font-size:13.5px; font-weight:600; margin:0 0 8px; }
.bq-n{ font-family:var(--mono); color:var(--accent); margin-right:8px; }
.bseg{ display:flex; height:22px; border-radius:7px; overflow:hidden; border:1px solid var(--line); }
.sg{ height:100%; }
.sg.agree{ background:var(--pos); } .sg.neu{ background:var(--neu); } .sg.opp{ background:var(--neg); }
.bkey{ display:flex; flex-wrap:wrap; gap:14px; margin-top:7px; font-size:11.5px; }
.bkey .k::before{ content:""; display:inline-block; width:10px; height:10px; border-radius:3px;
  margin-right:5px; vertical-align:-1px; }
.k.agree{ color:var(--pos); } .k.agree::before{ background:var(--pos); }
.k.neu{ color:var(--muted); } .k.neu::before{ background:var(--neu); }
.k.opp{ color:var(--neg); } .k.opp::before{ background:var(--neg); }
.sk-arch{ background:var(--card); border:1px solid var(--line); border-radius:14px;
  padding:16px 20px; margin:22px 0 0; }
.sk-arch-t{ margin:0 0 6px; font-size:13.5px; }
.sk-arch-b{ margin:0 0 12px; font-size:12.5px; line-height:1.9; color:var(--muted); }
.sk-arch-b b{ color:var(--ink); }
.sk-snap{ font:inherit; font-size:12.5px; cursor:pointer; background:transparent; color:var(--accent);
  border:1px solid var(--accent); border-radius:20px; padding:8px 16px; }
.sk-snap:hover{ background:var(--accent); color:#fff; }
.sk-pause{ background:var(--card); border:1px solid var(--line); border-left:3px solid #c1704f;
  border-radius:0 14px 14px 0; padding:20px 24px; font-size:14px; line-height:1.9; }
.note{ font-size:12px; color:var(--muted); line-height:1.85; margin-top:20px; }
.note b{ color:var(--ink); }
a.src{ color:var(--accent); text-decoration:none; } a.src:hover{ text-decoration:underline; }
"""

HTML=f'''<title>みんなの結果（集計）— 政策で照らす ｜ AI政策くらべ</title>
<style>{CSS}</style>
<div class="wrap"><div class="doc">
  <p class="eyebrow">比例区・投票ガイド ／ みんなの結果</p>
  <h1>みんなの結果（集計）</h1>
  <p class="demo" id="demoBadge">※ 現在はサンプル（ダミー）データです。実データはFirebase接続後に反映されます。</p>
  <p class="lede">「政策で照らす」に回答した人の集計です。<b>これは自分から答えに来た人だけの自己選択サンプルで、
  世論調査（代表サンプル）ではありません。</b>あくまで参考値としてご覧ください。個人情報は一切集めていません。</p>
  <div class="card" style="text-align:center">
    <div class="total" id="totalN">{RESPONSES:,}<small> 件の回答</small></div>
  </div>

  <hr class="rule">
  <p class="sec">C ／ 共感された「ワンイシュー」ランキング</p>
  <p class="sec-s">第1問で「最も共感する」と選ばれた各党ワンイシューの割合（1人1つの単一選択・必須）。</p>
  <div class="card" id="cCard">{''.join(c_items)}</div>

  <hr class="rule">
  <p class="sec">B ／ 各政策への賛否</p>
  <p class="sec-s">第2問以降の各設問に、回答者全体がどう答えたか。</p>
  <div class="card" id="bCard">{''.join(b_items)}</div>

  <hr class="rule">
  <p class="sec">D ／ みんなが「特に重視」した争点</p>
  <p class="sec-s">「政策で照らす」で「◎ 特に重視する」を押した割合（複数選択可）。いま何に関心が集まっているかの目安。</p>
  <div class="card" id="dCard">{''.join(d_items)}</div>

  <p class="note">
    <b>集計の作り方（予定）：</b>「政策で照らす」で「結果を見る」を押すと、選んだワンイシューと各設問の賛否だけが
    件数として1つずつ加算されます（個人が特定できる情報は保存しません）。<br>
    <b>読み方の注意：</b>回答者は自ら答えに来た人に偏っており、母集団を代表しません。数字の独り歩きに注意してください。<br>
    <a class="src" href="shindan.html">▸ 自分でも政策で照らしてみる</a>
  </p>
  <div class="sk-arch">
    <p class="sk-arch-t"><b>研究のための保管について</b></p>
    <p class="sk-arch-b">この集計は、設問・各党の判定・その根拠とあわせて
    <a class="src" href="https://github.com/ai-seisaku-kurabe/ai-seisaku-kurabe.github.io/tree/main/archive" target="_blank" rel="noopener">アーカイブ</a>
    に保管しています。判定基準は新しい採決や公約の確認によって変わるため、回答だけでなく
    <b>その時点の設問と判定基準ごと</b>残さないと、後から数字の意味を復元できないためです。
    設問は経年比較ができるよう、毎週ではなく<b>国会の会期ごと</b>に見直します。</p>
    <button type="button" class="sk-snap" id="snapBtn">スナップショットを保存（JSON）</button>
  </div>
  <p class="note" style="display:none">
    <a class="src" href="index.html">▸ トップにもどる</a>
  </p>
</div></div>'''
open("shukei.html","w",encoding="utf-8").write(HTML)
print("wrote shukei.html", len(HTML), "bytes")
