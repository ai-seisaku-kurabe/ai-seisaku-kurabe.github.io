# C. AIの政治利用のリスクと規制

調査日: 2026-07-21 / 担当C
方針: WebSearch・WebFetchで実際に取得できた情報のみ記載。確認できなかったものは「7. 未確認・要追跡」に隔離した。争いのある論点は「争いがある」と明示する。

---

## 1. LLM自体の政治的バイアス

### 1-1. 「バイアスがある」と報告した主要研究

**Feng, Park, Liu, Tsvetkov (2023) "From Pretraining Data to Language Models to Downstream Tasks: Tracking the Trails of Political Biases Leading to Unfair NLP Models", ACL 2023（ACL 2023 Best Paper Award）**
- https://aclanthology.org/2023.acl-long.656/
- コード: https://github.com/BunsenFeng/PoliLean
- 内容: 事前学習コーパスの政治的偏りを社会軸・経済軸で測定し、その上に構築した下流タスク（ヘイトスピーチ検出・誤情報検出）モデルの公平性を評価。事前学習済み言語モデルは政治的傾向を持ち、それが下流の分類器に伝播すると報告。
- **本プロジェクトにとっての意味**: 「AIに評価させると、評価対象ではなく評価器の偏りを測ってしまう」ことの最も引用される根拠。

**Rozado, D. (2024) "The political preferences of LLMs", PLOS ONE**
- https://journals.plos.org/plosone/article/file?id=10.1371%2Fjournal.pone.0306621&type=printable
- 手法: Political Compass Test、Eysenck's Political Test など11種の政治的志向テストを、GPT-3.5/GPT-4、Gemini、Claude、Grok、Llama 2、Mistral、Qwen など24の会話型LLMに投与。
- 結果: 多くの会話型LLMの回答が、多くのテスト機器で「中道左派寄り」と診断された。
- **著者自身の留保**: これはLLM開発企業が意図的に政治的選好を注入している証拠と解釈すべきではなく、アノテータ向け指示や支配的な文化的規範の意図せざる副産物である可能性がある、と明記している。
- 報道: https://www.eurekalert.org/news-releases/1052424 / https://techxplore.com/news/2024-07-analysis-reveals-major-source-llms.html

### 1-2. 測定手法そのものへの批判（重要・ここは争いがある）

**Röttger, Hofmann, Pyatkin, Hinck, Kirk, Schütze, Hovy (2024) "Political Compass or Spinning Arrow? Towards More Meaningful Evaluations for Values and Opinions in Large Language Models", ACL 2024**
- https://aclanthology.org/2024.acl-long.816/ / arXiv: https://arxiv.org/abs/2402.16786
- コード: https://github.com/paul-rottger/llm-values-pct
- 主張: 先行研究の多くはモデルをPolitical Compass Test (PCT) の多肢選択形式に**強制的に従わせている**。強制しない場合、モデルは実質的に異なる回答をする。強制の仕方によっても回答が変わる。言い換え（パラフレーズ）に対する頑健性がない。より現実的な自由記述設定では、さらに異なる回答になる。
- 結論: 価値・意見の「制約付き評価パラダイム」そのものに疑義。

**PCTの計測器としての妥当性への疑義（複数の指摘）**
- PCT は査読を経た心理測定尺度ではなく、項目がどう作られ誰に事前テストされたかの文書がほとんどない。誘導的（loaded）な項目を含む、という指摘。
- 関連: "The Elusiveness of Detecting Political Bias in Language Models" (CIKM 2024) https://dl.acm.org/doi/10.1145/3627673.3680002 — LLMの政治的志向は言い回しや文脈の微細な変化で容易に動き、標準的な質問では一貫して現れない。
- 関連: "A Detailed Factor Analysis for the Political Compass Test: Navigating Ideologies of Large Language Models" https://arxiv.org/html/2506.22493v2 — プロンプト変化とファインチューニングがPCTスコアを動かす。
- 理論駆動の代替尺度の提案: "Only a Little to the Left: A Theory-grounded Measure of Political Bias in Large Language Models" https://arxiv.org/html/2503.16148v1
- Paul Röttger による講演「Measuring Political Bias in Large Language Models」(Princeton CITP, 2025) https://citp.princeton.edu/events/2025/paul-r%C3%B6ttger-measuring-political-bias-large-language-models

**まとめ（中立記述）**: 「LLMは左寄りである」という所見は複数研究で再現されている一方、その測定に使われた道具（政治コンパス系テスト、強制選択形式）の妥当性・頑健性には強い学術的批判があり、**効果の存在と効果の大きさ・安定性については争いがある**。ただし本プロジェクトにとって重要なのは方向ではなく、**「どちら向きであれ、モデルの出力する政治的判断は測定条件で揺れる」**という点である。

### 1-3. 評価器としてのLLMの不安定性（LLM-as-a-judge）

政治的バイアス以前に、LLMを「評価者」に据えること自体に系統的バイアスがあることが報告されている。
- 位置バイアス（提示順で先に来た回答を選好）、冗長性バイアス（長い回答を選好）、自己選好バイアス（自分の生成物を高く評価）。
- "Self-Preference Bias in LLM-as-a-Judge" https://arxiv.org/pdf/2410.21819
- サーベイ: "A survey on LLM-as-a-judge" https://www.sciencedirect.com/science/article/pii/S2666675825004564
- 緩和策（順序ランダム化、ルーブリック明示、複数審査員のアンサンブル、モデル名のマスキング）はあるが、完全な除去はできないとされる。
- 参考（近年の指摘）: "Political Bias Audits of LLMs Capture Sycophancy to the Inferred Auditor" https://arxiv.org/pdf/2604.27633 — 政治バイアス監査が、モデルが推測した監査者への迎合（sycophancy）を測っている可能性を指摘。※本文未精読、要確認。

---

## 2. 選挙における生成AIの悪用と、その効果の実証的評価

### 2-1. 「効果は誇張されている」とする側

**Simon, Altay, Mercier (2023) "Misinformation reloaded? Fears about the impact of generative AI on misinformation are overblown", Harvard Kennedy School Misinformation Review**
- https://misinforeview.hks.harvard.edu/article/misinformation-reloaded-fears-about-the-impact-of-generative-ai-on-misinformation-are-overblown/
- PDF: https://misinforeview.hks.harvard.edu/wp-content/uploads/2023/10/simon_generative_AI_fears_20231018.pdf
- 論旨: 生成AIが誤情報の「量」「質」「個別最適化」を増やすという懸念を、コミュニケーション研究・認知科学・政治学の知見から検討し、現在の懸念は過大であると論じる。誤情報の供給がボトルネックだったことはなく、需要側（誰が何を見たいか）が律速である、という議論。

**CETaS（Alan Turing Institute 新興技術・安全保障センター）2024年選挙分析**
- https://cetas.turing.ac.uk/publications/ai-enabled-influence-operations-threat-analysis-2024-uk-and-european-elections
- https://www.turing.ac.uk/news/no-evidence-ai-disinformation-or-deepfakes-impacted-uk-french-or-european-elections-results
- https://cetas.turing.ac.uk/news/ai-generated-images-and-deepfakes-had-little-effect-2024-elections
- 所見: 英国総選挙でAI偽情報・ディープフェイクの「バイラル化した確認事例」は16件、EU・仏選挙合わせて11件。選挙結果に有意な影響を与えた証拠はない。露出は、すでにその主張に賛同していた小集団に限られていた。
- ただし CETaS は「民主的制度への信頼の毀損」「パロディ／ポルノ的ディープフェイクによる新たな害」は別個の懸念として残ると述べている。
- 続編: https://cetas.turing.ac.uk/publications/deepfake-scams-poisoned-chatbots （2025年の選挙安全保障）

### 2-2. 説得力の実証研究（ここが最も動いている領域）

**Salvi, Ribeiro, Gallotti, West "On the conversational persuasiveness of GPT-4", Nature Human Behaviour (2025)**
- https://www.nature.com/articles/s41562-025-02194-6 / arXiv原版 https://arxiv.org/abs/2403.14380 / PMC https://pmc.ncbi.nlm.nih.gov/articles/PMC12367540/
- 設計: 事前登録。2×2×3（対戦相手が人間かGPT-4か／相手が参加者の社会人口統計情報にアクセスできるか／論題の意見強度 低・中・高）、N=900。
- 結果: AIと人間が同等に説得的でなかったペアにおいて、**個人化されたGPT-4がより説得的だったのは64.4%**（事後同意が高くなるオッズの相対増加 +81.2%、95%CI [+26.0%, +160.7%], P<0.01）。
- **重要な限定**: 個人情報にアクセスできない条件では、GPT-4の説得力は人間と区別できなかった。

**Hackenburg & Margetts (2024) "Evaluating the persuasive influence of political microtargeting with large language models", PNAS**
- https://www.pnas.org/doi/10.1073/pnas.2403116121
- リポジトリ: https://github.com/kobihackenburg/GPT-4-political-microtargeting
- 大学発表: https://www.ox.ac.uk/news/2024-06-26-effectiveness-large-language-models-political-microtargeting-assessed-new-study
- 結果: GPT-4生成メッセージは全般に説得的だったが、**マイクロターゲティングされたメッセージの説得効果は、されていないメッセージと統計的に区別できなかった**。著者は「テキストのマイクロターゲティング自体があまり有効な戦略でない」か「GPT-4がこの設計ではうまくターゲティングできない」かの2説を挙げる。
- → **Salvi et al. と方向が食い違っており、この論点は争いがある**（設計・対話形式か一方向メッセージかの違いが効いている可能性）。

**Hackenburg, Tappin, Hewitt et al. (2025) "The levers of political persuasion with conversational artificial intelligence", Science 390(6777)**
- https://www.science.org/doi/10.1126/science.aea3884 / arXiv https://arxiv.org/abs/2507.13919
- 解説記事: https://www.science.org/doi/10.1126/science.aec9293
- 規模: 3実験、42,357人・76,977回答、19のLLM（説得目的でポストトレーニングされたものを含む）、707の政治的争点。LLMの主張466,769件の事実正確性も検証。
- 結果: AIの説得力は、**個人化やモデル規模の拡大よりも、ポストトレーニング（最大+51%）とプロンプト設計（最大+27%）に由来する**。情報・事実を多量かつ戦略的に提示するモデルほど説得的（感情的な語りより有効）。
- **最も重要な所見**: 説得力を上げた手法は、**同時に系統的に事実正確性を下げた**。

### 2-3. マイクロターゲティング（AI以前の基礎研究）

**Tappin, Wittenberg, Hewitt, Berinsky, Rand (2023) "Quantifying the potential persuasive returns to political microtargeting", PNAS 120(25) e2216261120**
- https://www.pnas.org/doi/10.1073/pnas.2216261120 / PMC https://pmc.ncbi.nlm.nih.gov/articles/PMC10288628/
- 規模: 米国成人 32,695人、74種の説得メッセージ。
- 結果: 同一の政策態度を狙う文脈では、マイクロターゲティング戦略が代替戦略を平均70%以上上回った。ただし「潜在的な（potential）リターン」の推定であり、実運用の条件下での上限に近い値である点に注意。

### 2-4. liar's dividend（偽物の存在が本物の否認に使われる）

- 概念の出典: 法学者 Bobby Chesney と Danielle Citron。概観: https://en.wikipedia.org/wiki/Liar's_dividend
- **Kaylyn Jackson Schiff, Daniel Schiff, Natália Bueno "The Liar's Dividend: Can Politicians Claim Misinformation to Evade Accountability?", American Political Science Review**
  - https://www.cambridge.org/core/journals/american-political-science-review/article/liars-dividend-can-politicians-claim-misinformation-to-evade-accountability/687FEE54DBD7ED0C96D72B26606AA073
  - Yale ISPS版: https://isps.yale.edu/research/publications/isps24-07
  - 設計: 米国成人15,000人超に5つのサーベイ実験。実在の政治スキャンダルを題材に、政治家が「誤情報だ」と反論する仮想シナリオを提示。
  - 結果: 「誤情報だ」との主張は党派を超えて政治家支持を上げた。ただし**テキストベースの報道に対しては有効だが、動画証拠に対してはほぼ無効**であり、メディア全般への信頼を下げる効果も見られなかった。
- 政策提言側: Brennan Center "Deepfakes, Elections, and Shrinking the Liar's Dividend" https://www.brennancenter.org/our-work/research-reports/deepfakes-elections-and-shrinking-liars-dividend
- 追加のプレプリント（要確認）: Grohmann, Halle & Appel (2026) "Deepfake! A Liar's Dividend for Audiovisual Material" https://www.mcm.uni-wuerzburg.de/fileadmin/06110000/2026/Grohmann__Halle___Appel_2026__Preprint_.pdf ※プレプリント、未精読。

### 2-5. まとめ（中立記述）
- 「生成AIが2024年の各国選挙結果を動かした」という証拠は、少なくともCETaSの英・EU・仏・米の分析では**見つかっていない**。
- 一方で、AIの説得力そのものは実験室的には確認されており（Salvi 2025、Hackenburg 2025 Science）、**個人化の寄与は当初想定より小さく、ポストトレーニング/プロンプトの寄与が大きい**という方向に知見が移動している。
- 「実験室での説得効果」と「実際の選挙結果への影響」の間には大きな隔たりがあり、ここを混同した報道が多い。この隔たりの評価には争いがある。

---

## 3. 要約・キュレーションによるバイアス

### 3-1. 自動要約の政治的歪み

- "When Neutral Summaries are not that Neutral: Quantifying Political Neutrality in LLM-Generated News Summaries" (AAAI 2025 Student Abstract)
  - arXiv: https://arxiv.org/abs/2410.09978 / PDF: https://arxiv.org/pdf/2410.09978 / AAAI: https://ojs.aaai.org/index.php/AAAI/article/view/35308
  - 20,344本のニュース記事を分析。複数の著名LLMで一貫して民主党寄りの偏りが観察され、銃規制（最大 -9.49%）と医療（-6.14%）で最も顕著。「客観的に要約せよ」と指示しても微妙な政治的傾きが混入しうる。
- "Entity-Based Evaluation of Political Bias in Automatic Summarization" https://arxiv.org/pdf/2305.02321
- "Bias in Opinion Summarisation from Pre-training to Adaptation: A Case Study in Political Bias" https://arxiv.org/pdf/2402.00322
- "P^3SUM: Preserving Author's Perspective in News Summarization with Diffusion Language Models" https://arxiv.org/pdf/2311.09741
- 近年の研究（要確認・未精読）: "When Bigger Isn't Better: A Comprehensive Fairness Evaluation of Political Bias in Multi-News Summarisation" https://arxiv.org/pdf/2604.21309 / "What Stays and What Goes: Auditing the Impact of LLM Summarization on News Partisanship" (CHI 2026 EA) https://dl.acm.org/doi/10.1145/3772363.3799057
  - 注: これらのうち一部は「LLM要約が記事の党派性を中央に引き寄せる」という、上記と逆向きの所見を報告しているとされる。**要約バイアスの方向についても知見が一貫していない**。

### 3-2. チャットボット／検索AIによる選挙情報の誤り

- AlgorithmWatch + AI Forensics「Bing Chat（現 Copilot）の選挙情報調査」（2023年8〜10月、スイス連邦選挙・ヘッセン州・バイエルン州選挙）
  - https://algorithmwatch.org/en/bing-chat-election-2023/
  - https://algorithmwatch.org/en/microsofts-bing-source-misinformation-elections/
  - https://aiforensics.org/work/bing-chat-elections
  - 所見: 回答の約3分の1に事実誤認（誤った選挙日、古い候補者、捏造されたスキャンダル）。40%は質問を回避。正しく報じていた情報源に、誤った回答を帰属させる事例も。1か月後の再サンプリングでも改善は乏しかった。
  - **本プロジェクトにとっての意味**: 「LLMに選挙・政治の事実を生成させる」経路そのものが、この失敗モードを引き受けることになる。

### 3-3. 検索順位・推薦アルゴリズムの政治的効果

**Search Engine Manipulation Effect (SEME) — 効果量に争いがある**
- 原著: Epstein & Robertson (2015) "The search engine manipulation effect (SEME) and its possible impact on the outcomes of elections", PNAS 112(33) https://www.pnas.org/doi/10.1073/pnas.1419828112
  - 5件の二重盲検RCT、未決定有権者4,556人（米国・インド）。偏った検索順位が投票選好を20%以上シフトさせ、被験者は操作に気づかないと報告。
- 批判: AlgorithmWatch の検証記事 https://algorithmwatch.org/en/watching-the-watchers-epstein-and-robertsons-search-engine-manipulation-effect/
  - 情報学者 Katharina Zweig による指摘として、多重比較の補正不足により小さなサブグループで効果量が過大に見積もられた可能性、報告された大きな数値は事前登録されていないサブグループ分析に由来する、という批判が紹介されている。著者自身も検討したグループが「やや恣意的で、重複があり、決定的ではない」と述べている。
  - 実験室的な擬似検索結果への曝露は、実世界のクロスリファレンス行動・クエリの多様性・パーソナライズを無視している、という設計批判。
- 追試: Epstein & Li (2024) "Can biased search results change people's opinions about anything at all? a close replication of the Search Engine Manipulation Effect (SEME)", PLOS ONE https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0300727
  - 注: これは原著者自身による追試であり、独立追試としての強度は限定的。**SEMEの効果量は争いがある**と記述すべき。

**フィルターバブル／エコーチェンバー論争 — 「効果は限定的」とする実証が積み上がっている**
- 2023年、Facebook/Instagram を対象とした大規模実地実験群が Science / Nature に同時掲載。
  - Nature の解説: https://www.nature.com/articles/d41586-023-02325-x
  - Nature の解説（エコーチェンバーの影響は小さい）: https://www.nature.com/articles/d41586-023-02425-8
  - 所見: Facebook 上で同質的コンテンツへの曝露は確かに広く見られるが、2020年米大統領選期間中にその曝露を減らしても、信念・態度の分極に測定可能な効果はなかった。
- レビュー: Reuters Institute「Echo chambers, filter bubbles, and polarisation: a literature review」 https://reutersinstitute.politics.ox.ac.uk/echo-chambers-filter-bubbles-and-polarisation-literature-review
- 系統的レビュー: "A systematic review of echo chamber research: comparative analysis of conceptualizations, operationalizations, and varying outcomes", Journal of Computational Social Science https://link.springer.com/article/10.1007/s42001-025-00381-z
  - 概念定義・操作化がバラバラで、そのために結論が分かれている、という指摘。
- **中立記述**: 「アルゴリズムがフィルターバブルを作り分極を生む」という通俗的主張は、近年の大規模実験では支持されていない。ただし「効果がゼロ」という証明ではなく、測定期間の短さ・介入の局所性という限界も指摘されており、**争いがある**。

### 3-4. 議題設定効果
本調査では、AI固有の議題設定効果を扱った実証研究を特定できなかった。7章に記載。

---

## 4. 規制・法（EU / 日本）

### 4-1. EU AI Act（Regulation (EU) 2024/1689）

**Annex III 8(b)：高リスク分類**
- https://artificialintelligenceact.eu/annex/3/
- 「選挙・国民投票の結果、または選挙・国民投票における自然人の投票行動に影響を与えることを意図して使用されるAIシステム」("intended to be used for influencing the outcome of an election or referendum or the voting behaviour of natural persons in the exercise of their vote in elections or referenda") が高リスクに分類される。
- **明示的な除外**: 「政治キャンペーンを管理的・ロジスティック的観点から組織・最適化・構造化するために用いられるツール」("tools used to organise, optimise or structure political campaigns from an administrative or logistical point of view") は高リスクから除かれる。
- **「AI政策くらべ」との関係**: 同サイトは候補者・政党の説得を目的としたシステムではなく、公開一次情報の集約・提示であるため、8(b) の「投票行動に影響を与えることを意図して」に該当するとは考えにくい。ただし**EU域内向けサービスではないため、そもそも適用対象外**である。この点は法的助言ではなく、条文の読みとしての整理にとどめる。

**Article 50：透明性義務**
- https://artificialintelligenceact.eu/article/50/
- 合成コンテンツを生成するAIシステムは、その出力を人工的に生成・操作されたものとしてマークしなければならない。職務上ディープフェイクを用いる事業者は、当該コンテンツが人工的に生成・操作されたものであることを開示しなければならない（法執行目的で許可された利用は除く）。
- 解説: https://artificialintelligenceact.eu/transparency-rules-article-50/ / https://www.wilmerhale.com/en/insights/blogs/wilmerhale-privacy-and-cybersecurity-law/20240528-limited-risk-ai-a-deep-dive-into-article-50-of-the-european-unions-ai-act
- 適用開始日について: Article 50 の透明性義務が 2026年8月2日から適用される、高リスクの適合性評価期限が Digital Omnibus により 2027年12月2日に延期された、と報じられている（https://www.techtimes.com/articles/320101/20260710/eu-ai-act-enforcement-here-chatbot-rules-live-high-risk-ai-delay-now-binding-law.htm）。**一次情報での確認が未了**。7章参照。

### 4-2. EU DSA（デジタルサービス法）選挙ガイドライン

- 欧州委員会「Guidelines for Providers of VLOPs and VLOSEs on the Mitigation of Systemic Risks for Electoral Processes」（DSA 第35条(3)に基づく）
  - 公開協議ページ: https://digital-strategy.ec.europa.eu/en/consultations/guidelines-providers-very-large-online-platforms-and-very-large-online-search-engines-mitigation
  - ガイドライン一覧: https://digital-strategy.ec.europa.eu/en/policies/dsa-guidelines
  - 協議期間 2024年2月8日〜3月7日、2024年4月に公表。DSA第35条に基づく初のガイドライン。
  - 生成AI関連の緩和措置例として、広告システムにおいて「広告主が生成AIで作成したコンテンツを明確にラベル付けできる選択肢を提供し、広告ポリシーで当該ラベルの使用を義務づける」ことが挙げられている。
  - 解説: https://www.lewissilkin.com/en/insights/2024/05/31/european-commission-publishes-guidelines-under-the-dsa-to-protect-the-integrity-o-102j8xw / https://www.dlapiper.com/en/insights/blogs/mse-today/2024/commission-guidelines-on-systematic-risks-electoral-processes
  - 批判: https://www.liberties.eu/en/stories/dsa-guidelines/45066

### 4-3. EU 政治広告規則（Regulation (EU) 2024/900）

- EUR-Lex: https://eur-lex.europa.eu/eli/reg/2024/900/oj/eng
- 欧州委員会: https://commission.europa.eu/strategy-and-policy/policies/justice-and-fundamental-rights/democracy-eu-citizenship-anti-corruption/democracy-and-electoral-rights/transparency-and-targeting-political-advertising_en
- 2024年3月13日採択、2024年4月9日発効、大部分の規定は2025年10月10日から適用。
- 内容: EU・国・地方すべてのレベルの政治広告に明確なラベル表示を要求し、資金提供者・費用・ターゲティング手法使用時の対象オーディエンスの明示を求める。人種・民族的出自・政治的意見等の特別カテゴリのデータを用いたプロファイリングを禁止。選挙・国民投票の3か月前からEU域外主体による政治広告の資金提供を禁止。
- 解説: https://www.twobirds.com/en/insights/2025/the-eu-political-advertising-regulation-what-you-need-to-know

### 4-4. 米国の州法（AI政治広告の表示義務）

- 2024年8月時点で、AI生成コンテンツの政治広告利用を規律する法律を制定した州は16州とする報道（PBS: https://www.pbs.org/newshour/politics/michigan-to-join-state-level-effort-to-regulate-ai-political-ads-as-federal-legislation-is-pending）。Public Citizen の追跡では2024年7月時点で約20州とも報じられている。**州数は情報源により食い違うため、確定した数字としては扱わない。**
- 大半の州法は生成AIの利用そのものを禁じるのではなく、**AI生成コンテンツを含む旨の開示**を求める形式。カリフォルニア、ミネソタ、テキサス、ワシントンなどが政治広告におけるディープフェイクを規律。ミシガンは選挙前90日以内のAI生成ディープフェイク使用について、改変メディアである旨の別途開示を要求。
- 参考リソース: https://law.washu.edu/ai-policy-and-regulation-resources/political-advertising/ / https://www.dglaw.com/ai-in-political-advertising-state-and-federal-regulations-in-focus/
- 連邦レベル: FEC の規則案「Disclosure and Transparency of Artificial Intelligence-Generated Content in Political Advertisements」 https://www.federalregister.gov/documents/2024/08/05/2024-16977/disclosure-and-transparency-of-artificial-intelligence-generated-content-in-political-advertisements （2024年8月5日 Federal Register 掲載。その後の帰趨は未確認）

### 4-5. 日本の公職選挙法

**第138条の3（人気投票の公表の禁止）— 本プロジェクトに最も直接効く条文**
- 条文（確認済み）: 「何人も、選挙に関し、公職に就くべき者を予想する人気投票の経過又は結果を公表してはならない。」（比例代表選出議員の選挙については、政党その他の政治団体、またはその当選人となるべき者の数・順位を予想するものを含む）
- 罰則: **第242条の2**。「第138条の3の規定に違反して人気投票の経過又は結果を公表した者は、2年以下の禁錮又は30万円以下の罰金に処する。」新聞・雑誌・放送については編集責任者・経営責任者等に関する特例あり。
- 出典（条文本文と罰則条番号の確認に用いた）: https://fukuno.jig.jp/1000549 / 参考: 神戸市FAQ https://faq.city.kobe.lg.jp/faq/show/4036 / 高知市 https://www.city.kochi.kochi.jp/soshiki/99/senkyoundo-sonota.html / 岡山市 https://www.city.okayama.jp/0000011132.html
- 立法趣旨として自治体解説で示されるのは「選挙人が候補者について誤った予断を抱くことを防ぎ、選挙の公正を失わせないため」。
- **重要な留意**: 「禁錮」は2022年改正刑法により2025年6月1日から「拘禁刑」に一本化されているため、現行の法定刑表記が「拘禁刑」に置き換わっている可能性がある。条文の現行表記は未確認（7章）。
- 関連する国会質疑: 「選挙期間中の情勢調査の公表記事に関する質問主意書」 https://www.shugiin.go.jp/internet/itdb_shitsumon.nsf/html/shitsumon/a195026.htm （報道機関の情勢調査と138条の3の関係を問うもの。本プロジェクトの「マッチング結果の匿名集計公開」が人気投票に当たるかの検討で参照価値あり）

**ネット選挙運動関連（2013年解禁）**
- 総務省の解説ページ群:
  - 概要 https://www.soumu.go.jp/senkyo/senkyo_s/naruhodo/naruhodo10.html
  - (1) インターネット等を利用する方法による選挙運動の解禁等 https://www.soumu.go.jp/senkyo/senkyo_s/naruhodo/naruhodo10_2.html
  - (2) 誹謗中傷・なりすまし対策 https://www.soumu.go.jp/senkyo/senkyo_s/naruhodo/naruhodo10_3.html
  - 現行の選挙運動の規制 https://www.soumu.go.jp/senkyo/senkyo_s/naruhodo/naruhodo10_1.html
- **第142条の3**: ウェブサイト等を利用する方法による選挙運動用文書図画の頒布（ウェブサイト、ブログ、SNS、動画共有サービス等。一般有権者も可）。
- **第142条の3第3項（および落選運動につき第142条の5第1項）**: 選挙運動用文書図画を掲載するウェブサイト等には**電子メールアドレス等の表示義務**。「電子メールアドレス等」には返信用フォームのURLやSNSのユーザー名も含まれる。ハンドルネームのみは不可だが、リンク先に連絡先が記載されていれば足りるとされる。違反の罰則は1年以下の禁錮または30万円以下の罰金、禁錮刑の場合は選挙権・被選挙権が停止。
  - 出典: https://www.soumu.go.jp/senkyo/senkyo_s/naruhodo/naruhodo10_2.html / 衆議院 法律案要綱 https://www.shugiin.go.jp/internet/itdb_annai.nsf/html/statics/housei/pdf/183hou3youkou.pdf / 改正法 https://www.shugiin.go.jp/internet/itdb_housei.nsf/html/housei/18320130426010.htm
- **第142条の4**: 電子メールを利用する方法による選挙運動用文書図画の頒布。**候補者・政党等に限定**され、一般有権者には認められない。
- **なりすまし・虚偽表示（第235条の5）**: 当選を得若しくは得しめ又は得しめない目的をもって、真実に反する氏名・名称・身分を表示してインターネット等を利用する方法により通信をした者は、2年以下の禁錮又は30万円以下の罰金。
- **虚偽事項公表罪（第235条）**: 第2項について、4年以下の懲役又は100万円以下の罰金（総務省ページからの抽出。条項の細部は要再確認）。
- 参考文献: 参議院常任委員会調査室・特別調査室「インターネット選挙運動をめぐる諸問題 —SNSや動画共有サイトにおける選挙運動—」（2025年7月25日）https://www.sangiin.go.jp/japanese/annai/chousa/rippou_chousa/backnumber/2025pdf/20250725173.pdf ※PDFテキスト抽出に失敗、内容未確認。要精読。
- 参考: 湯淺墾道「インターネット選挙運動の解禁に関する諸問題」情報セキュリティ総合科学 第5号（2013年11月） https://www.iisec.ac.jp/proc/vol0005/yuasa13.pdf

**選挙運動におけるAI表示義務の立法動向（進行中）**
- 2026年5月27日、与野党9党による「選挙運動に関する各党協議会」が、SNS上の偽・誤情報対策を含む**公職選挙法改正案の骨子**をまとめた。
  - 時事通信（2026年5月27日）https://www.jiji.com/jc/article?k=2026052700858&g=pol
  - ITmedia https://www.itmedia.co.jp/news/articles/2605/27/news072.html
  - 東京新聞 https://www.tokyo-np.co.jp/article/488128
  - 日経 https://www.nikkei.com/article/DGXZQOUA273UK0X20C26A4000000/
  - 骨子の内容（時事通信の記述に基づく）:
    - AIで作成した動画・画像で、**実際に撮影したと誤認される恐れがあるもの**に「AI作成」の表示を義務付ける
    - 明らかにAI使用と判別できる動画・画像は表示義務の対象外
    - インターネット利用者が候補者に関する虚偽情報を発信して選挙の公正を害することを禁止（罰則は継続議論）
    - SNS事業者に偽・誤情報対策（偽情報拡散アカウントの収益化停止、迅速な削除等）を義務づけ
    - 来春の統一地方選からの適用を想定、今国会中の法案提出を目指す
- **注意**: 対象は「動画・画像」であり、テキストや集計・可視化は骨子の記述からは対象外に見える。ただし条文化の過程で変わりうる。**成立・条文は未確認（2026年7月時点）。**

**その他の日本の関連法・行政対応**
- **AI推進法（人工知能関連技術の研究開発及び活用の推進に関する法律）**: 2025年5月28日成立、6月4日公布、2025年9月全面施行。内閣にAI戦略本部を置き、AI基本計画を策定。**直接の罰則規定はなく**、不適切な利用については調査・分析に基づく指導・助言、改善しない場合の事業者名公表等。
  - 政府広報 https://www.gov-online.go.jp/hlj/ja/november_2025/november_2025-08.html
  - 解説 https://www.businesslawyers.jp/articles/1475 / https://www.jdsupra.com/legalnews/ai-9046252/
  - **政治利用への直接の言及は、本調査で確認できなかった**（7章）。
- **情報流通プラットフォーム対処法（情プラ法）**: 2024年5月17日公布、**2025年4月1日施行**。大規模プラットフォーム事業者に対し、削除申出への対応の迅速化と運用状況の透明化を義務づける。2025年4月に Google LLC、LINEヤフー、Meta Platforms、TikTok Pte. Ltd.、X Corp. の5社を大規模特定電気通信役務提供者に指定。
  - 総務省 https://www.soumu.go.jp/main_sosiki/joho_tsusin/d_syohi/ihoyugai.html
  - 令和7年版情報通信白書 https://www.soumu.go.jp/johotsusintokei//whitepaper/ja/r07/html/nd123210.html
  - 指定報道 https://internet.watch.impress.co.jp/docs/news/2011282.html
- **選挙時の総務省の要請**: 2025年7月の第27回参議院議員通常選挙に際し、総務省はプラットフォーム事業者に利用規約等に基づく適切な対応、大規模事業者には削除申出窓口の公表・削除の適否の迅速な判断・削除基準の策定と公表等を要請。2024年10月の衆院選時にもSNS運営・AI開発の事業者に偽情報対応を要請したと報じられている（社数14との記載があるが、一次情報未確認）。
- **偽・誤情報対策技術の開発・実証事業（令和7年度）**: 総務省が生成AI起因の偽・誤情報を含むネット上の偽・誤情報への対策技術について、技術開発主体14者、研究・調査主体6者を採択。https://www.soumu.go.jp/main_sosiki/joho_tsusin/d_syohi/taisakugijutsu_fy2025.html
- 令和7年版情報通信白書（主な課題の概要） https://www.soumu.go.jp/johotsusintokei/whitepaper/ja/r07/html/nd123100.html

---

## 5. AI利用の開示規範

### 5-1. 報道機関向けの国際的規範

**Paris Charter on AI and Journalism（2023年11月10日、RSF ＝ 国境なき記者団と16パートナー）**
- https://rsf.org/en/paris-charter-ai-and-journalism
- 全文PDF: https://rsf.org/sites/default/files/medias/file/2023/11/Paris%20charter%20on%20AI%20in%20Journalism.pdf
- 発表: https://rsf.org/en/rsf-and-16-partners-unveil-paris-charter-ai-and-journalism
- マリア・レッサ（ノーベル平和賞受賞者）を委員長とし、20か国32名の委員が策定。10原則。
- 開示・透明性に関する原則（要旨）:
  - メディアはAIシステムの利用について透明性を維持する。ジャーナリスティックなコンテンツの**制作または配信に重大な影響を与えるAI利用は、明確に開示**され、当該コンテンツとともに受け手に伝えられるべき。
  - メディアは、**使用中および過去に使用したAIシステムの公開記録**を維持し、その目的・範囲・利用条件を記載すべき。
  - コンテンツの出所と追跡可能性を確保し、可能な限り真正性・来歴を保証する最新のツールを用いるべき。
- 批判的レビュー: https://thefix.media/2023/11/24/review-of-rsfs-new-guidelines-on-using-ai-in-journalism-what-they-achieve-and-where-they-fall-short/
- 参加団体の例: GIJN https://gijn.org/stories/gijn-joins-paris-charter-on-ai-and-journalism/ / IPTC https://iptc.org/news/the-iptc-welcomes-rsfs-paris-charter-on-ai-and-journalism/

### 5-2. 日本

**日本新聞協会**
- 声明・見解の一覧: https://www.pressnet.or.jp/statement/ai/
- 「生成AIによる報道コンテンツ利用をめぐる見解」（2023年5月17日）https://www.pressnet.or.jp/statement/20230517.pdf
- 「生成AIにおける報道コンテンツの保護に関する声明」（2025年6月4日）https://www.pressnet.or.jp/statement/ai/250604_15900.html
  - 生成AI開発企業に対し、ニュースサイト上で著作権者が示す利用拒否の意思（robots.txt 等）の順守と、報道記事の学習・利用にあたっての許諾取得を求める。
- 関連: 記者への誹謗中傷をめぐる声明 https://www.pressnet.or.jp/news/headline/250610_15918.html
- **留意**: 新聞協会の一連の声明は主として**「報道コンテンツが学習に使われる側」の権利**を扱っており、**「報道機関が自らAIを使ったことをどう開示するか」の統一ガイドラインは、本調査では確認できなかった**（7章）。

### 5-3. 規範の要点整理（本プロジェクトへの示唆）
上記から抽出できる共通の開示規範は概ね以下:
1. **重大な影響のあるAI利用は開示する**（Paris Charter）。逆に言えば、些末な補助的利用まで開示を要求する規範ではない。
2. **どのシステムを、どの目的・範囲・条件で使ったかの公開記録を持つ**（Paris Charter）。
3. **合成メディアには機械可読／人間可読のラベルを付す**（EU AI Act Art.50、DSA選挙ガイドライン、米国州法、日本の与野党骨子案）。
4. ラベルの対象は各法域とも**主に「実写と誤認されうる合成の音声・映像・画像」**であり、テキスト生成や集計・可視化への表示義務は、確認できた範囲では課されていない。

---

## 6. 「AI政策くらべ」への含意

※ 以下はサイトの公表原則（「点数化・格付けをしない」「AIに評価の結論を出力させない」「一次情報を機械的に収集」）を前提とした整理であり、法的助言ではない。

### 6-1. 既に手当てできている点

- **「AIに評価の結論を出力させない」原則は、1章の知見によって直接的に正当化される。** Feng et al. (ACL 2023) はモデルの政治的傾向が下流分類器に伝播することを示し、LLM-as-a-judge研究は位置・冗長性・自己選好の系統的バイアスを示している。加えて Röttger et al. (ACL 2024) は、モデルの政治的立場の測定自体が形式・言い回しに依存して揺れることを示した。**「LLMが左寄りか右寄りか」以前に、「LLMの政治的判断は測定条件で揺れるので評価器として使えない」**という論拠のほうが、より強く、より中立的である。この立て方を採るべき。
- **「点数化・格付けをしない」原則は、3-1（自動要約の党派的歪み）と3-2（Bing Chat の選挙情報誤答）の失敗モードを構造的に回避している。** LLMに要約・スコアリングをさせないなら、これらのバイアス経路がそもそも存在しない。
- **一次情報（会議録の発言、記名投票）を機械的に収集する設計は、AI Act Annex III 8(b) の「投票行動に影響を与えることを意図した」システムからは距離がある**（そもそもEU域外で適用対象外だが、設計思想としての整合）。
- **合成メディア（音声・映像・画像）を生成していないため、EU AI Act Art.50、米州法、日本の与野党骨子案の「AI作成」表示義務のいずれも、現行の設計では直接の対象にならない**と読める。

### 6-2. リスクが残る点

- **【最優先】公選法138条の3（人気投票の公表禁止）との関係。** 政策マッチング機能の利用者回答を匿名集計して公開する仕組みは、集計の見せ方によっては「公職に就くべき者を予想する人気投票の経過又は結果の公表」に該当しうる。罰則は242条の2（2年以下の禁錮又は30万円以下の罰金）。
  - 論点: (a) マッチング結果が「候補者・政党への支持」の形で集計・公開されているか、それとも「政策論点への賛否」の分布として公開されているか。(b) 集計が選挙期間中に更新・公開されるか。(c) 「予想」の要素があるか。
  - 本調査は法解釈を確定できない。**選挙管理委員会または弁護士への照会が必要**。「選挙期間中の情勢調査の公表記事に関する質問主意書」（https://www.shugiin.go.jp/internet/itdb_shitsumon.nsf/html/shitsumon/a195026.htm）は報道機関の情勢調査との線引きを論じており、照会前の下調べに有用。
- **公選法142条の3第3項の電子メールアドレス等表示義務。** サイトの掲載内容が「選挙運動用文書図画」に該当すると評価される場合、連絡先（メールアドレス、返信フォームURL、SNSユーザー名等）の表示義務が生じ、違反には罰則がある。個人運営サイトが「選挙運動」ではなく「情報提供」であると主張しうるかは、選挙期間中の掲載態様に依存する。**個人運営である以上、連絡先を表示しておくのはコストの低い予防策**である。
- **項目選択という不可避のキュレーション。** どの発言・どの投票・どの政策論点を取り上げるかの選択自体が、点数化しなくても議題設定的な効果を持つ。3章の議題設定に関する実証を本調査では特定できなかったが、リスクとしては残る。**選定基準を機械的ルールとして明文化・公開し、除外された対象も列挙可能にしておく**ことが、この批判に対する最も強い防御になる。
- **政策マッチングの設問設計が「誘導的項目」問題を抱えうる。** 1-2で見たPCTへの批判（loaded な項目、強制選択形式、言い換え非頑健性）は、そのまま政策マッチングの設問設計への批判になりうる。**設問の全文・選択肢・スコアリングロジックを公開し、言い換えによる結果の変動を自ら検証・公開する**ことが誠実な対応になる。
- **要約・見出し生成にLLMを一切使っていないかの確認。** 3-1の研究は「客観的に要約せよ」という指示下でも党派的傾きが混入することを示している。もし補助的にでもLLM要約を使っているなら、それは原則の実質的な破れになる。使っていないなら明示すべき。
- **AI利用の開示。** Paris Charter の規範（重大な影響のあるAI利用は開示し、使用システムの公開記録を持つ）に照らすと、「AIに評価させない」という原則を掲げるサイトほど、**「では何にはAIを使っているのか」（収集スクリプトの補助、コード生成、表記ゆれの正規化など）を明示的に記載する価値が高い**。原則の宣言だけでは、読者は検証できない。
- **liar's dividend の逆方向のリスク。** 2-4の Schiff et al. の所見では、「誤情報だ」という主張はテキストベースの報道に対して有効だった。**本サイトは会議録テキストと投票記録という、まさにテキストベースの証拠を扱っている。** 掲載内容を「AIが作った偽物だ」と否認される可能性に対しては、**一次情報へのdeep linkと取得日時・取得元の明示、収集スクリプトの公開**が最も実効的な対抗手段である（Paris Charter の「出所と追跡可能性」原則とも一致）。

---

## 7. 未確認・要追跡

以下は本調査で**確認できなかった、または一次情報に到達できなかった**項目。記述に使う前に検証が必要。

1. **公職選挙法の現行条文表記**: e-Gov API（https://laws.e-gov.go.jp/api/1/lawdata/325AC1000000100）からは冒頭章までしか取得できず、138条の3、142条の3、235条の5、242条の2 の**現行の正式条文テキストを一次情報で確認できていない**。特に2025年6月1日施行の刑法改正（懲役・禁錮→拘禁刑）が法定刑の表記に反映されているかは未確認。**e-Gov の法令ページで直接確認すること。**
2. **235条第2項（虚偽事項公表罪）の法定刑**: 総務省ページからの抽出で「4年以下の懲役又は100万円以下の罰金」とあるが、条項の細部と現行表記は未確認。
3. **参議院調査室「インターネット選挙運動をめぐる諸問題」（2025年7月25日）**: PDFのテキスト抽出に失敗（3.8MB）。AI・生成AIへの言及が含まれる可能性が高く、日本の論点整理として最も価値が高い文献。**要精読。** https://www.sangiin.go.jp/japanese/annai/chousa/rippou_chousa/backnumber/2025pdf/20250725173.pdf
4. **2026年公選法改正案の帰趨**: 2026年5月27日の与野党骨子（AI作成表示義務化）が法案として提出・成立したか、条文がどうなったかは未確認。**2026年7月時点で継続追跡が必要。** 特に表示義務の対象が「動画・画像」に留まるか、テキスト・集計にも及ぶかは本プロジェクトに直結する。
5. **EU AI Act の適用日程**: Article 50 の適用開始（2026年8月2日とされる）および Digital Omnibus による高リスク適合性評価の延期（2027年12月2日とされる）は、二次的なニュース記事（techtimes.com）でのみ確認。**EUR-Lex の一次情報で確認すること。**
6. **AI推進法における政治利用への言及**: AI推進法の条文に、選挙・政治利用に触れる規定があるかを**確認できなかった**。条文（e-Gov）にあたる必要がある。現時点では「確認できていない」以上のことは書けない。
7. **日本の報道機関の「自社のAI利用の開示」ガイドライン**: 日本新聞協会の声明群は「学習に使われる側」の権利が中心で、自社AI利用の開示規範は確認できなかった。NHK、朝日、読売、日経等の個社ガイドラインは未調査。
8. **AI固有の議題設定効果の実証研究**: LLM/推薦アルゴリズムによるアジェンダセッティング効果を直接測った査読研究を特定できなかった。
9. **要約バイアスの方向の不一致**: 3-1で「民主党寄りに偏る」とする研究と「中央に引き寄せる」とする研究の両方に言及したが、後者（arXiv 2604.21309、CHI 2026 EA）は**本文未精読**。検索スニペット由来の記述であり、そのまま引用しないこと。
10. **arXiv 2604.27633（政治バイアス監査とsycophancy）、arXiv 2509.18446（2024年米大統領選期間のLLM縦断調査）、Grohmann/Halle/Appel (2026) プレプリント**: いずれも検索で存在を確認したのみで**本文未読**。
11. **総務省が2024年衆院選時にSNS・AI開発の「14社」に要請した件**: 二次情報でのみ確認。総務省の一次情報（報道資料）で確認すること。なお「令和7年度 偽・誤情報等への対策技術の開発・実証事業」で技術開発主体14者を採択した件は別件であり、**混同しないこと**。
12. **情プラ法の大規模事業者指定（2025年5月の追加指定分）**: 検索結果に不自然な社名が混入しており、信頼できない。総務省の一次情報で確認すること。4-4に記載した2025年4月指定の5社（Google、LINEヤフー、Meta、TikTok、X）のみが確認済み。
13. **米国州法の州数**: 「16州」（PBS、2024年8月）と「約20州」（Public Citizen、2024年7月）で食い違う。Public Citizen のトラッカー本体のURLに到達できていない。
14. **FEC の AI政治広告規則案のその後**: 2024年8月の Federal Register 掲載以降、規則が確定したか撤回されたかは未確認。
15. **SEME の独立追試の有無**: Epstein & Li (2024, PLOS ONE) は原著者による追試。Max Planck Institute のチームによる追試があるとの記述を二次情報で見たが、**具体的な文献を特定できなかった**。独立追試の状況が確認できるまで、SEMEの効果量は「争いがある」以上には書かないこと。
