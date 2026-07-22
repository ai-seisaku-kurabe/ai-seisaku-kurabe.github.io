# B. AIを民主主義に使う側の先行研究・実践

調査日: 2026-07-21 / 担当B
本文の各項目は WebSearch / WebFetch で実際に到達できた情報のみを記載する。検索で確認できなかったものは「6. 未確認・要追跡」に分離した。

---

## 1. デジタル民主主義／熟議支援の実践

### 1.1 vTaiwan と Polis (pol.is)

- **Polis / vTaiwan（台湾, 2014-）** — vTaiwan は Polis の国家規模・長期運用としては最長級の事例で、立法プロセスへの適用ケーススタディを他国より多く産出している。
  - Computational Democracy Project によるケーススタディ: https://compdemocracy.org/case-studies/2014-vtaiwan/
  - Participedia の手法解説: https://participedia.net/method/vtaiwan
  - CrowdLaw for Congress の事例整理: https://congress.crowd.law/case-vtaiwan.html

- **動かし方の要点**: Polis は参加者が短い意見文を投稿し、他者の意見に賛成/反対/パスで投票する。機械学習で意見クラスタを可視化し、クラスタをまたいで支持される「ブリッジング（架橋）意見」を浮かび上がらせる。ここで得られた"rough consensus"を起点に、政策当局を含むステークホルダーが**ライブ配信の対面会議**を行い、具体的な勧告に落とす。
  - 参考: https://democracy-technologies.org/participation/consensus-building-in-taiwan/
  - People Powered のケーススタディ（vTaiwan のハイブリッド型 + AI 併用）: https://www.peoplepowered.org/news-content/digital-participation-case-study-taiwan

- **限界として文献上で指摘されている点**（重要。「AI政策くらべ」の設計判断に直結する）:
  1. **プラットフォーム単体では不十分**。Polis の前段（多様で質の高い意見文を生む対面/ファシリテート済み議論）と後段（ブリッジング意見を政策提言に翻訳する多主体対話）が不可欠。
  2. **失敗事例が体系的に記録されていない**。成功ケーススタディは豊富だが、実務での失敗がどの程度文書化されずに済まされているか不明、という指摘がある（上記 democracy-technologies 記事および関連研究）。
  3. **参加の幅は狭い**。vTaiwan の利用は広範ではなく、「浅く広く」ではなく「深く狭く、ただし政策行動につながる確率が高い」タイプ。

- 関連する査読前研究（フィールド知見）: "Bridging Voting and Deliberation with Algorithms: Field Insights from vTaiwan and Kultur Komitee" — https://arxiv.org/pdf/2502.05017
- 熟議技術とAIアラインメントを接続する論考: "Deliberative Technology for Alignment" — https://arxiv.org/pdf/2312.03893

### 1.2 Decidim / Consul（スペイン発、オープンソース）

- **Consul** は Madrid 市の decide.madrid.es の基盤として出発し、**Decidim** は 2016 年初頭に Barcelona が Consul をフォークして decidim.barcelona として立ち上げたもの。いずれも 15M 運動の市民アクティビスト由来で、現在多数の国に普及。
  - Decidim 公式: https://decidim.org/ / ドキュメント: https://docs.decidim.org/en/develop/understand/about.html
  - 概説（Springer, 書籍章）: https://link.springer.com/chapter/10.1007/978-3-031-50784-7_1

- **実績の数字（Barcelona 初期）**: 2か月弱で約25,000人が登録、10,860件の提案、410回の会合、16万超の賛成投票。
  - https://oidp.net/en/practice.php?id=1407 / https://www.ids.ac.uk/publications/decidim-barcelona-spain/

- **評価研究（限界の指摘）**:
  - Borge, Balcells & Padró-Solanet (2023) "Democratic Disruption or Continuity? Analysis of the Decidim Platform in Catalan Municipalities", *American Behavioral Scientist* — https://journals.sagepub.com/doi/abs/10.1177/00027642221092798
    透明性・参加・熟議の3次元で破壊的潜在力を検証した結果、**最も評価されている達成は「透明性・情報の整理・市民提案の収集」であって、熟議や主権の市民への移転ではない**（＝運営的な連続性の要素が強い）。
  - Aragón et al. "Deliberative Platform Design: The case study of the online discussions in Decidim Barcelona" — https://arxiv.org/pdf/1707.06526 （提案に否定的なコメントほど議論を誘発し、熟議的意思決定を促進する傾向）
  - Decidim の「ソフトインフラ」論（技術的自律の観点）: http://computationalculture.net/the-decidim-soft-infrastructure/

> 「AI政策くらべ」への含意の予告: Decidim 評価研究の結論（成果は熟議より**透明性と情報整理**にあった）は、本サイトが「点数化せず一次情報を整理して返す」ことに絞っている設計と、実証的に整合する。

### 1.3 Talk to the City / ブロードリスニング

- **Talk to the City (T3C)** — AI Objectives Institute（米カリフォルニアのNPO）が開発したオープンソースのLLMインターフェース。大量の定性データ（自由記述・インタビュー等）を分析し、集合的熟議と意思決定を支える。全コードOSS。
  - https://ai.objectives.institute/talk-to-the-city / https://talktothe.city/ / https://talktothe.city/about
  - 台湾での適用（デジタル発展部 MoDA、Taiwan AI Assembly ほか）: https://ai.objectives.institute/blog/amplifying-voices-talk-to-the-city-in-taiwan
  - vTaiwan・Chatham House との "Recursive Public" プロジェクト（OpenAI の Democratic Inputs 助成、AIガバナンスの優先課題特定に約1000人が参加）。同ブログ記事に記載。
- 「ブロードリスニング（broad listening）」という語は Audrey Tang による T3C 評（"broad-listening" を可能にする）と結びついて広まった。概説: https://www.combinationsmag.com/the-art-of-broad-listening/

### 1.4 日本: デジタル民主主義2030 / チームみらい（安野貴博）

- **デジタル民主主義2030** 公式: https://dd2030.org/
  公開ツール（サイト上で確認できたもの）:
  - **広聴AI (kouchou-ai)** — ブロードリスニング支援のOSS分析ツール。Talk to the City の改良版がベース。最新版 v4.0.0（2025-12-28 リリース）ほか v2/v3 の安定版リリースあり。
  - **いどばた (idobata)** — 大規模熟議プラットフォーム。台湾の JOIN・vTaiwan を参照して設計。
  - **Polimoney** — 政治資金の透明化ダッシュボード。
  - **Project Coreloop** — 市民意見を政策実行につなげる: https://coreloop.dd2030.org/
- プロジェクト全体像（本人発信）: https://note.com/annotakahiro24/n/na0e296bc30b8 / 立ち上げ会見全文: https://note.com/annotakahiro24/n/nfd4a855cd1a8
- 「Talk to the City と広聴AIの歴史」（西尾泰和）: https://note.com/nishiohirokazu/n/nb37adf96fe50
- 開発リポジトリ群: https://github.com/team-mirai
- 政策側の提示: 「声が届くマニフェスト」 https://policy.team-mir.ai/ ／ デジタル民主主義の章 https://policy.team-mir.ai/policies/digital-democracy
- 政府側への持ち込み: 内閣官房デジタル行財政改革会議への安野構成員提出資料 https://www.cas.go.jp/jp/seisaku/digital_gyozaikaikaku/senryaku2/senryaku2_siryou6.pdf
- 中立性の担保として、安野は 2025年5月時点でデジタル民主主義2030 の理事を退任（政治的中立性維持のため）と報じられている。
- 報道: https://ledge.ai/articles/ai_engineer_takahiro_anno_digital-democracy-2030

- **実践から言語化された知見（「しゃべれるマニフェスト」社会実験, 西尾泰和）**: https://note.com/nishiohirokazu/n/nb35e8d526fd4
  - マニフェストを読みながらAIに質問でき、意見はAIとの対話を通じて提案の形にまとめて提出でき、**提出意見の反映状況を追跡できる**。
  - GitHub をデータ基盤にしたことの実務的問題: APIレートリミット、PR差分での意見収集に伴うコンフリクト、GitHub に不慣れな人が直接来てしまう導線問題。
  - 得られた指針として、ブロードリスニングは「分類の仕方を変えること」で価値を出す、**双方向のトレーサビリティが必要**、個人でなく集団に注目させる設計、が挙げられている。

> 「AI政策くらべ」への含意の予告: 「双方向のトレーサビリティ」は本サイトの「一次情報への検証可能なリンクだけ提供する」原則とほぼ同じ思想。GitHub 導線の失敗知見も、有権者向けUIを作る際の直接の教訓。

### 1.5 Stanford Online Deliberation Platform（自動モデレーター）

- Stanford Deliberative Democracy Lab（James Fishkin, Deliberative Polling）+ Crowdsourced Democracy Team による、ビデオ小グループ（約10人）の熟議を**自動モデレーター**が運営するプラットフォーム。発言キュー形成、時間割り当て、公平な発言機会の確保を自動化する。
  - https://deliberation.stanford.edu/tools-resources/online-deliberation-platform
  - https://directory.civictech.guide/listing/stanford-online-deliberation-platform
  - 技術記事: https://www.humancomputation.com/2019/assets/papers/144.pdf
  - Stanford HAI の紹介記事「A Moderator ChatBot for Civic Discourse」: https://hai.stanford.edu/news/moderator-chatbot-civic-discourse
- 日本語を含む多言語で運用実績があり、チリ・カナダ・米国で全国規模の Deliberative Polling に使用。
- 設計上の要点: **AIは「何を言うべきか」を生成せず、「誰がいつどれだけ話すか」という手続きだけを制御する**。内容中立の自動化。

---

## 2. LLMを熟議・世論集約に使う研究

### 2.1 Habermas Machine（Google DeepMind）

- **正確な書誌（検索で確認済み）**: Michael Henry Tessler, Michiel A. Bakker, Daniel Jarrett, Hannah Sheahan, Martin J. Chadwick, Raphael Koster, Georgina Evans, Lucy Campbell-Gillingham, Tantum Collins, David C. Parkes, Matthew Botvinick, Christopher Summerfield, **"AI can help humans find common ground in democratic deliberation," *Science*, 386(6719), eadq2852 (2024-10-18)**.
  - https://www.science.org/doi/10.1126/science.adq2852
  - PubMed: https://pubmed.ncbi.nlm.nih.gov/39418380/
  - Semantic Scholar: https://www.semanticscholar.org/paper/5456e833710dba2bb3ae92621fa89c27733b1db0
  - ※ 掲載誌は **Science** であり、Nature Human Behaviour ではない（依頼文の記載を訂正）。

- **中身**: LLM群を「caucus mediator（幹事役の調停者）」として動かし、参加者個々の意見と、生成された草案への批評を反復的に統合して、集団の合意点を記述する声明文（group statement）を生成する。ハーバーマスのコミュニケーション的行為論に着想。
- **規模と結果**: 英国で5,700人超が参加。参加者は AI 媒介の集団声明を、人間ファシリテーターの作成した声明より**明確・情報量が多い・偏りが少ない**と評価。熟議後に意見を修正し共有見解へ収束する傾向。多数派に迎合せず**少数意見を声明に組み込む**点が特徴として報告されている。
- 報道解説: https://www.technologyreview.com/2024/10/17/1105810/ai-could-help-people-find-common-ground-during-deliberations/
- 実務者向け解説（Reboot Democracy）: https://rebootdemocracy.ai/blog/habermas-machine
- 講演記録（Harvard EconCS）: https://econcs.seas.harvard.edu/event/habermas-machine-ai-can-help-humans-find-common-ground-democratic-deliberation

### 2.2 Habermas Machine への批判的検討（査読論文）

- **"Toward an artificial deliberation? On Google DeepMind's Habermas Machine," *Ethics and Information Technology* (Springer, 2025)** — DOI 10.1007/s10676-025-09854-1
  - https://link.springer.com/article/10.1007/s10676-025-09854-1
  - ACM DL 経由: https://dl.acm.org/doi/10.1007/s10676-025-09854-1
  - 論点: AIによる**合意の生成**は、(a) その「合意」の本性、(b) 道徳的包摂（moral inclusivity）、(c) 暗黙に前提される合理性のあり方、について理論的・実践的な問題を生む。
  - ※ すなわち「AIに合意文を書かせること自体が規範的判断を含む」という指摘。「AI政策くらべ」が**AIに評価の結論を出力させない**としている原則の、学術的裏付けとして使える。

### 2.3 LLMをアノテーター／世論集約に使う際の信頼性

- **Gilardi, F., Alizadeh, M., & Kubli, M. (2023). "ChatGPT outperforms crowd workers for text-annotation tasks." *PNAS*, 120(30), e2305016120.**
  - https://www.pnas.org/doi/10.1073/pnas.2305016120 / プレプリント https://arxiv.org/pdf/2303.15056
  - ツイート・ニュース記事4データセット（n=6,183）で、relevance / **stance（立場）** / topics / frame detection のタスクを検証。ゼロショット精度がクラウドワーカーを平均約25ポイント上回り、コーダー間一致度もクラウドワーカー・訓練済みアノテーターの双方を上回った。1アノテーションあたり $0.003 未満（MTurk の約1/30）。
  - → **立場推定をLLMに任せる技術的可能性はある**、という肯定側の根拠。ただし下記の反証群と必ずセットで読むべき。

- **反証・慎重論（同じく確認済み）**:
  - **"LLMs as annotators: the effect of party cues on labelling decisions by large language models," *Humanities and Social Sciences Communications* (Nature ポートフォリオ, 2025)** — https://www.nature.com/articles/s41599-025-05834-4 / プレプリント https://arxiv.org/pdf/2408.15895
    **発言者の政党名という手がかりを与えるだけで、LLMのラベリングが偏る**ことを実証。政治テキストの機械分類にとって直撃的な知見。
  - "Navigating the Risks of Using Large Language Models for Text Annotation in Social Science Research" — https://arxiv.org/pdf/2503.22040
  - Egami ほか "Using Large Language Model Annotations for the Social Sciences"（Design-based Supervised Learning, DSL） — https://naokiegami.com/paper/dsl_ss.pdf
    アノテーション誤差を無視すると、誤差が小さくても**下流の統計分析に実質的なバイアス・無効な信頼区間・不正確なp値**をもたらす。平均精度ではなく、gold sample 上でのクラス条件付き誤差と下流への歪みを検証すべき、という主張。
  - "Large Language Model Hacking: Quantifying the Hidden Risks of Using LLMs"（LLM設定の違いで結論が反転しうる問題） — https://arxiv.org/pdf/2509.08825
  - プロプライエタリLLMを社会科学研究に使うことの透明性上の危険（Ollion, Shen, Macanovic & Chatelain, 2024 として言及されている。→ 6章で要追跡）

---

## 3. 議会・立法文書のNLP研究

### 3.1 基礎文献（政治テキスト分析）

- **Grimmer, J., & Stewart, B. M. (2013). "Text as Data: The Promise and Pitfalls of Automatic Content Analysis Methods for Political Texts." *Political Analysis*, 21(3), 267–297.**
  - https://www.cambridge.org/core/journals/political-analysis/article/text-as-data-the-promise-and-pitfalls-of-automatic-content-analysis-methods-for-political-texts/F7AAC8B2909441603FEB25C156448F20
  - https://www.semanticscholar.org/paper/b9921fb4d1448058642897797e77bdaf8f444404
  - 中核的主張: 自動テキスト分析は手作業のコストを劇的に下げるが、**モデル出力は必ず検証（validate）しなければならない**。この分野の"教義"として繰り返し引かれるのが「All quantitative models of language are wrong—but some are useful（言語の量的モデルはすべて間違っている。しかし一部は有用）」および「教師なし手法の出力を検証なしに信じるな」。

- **記名投票（roll call）の尺度化**:
  - Poole & Rosenthal の **NOMINATE / W-NOMINATE / DW-NOMINATE**（1980年代〜）。議員を多次元空間に配置し、投票の一致度から理念的距離を推定。 https://en.wikipedia.org/wiki/NOMINATE_(scaling_method) / https://voteview.com/about
  - **Clinton, J., Jackman, S., & Rivers, D. (2004). "The Statistical Analysis of Roll Call Data: A Unified Approach." *American Political Science Review*, 98(2), 355–370.** — https://www.cambridge.org/core/journals/american-political-science-review/article/abs/statistical-analysis-of-roll-call-data/75DBC6645F85A764AE9E5DBF468AB813
    ベイズ項目反応理論（IRT）による ideal point 推定（IDEAL）。
  - NOMINATE と IDEAL の比較: https://legacy.voteview.com/pdf/nominatevideal.pdf
    両者の差の多くは**識別制約という恣意的な選択**に由来し、不確実性の見え方が変わる（IDEAL は中位議員の位置に自信、NOMINATE は極端議員の位置に自信）。
  - ※ **重要な留保**: これらはいずれも投票行動から「一次元/二次元の潜在的位置」を推定する＝**事実上のスコア化**である。「AI政策くらべ」の「点数化・格付けをしない」原則と正面から衝突する手法群。5章参照。

### 3.2 日本の国会・地方議会会議録を使った研究

- **永渕景祐・木村泰知・門脇一真・荒木健治 (2024)「国会および地方議会の会議録に基づく大規模なコーパスと事前学習済み言語モデルの構築」『自然言語処理』31巻2号, pp. 707–732.**
  - https://www.jstage.jst.go.jp/article/jnlp/31/2/31_707/_article/-char/ja/
  - Web公開されている国会・地方議会会議録を収集して大規模コーパスを構築し、政治ドメイン向け日本語事前学習済み言語モデルを作成。同分野タスクで既存モデルを上回る性能。ドメイン適応・追加学習の効果を検証。

- **NTCIR QA Lab-PoliInfo（木村泰知ほか、NTCIR-14 / 15 / 17 と継続）** — 日本の議会情報を対象にした共有タスク。
  - NTCIR-14 最終報告: https://link.springer.com/chapter/10.1007/978-3-030-36805-0_10
  - NTCIR-15 PoliInfo-2 概要（Kimura ほか）: https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings15/pdf/ntcir/01-NTCIR15-OV-QALAB-KimuraY.pdf
  - NTCIR-17 PoliInfo-4 概要（Ogawa ほか）: https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings17/pdf/ntcir/01-NTCIR17-OV-QALAB-OgawaY.pdf
  - データセット: https://github.com/poliinfo2/NTCIR15-QA-Lab-PoliInfo-2-Dataset
  - **タスク構成**: (a) Segmentation（要約に対応する発言文を抽出）, (b) Summarization（発言の要約）, (c) **Classification（与えられた論題に対して議会発言を賛成/反対/中立の3スタンスに分類）**。論題の例として「築地市場は豊洲に移転すべき」。
  - PoliInfo-2 では「議員の質問」と「知事の答弁」という対話構造を踏まえた Dialog Summarization も追加。
  - 参加システム例: "Summarizing Utterances from Japanese Assembly Minutes using Political Sentence-BERT-based Method" — https://arxiv.org/pdf/2010.12077

  > **本サイトにとって決定的に重要**: 日本語の議会発言に対する**スタンス分類は既に共有タスクとして10年近く取り組まれており、公開データセットと評価指標がある**。つまり「AIに立場を判定させる」ことの精度水準は、独自の主張ではなく既存ベンチマークに照らして議論できる。

- その他:
  - KAKEN「国会会議録コーパスと地方議会会議録コーパスを横断した言語的分析」(20K00576) — https://kaken.nii.ac.jp/en/grant/KAKENHI-PROJECT-20K00576/ 発言スタイルの変化、方言語彙・オノマトペの使用、政治関連語彙の使用などを分析。
  - 説明可能AIによる国会会議録／地方議会会議録の特徴比較（BERTベースの二値分類器＋特徴表現の抽出） — https://www.kyowa-u.ac.jp/laboratory/pdf/ronso25/075.pdf
  - 増山幹高「国会審議映像検索システムと同形異音語の分析」法学研究96巻2号 (2023) — https://aslp.law.keio.ac.jp/pdf/AN00224504-20230228-0444.pdf
  - 河原達也ほか「議会の会議録作成のための音声認識 －衆議院のシステムの概要－」 — https://sap.ist.i.kyoto-u.ac.jp/diet/SLP12.pdf （衆議院の会議録作成が音声認識ベースであること＝一次情報そのものに機械処理由来の誤りが混入しうることの根拠）
  - 「日本語コーパスとしての『国会会議録検索システム検索用API』」 — https://repolab.lib.niigata-u.ac.jp/records/record-33451/
  - 「議事録からの課題発言の自動抽出」(言語処理学会年次大会2015) — https://www.anlp.jp/proceedings/annual_meeting/2015/pdf_dir/P3-29.pdf
  - 「自然言語処理技術を活用した議会議事録の要約支援方法について」 — https://www.jstage.jst.go.jp/article/jbfsa/12/2/12_KJ00006659552/_article/-char/ja/

---

## 4. 公共目的AIの透明性・説明責任の枠組み

### 4.1 アルゴリズム登録簿（Algorithm Register）

- **Amsterdam / Helsinki の AI Register（2020年9月公開）** — 自治体がどのアルゴリズムを行政サービスに使っているかを公開する、世界初期の公的登録簿。
  - Amsterdam: https://oecd.ai/en/dashboards/policy-initiatives/amsterdams-ai-register-8123
  - 解説（Amsterdam の Open Research）: https://openresearch.amsterdam/en/page/73074/public-ai-registers
  - 報道: https://venturebeat.com/ai/amsterdam-and-helsinki-launch-algorithm-registries-to-bring-transparency-to-public-deployments-of-ai / https://www.theregister.com/2020/10/01/amsterdam_helsinki_ai_store/ / https://www.government-transformation.com/data/helsinki-amsterdam-first-cities-in-world-to-establish-open-ai-registers
  - Cities for Digital Rights: https://citiesfordigitalrights.org/ai-public-service-accountability-ai-registers

- **登録簿が各アルゴリズムについて開示する項目**（＝公共目的AIで何を開示すべきかの実務的チェックリストとして使える）:
  1. モデルの学習に使ったデータセット
  2. アルゴリズムがどう使われているかの説明
  3. 人間が予測をどう利用しているか（human-in-the-loop の実態）
  4. バイアス・リスクをどう評価したか
  5. **責任者の氏名・所属部署・連絡先**
  6. 市民がフィードバックを返す経路
  - 両者とも Saidot の AI 透明性プラットフォーム上で実装。

- **批判的検討（重要）**: "Dutch Comfort: The limits of AI governance through municipal registers" — https://arxiv.org/pdf/2109.02944
  自治体登録簿によるAIガバナンスの限界を論じる。登録簿があること自体が実質的な説明責任を保証しない、という趣旨。
- 実務レポート: "Making Algorithm Registers Work for Meaningful Transparency" — https://iaciudadana.org/wp-content/uploads/2025/03/Report-1.pdf

### 4.2 モデル／データセットの文書化規範

- **Mitchell, M., Wu, S., Zaldivar, A., Barnes, P., Vasserman, L., Hutchinson, B., Spitzer, E., Raji, I. D., & Gebru, T. (2019). "Model Cards for Model Reporting." *ACM FAccT (FAT\*) 2019*.**
  - https://arxiv.org/pdf/1810.03993
  - モデルの「栄養成分表示」。モデル種別、**意図された用途（intended use）**、性能が変動しうる属性、性能指標を、ユースケース／データ分布／社会的文脈ごとに記述する。
- **Gebru, T. et al. "Datasheets for Datasets."**（電子部品のデータシートに着想）— データセットの動機、構成、収集プロセス、ラベリング、配布、メンテナンスを記述する。
  - 概説（Model Card と Datasheet の関係整理）: https://arxiv.org/pdf/2401.13822 / https://medium.com/@akankshasinha247/model-cards-datasheets-governance-frameworks-0cda9605c94e
  - ※ Datasheets 論文そのものの正式書誌（arXiv:1803.09010, *Communications of the ACM* 2021）は今回の検索で直接ページを取得できていない → 6章参照。
- 実装テンプレート例: https://mlr3fairness.mlr-org.com/articles/modelcard/modelcard.html

---

## 5. 「AI政策くらべ」への含意

事実ベースで、採用可能なもの／原則と衝突するものを分けて記す。評価や推奨ではなく、文献上の対応関係の記述である。

### 5.1 このサイトの原則を支持する、または直接使える知見

| 文献・実践 | 対応する含意 |
|---|---|
| Borge et al. 2023（Decidim 評価） | 参加型プラットフォームの実証的成果は「熟議」より **透明性・情報の整理・提案の収集**に現れた。一次情報の整理・提示に絞る設計は、実証研究の見立てと整合する。 |
| Amsterdam / Helsinki AI Register の開示6項目 | **サイトのAI運用ルール公開ページの項目立てにそのまま流用できる**（使用データ、AIの用途、人間がどう使うか、リスク評価、責任者と連絡先、フィードバック経路）。 |
| Model Cards (Mitchell et al. 2019) | 「意図された用途」と「性能が変動しうる条件」を明記する規範。編集・検証にAIを使う工程ごとに、intended use と既知の失敗様式を書く形に移せる。 |
| Grimmer & Stewart 2013 | 自動テキスト分析の出力は**必ず人手で検証**という規範。会議録の抽出・整理をAIで行い、出力を一次情報リンクで検証可能にする本サイトの構造は、この規範の実装形とみなせる。 |
| 『自然言語処理』31(2) 会議録コーパス＋事前学習モデル、NTCIR PoliInfo | 日本の会議録に対する収集・前処理・評価の**既存の技術基盤と公開データが存在する**。独自にゼロから作る必要はなく、既存タスク定義（Segmentation / Summarization / Classification）を参照できる。 |
| 河原ほか（衆議院の音声認識による会議録作成） | 「一次情報」自体も機械処理を経ている。会議録を一次情報として扱う際、その生成過程を注記する根拠になる。 |
| デジタル民主主義2030／しゃべれるマニフェストの知見 | 「**双方向のトレーサビリティ**（提出意見の反映状況を追跡できる）」は、本サイトの「検証可能なリンクだけ提供する」原則と同一方向。GitHub 導線の失敗（レートリミット、非習熟者の流入）は、実装上の既知の落とし穴。 |
| Stanford Online Deliberation Platform の自動モデレーター | AIに**内容ではなく手続きだけ**を担当させる設計パターン。「AIに評価の結論を出力させない」の先行実装例。 |

### 5.2 このサイトの原則と衝突する手法

| 手法 | 衝突の内容 |
|---|---|
| NOMINATE / W-NOMINATE / DW-NOMINATE、Bayesian IRT (Clinton-Jackman-Rivers, IDEAL) | 記名投票データから議員・政党を**一次元ないし二次元の潜在尺度上に配置する**。政治学では標準手法だが、これは定義上「点数化・格付け」である。参議院記名投票データを持つ本サイトは技術的にはこれを実行できるが、原則に反する。加えて、NOMINATE と IDEAL の差の大部分が**識別制約という恣意的選択**に由来する（voteview の比較文書）ことから、「客観的スコア」として提示すること自体に問題がある。 |
| Habermas Machine 型の合意文生成 | AIに集団の合意声明を書かせる手法。*Ethics and Information Technology* (2025) の批判が指摘するとおり、合意の本性・道徳的包摂・暗黙の合理性という規範的判断が生成に埋め込まれる。「AIに評価の結論を出力させない」原則と正面から衝突する。 |
| LLMによるスタンス分類（賛成/反対/中立の自動ラベリング） | Gilardi et al. 2023 は精度面で有望とするが、*Humanities and Social Sciences Communications* (2025) は**政党名の手がかりだけでLLMのラベルが偏る**ことを実証。政治テキストでは最も危険な適用先。NTCIR PoliInfo の Classification タスクとして日本語ベンチマークは存在するが、少なくとも「AIが判定した立場」を無検証で有権者に提示することは支持されない。 |
| Polis 型のクラスタリング＋ブリッジング意見抽出 | 直接の衝突ではないが、vTaiwan の知見では**プラットフォーム単体では機能せず**、前段の質の高い意見生成と後段の対面翻訳作業が不可欠。また失敗事例が体系的に文書化されていない、という指摘がある。 |
| LLMアノテーションの下流利用一般 | Egami ほか（DSL）: 誤差が小さくても、それを無視すると下流分析に実質的バイアス・無効な信頼区間をもたらす。「AIが整理した結果を集計して見せる」形式をとる場合、平均精度ではなくクラス条件付き誤差の検証が要る。 |

### 5.3 実装上、すぐ持ち帰れる具体点

1. **AI運用ルール公開ページの項目**を Amsterdam/Helsinki AI Register の開示項目 + Model Card の「意図された用途」に揃える。特に「責任者と連絡先」「フィードバック経路」は登録簿では必須項目。
2. **会議録の由来を注記**する（衆議院は音声認識ベースで作成されている＝一次情報にも生成過程がある）。
3. **スタンス分類を行わない、または行う場合は NTCIR PoliInfo の公開データセットで自前の精度を測って公開する**。既存ベンチマークがあるので「測っていない」は選択肢として弱い。
4. **記名投票の可視化は「配置」ではなく「一致/不一致の生データ提示」に留める**。尺度化した瞬間に格付けになる。

---

## 6. 未確認・要追跡

以下は今回の調査で**一次ソースに到達できなかった**もの。記憶や間接言及に基づくため、引用前に必ず確認すること。

1. **【未確認】Gebru et al. "Datasheets for Datasets" の正式書誌**。arXiv:1803.09010、*Communications of the ACM* 64(12), 2021 掲載と記憶しているが、今回は二次的言及（Medium 記事、arXiv:2401.13822）でしか確認できていない。arXiv ページを直接取得して確認すること。
2. **【未確認】Ollion, Shen, Macanovic & Chatelain (2024)** — プロプライエタリLLMを社会科学研究に使うことの危険を論じたとされる文献。arXiv:2503.22040 内での引用としてのみ確認。掲載誌・正確なタイトル未確認。
3. **【未確認】Grimmer & Stewart の "All quantitative models of language are wrong—but some are useful"** は当該論文の有名な一節として広く引かれるが、原文該当箇所を今回直接確認していない。引用する場合は論文本文で照合すること。
4. **【未確認】Consul / decide.madrid.es 側の評価研究**。Decidim (Barcelona) 側の評価研究は確認できたが、Madrid の Consul 単体を対象にした査読評価研究は今回特定できていない。
5. **【未確認】Helsinki AI Register の現在の稼働状況と登録件数**。2020年の立ち上げ報道は確認できたが、現行URLと最新の登録件数は未確認。Amsterdam 側も同様。
6. **【未確認】広聴AI / いどばた の学術的評価**。dd2030.org のリリース情報とプロジェクト側の note 記事は確認できたが、**第三者による査読済みの効果検証は今回発見できていない**。実践知見として引くのは可（出典は当事者発信であると明示すること）、効果の検証済み事実として引くのは不可。
7. **【未確認】チームみらいの2025年参院選での広聴AI利用の定量的実績**（意見件数、マニフェスト反映件数等）。Wikipedia と当事者 note に言及はあるが、数字の一次ソースは未確認。
8. **【未確認】NTCIR PoliInfo の Classification タスクにおける到達精度の具体値**。タスク設計は概要論文で確認したが、賛成/反対/中立分類の最高スコアは各回の概要論文本文を読む必要がある（URLは3.2節に記載済み）。
9. **【未確認】EU AI Act の公共部門AIに対する透明性義務の具体条文**、および日本のデジタル庁・総務省による行政AI利活用ガイドラインの該当箇所。本テーマの4章を補強する材料だが今回未調査。
10. **【未確認】Polis の推薦・クラスタリングアルゴリズムの技術詳細**（PCA + k-means と理解しているが、compdemocracy の技術文書で確認していない）。
11. **【要追跡】検索結果に arXiv:2605.*, 2606.*, 2601.*, 2602.* 等の2026年IDの関連論文（AI熟議、LLMアノテーターの社会的望ましさバイアス、地方議会議事録NLPのベンチマーク論文等）が複数ヒットしたが、内容を直接取得していないため本文には採用しなかった**。特に「NLP for Local Governance Meeting Records: A Focus Article on Tasks, Datasets, Metrics and Benchmark」(https://arxiv.org/pdf/2602.08162) は本テーマに極めて近く、次の調査で最優先で確認すべき。
