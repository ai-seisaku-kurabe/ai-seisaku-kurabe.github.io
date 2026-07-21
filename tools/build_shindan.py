# -*- coding: utf-8 -*-
"""政党相性診断 v1.0
第1問=ワンイシュー共感、第2問以降=政策整合。各党の賛否は第217回・第221回国会の参院採決と国会発言に基づく。
結果は二段(ワンイシュー / 政策整合ランキング)。点数化で党を格付けするのではなく、
"あなたの回答との一致度"を透明に示す。"""
import json, html, urllib.parse

# 党(具体ワンイシュー)。ワンイシューはブラウズ版と一致。why=なぜこの1点か、link=根拠発言(会議録)。
PARTIES = [
 {"full":"自由民主党","short":"自民","oneissue":"防衛力の強化と現実的な政権運営",
  "why":"広範な政権与党で単一争点ではないが、強いて挙げれば抑止力の向上・防衛力強化を前面に掲げる。",
  "link":"https://kokkai.ndl.go.jp/txt/121713950X00720250415/66"},
 {"full":"立憲民主党","short":"立憲","oneissue":"行政・財政の透明化と説明責任",
  "why":"政治とカネや予算・財務の説明責任を追及し、行政の透明化を前面に掲げる。",
  "link":"https://kokkai.ndl.go.jp/txt/121705261X00320250203/71"},
 {"full":"日本維新の会","short":"維新","oneissue":"身を切る改革・歳出改革",
  "why":"議員・公務員が自ら身を切る行財政改革と、徹底した歳出削減を党是に掲げる。",
  "link":"https://kokkai.ndl.go.jp/txt/121714370X00920250417/78"},
 {"full":"国民民主党","short":"国民","oneissue":"手取りを増やす（減税・103万円の壁）",
  "why":"「対決より解決」を掲げ、減税や103万円の壁の見直しで可処分所得を増やすことを最重要に据える。",
  "link":"https://kokkai.ndl.go.jp/txt/121724293X00320250611/36"},
 {"full":"公明党","short":"公明","oneissue":"福祉と現場の処遇改善",
  "why":"現場の技能者・生活者の処遇改善や子育て・福祉など、生活者目線の政策を重視する。",
  "link":"https://kokkai.ndl.go.jp/txt/121714319X01920250612/92"},
 {"full":"日本共産党","short":"共産","oneissue":"軍拡より暮らし（大軍拡・改憲に反対）",
  "why":"大軍拡と改憲に一貫して反対し、その財源を暮らし・社会保障に回すべきだと主張する。",
  "link":"https://kokkai.ndl.go.jp/txt/121705262X00120250225/103"},
 {"full":"れいわ新選組","short":"れいわ","oneissue":"消費税廃止・積極財政",
  "why":"結党以来の看板政策。消費税廃止と積極財政で個人消費を喚起し、経済を底上げすると主張する。",
  "link":"https://kokkai.ndl.go.jp/txt/121705261X02220250512/150"},
 {"full":"チームみらい","short":"みらい","oneissue":"テクノロジーで政治を作り変える","why":"デジタル技術で行政の効率化・政治資金の可視化・プッシュ型支援を進めることを前面に掲げる。","link":"https://team-mir.ai/"},
 {"full":"社会民主党","short":"社民","oneissue":"憲法9条を守り、暮らしを底上げする","why":"護憲と反戦を党是とし、食料品消費税ゼロや最低賃金の引き上げで生活を支えると訴える。","link":"https://sdp.or.jp/"},
 {"full":"参政党","short":"参政","oneissue":"消費税減税・インボイス廃止",
  "why":"既存政治への異議として、消費税減税やインボイス廃止など負担軽減を前面に掲げる。",
  "link":"https://kokkai.ndl.go.jp/txt/121714370X00420250325/231"},
]
# 政策設問。stance: +1=賛成/近い, -1=反対/遠い, 0=中立・不明。
# pro/con=賛成派・反対派の主張(編集要約)、links=根拠資料[(ラベル,URL)]。
SANGIIN="https://www.sangiin.go.jp/japanese/touhyoulist/217/"
POLICY = [
 {"q":"消費税は引き下げる（または廃止する）べきだ",
  "stance":{"自由民主党":-1,"立憲民主党":0,"日本維新の会":0,"国民民主党":1,"公明党":0,"日本共産党":1,"れいわ新選組":1,"参政党":1,"チームみらい":-1,"社会民主党":1},
  "pro":"消費税は所得が低い人ほど負担が重い「逆進性」を持つ。物価高で苦しむ家計の手取りを直接増やし、GDPの約6割を占める個人消費を刺激して景気を底上げできる。減った税収は国債の発行や、大企業・富裕層への課税強化で補えるとする。",
  "con":"消費税は法律で使途を年金・医療・介護・子育ての「社会保障4経費」に限定した安定財源で、景気に左右されにくい。少子高齢化で膨らみ続ける社会保障を全世代で支える柱になっており、安易な引き下げは十数兆円規模の財源を失い、社会保障の削減か将来世代への借金の付け回しを招く、と反論する。",
  "links":[("引き下げ賛成：れいわ・消費税廃止の主張（会議録）","https://kokkai.ndl.go.jp/txt/121705261X02220250512/150"),
           ("維持側：消費税の使途（財務省）","https://www.mof.go.jp/tax_policy/summary/consumption/d05.htm")]},
 {"q":"防衛費を増やし、防衛力を強化すべきだ",
  "stance":{"自由民主党":1,"立憲民主党":1,"日本維新の会":1,"国民民主党":1,"公明党":1,"日本共産党":-1,"れいわ新選組":-1,"参政党":1,"チームみらい":1,"社会民主党":-1},
  "pro":"中国の軍拡、北朝鮮のミサイル、ロシアの動向など日本周辺の安全保障環境は急速に厳しくなっている。十分な防衛力と反撃能力を備えることが相手に攻撃を思いとどまらせる「抑止力」となり、結果として戦争を防ぐ。同盟国と足並みをそろえた防衛投資も欠かせない、とする。",
  "con":"GDP比2%への防衛費倍増は数兆円規模の財源を要し、増税や他の予算の圧迫につながる。軍拡競争はかえって近隣国との緊張を高め、安全を損ないかねない。まずは外交による緊張緩和と、物価高・社会保障といった暮らしの予算を優先すべきだ、と主張する。",
  "links":[("賛成：自民・抑止力向上の主張（会議録）","https://kokkai.ndl.go.jp/txt/121713950X00720250415/66"),
           ("反対：共産・軍事費より暮らし（会議録）","https://kokkai.ndl.go.jp/txt/121705262X00120250225/103"),
           ("参院採決（防衛省設置法改正）",SANGIIN+"217-0521-v011.htm")]},
 {"q":"今回の年金制度改革（給付水準の調整を含む現行案）を支持する",
  "stance":{"自由民主党":1,"立憲民主党":1,"日本維新の会":-1,"国民民主党":-1,"公明党":1,"日本共産党":-1,"れいわ新選組":-1,"参政党":0,"チームみらい":0,"社会民主党":0},
  "pro":"パート労働者らへの厚生年金の適用拡大や基礎年金の底上げにより、将来世代や低年金の人の給付水準を確保しようとするもの。制度を放置すれば給付はさらに目減りするため、痛みを伴っても早めに手を打つ現実的な改革だ、とする。",
  "con":"反対の理由は党で大きく異なる。共産・れいわは「マクロ経済スライドによる給付抑制が続く限り、今まさに困窮する年金生活者の暮らしは改善しない」と批判。一方、維新・国民は逆に「抜本改革に踏み込めず、与党審査で内容が後退した中途半端な案だ」として反対しており、方向性は正反対である。",
  "links":[("賛成：立憲・基礎年金の底上げ（会議録）","https://kokkai.ndl.go.jp/txt/121704260X02620250618/8"),
           ("反対：共産・給付抑制に反対（会議録）","https://kokkai.ndl.go.jp/txt/121715254X02720250613/38"),
           ("参院採決（年金制度改革法）",SANGIIN+"217-0613-v007.htm")]},
 {"q":"脱炭素・GXを政府主導で強力に進めるべきだ",
  "stance":{"自由民主党":1,"立憲民主党":1,"日本維新の会":1,"国民民主党":1,"公明党":1,"日本共産党":-1,"れいわ新選組":-1,"参政党":-1,"チームみらい":0,"社会民主党":1},
  "pro":"気候変動対策は待ったなしで、再生可能エネルギーや水素などへの投資は将来の基幹産業を育てる好機でもある。カーボンプライシング（炭素への価格付け）で省エネ・再エネ投資を促せば、脱炭素と経済成長を両立できる、とする。",
  "con":"急激な脱炭素は電気料金や産業界の負担を押し上げ、国民生活と国際競争力を損なう恐れがある。太陽光パネルの大量導入は中国依存や安全保障・環境上の新たなリスクも生む。安定供給とコスト、国産技術を優先し、現実的なペースで進めるべきだ、とする。",
  "links":[("賛成：立憲・カーボンプライシングで成長（会議録）","https://kokkai.ndl.go.jp/txt/121704080X01420250514/69"),
           ("懐疑：参政・脱炭素に慎重（会議録）","https://kokkai.ndl.go.jp/txt/121704006X01020250603/225"),
           ("参院採決（GX推進法）",SANGIIN+"217-0528-v008.htm")]},
 {"q":"憲法改正（緊急事態条項・議員任期延長など）を進めるべきだ",
  "stance":{"自由民主党":1,"立憲民主党":-1,"日本維新の会":1,"国民民主党":0,"公明党":0,"日本共産党":-1,"れいわ新選組":-1,"参政党":1,"チームみらい":0,"社会民主党":-1},
  "pro":"大災害やパンデミックで国政選挙が実施できない事態に備え、議員任期の延長など「緊急事態条項」を憲法に整えておくべきだ、というのが自民・維新の立場。現実に合わせて条文案を起草し、国会での議論を前に進めるべきだとする。",
  "con":"国民の多くは改憲を切実には求めておらず、任期延長の必要性（立法事実）の議論も尽くされていない、というのが立憲・共産・れいわの批判。緊急事態条項は政府への権力集中や濫用を招き、国民の権利を制限する危険があると警戒する。",
  "links":[("賛成：自民・任期延長の合意（会議録）","https://kokkai.ndl.go.jp/txt/121704183X00920250612/14"),
           ("反対：共産・改憲論議に反対（会議録）","https://kokkai.ndl.go.jp/txt/121704183X00920250612/16")]},
 {"q":"財政は健全化（PB黒字化・歳出抑制）を積極財政より優先すべきだ",
  "stance":{"自由民主党":1,"立憲民主党":0,"日本維新の会":1,"国民民主党":0,"公明党":0,"日本共産党":-1,"れいわ新選組":-1,"参政党":-1,"チームみらい":0,"社会民主党":-1},
  "pro":"日本の債務残高はGDPの2倍超と主要国で突出しており、基礎的財政収支（PB）の黒字化で借金頼みの財政から脱却すべきだ、という立場。財政規律を失えば金利上昇や将来世代への過大なツケ、いざという時の対応力の低下を招くとする。",
  "con":"過度な緊縮（増税・歳出削減）はかえって景気を冷やし、税収も減って財政を悪化させる、というのが積極財政派（れいわ・共産等）の主張。まずは政府支出で需要と成長を底上げし、経済のパイを大きくすることが、結果的に財政を健全化する近道だ、とする。",
  "links":[("健全化側：財政を考える（財務省）","https://www.mof.go.jp/zaisei/fiscal-soundness/fiscal-soundness-01.html"),
           ("参考：プライマリーバランスとは（財務省）","https://www.mof.go.jp/zaisei/reference/reference-03.html"),
           ("積極財政側：れいわ・反緊縮の主張（会議録）","https://kokkai.ndl.go.jp/txt/121704376X02320250528/106")]},
 {"q":"日米同盟を基軸に安全保障協力（協定など）を強化すべきだ",
  "stance":{"自由民主党":1,"立憲民主党":1,"日本維新の会":1,"国民民主党":1,"公明党":1,"日本共産党":-1,"れいわ新選組":-1,"参政党":1,"チームみらい":1,"社会民主党":-1},
  "pro":"厳しい安全保障環境の下、日米同盟を基軸に、豪州やフィリピンなど同志国との防衛協力（円滑化協定など）を広げることが抑止力と地域の安定を高める、という立場。一国では守り切れない安全を、信頼できる国々との連携で確保するとする。",
  "con":"米国への追従を強めれば、米国の戦争や対立に巻き込まれるリスクが高まる、という懸念（共産・れいわ）。在日米軍の基地負担の集中や主権の制約という問題もあり、対米自立と、近隣国も含めた外交努力を重視すべきだ、とする。",
  "links":[("賛成：参院採決（日比・自衛隊円滑化協定）",SANGIIN+"217-0606-v001.htm"),
           ("反対：れいわ・非軍事と平和（会議録）","https://kokkai.ndl.go.jp/txt/121714889X01720250527/208")]},
 # --- 以下は各党の公約・方針にもとづく設問（2025年参院選前後の各党マニフェスト等） ---
 {"q":"原発を再稼働し、活用（新増設・次世代炉を含む）を進めるべきだ",
  "stance":{"自由民主党":1,"立憲民主党":-1,"日本維新の会":1,"国民民主党":1,"公明党":1,"日本共産党":-1,"れいわ新選組":-1,"参政党":1,"チームみらい":0,"社会民主党":-1},
  "pro":"原発は発電時にCO2を出さず、電気を安定的・安価に大量供給できる。電力不足や電気料金の高騰、脱炭素、エネルギー安全保障への対応として、安全を確認した原発の再稼働と、次世代型炉の開発・新増設を進めるべきだ、とする（推進は自民・公明・国民・維新・参政）。",
  "con":"重大事故が起きれば被害は甚大で、避難計画や地元合意、使用済み核燃料（核のゴミ）の最終処分先も未解決。コストも安くはなく、再エネと省エネへの転換を急ぐべきだとして「原発ゼロ」を目指す（立憲・共産・れいわ）。",
  "links":[("各党の公約：エネルギー（日経・比較）","https://www.nikkei.com/article/DGXZQODL2058P0Q5A620C2000000/"),
           ("推進側の公式：資源エネルギー庁","https://www.enecho.meti.go.jp/"),
           ("反対側：日本共産党「原発ゼロ」","https://www.jcp.or.jp/web_policy/11712.html"),
           ("マニフェスト比較（FoE Japan）","https://foejapan.org/issue/staffblog/2025/07/02/staffblog-24594/")]},
 {"q":"外国人の受け入れは、もっと規制・抑制すべきだ",
  "stance":{"自由民主党":1,"立憲民主党":-1,"日本維新の会":1,"国民民主党":1,"公明党":0,"日本共産党":-1,"れいわ新選組":-1,"参政党":1,"チームみらい":1,"社会民主党":-1},
  "pro":"外国人の急増が治安・社会保険・地価などに与える影響や、社会の急な変化への不安から、受け入れの総量規制やルール違反への厳格な対応を強めるべきだ、とする立場（「日本人ファースト」の参政党、総量規制を掲げる維新）。",
  "con":"人口減少で労働力が不足するなか外国人は社会の担い手であり、排外的な規制は差別や人権侵害につながる。ルールを整えつつ「多文化共生」を進めるべきだ、とする（立憲・共産・れいわ・公明）。自民・国民は管理強化を掲げつつ総量規制には慎重で中間的。",
  "links":[("参院採決（入管法改正・第221回）","https://www.sangiin.go.jp/japanese/touhyoulist/221/221-0529-v007.htm"),
           ("政府の趣旨説明（法務委員会・会議録）","https://kokkai.ndl.go.jp/txt/122115206X00920260519/5"),
           ("論点整理（NRI・中立の分析）","https://www.nri.com/jp/media/column/kiuchi/20250710.html"),
           ("規制強化の動き（時事通信）","https://www.jiji.com/jc/article?k=2025071701040&g=pol"),
           ("共生・難民保護の視点（難民支援協会・各党公約）","https://www.refugee.or.jp/report/refugee/2025/07/manifest2507/"),
           ("公式：出入国在留管理庁","https://www.moj.go.jp/isa/")]},
 {"q":"高校・大学まで、教育の無償化を進めるべきだ",
  "stance":{"自由民主党":0,"立憲民主党":1,"日本維新の会":1,"国民民主党":1,"公明党":1,"日本共産党":1,"れいわ新選組":1,"参政党":1,"チームみらい":1,"社会民主党":1},
  "pro":"教育費の重さが少子化や格差の一因。高校・大学までの無償化で、家庭の経済状況にかかわらず学べるようにし、「人への投資」で社会全体を底上げすべきだ、とする（教育無償化を看板とする維新ほか、多くの党が拡充を主張）。",
  "con":"無償化には巨額の恒久財源が必要で、増税や他の予算の圧迫を招く。所得の高い世帯まで一律に無償化するより、本当に支援が必要な層への重点化や、教育の質・現場の待遇改善を優先すべきだ、という慎重論（自民は児童手当など現金給付を中心に、全面無償化には相対的に慎重）。",
  "links":[("各党の公約：家族・子育て（日経・比較）","https://www.nikkei.com/article/DGXZQODL205AZ0Q5A620C2000000/"),
           ("公式：こども家庭庁","https://www.cfa.go.jp/"),
           ("財源の論点：財政を考える（財務省）","https://www.mof.go.jp/zaisei/fiscal-soundness/fiscal-soundness-01.html")]},
]
# 各設問の「判定の根拠」を設問ごとに開示する（採決から立場を一意に導けない場合は明示する）
for _i,(_b,_u) in enumerate([('該当する記名採決が無いため、各党の公約と国会での発言にもとづく判定です。', ''), ('各党の公約と国会での発言にもとづく判定です。関連する採決はありますが、賛否だけでは賛成・反対の理由を一意に 判断 できないため、採決のみを根拠とはしていません。', ''), ('該当する記名採決が無いため、各党の公約と国会での発言にもとづく判定です。', ''), ('該当する記名採決が無いため、各党の公約と国会での発言にもとづく判定です。', ''), ('憲法審査会は討議の場で記名採決の議案が無いため、各党の公約と国会での発言にもとづく判定です。', ''), ('各党の公約と国会での発言にもとづく判定です。予算への賛否は「規模が大きすぎる／小さすぎる」の両方の理由から反対が生じるため、採決のみを根拠とはしていません。', ''), ('第221回国会・日比ACSA（物品役務相互提供協定）の承認に対する各党の賛否にもとづく判定です。', 'https://www.sangiin.go.jp/japanese/touhyoulist/221/221-0619-v001.htm'), ('該当する記名採決が無いため、各党の公約と国会での発言にもとづく判定です。', ''), ('第221回国会・入管法改正への賛否にもとづく判定です。政府の趣旨説明は「不法残留等を企図する者の入国を防止することにより厳格な出入国管理を実現する」「在留外国人にも相応の負担を求める」と述べており、規制を強める内容と確認しました。ただし公明党は、賛成しつつ低所得の外国人の手数料免除を求める修正案を提出しているため、中立としています。', 'https://www.sangiin.go.jp/japanese/touhyoulist/221/221-0529-v007.htm'), ('各党の公約にもとづく判定です。関連する採決として第221回の高等学校等就学支援金法改正がありますが、参政党とれいわ新選組はこれに反対票を投じています。討論が行われず反対の理由を確認できないため、採決を判定の根拠にはしていません。判定と投票行動が食い違う例として、採決結果も併せてご確認ください。', 'https://www.sangiin.go.jp/japanese/touhyoulist/221/221-0331-v006.htm')]):
    POLICY[_i]["basis"]=_b; POLICY[_i]["basis_url"]=_u

# 結果画面の個別フィードバック用の短ラベル(POLICYと同順)
for _i,_s in enumerate(["消費税減税","防衛費増額","年金改革","脱炭素・GX","憲法改正",
                        "財政健全化","日米同盟","原発活用","外国人受け入れ規制","教育無償化"]):
    POLICY[_i]["short"]=_s
DATA = {"parties": PARTIES, "policy": POLICY}
DATA_JSON = json.dumps(DATA, ensure_ascii=False)

# Q1 ワンイシュー選択肢(選択エリア + 詳しく見る折りたたみ)
oi_picks = "".join(
 f'<div class="oi-item" data-party="{html.escape(p["full"])}">'
 f'<div class="oi-main" role="button" tabindex="0" aria-pressed="false">'
 f'<span class="oip-s">{html.escape(p["short"])}</span>'
 f'<span class="oip-i">{html.escape(p["oneissue"])}</span></div>'
 f'<details class="oi-more"><summary>詳しく見る</summary>'
 f'<div class="oi-detail"><p>{html.escape(p["why"])}</p>'
 f'<a class="src" href="{html.escape(p["link"])}" target="_blank" rel="noopener">根拠の発言（会議録） ↗</a>'
 f'</div></details></div>' for p in PARTIES)

# 政策設問
def links_html(links):
    return "　".join(
        f'<a class="src" href="{html.escape(u)}" target="_blank" rel="noopener">{html.escape(lb)} ↗</a>'
        for lb,u in links)

# 各設問のGoogle News検索クエリ(POLICYと同順)
NEWS_QUERY = ["消費税 減税", "防衛費 増額", "年金制度改革", "GX 脱炭素 政策",
              "憲法改正 緊急事態条項", "財政健全化 プライマリーバランス", "日米同盟 安全保障",
              "原発 再稼働", "外国人 受け入れ 政策", "教育 無償化"]
def news_link(i):
    q = urllib.parse.quote(NEWS_QUERY[i])
    return (f'<a class="src news" href="https://news.google.com/search?q={q}&hl=ja&gl=JP&ceid=JP:ja" '
            f'target="_blank" rel="noopener">🔎 この争点の最新ニュース ↗</a>')

SHORT_BY_FULL = {p["full"]: p["short"] for p in PARTIES}
def side_parties(stance, v):
    names = [SHORT_BY_FULL[p["full"]] for p in PARTIES if stance.get(p["full"], 0) == v]
    return "・".join(names) if names else "（なし）"

pq = ""
for i,q in enumerate(POLICY):
    pq += (f'<div class="pq" data-qi="{i}"><p class="pq-q"><span class="pq-n">Q{i+2}</span>'
           f'{html.escape(q["q"])}</p>'
           f'<div class="opts">'
           f'<button type="button" class="opt" data-val="1">賛成</button>'
           f'<button type="button" class="opt" data-val="0">どちらでもない</button>'
           f'<button type="button" class="opt" data-val="-1">反対</button></div>'
           f'<button type="button" class="wt">◎ この争点を特に重視する</button>'
           f'<details class="arg"><summary>この争点の対立軸（賛成派・反対派の主張）を見る</summary>'
           f'<div class="arg-cols">'
           f'<div class="arg-col pro"><div class="arg-hrow">'
           f'<span class="arg-h pro">賛成派の主張</span>'
           f'<span class="arg-parties pro">賛成：{side_parties(q["stance"],1)}</span></div>'
           f'<p>{html.escape(q["pro"])}</p></div>'
           f'<div class="arg-col con"><div class="arg-hrow">'
           f'<span class="arg-h con">反対派の主張</span>'
           f'<span class="arg-parties con">反対：{side_parties(q["stance"],-1)}</span></div>'
           f'<p>{html.escape(q["con"])}</p></div></div>'
           f'<p class="arg-l">根拠資料：{links_html(q["links"])}</p>'
           f'<p class="arg-basis"><b>この設問での各党の立場は何にもとづくか：</b>{html.escape(q.get("basis",""))}'
           + (f' <a class="src" href="{q["basis_url"]}" target="_blank" rel="noopener">採決の原典→</a>' if q.get("basis_url") else '')
           + '</p>'
           f'<p class="arg-l">{news_link(i)}　'
           f'<span class="arg-neutral">※「どちらでもない/不明」の党は各分野で中立扱い</span></p>'
           f'<div class="newsbox" data-qi="{i}"></div>'
           f'</details></div>')

# 設問の選び方の開示。
# 先行研究（Walgrave ら 2009）は、設問の選択そのものが一致度を左右することを実証している。
# 選び方を書かずに結果だけ出すのは、いちばん効く編集判断を隠すことになるので、
# 設問の直前に置く（研究の詳しい話と数字は research.html へ）。
_n_vote = sum(1 for q in POLICY if q.get("basis_url"))
HOWPICKED = (
  '<details class="howpicked"><summary>この' + str(len(POLICY) + 1)
  + '問は、どうやって選んだのか</summary>'
  '<p><b>設問を選ぶこと自体が、いちばん大きな編集判断です。</b>'
  '設問の選び方によって、どの党と一致しやすいかは変わります。'
  'そのため、選び方を隠さずに書いておきます。</p>'
  '<ul>'
  '<li><b>誰が選んだか：</b>運営者が選びました。'
  'ドイツの Wahl-O-Mat のように、混成チームが多数の案を作り、'
  '<b>全政党に回答させたうえで絞り込むといった多段階の手続きは踏んでいません。</b></li>'
  '<li><b>第1問（ワンイシュー）も編集判断です。</b>'
  '各党が特に重視する1点を、国会での言動から運営者が1つに絞ったものです。'
  '何を根拠にその1点にしたかは、第1問の各党の「詳しく見る」と'
  '<a class="src" href="oneissue.html">ワンイシューのページ</a>に出しています。'
  '以下の内訳は、第2問以降の' + str(len(POLICY)) + '問についてのものです。</li>'
  '<li><b>何から作ったか：</b>' + str(len(POLICY)) + '問のうち<b>' + str(_n_vote)
  + '問</b>は参議院の記名採決での各党の賛否から立場を判定し、'
  '<b>' + str(len(POLICY) - _n_vote) + '問</b>は各党の公約と国会での発言から判定しています。'
  '設問ごとの根拠は、各設問の「この争点の対立軸」を開くと書いてあります。</li>'
  '<li><b>選ばなかった争点：</b>掲載している会期の記名投票はあわせて数百件あり、'
  'そのほとんどは設問になっていません。'
  '<b>検討して外したのではなく、多くは検討そのものをしていません。</b></li>'
  '<li><b>選定の基準は、選んだ時点で文書になっていませんでした。</b>'
  'いま公開しているのは事後に洗い出した記録で、当時の議事録ではありません。'
  '件数と内訳は'
  '<a class="src" href="research.html">先行研究と、この設計の根拠</a>の'
  '「04 ／ 自分たちで測ったこと」に出しています。</li>'
  '</ul></details>')

CSS = """
:root{ --paper:#f3f4f7; --card:#fbfbfd; --ink:#1b2130; --muted:#5c6675; --line:#dcdfe6;
  --accent:#3a4d8f; --accent-soft:#e6e9f4; --pos:#2f8f7f; --neg:#c1704f;
  --shadow:0 1px 2px rgba(20,28,50,.05),0 8px 24px rgba(20,28,50,.05); }
@media (prefers-color-scheme:dark){ :root{ --paper:#12151d; --card:#191d27; --ink:#e7eaf1;
  --muted:#98a1b2; --line:#282e3b; --accent:#8ea2e6; --accent-soft:#222a40;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35); } }
:root[data-theme="dark"]{ --paper:#12151d; --card:#191d27; --ink:#e7eaf1; --muted:#98a1b2;
  --line:#282e3b; --accent:#8ea2e6; --accent-soft:#222a40;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35); }
:root[data-theme="light"]{ --paper:#f3f4f7; --card:#fbfbfd; --ink:#1b2130; --muted:#5c6675;
  --line:#dcdfe6; --accent:#3a4d8f; --accent-soft:#e6e9f4;
  --shadow:0 1px 2px rgba(20,28,50,.05),0 8px 24px rgba(20,28,50,.05); }
*{ box-sizing:border-box; }
.wrap{ --serif:"Hiragino Mincho ProN","Yu Mincho",YuMincho,"Noto Serif JP",serif;
  --sans:"Hiragino Kaku Gothic ProN","Yu Gothic",YuGothic,"Noto Sans JP",Meiryo,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  background:var(--paper); color:var(--ink); font-family:var(--sans); line-height:1.7;
  -webkit-font-smoothing:antialiased; padding:clamp(20px,5vw,56px) clamp(16px,5vw,40px); }
.doc{ max-width:760px; margin:0 auto; }
.eyebrow{ font-family:var(--mono); font-size:12px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); margin:0 0 12px; }
h1{ font-family:var(--serif); font-weight:600; font-size:clamp(24px,4.4vw,36px); line-height:1.3;
  text-wrap:balance; margin:0 0 14px; }
.lede{ color:var(--muted); font-size:14.5px; margin:0 0 8px; }
.lede b{ color:var(--ink); }
.rule{ height:1px; background:var(--line); border:0; margin:26px 0; }
.qhead{ font-family:var(--serif); font-size:18px; font-weight:600; margin:0 0 4px; }
.qsub{ color:var(--muted); font-size:13px; margin:0 0 16px; }
/* 進捗バー：回答中は常に上部に見える。この画面ではサイトヘッダは追従させず進捗を優先 */
.sitehdr{ position:static !important; }
.prog{ position:sticky; top:0; z-index:80; background:var(--paper);
  display:flex; align-items:center; gap:12px; padding:11px 0; margin:0 0 14px; border-bottom:1px solid var(--line); }
.prog-bar{ flex:1; height:8px; background:var(--accent-soft); border-radius:99px; overflow:hidden; }
.prog-fill{ height:100%; width:0%; background:var(--accent); border-radius:99px; transition:width .35s ease; }
.prog-txt{ font-family:var(--mono); font-size:12px; color:var(--muted); white-space:nowrap; font-variant-numeric:tabular-nums; }
.prog-txt b{ color:var(--accent); font-size:14.5px; }
.oi-grid{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }
@media (max-width:560px){ .oi-grid{ grid-template-columns:1fr; } }
.oi-item{ background:var(--card); border:1.5px solid var(--line); border-radius:12px;
  overflow:hidden; transition:.12s; }
.oi-item.sel{ border-color:var(--accent); background:var(--accent-soft); box-shadow:var(--shadow); }
.oi-main{ cursor:pointer; padding:12px 14px 11px; position:relative; }
.oi-main:hover{ background:rgba(58,77,143,.04); }
.oi-item.sel .oi-main::after{ content:"✓"; position:absolute; top:10px; right:12px; color:var(--accent);
  font-weight:700; }
.oip-s{ display:block; font-family:var(--serif); font-weight:600; font-size:15px; }
.oip-i{ display:block; font-size:12.5px; color:var(--muted); margin-top:2px; padding-right:16px; }
.oi-more{ border-top:1px dashed var(--line); padding:0 14px; }
.oi-more>summary{ font-family:var(--mono); font-size:11px; color:var(--accent); cursor:pointer;
  list-style:none; padding:8px 0; }
.oi-more>summary::-webkit-details-marker{ display:none; }
.oi-more>summary::before{ content:"▸ "; }
.oi-more[open]>summary::before{ content:"▾ "; }
.oi-detail{ padding:0 0 12px; }
.oi-detail p{ margin:0 0 8px; font-size:12.5px; line-height:1.75; color:var(--ink); }
.oi-detail .src{ font-size:11.5px; }
.oi-none{ margin-top:10px; }
.req{ font-family:var(--sans); font-size:11px; font-weight:700; color:#fff; background:var(--neg);
  border-radius:6px; padding:2px 8px; vertical-align:2px; margin-left:4px; }
.q1err{ display:none; color:var(--neg); font-size:13px; font-weight:600; margin:12px 0 0; }
.pq{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:16px 18px;
  margin-bottom:12px; box-shadow:var(--shadow); }
.pq-q{ font-size:14.5px; font-weight:600; margin:0 0 12px; }
.pq-n{ font-family:var(--mono); color:var(--accent); margin-right:8px; }
.opts{ display:flex; gap:8px; flex-wrap:wrap; }
.opt{ flex:1; min-width:96px; font:inherit; font-size:13.5px; cursor:pointer; background:transparent;
  color:var(--muted); border:1px solid var(--line); border-radius:10px; padding:9px 10px; transition:.12s; }
.opt:hover{ border-color:var(--accent); color:var(--ink); }
.opt.sel{ background:var(--accent); color:#fff; border-color:var(--accent); font-weight:600; }
.pq-b{ font-size:11.5px; color:var(--muted); margin:11px 0 0; font-family:var(--mono); }
.wt{ margin-top:10px; font:inherit; font-size:12px; cursor:pointer; background:transparent;
  color:var(--muted); border:1px dashed var(--line); border-radius:20px; padding:5px 13px; transition:.12s; }
.wt:hover{ border-color:var(--accent); color:var(--accent); }
.wt.on{ background:var(--accent-soft); color:var(--accent); border-style:solid; border-color:var(--accent);
  font-weight:600; }
.wt.on::before{ content:"✓ "; }
details.arg{ margin-top:12px; border-top:1px dashed var(--line); padding-top:10px; }
details.arg>summary{ font-family:var(--mono); font-size:11.5px; color:var(--accent); cursor:pointer;
  list-style:none; }
details.arg>summary::-webkit-details-marker{ display:none; }
details.arg>summary::before{ content:"▸ "; }
details.arg[open]>summary::before{ content:"▾ "; }
details.arg[open]>summary{ margin-bottom:10px; }
.arg-cols{ display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:12px; }
@media(max-width:560px){ .arg-cols{ grid-template-columns:1fr; } }
.arg-col{ border-radius:10px; padding:13px 15px; border:1px solid transparent; }
.arg-col.pro{ background:rgba(47,143,127,.10); border-color:rgba(47,143,127,.35); }
.arg-col.con{ background:rgba(193,112,79,.11); border-color:rgba(193,112,79,.38); }
.arg-hrow{ display:flex; align-items:baseline; justify-content:space-between; gap:8px;
  flex-wrap:wrap; margin-bottom:8px; }
.arg-h{ font-family:var(--sans); font-size:12px; font-weight:700; letter-spacing:.02em; }
.arg-h.pro{ color:var(--pos); } .arg-h.con{ color:var(--neg); }
.arg-parties{ font-size:10.5px; line-height:1.5; text-align:right; }
.arg-parties.pro{ color:var(--pos); } .arg-parties.con{ color:var(--neg); }
.arg-col p{ margin:0; font-size:12.5px; line-height:1.85; color:var(--ink); }
.arg-basis{ background:var(--paper); border:1px solid var(--line); border-radius:8px;
  padding:9px 12px; font-size:12px; line-height:1.8; color:var(--muted); margin:12px 0 0; }
.arg-basis b{ color:var(--ink); }
.arg-l{ font-size:11.5px; color:var(--muted); line-height:1.95; margin:0; }
.arg-neutral{ opacity:.85; }
.arg-l .news{ font-weight:600; }
.newsbox:empty{ display:none; }
.newsbox{ margin-top:10px; border-top:1px dashed var(--line); padding-top:10px; }
.news-h{ font-family:var(--mono); font-size:10.5px; color:var(--muted); margin-bottom:7px; }
.newsitem{ display:block; text-decoration:none; color:var(--ink); font-size:12.5px; line-height:1.55;
  padding:6px 0; border-bottom:1px solid var(--line); }
.newsitem:last-child{ border-bottom:0; }
.newsitem:hover{ color:var(--accent); }
.news-s{ display:block; font-size:10.5px; color:var(--muted); margin-top:2px; }
.actions{ display:flex; gap:12px; align-items:center; margin:22px 0; flex-wrap:wrap; }
.btn{ font:inherit; font-weight:600; font-size:15px; cursor:pointer; border-radius:12px; padding:12px 26px;
  border:1px solid var(--accent); background:var(--accent); color:#fff; }
.btn.ghost{ background:transparent; color:var(--accent); }
.btn:hover{ opacity:.92; }
#result{ margin-top:8px; }
.rcard{ background:var(--card); border:1px solid var(--line); border-radius:16px; padding:22px 24px;
  box-shadow:var(--shadow); margin-bottom:16px; }
.rcard h3{ font-family:var(--serif); font-size:16px; margin:0 0 12px; }
.rlabel{ font-family:var(--mono); font-size:11px; letter-spacing:.08em; color:var(--accent); }
.pick-list{ display:flex; flex-wrap:wrap; gap:8px; }
.pill{ font-size:13px; font-weight:600; background:var(--accent-soft); color:var(--ink);
  border:1px solid var(--line); border-radius:20px; padding:5px 13px; }
.rank{ display:flex; flex-direction:column; gap:10px; }
.row{ display:grid; grid-template-columns:64px 1fr auto; gap:12px; align-items:center; }
.row .nm{ font-family:var(--serif); font-weight:600; }
.row .oi{ font-size:11.5px; color:var(--muted); }
.bar{ height:12px; border-radius:6px; background:var(--line); overflow:hidden; }
.bar>i{ display:block; height:100%; background:var(--accent); }
.row.top .bar>i{ background:var(--pos); }
.sc{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:12.5px; color:var(--muted);
  white-space:nowrap; }
.diverge{ background:var(--accent-soft); border:1px solid var(--line); border-left:3px solid var(--accent);
  border-radius:0 10px 10px 0; padding:12px 15px; font-size:13px; margin-top:14px; }
.matchwhy{ background:var(--pos-soft,rgba(47,143,127,.10)); border:1px solid rgba(47,143,127,.28);
  border-left:3px solid var(--pos); border-radius:0 10px 10px 0; padding:11px 15px;
  font-size:13px; line-height:1.8; margin-top:14px; }
.matchwhy b{ color:var(--ink); }
/* 同率1位の告知。評価ではなく事実の通知なので、色は付けず紙面と同系でおさえる */
.tienote{ background:var(--paper); border:1px solid var(--line); border-radius:10px;
  padding:11px 15px; font-size:13px; line-height:1.8; margin-top:14px; }
.tienote b{ color:var(--ink); }
/* 設問の選び方の開示。目立たせすぎず、しかし設問の前に必ず置く */
.howpicked{ background:var(--card); border:1px solid var(--line); border-radius:12px;
  padding:11px 15px; margin:0 0 16px; font-size:13px; }
.howpicked summary{ cursor:pointer; color:var(--accent); font-weight:600; }
.howpicked p{ line-height:1.85; margin:10px 0 0; }
.howpicked ul{ margin:8px 0 0; padding-left:18px; }
.howpicked li{ line-height:1.85; margin:6px 0; }
.caveat{ font-size:12px; color:var(--muted); line-height:1.85; margin-top:14px; }
.caveat b{ color:var(--ink); }
a.src{ color:var(--accent); text-decoration:none; } a.src:hover{ text-decoration:underline; }
:focus-visible{ outline:2px solid var(--accent); outline-offset:2px; border-radius:4px; }
"""

JS = """
const DATA = __DATA__;
function selectOne(item){   // 単一選択(必須・ラジオ式)
  document.querySelectorAll('.oi-item').forEach(x=>{
    x.classList.remove('sel');
    const mm=x.querySelector('.oi-main'); if(mm) mm.setAttribute('aria-pressed','false');
  });
  item.classList.add('sel');
  const m=item.querySelector('.oi-main');
  if(m) m.setAttribute('aria-pressed','true');
  const err=document.getElementById('q1err'); if(err) err.style.display='none';
  updateProg();
}
function updateProg(){
  const oi=document.querySelector('.oi-item.sel')?1:0;
  const pol=document.querySelectorAll('.pq .opt.sel').length;
  const n=oi+pol, total=11;
  const num=document.getElementById('progNum'); if(num) num.textContent=n;
  const fill=document.getElementById('progFill'); if(fill) fill.style.width=(n/total*100)+'%';
}
document.querySelectorAll('.oi-main').forEach(m=>{
  const item=m.closest('.oi-item');
  m.addEventListener('click',()=>selectOne(item));
  m.addEventListener('keydown',e=>{ if(e.key==='Enter'||e.key===' '){e.preventDefault();selectOne(item);} });
});
document.querySelectorAll('.pq .opt').forEach(b=>b.addEventListener('click',()=>{
  b.parentNode.querySelectorAll('.opt').forEach(x=>x.classList.remove('sel'));
  b.classList.add('sel');
  updateProg();
  // 「どちらでもない」を選んだら、その争点の対立軸を自動で開いて理解を助ける
  if(b.dataset.val==='0'){ var d=b.closest('.pq').querySelector('details.arg'); if(d&&!d.open) d.open=true; }
}));
document.querySelectorAll('.pq .wt').forEach(b=>b.addEventListener('click',()=>b.classList.toggle('on')));
function esc(s){return String(s).replace(/[&<>]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));}
function compute(){
  const ans = DATA.policy.map((q,i)=>{
    const s=document.querySelector('.pq[data-qi="'+i+'"] .opt.sel');
    return s?parseInt(s.dataset.val):0;
  });
  const wts = DATA.policy.map((q,i)=>
    document.querySelector('.pq[data-qi="'+i+'"] .wt.on')?3:1);
  const res = DATA.parties.map(p=>{
    let considered=0, agree=0, raw=0;
    DATA.policy.forEach((q,i)=>{
      const ps=q.stance[p.full]||0, ua=ans[i];
      if(ps!==0 && ua!==0){ var w=wts[i]; considered+=w; raw++; if(Math.sign(ps)===Math.sign(ua)) agree+=w; }
    });
    return {p, considered, agree, raw, pct: considered? agree/considered : null};
  });
  res.sort((a,b)=>{
    const pa=a.pct===null?-1:a.pct, pb=b.pct===null?-1:b.pct;
    return pb-pa || b.considered-a.considered;
  });
  const selItem=document.querySelector('.oi-item.sel');
  if(!selItem){   // 第1問は必須
    const err=document.getElementById('q1err');
    if(err){ err.style.display='block'; err.scrollIntoView({behavior:'smooth',block:'center'}); }
    return;
  }
  const pick=selItem.dataset.party;  // 'none' か 党フルネーム
  LAST_ANS=ans; LAST_WTS=wts;
  render(res, pick, ans.filter(a=>a!==0).length);
}
let LAST_ANS=[], LAST_WTS=[];
function partyByFull(f){return DATA.parties.find(p=>p.full===f);}
function render(res, pick, answered){
  // A: ワンイシュー(単一選択)
  let a='';
  if(pick && pick!=='none'){
    const p=partyByFull(pick);
    a = '<span class="pill">'+esc(p.short)+'：'+esc(p.oneissue)+'</span>';
  } else {
    a = '<p class="oi" style="margin:0">「特にない」を選択。ワンイシューにはこだわらず、下の政策整合で見ていきましょう。</p>';
  }
  // B: 政策整合ランキング
  // 一致度が同じ党は「同率」として全部そろえて出す。先頭の1党だけを1位に見せると、
  // 並べ替えの規則（判定に使われた設問数）が優劣に見えてしまうため。
  const scored=res.filter(r=>r.pct!==null);
  const top = scored.length?scored[0]:null;
  const topPct = top?top.pct:null;
  const tops = top?scored.filter(r=>r.pct===topPct):[];
  let rows = res.map((r,idx)=>{
    const isTop = r.pct!==null && r.pct===topPct;
    const w = r.pct===null?0:Math.round(r.pct*100);
    const sc = r.pct===null?'判定材料なし':('一致度 '+w+'%');
    return '<div class="row'+(isTop?' top':'')+'"><div><span class="nm">'+esc(r.p.short)+'</span></div>'
      +'<div><div class="oi">'+esc(r.p.oneissue)+'</div><div class="bar"><i style="width:'+w+'%"></i></div></div>'
      +'<div class="sc">'+sc+'</div></div>';
  }).join('');
  // 同率のときは、その事実を先に伝える（この設問数では区別できない、という情報のため）
  let tie='';
  if(tops.length>1){
    tie='<p class="tienote"><b>一致度が同じ党が'+tops.length+'つあります（'
      +tops.map(r=>esc(r.p.short)).join('・')+'）。</b>'
      +'この'+DATA.policy.length+'問の範囲では、これらの党を区別できません。'
      +'上下の並びは判定に使われた設問数の多い順で、優劣ではありません。'
      +'設問を増やせば差がつくこともあります。</p>';
  }
  // 個別フィードバック：一致度が最も高い党と、あなたの回答が一致した争点(重視した争点を優先)
  let why='';
  if(top){
    const tp=top.p, matched=[];
    DATA.policy.forEach((q,i)=>{
      const ps=q.stance[tp.full]||0, ua=LAST_ANS[i]||0;
      if(ps!==0 && ua!==0 && Math.sign(ps)===Math.sign(ua))
        matched.push({label:q.short||q.q, w:LAST_WTS[i]||1});
    });
    matched.sort((a,b)=>b.w-a.w);  // ◎重視した争点を先に
    if(matched.length){
      const names=matched.slice(0,3).map(m=>m.w>1?('<b>'+esc(m.label)+'</b>（重視）'):esc(m.label));
      why='<p class="matchwhy">'+(tops.length>1?'同率のうち':'')+'<b>'+esc(tp.short)+'</b>とは、'+names.join('・')
        +(matched.length>3?(' ほか'+(matched.length-3)+'件'):'')
        +'であなたの回答と'+esc(tp.short)+'の投票・発言の傾向が一致しました。</p>';
    }
  }
  // 食い違い注意
  let div='';
  if(top && pick && pick!=='none' && !tops.some(r=>r.p.full===pick)){
    div='<div class="diverge"><b>ワンイシューと政策整合が食い違っています。</b>'
      +'あなたが選んだワンイシューの党（'+esc(partyByFull(pick).short)
      +'）と、政策全体の一致度が最も高い党（'+tops.map(r=>esc(r.p.short)).join('・')+'）が異なります。'
      +'「1点で選ぶか、全体で選ぶか」を意識して考えてみてください。</div>';
  }
  const html_ = ''
   +'<div class="rcard"><span class="rlabel">結果 A ／ ワンイシューで惹かれた党</span>'
   +'<h3>あなたが共感した「1点」</h3><div class="pick-list">'+a+'</div></div>'
   +'<div class="rcard"><span class="rlabel">結果 B ／ 政策の整合が高い順</span>'
   +'<h3>あなたの回答との一致度（'+answered+'問に回答）</h3><div class="rank">'+rows+'</div>'+tie+why+div+'</div>'
   +'<div class="rcard"><span class="rlabel">この照合の限界</span>'
   +'<p class="caveat"><b>これは断定ではなく出発点です。</b>各党の賛否は、第217回・第221回国会の参院採決・国会発言や各党の公約にもとづく編集判断で、'
   +'「中立/不明(0)」も含みます。「◎ 特に重視」を選んだ争点は3倍で計算しています。'
   +'この照合の癖（どの党が1位に出やすいか、計算方法を変えると何％で1位が入れ替わるか）は、'
   +'ありうる回答すべてを計算して<a class="src" href="research.html">先行研究と、この設計の根拠</a>で公開しています。'
   +'必ず<a class="src" href="guide.html">政党で選ぶ</a>で'
   +'各党の実際の言と行（原典リンク付き）を確かめてください。</p></div>';
  const r=document.getElementById('result'); r.innerHTML=html_;
  r.scrollIntoView({behavior:'smooth',block:'start'});
}
document.getElementById('go').addEventListener('click',compute);
document.getElementById('reset').addEventListener('click',()=>{
  document.querySelectorAll('.sel,.wt.on').forEach(e=>{e.classList.remove('sel');e.classList.remove('on');});
  document.getElementById('result').innerHTML='';
  updateProg();
  window.scrollTo({top:0,behavior:'smooth'});
});
updateProg();
// 最新ニュース: 同一フォルダの news.json を読んで各設問に見出しを表示(無ければ何もしない)
fetch('news.json').then(function(r){return r.ok?r.json():null;}).then(function(nd){
  if(!nd||!nd.topics) return;
  document.querySelectorAll('.newsbox').forEach(function(box){
    var list=nd.topics[box.dataset.qi]||[];
    if(!list.length) return;
    box.innerHTML='<div class="news-h">最新ニュース見出し'+(nd.updated?'（'+nd.updated+' 時点）':'')+'</div>'+
      list.map(function(h){return '<a class="newsitem" href="'+h.u+'" target="_blank" rel="noopener">'+
        esc(h.t)+'<span class="news-s">'+esc(h.s||'')+'</span></a>';}).join('');
  });
}).catch(function(){});
"""

HTML = f'''<title>政策で照らす — あなたの考えと各党の言と行を照らし合わせる ｜ AI政策くらべ</title>
<style>{CSS}</style>
<div class="wrap"><div class="doc">
  <p class="eyebrow">比例区・投票ガイド ／ 政策で照らす</p>
  <h1>あなたに近い政党は？ ― 1点で選ぶか、全体で選ぶか</h1>
  <p class="lede">2つの角度で照らし合わせます。<b>第1問</b>は各党の「ワンイシュー（特に重視する1点）」への共感、
  <b>第2問以降</b>は主要政策への賛否です。各党の立場は<b>第217回・第221回国会の参院採決・国会発言</b>に基づきます。何にもとづく判定かは、設問ごとに個別に記載しています。
  <b>点数で党を格付けするものではなく、あなたの回答との一致度を示すだけ</b>です。</p>
  <hr class="rule">

  <div class="prog" id="prog">
    <div class="prog-bar"><div class="prog-fill" id="progFill"></div></div>
    <span class="prog-txt"><b id="progNum">0</b> / 11 問 回答</span>
  </div>

  <p class="qhead">第1問　各党のワンイシュー、特に共感するものを1つ選んでください <span class="req">必須</span></p>
  <p class="qsub">最も共感する1つを選択（1つだけ）。ワンイシューにこだわらないなら「特にない」を。
  各カードの「詳しく見る」で、なぜその1点なのか（＋根拠発言）を確認できます。</p>
  <div class="oi-grid">{oi_picks}</div>
  <div class="oi-none"><div class="oi-item" data-party="none">
    <div class="oi-main" role="button" tabindex="0" aria-pressed="false">
    <span class="oip-s">特にない</span>
    <span class="oip-i">ワンイシューにはこだわらず、政策全体で判断したい</span></div></div></div>
  <p id="q1err" class="q1err">第1問を1つ選んでください（必須）。</p>

  <hr class="rule">
  <p class="qhead">第2問〜　主要政策への賛否</p>
  <p class="qsub">賛成・反対がはっきりしない設問は「どちらでもない」で構いません。
  特に大事だと思う争点は <b>「◎ この争点を特に重視する」</b> を押すと、一致度の計算で3倍の重みになります。</p>
  {HOWPICKED}
  {pq}

  <div class="actions">
    <button type="button" class="btn" id="go">結果を見る</button>
    <button type="button" class="btn ghost" id="reset">やり直す</button>
  </div>
  <div id="result"></div>

  <p class="caveat" style="margin-top:20px">
    データ出典：<a class="src" href="https://kokkai.ndl.go.jp/" target="_blank" rel="noopener">国会会議録検索システム</a>／
    <a class="src" href="https://www.sangiin.go.jp/japanese/touhyoulist/217/vote_ind.htm" target="_blank" rel="noopener">参議院 記名投票結果</a>（第217回国会）。
    参政党は会派未結成のため一部の採決データがなく、該当設問は中立扱いです。
  </p>
</div></div>
<script>{JS.replace("__DATA__", DATA_JSON)}</script>'''

open("shindan.html","w",encoding="utf-8").write(HTML)
print("wrote shindan.html", len(HTML), "bytes / policy Qs:", len(POLICY))
