# A. 投票支援ツール(VAA)の先行研究

調査日: 2026-07-21 / 担当A
方針: WebSearch・WebFetchで実際に確認できた情報のみを本文に記載。確認できなかったものは「6. 未確認・要追跡」に隔離した。

---

## 1. 主要な実例

### 1-1. オランダ StemWijzer（1989年〜、Web版1998年〜）
- 運営: ProDemos（民主主義・法の支配のための家、公的資金を受ける非営利機関）。
- 形式: 30程度のステートメントに「賛成／反対／どちらでもない」で回答させ、政党との一致度を**ランキング**として表示。ユーザー回答は二値的。
- 政党の立場の決定: 選挙公約（マニフェスト）と、政党自身によるステートメントへの回答の両方に基づく。
- 規模: 2012年オランダ総選挙前に400万人以上が利用。
- URL: https://en.wikipedia.org/wiki/StemWijzer / https://www.nporadio2.nl/nieuws/npo-radio-2/8c566438-9a2e-40c1-94a1-d655c26ca4b7/wat-is-het-verschil-tussen-kieskompas-en-stemwijzer

### 1-2. オランダ Kieskompas（対抗する設計思想）
- 開発者: André Krouwel（アムステルダム自由大学の政治学者）。投票行動・政党ポジショニングの学術研究を土台にしている。
- 形式: 30ステートメント、ユーザー回答は**5件法リッカート尺度**。結果は「社会経済（左右）」×「社会文化（進歩/保守）」の**2次元空間上の位置**として提示され、ランキング（％の一致度）を出さない。
- 政党の立場の決定: マニフェストと政党の回答。**協力を拒否した政党については、Kieskompas側が立場を決定する**（＝自己申告が得られない場合の専門家コーディングへの依存）。
- URL: https://en.wikipedia.org/wiki/Kieskompas / https://www.nporadio2.nl/nieuws/npo-radio-2/8c566438-9a2e-40c1-94a1-d655c26ca4b7/wat-is-het-verschil-tussen-kieskompas-en-stemwijzer

> StemWijzer と Kieskompas は同じ国・同じ選挙で並存しており、「同じ有権者が両方を使うと違う答えが出る」ことが公然の前提になっている。これは後述の「アルゴリズム/空間モデルの恣意性」の実地デモンストレーションになっている。

### 1-3. ドイツ Wahl-O-Mat（2002年〜）
- 運営: 連邦政治教育センター（Bundeszentrale für politische Bildung, bpb）および各州の政治教育センター。**国家の政治教育機関が運営**している点が特徴。
- 設問作成プロセス（公開されている）:
  1. 若年有権者・学界/ジャーナリズム/教育の専門家・bpb（または州センター）担当者からなる編集チームを組成。
  2. 各党のマニフェストとメディア発言の分析から、まず80〜100件のステートメント案を作成。
  3. **すべての立候補政党に全案を提示し、各党が「賛成／反対／中立」で回答**、500字以内の理由説明を付す。
  4. 各党の回答が出そろった後、論点をよく反映する**38件**に絞り込む。
- ユーザーは同じ38ステートメントに回答し、％の一致度を得る。
- 規模: 2002年の開始以来のべ5000万人超が利用。2017年連邦議会選挙前だけで1500万人。
- URL: https://www.wahl-o-mat.de/ / https://de.wikipedia.org/wiki/Wahl-O-Mat / https://www.deutschland.de/en/topic/politics/wahl-o-mat-bundestag-election-election-manifesto-parties

### 1-4. スイス smartvote（2003年〜）
- 運営: Politools（ベルンに拠点を置く登録団体。政治的に中立で特定宗派に属さないと自称）。
- 政党/候補者の立場の決定: **候補者本人がsmartvoteの質問票に回答する**（自己申告方式）。質問票は多数の利益団体・市民社会組織・複数メディアのジャーナリストに諮った上でPolitoolsが設計。
- 結果表示: 「smartspider」（8軸のレーダーチャート、各軸は2〜4問から0〜100点で算出。複数軸に割り当てられる設問も、どの軸にも割り当てない設問もある）と「smartmap」。
- 一致度アルゴリズム: **ユークリッド距離**ベース。
- 国際展開: smartvote International（ルクセンブルク smartwielen 等）。
- URL: https://smartvote.org/ / https://politools.net/en/projects-services/smartvote/ / https://demo.smartvote.org/de/wiki/demo-methodology / https://en.wikipedia.org/wiki/Smartvote

### 1-5. フィンランド Vaalikone（1996年〜）
- Yle（公共放送）の Vaalikone が1996年に初登場。現在は Helsingin Sanomat をはじめ多数の新聞社が独自版を運営（vaalikone.fi）。
- Yle版は、Suomen Kuvalehti, Landbygdens Folk, Åbo Underrättelser, Maaseudun Tulevaisuus, Bonnier News Finland, Kotiseudun Sanomat 等の提携媒体に、Yleの設問をベースにしたカスタム版を提供している。
- URL: https://yle.fi/a/74-20020699 / https://www.vaalikone.fi/

### 1-6. EU横断 EU Profiler / euandi（2009, 2014, 2019, 2024）
- 運営: 欧州大学院大学（EUI）。Alexander H. Trechsel が主導。
- 政党の立場の決定: **政党の自己申告（self-placement）と専門家コーディングを組み合わせる「反復的(iterative)手法」**。両手法の長所を活かし短所を相殺することを明示的に狙った設計。選挙期間中に政党本体とやりとりしながら、エビデンスに基づく専門家コーディングを修正していく。
- データ公開: 2009-2019の3波で28カ国411政党、2万超の政党ポジションを収録した縦断データセットが公開されている。
- URL: https://euandi.eu/en/data-research.html / https://europeangovernanceandpolitics.eui.eu/project/research-and-impact-through-european-wide-and-national-voting-advice-applications-euandi/ / https://pubmed.ncbi.nlm.nih.gov/32671164/
- 関連文献: Garzia, D., Trechsel, A., De Sio, L. (2017) "Party placement in supranational elections", *Party Politics*. https://doi.org/10.1177/1354068815593456

### 1-7. 日本 JAPAN CHOICE（NPO法人Mielka）
- 運営: NPO法人Mielka。同団体サイトには「2016年に発足」と記載（別の記事では2014年設立との記述もあり不一致。要確認）。「政治×テクノロジー×教育」を軸に、教育事業・エンタメ事業・ラボ事業の3部門で活動。国政選挙向けが JAPAN CHOICE、地方選挙向けが LOCAL VOTE。
- 機能: 投票ナビ（意見の近い政党とのマッチング）、政策比較、世論を追う、選挙クイズ、データダウンロード等。
- 資金: JAPAN CHOICE の開発ではクラウドファンディング（CAMPFIRE）を実施。公開された予算内訳は機材費約100万円、人件費約300万円、広報費約10万円、サービス手数料約45万円（9%＋税）。
- 注意: サイトのトップページからは**マッチングの算出方法や政党ポジションの決定手順の記載を確認できなかった**（運営団体ページへのリンクはあるが本文未取得）。
- URL: https://japanchoice.jp/ / https://mielka.org/ / https://camp-fire.jp/projects/486286/view / https://prtimes.jp/main/html/rd/p/000000006.000029162.html

### 1-8. 日本 毎日新聞「えらぼーと」
- 運営: 毎日新聞社（商業メディア）。
- 形式: 政策に関する**25問**に答えると、立候補者・政党との「一致度」が数値で出る。
- 立場の決定: **毎日新聞が事前に立候補者に実施した政策アンケートの回答**を基礎データにする（＝候補者本人の自己申告）。
- 機能: 設問ごとに「重要度」で重み付けして絞り込める。候補者個人・選挙区・政党の各単位で一致度を見られる。
- URL: https://prtimes.jp/main/html/rd/p/000000668.000032749.html / https://x.com/mainichieravote

---

## 2. 効果の実証研究

### 2-1. メタ分析（最重要）
**Munzert, S., & Ramirez-Ruiz, S. (2021). "Meta-Analysis of the Effects of Voting Advice Applications." *Political Communication*, 38(6).**
- 9カ国・22研究・55効果量・参加者73,673名を統合。
- 投票参加（reported turnout）に対する正の効果に強いエビデンス: **OR = 1.87, 95%CI [1.50, 2.33]**
- 投票先（vote choice）への効果にも強いエビデンス: **OR = 1.44, 95%CI [1.16, 1.78]**
- 政治知識の増加には**穏当なエビデンスにとどまる**: partial correlation = 0.09, 95%CI [−0.01, 0.18]（信頼区間が0をまたぐ）
- 効果量の異質性が大きく、**その主要な駆動要因は研究デザインそのもの**であると報告している。＝観察研究と実験研究で結果が食い違う。
- URL: https://www.tandfonline.com/doi/abs/10.1080/10584609.2020.1843572 / https://opus4.kobv.de/opus4-hsog/frontdoor/index/index/year/2021/docId/3980

### 2-2. 投票率への効果
- **Gemenis, K., & Rosema, M. (2014). "Voting Advice Applications and electoral turnout." *Electoral Studies*, 36, 281-289. DOI: 10.1016/j.electstud.2014.06.010** — https://www.sciencedirect.com/science/article/abs/pii/S0261379414000742
- **Marschall, S., & Schultze, M. (2012)**: ドイツ2009年連邦議会選挙前のWahl-O-Mat利用が投票意思に効果を持つことを支持（ResearchGate掲載題名: "Voting Advice Applications and Their Effect on Voter Turnout: The Case of the German Wahl-O-Mat"）。掲載誌名は本調査では未確定（→6章）。 https://www.researchgate.net/publication/264815452
- 2009年ドイツWahl-O-Matの出口調査では、回答者の約7%が「使う前は投票する予定がなかったが、使ったことで投票した」と報告している。
- スイスsmartvote利用は個人レベルの投票確率を有意に上昇させた、オランダ2010年総選挙でStemWijzer利用が参加を有意に高めた、との報告がある（Oxford Research Encyclopedia の記述より）。
- スウェーデン・ヨーテボリ大学のレポート: "How Voting Advice Applications Affect Turnout" (Report 2024:6) — https://www.gu.se/sites/default/files/2024-12/R2024_6.pdf

### 2-3. 投票先の変更・政党選好への効果
**Germann, M., Mendez, F., & Gemenis, K. (2023). "Do Voting Advice Applications Affect Party Preferences? Evidence from Field Experiments in Five European Countries." *Political Communication*, 40(5), 596-614. DOI: 10.1080/10584609.2023.2181896**
- 5カ国でのフィールド実験。VAAが政党選好に与える影響を因果推論的に検証した数少ない研究。
- URL: https://www.tandfonline.com/doi/full/10.1080/10584609.2023.2181896

### 2-4. 政治知識・分極化
- ドイツWahl-O-Matの利用は**政党の立場に関する知識の高さと相関**する（Oxford Research Encyclopediaの記述）。
- 2023年スイス連邦議会選挙前後の2波パネル調査＋フィールド実験のデータからは、選挙期間中のVAA利用が**イデオロギー的分極・情緒的分極の低減に寄与しうる**という部分的なエビデンスが得られている（同上）。
- 逆方向の報告もある: Fröhle (2026) "From Swipes to Votes: The Role of the Voting Advice Application Voteswiper in Polarizing Voter Choices for the 2025 General Election in Germany", *Policy & Internet*. — https://onlinelibrary.wiley.com/doi/10.1002/poi3.70028（タイトルは「分極化させる(polarizing)」方向を示唆。本文未読、→6章）

### 2-5. レビュー論文
- **Garzia, D., & Marschall, S. (2019). "Voting Advice Applications." *Oxford Research Encyclopedia of Politics*. DOI: 10.1093/acrefore/9780190228637.013.620** — https://oxfordre.com/politics/view/10.1093/acrefore/9780190228637.001.0001/acrefore-9780190228637-e-620
- **Garzia, D., & Marschall, S. (2016). "Research on Voting Advice Applications: State of the Art and Future Directions." *Policy & Internet*, 8(4).** — https://onlinelibrary.wiley.com/doi/full/10.1002/poi3.140 （本文は有料。本調査では取得できず）
- **Rosema, M., Anderson, J., & Walgrave, S. (2014). "The design, purpose, and effects of voting advice applications." *Electoral Studies*, 36, 240-243. DOI: 10.1016/j.electstud.2014.04.003**（Electoral Studies の VAA特集号の巻頭）— https://medialibrary.uantwerpen.be/oldcontent/container2608/files/Rosema,%20Anderson,%20Walgrave%20-%20The%20design,%20purpose%20and%20effects%20of%20VAAs.pdf

---

## 3. 既知の批判と方法論的問題

### 3-1. 設問選択のバイアス（issue selection）
**Walgrave, S., Nuytemans, M., & Pepermans, K. (2009). "Voting Aid Applications and the Effect of Statement Selection." *West European Politics*, 32(6), 1161-1180. DOI: 10.1080/01402380903230637**
- **ステートメントの選択が、政党とユーザーの間で観測される一致度に深甚な影響を与える**ことを実証した。VAA批判の最も基礎的な文献。
- URL: https://medialibrary.uantwerpen.be/oldcontent/container2608/files/Walgrave%20et%20al%202009%20-%20voting%20aid%20applications.pdf

関連して、Gemenis (2024) は「どの政策ステートメントを含めるかの選択は、特定の政党をより頻繁にユーザーとマッチさせる形で有利にしうる」とし、現行の設問選択が**研究者の直観に依存しており、系統的・データ駆動的な手法になっていない**と指摘している。

### 3-2. 設問の文言・提示のしかた（wording / framing / polarity）
- **質問の極性（positive/negative wording）が回答を系統的に変える**: "Positive vs. Negative: The Impact of Question Polarity in Voting Advice Applications" — https://pmc.ncbi.nlm.nih.gov/articles/PMC5056712/
- **左派的／右派的な見出し（header）を付けるだけで報告される態度が変わる**: "Issue framing in online voting advice applications: The effect of left-wing and right-wing headers on reported attitudes", *PLOS ONE*, 2019. DOI: 10.1371/journal.pone.0212555 — https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0212555

### 3-3. 政党の立場を誰がどう決めるか（party positioning）
**Gemenis, K. (2013). "Estimating parties' policy positions through voting advice applications: Some methodological considerations." *Acta Politica*, 48, 268-295. DOI: 10.1057/ap.2012.36**
- VAAが政党ポジションを推定するために用いる手法についての知見が乏しいと指摘し、以下を系統的に検討:
  - ステートメントの文言（statement phrasing）
  - 回答尺度（response scale）の形式
  - 政策文書を回答キーにコーディングする際の**コーダー間信頼性(intercoder reliability)**
  - 項目を次元にスケーリングする際の信頼性・妥当性
- 結論: VAAには潜在力があるが方法論的改善の余地が大きい。設計上の推奨を提示。
- URL: https://link.springer.com/article/10.1057/ap.2012.36

方式の3類型と、実例における対応:
| 方式 | 実例 | 弱点 |
|---|---|---|
| 政党/候補者の自己申告 | smartvote、毎日新聞えらぼーと、Wahl-O-Mat（絞り込み前に全党回答） | **戦略的操作(strategic manipulation)** の余地。政党が有利になるよう回答しうる |
| 専門家コーディング | Kieskompas（非協力政党について）、EU Profiler | コーダー間信頼性、コーダーの政治的立場 |
| 両者の反復的組合せ | EU Profiler / euandi | コスト。どちらを優先するかの裁定基準 |
| 議会記録・投票記録ベース | （VAAでは稀。→4章のツール群） | 4章の限界がそのまま乗る |

VAAから抽出した政党ポジションの外的妥当性については、**左右軸・経済次元では他の指標との収束的妥当性が強いが、移民・環境については見劣りする**という報告がある（検索結果の要約より。原典未特定、→6章）。

### 3-4. 一致度アルゴリズム／空間モデルの恣意性
**Louwerse, T., & Rosema, M. (2014). "The design effects of voting advice applications: Comparing methods of calculating matches." *Acta Politica*, 49(3), 286-312. DOI: 10.1057/ap.2013.30**
- 助言は採用する空間モデルに強く依存する。**StemWijzerの利用者の過半数は、別の空間モデルを使っていれば別の助言を受け取っていた**。
- URL: https://link.springer.com/article/10.1057/ap.2013.30

**Otjes, S., & Louwerse, T. (2014). "Spatial models in voting advice applications." *Electoral Studies*, 36, 263-271. DOI: 10.1016/j.electstud.2014.04.004**

**Mendez, F. (2012). "Matching voters to parties: Voting advice applications and models of party choice." *Acta Politica*.** — https://link.springer.com/article/10.1057/ap.2011.29 （著者・年は検索結果からの推定を含む、→6章）

Gemenis (2024) の整理: アルゴリズムは**次元数(dimensionality)、距離尺度(distance metrics)、重み付け(weighting schemes)**の取り方によって異なる結果を出すにもかかわらず、ユーザーには不透明で、標準化にも抵抗している。

### 3-5. 「中立性」の主張は成立するか（規範理論からの批判）
**Fossen, T., & Anderson, J. (2014). "What's the point of voting advice applications? Competing perspectives on democracy and citizenship." *Electoral Studies*, 36, 244-251. DOI: 10.1016/j.electstud.2014.04.005**（DOI末尾は要確認、→6章）
- 中核主張: **よく構成されたマッチング型・熟議型VAAは「非党派的(non-partisan)」ではありうるが、「政治的に中立(politically neutral)」ではない。** VAAは開発者の前提に基づいて政治情報を構造化し、**争点と政党の選択を通じて選挙アジェンダそのものを形成する**からである。
- 3つの民主主義観の対比: (a) 選挙を有権者の政策選好の集計とみなす社会的選択モデル（マッチング型VAAが暗黙に前提している）、(b) 政治的見解の継続的な修正を重視する熟議民主主義、(c) 現行の政治的布置の外を見ることを重視する闘技的(agonistic)/異議申立てモデル。
- 結論: マッチングモデルだけでは市民的能力の涵養と民主主義の強化の可能性を汲み尽くせない。
- URL: https://www.sciencedirect.com/science/article/pii/S0261379414000419 / https://cyberleninka.org/article/n/1303646

**Stockinger, E., Maas, J., Talvitie, C., & Dignum, V. (2024). "Trustworthiness of voting advice applications in Europe." *Ethics and Information Technology*, 26(3). DOI: 10.1007/s10676-024-09790-6**
- 「有権者の選択には**確立されたground truthが存在しない**」ため、VAAの推薦はアーキテクチャと設計上の選択に強く依存する、という前提から出発。
- 欧州の代表的VAA群を、欧州委員会の「信頼できるAIのための倫理ガイドライン」に照らして公開情報のみから評価。**多くの要件でスコアは低く、VAA間の差は開発主体の種別を反映していた。**
- 改善が必要な4点: (i) **推薦が主観的であることについての透明性**、(ii) ステークホルダー参加の多様性、(iii) ユーザー目線でのアルゴリズム文書化、(iv) **基礎にある価値と前提の開示**。
- URL: https://link.springer.com/article/10.1007/s10676-024-09790-6 / https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11415416/

### 3-6. 研究そのもののセレクションバイアス
**Pianzola, J. (2014). "Selection biases in Voting Advice Application research." *Electoral Studies*, 36, 272-280. DOI: 10.1016/j.electstud.2014.04.012**
- 観察データからVAA利用の因果効果を導くには、**処置への自己選択(self-selection into the treatment)** と **標本への自己選択(self-selection into the sample)** の双方を統制する必要がある。VAAを使うかどうかと、その後の投票行動の双方に影響する未観測要因による内生性の問題。
- **「VAA研究のいくつかはセレクションバイアスの問題を認識しているが、実際にその欠点の改善に踏み込んだものはほとんどない」**。
- URL: https://www.sciencedirect.com/science/article/abs/pii/S0261379414000523

### 3-7. その他
- VAAの利用者は**教育程度が高く、若く、政治的関心の高い層に偏る**ため、克服しようとしていた参加の不平等をかえって増幅しうる（Gemenis 2024）。
- VAAはアカウンタビリティ、争点の顕出性(salience)、遂行能力(competence)、非政策的要因をほぼ無視する。
- 政党による戦略的操作を受けうる。
- 敵対的環境での頑健性: "Recommender Systems for Democracy: Toward Adversarial Robustness in Voting Advice Applications" — https://arxiv.org/html/2505.13329
- **Gemenis, K. (2024). "Artificial intelligence and voting advice applications." *Frontiers in Political Science*, 6, 1286893.** — https://www.frontiersin.org/journals/political-science/articles/10.3389/fpos.2024.1286893/full

---

## 4. 議会投票記録ベースのツールと研究

### 4-1. 米 Voteview / DW-NOMINATE
- NOMINATE (nominal three-step estimation) は Keith T. Poole と Howard Rosenthal が1980年代前半に開発した多次元尺度構成法。点呼投票(roll call)行動から議員を空間上に配置する。D-NOMINATE → W-NOMINATE → DW-NOMINATE（dynamic, weighted）と発展。
- 空間地図上での2議員の近さ ＝ 投票記録の類似度。
- URL: https://voteview.com/about / https://en.wikipedia.org/wiki/NOMINATE_(scaling_method) / https://legacy.voteview.com/pdf/prapsd99.pdf

**限界の議論**（Caughey, D., & Schickler, E. "Substance and Change in Congressional Ideology: NOMINATE and Its Alternatives", *Studies in American Political Development*）:
1. NOMINATEが取り出す次元は、**時代を通じて一貫したイデオロギー的意味を持つとは限らない**。1920年代の事例研究では、党派線が当時の思想的論争の主要な輪郭とうまく対応しない時期のスコア解釈が困難であることを示した。
2. DW-NOMINATEの前提は、**急速な、あるいは非単調なイデオロギー変化の扱いに適していない**。
3. 空間投票モデルから逸脱する議員のスコアは標準誤差が大きく、正確でない可能性がある。
4. **議員の座標はイデオロギーだけでなく、政党組織からの圧力、選挙区の要求など複数要因の関数**である。
- URL: https://devincaughey.github.io/files/caughey_schickler_2016_nominate/caughey_schickler_2016_nominate.pdf / 反論として "In Defense of DW-NOMINATE" (*Studies in American Political Development*) https://www.cambridge.org/core/journals/studies-in-american-political-development/article/abs/in-defense-of-dwnominate/0D5161CCD8C62BEC8DD5ECF8FA8DABEA

### 4-2. 議院内閣制・党議拘束下でのroll callの限界（日本に直接効く論点）
- roll callデータは2つの問題を抱える: **(a) 記録に残らない投票による選抜バイアス（selection bias due to unrecorded votes）**、**(b) 強い党議拘束により、投票が選好の誠実な表明ではなく戦略的なものになること**。
- Hix, S., Noury, A., & Roland, G. (2018) "Is there a selection bias in roll call votes? Evidence from the European Parliament" — https://ideas.repec.org/p/ehl/lserod/87696.html
- Høyland, B. (2010) "Procedural and party effects in European Parliament roll-call votes" — https://journals.sagepub.com/doi/abs/10.1177/1465116510379925
- "Roll Call Votes in the European Parliament: a good sample or a poisoned dead end?", *Parliaments, Estates and Representation*, 37(1) — https://www.tandfonline.com/doi/abs/10.1080/02606755.2016.1232994
- 対応策として、**投票より制約の弱い議会演説から立場を推定する**アプローチが提案されている（党指導部は投票と違って発言を罰しにくいため）: "Measuring Political Positions from Legislative Speech", *Political Analysis* — https://www.cambridge.org/core/journals/political-analysis/article/abs/measuring-political-positions-from-legislative-speech/35D8B53C4B7367185325C25BBE5F42B4 / "Estimating Intra-Party Preferences: Comparing Speeches to Votes", *Political Science Research and Methods* — https://www.cambridge.org/core/journals/political-science-research-and-methods/article/abs/estimating-intraparty-preferences-comparing-speeches-to-votes/D5812B196E0945B1341AFCD050F24858

### 4-3. 英 TheyWorkForYou（mySociety）と Public Whip
TheyWorkForYouは個別投票を表示するほか、庶民院については複数の採決を「気候変動の防止」「印紙税の引上げ」といった**政策(policy)にまとめた投票サマリ**（「一貫して賛成した」等）を作る。
- **自動分類はできず、mySocietyがすべての採決を手作業でカテゴライズしている**（＝ここに編集判断が入る）。
- URL: https://www.mysociety.org/2015/08/21/everything-about-theyworkforyous-voting-information/ / https://www.mysociety.org/2025/05/19/theyworkforyou-votes/

**2024年の方式改訂で自ら認めた問題点**（https://research.mysociety.org/html/2024-voting-records/ ）:
- **ゲーミング**: 議員や政党が、実質的な議会権限を伴わない非拘束的動議を、政治的分断を作るために提出する。政府側は参加しないことも選べるため、実態を反映しない「勝ち」が生まれる。
- **欠席の扱い**: 旧Public Whip方式は欠席を時に棄権として、時に軽い減点として扱っており、説明が困難だった。代理投票・病気・育児休暇など正当な理由で欠席した議員が、投票した同僚より支持的でないように見えてしまう。
- **弱い投票(weak votes)**: 「強い」投票の1/5の重みしか持たない採決は、スコアへの影響が小さいわりに複雑さを増した。特に新人議員では弱い投票がその政策に関する記録のすべてを占めることがある。
- **党議拘束がアカウンタビリティを覆い隠す**: 投票記録が測っているのが個人の信念なのか集団的な党の規律なのか、混乱を生む。

改訂の内容:
- **議会の実際の権限を行使する採決（立法、文書公開、内部規則）だけをスコアに算入**し、象徴的な意思表明は「informative（参考）」として別枠表示。
- 欠席は棄権として数えず**完全に除外**（説明しやすさを優先）。
- **弱い投票の階層を廃止**、強い投票のみをスコアに算入。
- 分割投票なしに可決された決定を含める「agreements」カテゴリを新設（慎重に適用）。
- 自己評価: 「もっとも単純な要点はおおむね正しいはずだ」としつつ、ツールは依然として鈍い(blunt)器具であると認めている。「簡単な答えはないので、我々の見解も時とともに変わると考えるべきだ」。個々の議員のアカウンタビリティに焦点を当てることが、議会内で歴史的に代表の少なかった集団に敵対的な仕組みを意図せず強化しうる、という懸念も明記している。
- 2026年7月にも投票サマリの更新を実施 — https://www.mysociety.org/2026/07/01/theyworkforyou-voting-summaries-update-july-2026/
- 英国における議員の投票記録の公開そのものの是非を論じたもの: The Constitution Unit Blog "Should we be allowed to see MPs' voting records?" (2021) — https://constitution-unit.com/2021/12/20/should-we-be-allowed-to-see-mps-voting-records/

### 4-4. 米 GovTrack — 定量スコアの撤回事例
- GovTrackのイデオロギースコアは**投票ではなく法案の共同提案(cosponsorship)パターンの類似度**から算出される。発言も投票も見ず、法案の内容を保守/リベラルと読んで格付けすることもしない。
- URL: https://www.govtrack.us/about/analysis
- **2024年7月、GovTrackは2013年・2015年・2017年・2019年の単年度議員ランキング（レポートカード）を撤回した。**
  - 撤回理由: スコアは投入する共同提案データの年数によって変動し、データが少ないほど分析の信頼性が落ちる（世論調査の誤差のようなもの）。単年ランキングは複数年分析と著しく異なる結果を出していた。
  - 具体例: 2019年の単年ランキングは当時のKamala Harris上院議員を**上院全体で最もリベラル**と位置づけたが、2021年公表の新ランキングでは**民主党上院議員の中で最左**という結果になった。2020年にWashington Postがこの食い違いを取り上げ、分析が何かを取りこぼしている可能性を指摘した。
  - URL: https://www.govtrack.us/posts/434/2024-07-26_we-retracted-our-single-year-legislator-report-cards-after-warning-about-their-unreliability
- Ballotpedia によるGovTrackランキングの解説: https://ballotpedia.org/GovTrack%27s_Political_Spectrum_%26_Legislative_Leadership_ranking

> **この事例の含意**: 一次情報（議会記録）から機械的に算出した定量スコアであっても、集計期間の取り方ひとつで結論が反転し、運営者自身が撤回に追い込まれることがある。「機械的に算出したから中立」は成立しない。

---

## 5. 「AI政策くらべ」への含意

前提として、AI政策くらべ側の記載（https://ai-seisaku-kurabe.github.io ）から確認できたのは以下: データ源は国会会議録検索システムと参議院記名投票結果（第217・219・221回国会）。機能は政策マッチング診断（2〜3分、登録不要）、政党比較ガイド（ワンイシュー＋6分野を原典リンク付きで表示）、診断回答者の傾向の参考値表示。設計原則として点数化・格付けをしない、優劣評価をしない、判断は利用者に委ねる、編集判断を含むため原典での検証を促す。「このサイトについて」で編集方法論・限界・点数化しない理由を公開している。

### 5-1. すでに回避できている（先行研究の批判が直接は刺さらない）点

- **一次情報への検証可能なリンクを付けている点** は、Stockinger et al. (2024) が欧州VAAに欠けていると指摘した「ユーザー目線でのアルゴリズム/根拠の文書化」の一部を、少なくとも根拠データのレベルでは満たしている。欧州の主要VAAの多くはこのスコアが低かった。
- **点数化・格付けをしない設計** は、GovTrackが2024年に単年度レポートカードを撤回した種類の失敗（スコアの見かけの精密さと実際の頑健性の乖離）を構造的に回避している。またmySocietyが2024年改訂で苦闘した「弱い投票の重み付け」「欠席の扱い」といった、重み付け設計に固有の恣意性の泥沼にも入らずに済む。
- **「編集方法論・限界・点数化しない理由」を公開している点** は、Fossen & Anderson (2014) の「VAAは非党派的ではありえても中立ではない」という批判、および Stockinger et al. (2024) の「推薦が主観的であることの透明性」「基礎にある価値と前提の開示」という要求に対する、正面からの部分的応答になっている。多くの既存VAAはここを曖昧にしている。
- **政党の立場を政党の自己申告ではなく議会記録から取っている点** は、Gemenis (2013) が指摘する「政党による戦略的操作」のリスクを大幅に減らす。smartvoteや毎日新聞えらぼーとが構造的に負っているリスク（候補者が有利になるよう回答する）を負わない。

### 5-2. まだ手当てできていない、または新たに負っている問題

- **設問選択のバイアスは回避できていない。** Walgrave et al. (2009) が示したのは「ステートメント選択が一致度に深甚な影響を与える」ことであり、これは点数化の有無とは独立に、マッチング機能を持つ限り必ず生じる。10問程度という設問数の少なさはこの問題を緩和しない（むしろ1問あたりの影響が大きくなる）。誰がどういう手続きで設問を選んだかの開示が、Wahl-O-Matの多段階編集プロセス（若年有権者・学界・ジャーナリズム・教育の混成チーム、80〜100案→全党回答→38問に絞込み）に相当するレベルまで具体化されているかは要点検。
- **設問の文言・極性・提示順のバイアスも回避できていない。** 質問の極性（PMC5056712）や左派/右派的な見出し（PLOS ONE 2019）だけで報告される態度が変わることが実証されている。マッチング設問の文言レビュー手続きが必要。
- **「点数化しない」と「一致度を出す」の緊張。** 政策マッチングが「一致度」を出す以上、それは政党別の数値の並びであり、機能的には順位になる。Louwerse & Rosema (2014) の「StemWijzer利用者の過半数は別の空間モデルなら別の助言を受けていた」という結果は、一致度アルゴリズムの選択そのものが編集判断であることを意味する。**一致度の算出式（距離尺度、次元の扱い、重み付け）が公開されているか**は、この設計原則の一貫性にとって決定的。Gemenis (2024) は、アルゴリズムが次元数・距離尺度・重み付けで結果を変えるのにユーザーには不透明であることを主要な問題として名指ししている。
- **党議拘束下のroll callという、日本に特に強く効く限界。** 参議院の記名投票は、強い党議拘束の下では議員個人の選好の誠実な表明ではなく戦略的な行動である（Hix et al. 2018 等）。さらに**記名投票は参議院の採決のごく一部にすぎず、記録に残らない採決による選抜バイアス**が乗る。「行」として記名投票を提示するとき、この2点（(a) 党議拘束のため個人の立場を示さない、(b) 記名投票にかかる議案は代表標本ではない）が明示されているかは要点検。
- **「言」（会議録の発言）と「行」（記名投票）の対応づけ自体が編集判断である。** どの発言をどの政策分野に紐づけ、どの記名投票をどの分野に紐づけるかは、TheyWorkForYouが「自動分類はできず、すべて手作業でカテゴライズしている」と明言しているのと同じ作業であり、同じ恣意性を持つ。mySocietyはこのカテゴライズ方式を2024年に大幅に改訂しており、方式が一意でないことを実例で示している。
- **参議院のみ・3国会分というデータ範囲の非対称性。** 衆議院の記名投票（押しボタン式ではないため公開データが限定的である可能性）が入らないことで、衆議院中心の政治過程が「行」の側から見えない。この非対称性が利用者に伝わらないと、「行の記録が少ない政党＝行動していない政党」という誤読を生みうる。
- **利用者の自己選択バイアス。** Pianzola (2014) の指摘（処置への自己選択・標本への自己選択）は、「診断回答者の傾向を参考値として表示する」機能に直接効く。この集計はサイト利用者という強く偏った母集団の集計であり、世論ではない。Gemenis (2024) はVAA利用者が高学歴・若年・政治的関心の高い層に偏り、参加の不平等をかえって増幅しうると指摘している。参考値表示にこの旨の注記が必要。
- **効果に関するエビデンスの整理。** Munzert & Ramirez-Ruiz (2021) のメタ分析では、投票率と投票先への効果は強いエビデンスがある一方、**政治知識の向上は信頼区間が0をまたぐ穏当なエビデンスにとどまる**。「有権者が判断できるようにする」という目的を掲げる場合、知識向上効果が自明でないことは織り込むべき。また効果量の異質性の主因が研究デザインであることも、自前で効果を主張する際の注意点になる。
- **中立性を主張しないという選択肢。** Fossen & Anderson (2014) の論点は、VAAが「争点と政党の選択を通じて選挙アジェンダそのものを形成する」ことであり、これはリンクの検証可能性では解消されない。「点数化しない」ことは非党派性の担保にはなるが中立性の担保にはならない。この区別を「このサイトについて」で明示的に述べる（＝「中立ではない、非党派的であろうとしている」と書く）ことが、先行研究に照らして最も誠実な立て方になる。

---

## 6. 未確認・要追跡

以下は本調査で**確認しきれなかった／原典に当たれなかった**もの。本文中の該当箇所からもここを参照している。**記憶ベースの推測を含むため、そのまま引用してはならない。**

1. **Garzia & Marschall (2016) *Policy & Internet* 8(4) の本文** — HTTP 402で取得不可。VAA研究のレビューとして重要なので、大学図書館経由等での入手を推奨。URL: https://onlinelibrary.wiley.com/doi/full/10.1002/poi3.140
2. **Garzia & Marschall (2019) Oxford Research Encyclopedia 本文** — oxfordre.com が academic.oup.com にリダイレクトし、本文を取得できなかった。本文中で「Oxford Research Encyclopediaの記述より」としている記述（smartvoteの投票確率上昇、StemWijzerの2010年総選挙での効果、Wahl-O-Mat利用と政党立場知識の相関、2023年スイス選挙の分極化低減）は、**検索エンジンが返した要約に基づくもので、原典の該当箇所を確認していない**。個別の一次論文に当たり直すこと。
3. **Marschall & Schultze (2012) の掲載誌・巻号・ページ** — ResearchGateでタイトルは確認できたが、掲載誌が *German Politics* かどうかを確認できていない。要確認。
4. **Mendez, F. (2012) "Matching voters to parties" の著者・年** — Springerのページ（https://link.springer.com/article/10.1057/ap.2011.29 ）は確認したが、著者名と刊行年を検索結果から確定できていない。CrossrefでDOI 10.1057/ap.2011.29 を引くこと。
5. **Fossen & Anderson (2014) のDOI末尾** — 巻(36)・ページ(244-251)は確認できたが、DOIの末尾番号は未確認。
6. **「VAA由来の政党ポジションは左右軸・経済次元では収束的妥当性が高いが移民・環境では劣る」の原典** — 検索結果の要約に現れたが、どの論文の知見か特定できていない。おそらくEU Profiler/euandiデータの妥当性検証論文（ECPR paper "Comparing Party Positions in a European Multidimensional Political Space: a Cross-Validation of the EU Profiler/euandi Longitudinal Dataset, 2009-2019" https://ecpr.eu/Events/Event/PaperDetails/55009 ）だが未確認。
7. **Fröhle (2026) "From Swipes to Votes" (*Policy & Internet*)** — タイトルからVoteswiperが投票選択を分極化させる方向の知見と読めるが、本文未読。2章の「分極化を低減しうる」という記述と矛盾する可能性があるので必ず確認すること。URL: https://onlinelibrary.wiley.com/doi/10.1002/poi3.70028
8. **NPO法人Mielkaの設立年** — mielka.org には「2016年に発足」、検索結果の別記述には「2014年設立」とある。一次情報（NPO法人の登記情報、定款、年次報告）で確認すること。
9. **JAPAN CHOICEの「投票ナビ」のマッチング方法論** — 政党ポジションを誰がどう決めているか、一致度をどう計算しているかを、公開ドキュメントから確認できなかった。japanchoice.jp の「運営団体について」ページとnote記事を個別に当たること。本プロジェクトにとって最も直接的な国内比較対象なので優先度が高い。
10. **毎日新聞「えらぼーと」の設問作成手順** — 「毎日新聞が事前に立候補者に実施した政策アンケート」を基礎にすることは確認できたが、25問をどういう手続きで選んでいるか、政党（候補者ではなく党）の一致度をどう算出しているかは未確認。
11. **朝日新聞・読売新聞・NHKなど他の日本のボートマッチ／候補者アンケートの実例** — 本調査では取得できていない。日本の事例は毎日新聞とJAPAN CHOICEの2件しか押さえられていない。
12. **日本の議会記録を用いた政治学的な立場推定研究（日本語・英語とも）** — 参議院の記名投票や国会会議録から議員・政党の立場を推定した査読研究を本調査では特定できなかった。「日本 国会 ideal point estimation」等での追加調査が必要。**このプロジェクトの方法論的妥当性を国内文脈で裏付ける／限界を知るうえで最も重要な空白。**
13. **Public Whip の現状と方法論の一次情報** — mySocietyの記事経由で「旧Public Whip方式」への言及は確認したが、Public Whip 自体のサイト・方法論ドキュメントには当たれていない。
14. **VoteMatch（欧州のVAAネットワーク）** — https://en.wikipedia.org/wiki/VoteMatch が検索結果に現れたが未取得。StemWijzer系VAAの国際ネットワークと思われる。
15. **VAAの資金源に関する比較研究** — 各VAAの運営主体は確認できたが、資金構造（公費／メディア／寄付／助成）を横断的に比較した研究は特定できていない。Stockinger et al. (2024) が「VAA間のスコア差は開発主体の種別を反映していた」としているので、この論文の本文に手がかりがある可能性が高い。
