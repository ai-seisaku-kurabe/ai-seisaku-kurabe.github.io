# -*- coding: utf-8 -*-
"""政策くらべ v0.4 「言と行」 財政＋外交の2領域
言=会議録の発言(原文引用+リンク)、行=参院記名投票の会派別賛否(原典リンク)。点数化しない。"""
import html, json, re
def esc(s): return html.escape(str(s))

def clean_quote(q):
    """推測で補った括弧を除去し、原文が切れる自然な位置で「…」止めにする"""
    q = q.strip()
    for _ in range(2):
        q = re.sub(r'[…\.\s]*[（(][^）)]*[）)][…\.\s]*$', '', q)  # 末尾の補完括弧を除去
    q = re.sub(r'[…、,\s]+$', '', q)
    if not q.endswith(('。', '！', '？', '」')):
        q += '…'
    return q

FVOTES = json.load(open("votes_data.json", encoding="utf-8"))
DVOTES = json.load(open("diplo_votes.json", encoding="utf-8"))
SVOTES = json.load(open("ss_votes.json", encoding="utf-8"))
EVOTES = json.load(open("energy_votes.json", encoding="utf-8"))
CVOTES = json.load(open("econ_votes.json", encoding="utf-8"))
VBASE = "https://www.sangiin.go.jp/japanese/touhyoulist/217/"
FLABEL = ["予算", "所得税法", "地方交付税", "特会法"]
DLABEL = ["防衛省設置法", "日比協定", "北朝鮮制裁", "円滑化実施法"]
SLABEL = ["年金改革", "児童福祉", "薬機法", "労働施策"]
ELABEL = ["GX推進", "環境アセス", "洋上風力", "物価対策予備費"]
CLABEL = ["下請法", "事業再生法", "政投銀法", "保険業法"]

def votes_html(vkey, votes, labels):
    if vkey is None:
        return ('<div class="votes"><span class="vlbl">行 ／ 参院採決</span>'
                '<span class="vna">会派未結成のため会派別の賛否記録なし</span></div>')
    chips = []
    for i, b in enumerate(votes["bills"]):
        st = next((v["stance"] for name, v in b["parties"].items() if vkey in name), None)
        cls = {"賛成": "yes", "反対": "no"}.get(st or "", "na")
        chips.append(
            f'<a class="vchip {cls}" href="{esc(VBASE + b["id"] + ".htm")}" target="_blank" '
            f'rel="noopener" title="{esc(b["label"])}：{esc(st or "—")}（原典へ）">'
            f'{esc(labels[i])}<b>{esc(st or "—")}</b></a>')
    return ('<div class="votes"><span class="vlbl">行 ／ 参院記名投票</span>'
            f'<div class="vrow">{"".join(chips)}</div></div>')

NO_VOTE_BLOCK = ('<div class="votes"><span class="vlbl">行 ／ 参院採決</span>'
    '<span class="vna">該当なし — 憲法審査会は討議の場で、本会議の記名投票にかかる議案がありません</span></div>')

def cards_html(items, votes, labels):
    out = []
    for f in items:
        tag = f'<span class="tag">◉ {esc(f["tag"])}</span>' if f["tag"] else ""
        vblock = NO_VOTE_BLOCK if votes is None else votes_html(f["vkey"], votes, labels)
        out.append(f'''
      <article class="pcard">
        <header><h3>{esc(f["party"])}</h3>{tag}</header>
        <p class="point"><span class="lbl">言 ／ 力点（編集要約）</span>{esc(f["point"])}</p>
        <blockquote>「{esc(clean_quote(f["quote"]))}」
          <cite>— {esc(f["who"])}議員・第217回国会</cite>
          <a class="evq" href="{esc(f["url"])}" target="_blank" rel="noopener">全文→</a></blockquote>
        {vblock}
      </article>''')
    return "".join(out)

# ---------- 財政 ----------
FISCAL = [
 {"party":"自由民主党","who":"西田昌司","tag":None,"vkey":"自由民主党",
  "point":"党内に財政健全化重視と、拙速なPB黒字化への慎重論が併存。政府は「健全化の旗は降ろさない」立場。",
  "quote":"政府は、金利ある世界を恐れ、プライマリーバランスの黒字化を早く達成しようとしています。",
  "url":"https://kokkai.ndl.go.jp/txt/121714370X01520250603/21"},
 {"party":"立憲民主党","who":"本庄知史","tag":"財政の透明化","vkey":"立憲民主",
  "point":"財政健全化と補正予算のあり方、財務諸表の分かりやすさ(説明責任)を追及。",
  "quote":"まず、財政健全化と補正予算についてお伺いをしたいと思います。",
  "url":"https://kokkai.ndl.go.jp/txt/121705261X00320250203/71"},
 {"party":"れいわ新選組","who":"高井崇志","tag":"反緊縮・積極財政","vkey":"れいわ",
  "point":"「財政危機論」そのものに反対。緊縮と増税に反対し、積極財政を主張。",
  "quote":"日本の財政がギリシャより悪い、極めてよろしくないと言うのは、これはやはり…",
  "url":"https://kokkai.ndl.go.jp/txt/121704376X02320250528/106"},
 {"party":"日本維新の会","who":"藤巻健史","tag":"歳出改革","vkey":"日本維新の会",
  "point":"PB黒字化の見通しの楽観的な前提に懐疑的。歳出改革と決断を重視。",
  "quote":"まさに楽観的な予想もいいところで、まさに基礎的財政収支黒字化の経済予想と全く同じような前提に立っている",
  "url":"https://kokkai.ndl.go.jp/txt/121714370X00920250417/78"},
 {"party":"国民民主党","who":"田村まみ","tag":"手取りを増やす","vkey":"国民民主",
  "point":"税収増の使途と、社会保障(診療・薬価・介護報酬改定)と財政の連関を追及。",
  "quote":"診療報酬改定、薬価改定、介護報酬改定、ここが大きく",
  "url":"https://kokkai.ndl.go.jp/txt/121714260X00620250403/66"},
 {"party":"公明党","who":"山本博司","tag":None,"vkey":"公明党",
  "point":"潜在的国民負担率や地方財政の持続性に着目した質疑。",
  "quote":"地方財政の課題に関しまして質問をさせていただきます。",
  "url":"https://kokkai.ndl.go.jp/txt/121714601X00420250325/20"},
 {"party":"日本共産党","who":"田村智子","tag":"軍拡より暮らし","vkey":"日本共産党",
  "point":"軍事費拡大下の財政規律を問い、財政投融資特会の使途変更に反対。",
  "quote":"特別会計に関する法律の一部を改正する法律案に反対の討論を行います。",
  "url":"https://kokkai.ndl.go.jp/txt/121704376X01920250422/8"},
 {"party":"参政党","who":"神谷宗幣","tag":"消費税減税","vkey":None,
  "point":"消費税減税と「統合政府」論を軸に、財源観と国民生活の比較衡量を主張。",
  "quote":"消費税を減らすと税収は減ることが見込まれるわけですけど、でも、結局…",
  "url":"https://kokkai.ndl.go.jp/txt/121714370X00420250325/231"},
]

# ---------- 外交・安保 ----------
DIPLO = [
 {"party":"自由民主党","who":"若林洋平","tag":"抑止力の向上","vkey":"自由民主党",
  "point":"日本の抑止力向上を最重視し、防衛力強化を推進。",
  "quote":"全てにおいて日本の抑止力を上げることが最も重要なことだと思います。",
  "url":"https://kokkai.ndl.go.jp/txt/121713950X00720250415/66"},
 {"party":"立憲民主党","who":"奥野総一郎","tag":"財源を追及","vkey":"立憲民主",
  "point":"防衛力強化には賛成しつつ、その財源(NTT株売却等)と手続きの妥当性を追及。",
  "quote":"NTT法を廃止して株を売却してそれを防衛費に充てるというような議論があって、そこからスタートしている…",
  "url":"https://kokkai.ndl.go.jp/txt/121704601X01420250508/31"},
 {"party":"れいわ新選組","who":"大島九州男","tag":"非軍事・平和","vkey":"れいわ",
  "point":"防衛関連法案から北朝鮮制裁承認まで一貫して反対した唯一の会派。非軍事・平和利用を掲げる。",
  "quote":"こういう政策で行けば当然人をあやめることがない、やはりそういう平和利用(を重視する)…",
  "url":"https://kokkai.ndl.go.jp/txt/121714889X01720250527/208"},
 {"party":"日本維新の会","who":"杉本和巳","tag":"抗堪性強化","vkey":"日本維新の会",
  "point":"防衛力(抗堪性)強化を支持する一方、米国の過大な防衛費要求には懸念を示す。",
  "quote":"抗堪化、抗堪力をどんどん増していただきたい…国防次官になったコルビーさんが、日本の防衛費を三倍にしろとかと言った",
  "url":"https://kokkai.ndl.go.jp/txt/121703968X01220250521/89"},
 {"party":"国民民主党","who":"橋本幹彦","tag":"自衛官の処遇","vkey":"国民民主",
  "point":"自衛官の処遇改善など現場重視で、防衛力強化に積極的。",
  "quote":"この間、いろいろなことが進みました。自衛官の処遇",
  "url":"https://kokkai.ndl.go.jp/txt/121703815X01120250612/38"},
 {"party":"公明党","who":"浜地雅一","tag":"9条との整合","vkey":"公明党",
  "point":"憲法9条と自衛隊の整合を重視しつつ、現実的な防衛政策を志向。",
  "quote":"この議論の出発点は、九条二項に戦力の不保持、交戦権の否認とある",
  "url":"https://kokkai.ndl.go.jp/txt/121704183X00820250605/10"},
 {"party":"日本共産党","who":"本村伸子","tag":"軍拡に反対","vkey":"日本共産党",
  "point":"大幅な軍事費増に反対し、防衛費拡大と財政規律の整合を問う。",
  "quote":"八兆七千億円の軍事費が計上されておりますけれども、軍事費と放漫財政の問題、財政規律の問題について…",
  "url":"https://kokkai.ndl.go.jp/txt/121705262X00120250225/103"},
 {"party":"参政党","who":"神谷宗幣","tag":"対米依存の見直し","vkey":None,
  "point":"対米依存の見直しと自主防衛、危機時の財源(財政規律)の観点を提起。",
  "quote":"アメリカはもはやヨーロッパの安全保障の主な保証人であるべきではないと主張した",
  "url":"https://kokkai.ndl.go.jp/txt/121714370X00220250313/179"},
]

# ---------- 社会保障（年金改革が主戦場。参政党は当会期の代表発言・会派別採決が乏しく掲載見送り） ----------
SOCIAL = [
 {"party":"自由民主党","who":"山田宏","tag":None,"vkey":"自由民主党",
  "point":"年金制度の機能強化(被用者保険の適用拡大・基礎年金の底上げ)を与党として推進。",
  "quote":"いよいよこの大事な年金改革法案も審議が大分進んでまいりました。",
  "url":"https://kokkai.ndl.go.jp/txt/121714260X02120250612/7"},
 {"party":"立憲民主党","who":"宗野創","tag":"年金底上げに賛成","vkey":"立憲民主",
  "point":"自公と修正合意し年金改革に賛成。基礎年金の底上げと現役世代の年金水準確保を重視。",
  "quote":"厚生年金を含めた基礎年金の底上げ、ここがポイントだと思います。…現役世代の年金水準を確保する",
  "url":"https://kokkai.ndl.go.jp/txt/121704260X02620250618/8"},
 {"party":"公明党","who":"新妻秀規","tag":"三党修正合意","vkey":"公明党",
  "point":"自民・立憲・公明の三党修正合意を主導。底上げ財源(厚生年金積立金の活用)の透明性を問う。",
  "quote":"自民党、立憲民主党、公明党の三党の修正合意に基づいて、附則に…",
  "url":"https://kokkai.ndl.go.jp/txt/121714260X02120250612/200"},
 {"party":"日本維新の会","who":"猪瀬直樹","tag":"抜本改革を要求","vkey":"日本維新の会",
  "point":"社会保障費の抜本改革が不十分として年金改革法に反対。",
  "quote":"年金法改正案について、反対の立場で討論いたします。…医療、年金を始めとした社会保障費(の…)",
  "url":"https://kokkai.ndl.go.jp/txt/121715254X02720250613/32"},
 {"party":"国民民主党","who":"田村まみ","tag":"内容後退を批判","vkey":"国民民主",
  "point":"与党審査での改正内容の後退と提出遅延を批判し、年金改革法に反対。",
  "quote":"本案原案は、与党審査において改正内容を後退させた上に、提出を二か月も遅らせた…",
  "url":"https://kokkai.ndl.go.jp/txt/121715254X02720250613/36"},
 {"party":"日本共産党","who":"倉林明子","tag":"給付抑制に反対","vkey":"日本共産党",
  "point":"マクロ経済スライドによる給付抑制が年金生活者の困窮に背を向けるとして反対。",
  "quote":"多くの年金生活者の今の困窮に背を向けてマクロ経済スライドを(継続する)…",
  "url":"https://kokkai.ndl.go.jp/txt/121715254X02720250613/38"},
 {"party":"れいわ新選組","who":"天畠大輔","tag":"底上げ不十分","vkey":"れいわ",
  "point":"給付水準の実態(生活困窮)を問題視し年金改革法に反対。障害年金の社会モデルも主張。",
  "quote":"人権を軽視し、庶民を欺く年金議論は許せません。…反対の立場から討論いたします。",
  "url":"https://kokkai.ndl.go.jp/txt/121714260X02120250612/246"},
]

# ---------- エネルギー・環境 ----------
ENERGY = [
 {"party":"自由民主党","who":"梶原大介","tag":None,"vkey":"自由民主党",
  "point":"環境アセスの効率化と再エネの地域理解を重視し、関連法改正を与党として推進。",
  "quote":"環境影響評価法の一部を改正する法律案について順次質問を…我が国の環境影響評価制度、いわゆるアセス制度",
  "url":"https://kokkai.ndl.go.jp/txt/121714006X00920250612/5"},
 {"party":"立憲民主党","who":"岡田克也","tag":"カーボンプライシング","vkey":"立憲民主",
  "point":"カーボンプライシングを通じ、省エネ・再エネ投資と経済成長の両立を主張。",
  "quote":"カーボンプライシング、そのことによって、省エネルギー…再生可能エネルギーの導入…設備投資も進み",
  "url":"https://kokkai.ndl.go.jp/txt/121704080X01420250514/69"},
 {"party":"れいわ新選組","who":"上村英明","tag":"100%再エネ","vkey":"れいわ",
  "point":"2050年までに電力を全て再生可能エネルギーで賄うことを公約に掲げ、原発に反対。",
  "quote":"二〇五〇年までのできるだけ早い時期にエネルギー供給を全て再生可能エネルギーで賄うことを公約に掲げている",
  "url":"https://kokkai.ndl.go.jp/txt/121704889X02520250530/44"},
 {"party":"日本維新の会","who":"藤巻健太","tag":"安定供給重視","vkey":"日本維新の会",
  "point":"再エネ推進と、安価で安定的な電力供給の両立の難しさを指摘する現実重視の立場。",
  "quote":"安価で安定的な電力供給、これと並立するのは今の技術で見るとなかなか難しい側面も否めない",
  "url":"https://kokkai.ndl.go.jp/txt/121703895X00520250613/43"},
 {"party":"国民民主党","who":"丹野みどり","tag":None,"vkey":"国民民主",
  "point":"水素・蓄電池など再エネの基盤技術と、現実的な電源確保を重視。",
  "quote":"今日は水素を取り上げます。",
  "url":"https://kokkai.ndl.go.jp/txt/121704080X01820250604/151"},
 {"party":"公明党","who":"山口良治","tag":None,"vkey":"公明党",
  "point":"第7次エネルギー基本計画を踏まえ、地熱など多様な再エネの拡大を志向。",
  "quote":"今回の七次エネルギー基本計画では、我が国は…（地熱発電について）",
  "url":"https://kokkai.ndl.go.jp/txt/121704080X01820250604/179"},
 {"party":"日本共産党","who":"田村貴昭","tag":"脱・化石燃料","vkey":"日本共産党",
  "point":"化石燃料依存からの脱却と省エネ・再エネ転換を主張、その場しのぎの補助を批判。",
  "quote":"その場しのぎの補助に巨費を投じるのではなくて、省エネや再生可能エネルギーへの転換に急いで(進む)",
  "url":"https://kokkai.ndl.go.jp/txt/121704376X02720250620/228"},
 {"party":"参政党","who":"北野裕子","tag":"脱炭素に懐疑的","vkey":None,
  "point":"脱炭素目標(パリ協定/IPCC)を懐疑的に検証し、太陽光パネル拡大の安全保障リスクを問題視。",
  "quote":"政府の方針により、これからますます太陽光パネルが増えていくんです。",
  "url":"https://kokkai.ndl.go.jp/txt/121704006X01020250603/225"},
]

# ---------- 経済・産業（賃上げ・価格転嫁・中小企業が主戦場） ----------
ECON = [
 {"party":"自由民主党","who":"田中昌史","tag":None,"vkey":"自由民主党",
  "point":"省力化投資と生産性向上を通じた持続的な賃上げを重視(与党)。",
  "quote":"先ほど、今、省力化から賃上げというお話がございました。実際にどういうふうになっていくのか…",
  "url":"https://kokkai.ndl.go.jp/txt/121714080X01320250605/27"},
 {"party":"立憲民主党","who":"村田享子","tag":"価格転嫁","vkey":"立憲民主",
  "point":"改正下請法での労務費の価格転嫁を重視し、中小企業の賃上げ原資の確保を求める。",
  "quote":"改正下請法であっても、価格転嫁が大事…労務費の価格転嫁の指針を政府の方で出していただいて",
  "url":"https://kokkai.ndl.go.jp/txt/121714080X01320250605/115"},
 {"party":"れいわ新選組","who":"高井崇志","tag":"消費税廃止","vkey":"れいわ",
  "point":"結党以来一貫して消費税廃止を主張し、需要喚起による経済底上げを掲げる。",
  "quote":"れいわ新選組は、結党以来一貫して消費税廃止を訴えてきました。…今や全ての野党が消費税減税を公約に",
  "url":"https://kokkai.ndl.go.jp/txt/121705261X02220250512/150"},
 {"party":"日本維新の会","who":"池下卓","tag":"リスキリング","vkey":"日本維新の会",
  "point":"氷河期世代への支援やリスキリングなど、労働市場改革を重視。",
  "quote":"これからの賃上げ対策であったりとかリスキリング、あと就職機会、これをしっかり支援されていく…",
  "url":"https://kokkai.ndl.go.jp/txt/121704260X01920250521/211"},
 {"party":"国民民主党","who":"玉木雄一郎","tag":"手取りを増やす","vkey":"国民民主",
  "point":"「賃上げより手取り」を掲げ、税収の上振れ分の国民還元を主張。",
  "quote":"税収の上振れがあったときは、その上振れた税収は、自民党のものでも公明党のものでもない…一生懸命働いている国民の",
  "url":"https://kokkai.ndl.go.jp/txt/121724293X00320250611/36"},
 {"party":"公明党","who":"安江伸夫","tag":None,"vkey":"公明党",
  "point":"建設業など現場の技能者の処遇改善・賃上げを重視。",
  "quote":"建設業における技能者の皆様の処遇の改善に関してお伺いをしたい…",
  "url":"https://kokkai.ndl.go.jp/txt/121714319X01920250612/92"},
 {"party":"日本共産党","who":"小池晃","tag":"公的分野の賃上げ","vkey":"日本共産党",
  "point":"医療・介護など公的分野の確実な賃上げを求め、歳出改革頼みの手法を批判。",
  "quote":"医療、介護の賃上げは喫緊の課題…歳出改革努力によって生み出すという話じゃないですか。",
  "url":"https://kokkai.ndl.go.jp/txt/121714370X01820250612/93"},
 {"party":"参政党","who":"神谷宗幣","tag":"インボイス廃止","vkey":None,
  "point":"減税やインボイス廃止による生産性向上を主張し、政府の「賃上げ起点」路線に疑問。",
  "quote":"野党が求める減税政策での手取り増を否定し、賃上げを起点とし(た骨太の方針)…",
  "url":"https://kokkai.ndl.go.jp/txt/121714370X01720250610/96"},
]

# ---------- 憲法（憲法審査会は討議中心＝記名投票の議案なし→「言のみ」。参政党は当審査会に発言なく掲載見送り） ----------
KENPO = [
 {"party":"自由民主党","who":"船田元","tag":"任期延長改憲を主導",
  "point":"選挙困難事態に備えた議員任期の延長など、緊急事態条項の改憲を主導。",
  "quote":"選挙困難事態があるということ、そして、その際は議員任期を延長するということ自体は合意をいたしております",
  "url":"https://kokkai.ndl.go.jp/txt/121704183X00920250612/14"},
 {"party":"立憲民主党","who":"五十嵐えり","tag":"任期延長に慎重",
  "point":"任期延長改憲の立法事実(選挙の一体性)の議論が不十分と批判し、拙速な条文化に慎重。",
  "quote":"任期延長の主張の根幹たる選挙の一体性についてはほぼ議論がなされず、全く理解(できない)",
  "url":"https://kokkai.ndl.go.jp/txt/121704183X00920250612/24"},
 {"party":"れいわ新選組","who":"山本太郎","tag":"改憲に反対",
  "point":"国民投票法のCM・広告規制の不備を突き、緊急事態条項など改憲の動きに強く反対。",
  "quote":"現在の国民投票法には広告宣伝活動に対する明確な規制がほとんどなく、極めて不備が多いということ",
  "url":"https://kokkai.ndl.go.jp/txt/121714183X00620250618/14"},
 {"party":"日本維新の会","who":"馬場伸幸","tag":"改憲議論の加速",
  "point":"自由討議からの脱却と、条文起草など具体的な改憲論議の加速を要求。",
  "quote":"相も変わらぬ自由討議というお題目の下、各会派による放談会から脱却できていない",
  "url":"https://kokkai.ndl.go.jp/txt/121704183X00920250612/6"},
 {"party":"国民民主党","who":"川合孝典","tag":"デジタル人権",
  "point":"デジタル時代の人権保障(AIと思想・良心の自由)の観点から、憲法論議を提起。",
  "quote":"ＡＩの普及は、既に個人の思想や良心の形成過程に影響を及ぼしており(人権保障の見直しが必要)",
  "url":"https://kokkai.ndl.go.jp/txt/121714183X00620250618/10"},
 {"party":"公明党","who":"河西宏一","tag":"国民投票法",
  "point":"国民投票法改正(CM規制など三項目)を推進し、丁寧な合意形成を重視。",
  "quote":"令和四年に我が党を含む四会派が提出をした国民投票法改正案、いわゆる三項目案",
  "url":"https://kokkai.ndl.go.jp/txt/121704183X00920250612/10"},
 {"party":"日本共産党","who":"赤嶺政賢","tag":"改憲に反対",
  "point":"改憲のための議論そのものに反対。国民の多くは改憲を求めていないと主張。",
  "quote":"憲法審査会で改憲のための議論はやるべきではない…国民の多くが改憲を求めていないから",
  "url":"https://kokkai.ndl.go.jp/txt/121704183X00920250612/16"},
]

DOMAINS = [("財政", True), ("外交・安保", True), ("社会保障", True),
           ("エネルギー・環境", True), ("憲法", True), ("経済・産業", True)]
domtabs = "".join(
    f'<button class="dtab{" on" if i==0 else ""}" data-d="{i}"{"" if live else " disabled"}>'
    f'{esc(name)}{"" if live else " ·準備中"}</button>'
    for i, (name, live) in enumerate(DOMAINS))

fiscal_cards = cards_html(FISCAL, FVOTES, FLABEL)
diplo_cards = cards_html(DIPLO, DVOTES, DLABEL)
social_cards = cards_html(SOCIAL, SVOTES, SLABEL)
energy_cards = cards_html(ENERGY, EVOTES, ELABEL)
econ_cards = cards_html(ECON, CVOTES, CLABEL)
kenpo_cards = cards_html(KENPO, None, None)

HTML = f'''<title>政策くらべ — 言と行（比例区）v1.0</title>
<style>
:root{{ --paper:#f3f4f7; --card:#fbfbfd; --ink:#1b2130; --muted:#5c6675; --line:#dcdfe6;
  --accent:#3a4d8f; --accent-soft:#e6e9f4; --answer:#9aa3b2;
  --shadow:0 1px 2px rgba(20,28,50,.05),0 8px 24px rgba(20,28,50,.05); }}
@media (prefers-color-scheme:dark){{ :root{{ --paper:#12151d; --card:#191d27; --ink:#e7eaf1;
  --muted:#98a1b2; --line:#282e3b; --accent:#8ea2e6; --accent-soft:#222a40; --answer:#5c6473;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35); }} }}
:root[data-theme="dark"]{{ --paper:#12151d; --card:#191d27; --ink:#e7eaf1; --muted:#98a1b2;
  --line:#282e3b; --accent:#8ea2e6; --accent-soft:#222a40; --answer:#5c6473;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35); }}
:root[data-theme="light"]{{ --paper:#f3f4f7; --card:#fbfbfd; --ink:#1b2130; --muted:#5c6675;
  --line:#dcdfe6; --accent:#3a4d8f; --accent-soft:#e6e9f4; --answer:#9aa3b2;
  --shadow:0 1px 2px rgba(20,28,50,.05),0 8px 24px rgba(20,28,50,.05); }}
*{{ box-sizing:border-box; }}
.wrap{{ --serif:"Hiragino Mincho ProN","Yu Mincho",YuMincho,"Noto Serif JP",serif;
  --sans:"Hiragino Kaku Gothic ProN","Yu Gothic",YuGothic,"Noto Sans JP",Meiryo,sans-serif;
  --mono:ui-monospace,"SF Mono",Menlo,Consolas,monospace;
  background:var(--paper); color:var(--ink); font-family:var(--sans); line-height:1.7;
  -webkit-font-smoothing:antialiased; padding:clamp(20px,5vw,56px) clamp(16px,5vw,40px); }}
.doc{{ max-width:920px; margin:0 auto; }}
.eyebrow{{ font-family:var(--mono); font-size:12px; letter-spacing:.16em; text-transform:uppercase;
  color:var(--accent); margin:0 0 12px; }}
h1{{ font-family:var(--serif); font-weight:600; font-size:clamp(24px,4.4vw,38px); line-height:1.3;
  text-wrap:balance; margin:0 0 14px; }}
.lede{{ color:var(--muted); font-size:15px; max-width:62ch; margin:0; }}
.lede b{{ color:var(--ink); }}
.entries{{ display:grid; grid-template-columns:1fr 1fr; gap:14px; margin:28px 0 8px; }}
@media (max-width:600px){{ .entries{{ grid-template-columns:1fr; }} }}
.entry{{ text-align:left; font:inherit; cursor:pointer; background:var(--card);
  border:1.5px solid var(--line); border-radius:14px; padding:18px 20px; color:inherit; }}
.entry.on{{ border-color:var(--accent); box-shadow:var(--shadow); }}
.entry .k{{ font-family:var(--mono); font-size:11px; letter-spacing:.12em; color:var(--accent);
  text-transform:uppercase; }}
.entry .t{{ font-family:var(--serif); font-size:20px; font-weight:600; margin:6px 0 3px; }}
.entry .s{{ font-size:12.5px; color:var(--muted); }}
.entry:disabled{{ opacity:.55; cursor:not-allowed; }}
.entry .soon{{ font-family:var(--mono); font-size:10.5px; border:1px solid var(--line);
  border-radius:20px; padding:2px 8px; color:var(--muted); float:right; }}
.rule{{ height:1px; background:var(--line); border:0; margin:26px 0; }}
.dtabs{{ display:flex; flex-wrap:wrap; gap:8px; margin:6px 0 22px; }}
.dtab{{ font:inherit; font-size:13.5px; cursor:pointer; background:transparent; color:var(--muted);
  border:1px solid var(--line); border-radius:22px; padding:7px 15px; transition:.15s; }}
.dtab.on{{ background:var(--accent); color:#fff; border-color:var(--accent); font-weight:600; }}
.dtab:not(.on):not(:disabled):hover{{ border-color:var(--accent); color:var(--ink); }}
.dtab:disabled{{ opacity:.5; cursor:not-allowed; }}
.axis{{ background:var(--accent-soft); border-radius:12px; padding:14px 18px; margin-bottom:16px;
  font-size:13.5px; color:var(--ink); }}
.axis b{{ font-family:var(--serif); }}
.axis .flow{{ display:flex; align-items:center; gap:10px; margin-top:8px; font-family:var(--mono);
  font-size:12px; color:var(--muted); }}
.axis .flow span{{ flex:0 0 auto; }} .axis .flow hr{{ flex:1; height:1px; background:var(--answer); border:0; }}
.callout{{ background:var(--card); border:1px solid var(--line); border-left:3px solid var(--accent);
  border-radius:0 10px 10px 0; padding:13px 16px; margin-bottom:20px; font-size:13px;
  line-height:1.8; color:var(--muted); }}
.callout b{{ color:var(--ink); }}
.grid{{ display:grid; grid-template-columns:1fr 1fr; gap:14px; }}
@media (max-width:640px){{ .grid{{ grid-template-columns:1fr; }} }}
.pcard{{ background:var(--card); border:1px solid var(--line); border-radius:14px; padding:18px 20px;
  box-shadow:var(--shadow); display:flex; flex-direction:column; gap:10px; }}
.pcard header{{ display:flex; align-items:center; justify-content:space-between; gap:10px; }}
.pcard h3{{ font-family:var(--serif); font-size:18px; font-weight:600; margin:0; }}
.tag{{ font-family:var(--sans); font-size:11.5px; font-weight:600; color:var(--accent);
  background:var(--accent-soft); border-radius:20px; padding:3px 10px; white-space:nowrap; }}
.point{{ font-size:13.5px; margin:0; }}
.lbl{{ display:inline-block; font-family:var(--mono); font-size:10px; letter-spacing:.08em;
  color:var(--muted); border:1px solid var(--line); border-radius:5px; padding:1px 6px; margin-right:8px;
  vertical-align:1px; }}
blockquote{{ margin:0; padding:11px 14px; border-left:3px solid var(--accent); background:var(--paper);
  border-radius:0 8px 8px 0; font-size:13.5px; line-height:1.75; }}
blockquote cite{{ display:block; font-style:normal; font-family:var(--mono); font-size:11px;
  color:var(--muted); margin-top:6px; }}
blockquote .evq{{ font-family:var(--mono); font-size:11px; color:var(--accent); text-decoration:none;
  margin-left:8px; white-space:nowrap; }}
blockquote .evq:hover{{ text-decoration:underline; }}
.votes{{ margin-top:auto; padding-top:12px; border-top:1px dashed var(--line); }}
.vlbl{{ display:block; font-family:var(--mono); font-size:10px; letter-spacing:.08em;
  color:var(--muted); margin-bottom:8px; }}
.vrow{{ display:flex; flex-wrap:wrap; gap:6px; }}
.vchip{{ display:inline-flex; flex-direction:column; align-items:center; gap:1px;
  font-size:10.5px; color:var(--muted); text-decoration:none; border:1px solid var(--line);
  border-radius:8px; padding:5px 9px; line-height:1.3; }}
.vchip b{{ font-size:12px; font-weight:700; }}
.vchip.yes{{ color:#2f8f7f; border-color:#2f8f7f66; background:#2f8f7f18; }}
.vchip.yes b{{ color:#2f8f7f; }}
.vchip.no{{ color:#c1704f; border-color:#c1704f66; background:#c1704f18; }}
.vchip.no b{{ color:#c1704f; }}
.vchip.na b{{ color:var(--muted); }}
.vna{{ font-size:12px; color:var(--muted); }}
.note{{ margin-top:26px; font-size:12.5px; color:var(--muted); line-height:1.9; }}
.note b{{ color:var(--ink); }}
a.src{{ color:var(--accent); text-decoration:none; }} a.src:hover{{ text-decoration:underline; }}
:focus-visible{{ outline:2px solid var(--accent); outline-offset:2px; border-radius:4px; }}
</style>

<div class="wrap"><div class="doc">
  <p class="eyebrow">比例区・投票ガイド ／ v1.0「言と行」</p>
  <h1>言っていること（言）と、投票したこと（行）を、並べて見る</h1>
  <p class="lede">知名度でなく中身で選ぶための道具。各党が国会で<b>何を論じ（言）</b>、
  実際の議案に<b>どう賛否を投じたか（行）</b>を領域ごとに並べます。一致か乖離かは判定せず、
  <b>点数も格付けもしません</b>。発言も採決も全て原典リンク付き。</p>

  <div class="entries">
    <button class="entry on" disabled>
      <span class="k">入口 1 ／ Proportional</span>
      <div class="t">比例区で選ぶ<span class="soon">実装中</span></div>
      <div class="s">政党の政策を領域別にくらべる（このページ）</div>
    </button>
    <button class="entry" disabled>
      <span class="k">入口 2 ／ District</span>
      <div class="t">小選挙区で選ぶ<span class="soon">準備中</span></div>
      <div class="s">自分の選挙区の候補者を同じ形でくらべる（次段階）</div>
    </button>
  </div>

  <hr class="rule">
  <div class="dtabs">{domtabs}</div>

  <section class="pane" data-pane="0">
    <div class="axis"><b>財政の対立軸</b>（どちらが正しいという評価はしません）
      <div class="flow"><span>財政健全化・PB黒字化を優先</span><hr><span>積極財政・減税を優先</span></div></div>
    <div class="callout"><b>「行」の読み方：</b>予算そのものへの賛否は政策の中身より
      <b>与党・野党の立場</b>を強く映します。むしろ党の線が割れる法案に情報がある——
      <b>特別会計法改正では維新が反対（与党側から離脱）、国民が賛成（野党側から離脱）</b>。</div>
    <div class="grid">{fiscal_cards}</div>
  </section>

  <section class="pane" data-pane="1" hidden>
    <div class="axis"><b>外交・安保の対立軸</b>（どちらが正しいという評価はしません）
      <div class="flow"><span>防衛力強化・日米同盟の深化</span><hr><span>非軍事・外交と対米自立</span></div></div>
    <div class="callout"><b>財政とは対立軸が変わります：</b>防衛3法案は
      <b>立憲・国民・維新まで与党と同じ賛成</b>で合意が広く、反対はれいわ・共産・沖縄の風のみ。
      北朝鮮制裁の承認では<b>共産も賛成し、反対はれいわと沖縄の風だけ</b>。
      同じ党でも領域が変われば位置が変わる——だから領域別に見る意味があります。</div>
    <div class="grid">{diplo_cards}</div>
  </section>

  <section class="pane" data-pane="2" hidden>
    <div class="axis"><b>社会保障の対立軸</b>（どちらが正しいという評価はしません）
      <div class="flow"><span>給付水準の維持・拡充</span><hr><span>制度の持続性・給付の抑制</span></div></div>
    <div class="callout"><b>また別の組み替えが起きます：</b>年金制度改革法では
      <b>立憲が賛成（自民・公明と三党修正合意）、維新と国民が反対</b>。財政でも外交でもない三つ目の分かれ方。
      一方、児童福祉・薬機・労働の各法案は<b>共産・れいわのみ反対</b>で他は賛成。争点ごとに地図が変わります。
      <br><span style="font-size:11.5px">※参政党は当会期の社会保障分野で会派としての代表発言・会派別採決が乏しく、今回は掲載を見送りました。</span></div>
    <div class="grid">{social_cards}</div>
  </section>

  <section class="pane" data-pane="3" hidden>
    <div class="axis"><b>エネルギー・環境の対立軸</b>（どちらが正しいという評価はしません）
      <div class="flow"><span>脱炭素・再エネ拡大を優先</span><hr><span>安定供給・コスト・国産化を優先</span></div></div>
    <div class="callout"><b>合意と対立が混在します：</b>洋上風力(海洋再エネ)法は
      <b>235対1でほぼ全会一致</b>（共産・れいわも賛成）——再エネ拡大は超党派の合意。
      一方、物価高騰対策予備費では<b>立憲・維新が反対、国民が賛成</b>と、支出への賛否でまた線が割れます。</div>
    <div class="grid">{energy_cards}</div>
  </section>

  <section class="pane" data-pane="4" hidden>
    <div class="axis"><b>憲法の対立軸</b>（どちらが正しいという評価はしません）
      <div class="flow"><span>改憲を進める（任期延長・緊急事態条項）</span><hr><span>改憲に慎重・反対</span></div></div>
    <div class="callout"><b>この領域だけ「言のみ」です：</b>憲法審査会は
      <b>討議・意見表明の場</b>で、本会議の記名投票にかかる議案がありません。よって各党の「行(採決)」は
      <b>該当なし</b>と明示し、憲法審査会での発言(言)だけを並べます。争点は議員任期延長・緊急事態条項・国民投票法など。
      <br><span style="font-size:11.5px">※参政党は当会期の憲法審査会で発言が確認できず、掲載を見送りました。</span></div>
    <div class="grid">{kenpo_cards}</div>
  </section>

  <section class="pane" data-pane="5" hidden>
    <div class="axis"><b>経済・産業の対立軸</b>（どちらが正しいという評価はしません）
      <div class="flow"><span>賃上げ・投資促進を起点に</span><hr><span>減税・手取り増を起点に</span></div></div>
    <div class="callout"><b>ここも合意と対立が混在：</b>下請法・保険業法の改正は
      <b>227〜228対数票でほぼ全会一致</b>（共産・れいわも賛成）——中小企業保護は超党派の合意。
      一方、日本政策投資銀行法では<b>立憲が反対</b>（国民・維新は賛成）と線が割れます。</div>
    <div class="grid">{econ_cards}</div>
  </section>

  <section class="pane" data-pane="soon" hidden>
    <div class="callout" style="text-align:center; border-left:0; border:1px dashed var(--line);">
      この領域は準備中です。財政・外交と同じ形式（各党の国会発言＋参院採決＋証拠リンク）で順次追加します。</div>
  </section>

  <p class="note">
    <b>データの出どころ：</b>「言」＝<a class="src" href="https://kokkai.ndl.go.jp/" target="_blank" rel="noopener">国会会議録検索システム（国立国会図書館）</a>第217回国会の発言原文。
    「行」＝<a class="src" href="https://www.sangiin.go.jp/japanese/touhyoulist/217/vote_ind.htm" target="_blank" rel="noopener">参議院 本会議投票結果（記名投票の会派別賛否）</a>。<br>
    <b>正直な断り：</b>①「力点」は<b>編集要約</b>で党の公式見解そのものではない（個々の議員の発言に基づく）。②「行」は<b>参議院のみ</b>（衆院は個人別の賛否が記録に残らない）。③<b>参政党は当時会派未結成</b>のため会派別の賛否データがありません。<br>
    <b>次段階：</b>①衆院の記名投票分の補完　②衆院の記名投票分の補完　③小選挙区（候補者）版。
  </p>
</div></div>

<script>
(function(){{
  var tabs=document.querySelectorAll('.dtab');
  var panes=document.querySelectorAll('.pane');
  tabs.forEach(function(t){{
    t.addEventListener('click',function(){{
      if(t.disabled) return;
      tabs.forEach(function(x){{x.classList.remove('on');}});
      t.classList.add('on');
      var d=t.dataset.d;
      var has=document.querySelector('.pane[data-pane="'+d+'"]');
      var target=has?d:'soon';
      panes.forEach(function(p){{ p.hidden=(p.dataset.pane!==target); }});
    }});
  }});
}})();
</script>'''

open("policy_guide.html", "w", encoding="utf-8").write(HTML)
print("wrote policy_guide.html", len(HTML), "bytes")
