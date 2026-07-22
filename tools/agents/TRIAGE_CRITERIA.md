# 採決トリアージの取り決め(記名投票の全件判定)

「政策で照らす」の設問開示にあった「多くは検討そのものをしていません」を解消するための手続き。
掲載3会期の参議院記名投票**全件**に、設問候補性の判定(理由コード)を付け、判定表ごと公開する。

設計相談の記録: `C:\Users\madak\,politics\vote_triage_design_20260722.md`(ChatGPT gpt-5.5との検討、2026-07-22)。

## 原則(サイト憲法の適用)

1. **「除外」ではなく「分類」。** どのコードも「重要でない」という意味を持たない。全会一致は
   「弁別力がない」だけ、人事案件は「設問の形に変換しない」だけ。コードの説明文にもそう書く。
2. **全件を表に残す。** フィルタで見えなくしない。判定表は votes.html で全280件を公開する。
3. **機械でできる段は機械、編集判断の段は人間。** 機械段(layer: machine)の判定語・規則は
   `triage_votes.py` にあり、公開リポジトリで再現できる。人間段(layer: human)は
   AIが下書きし、運営者がPRで確認して確定する(AIに最終判断をさせない)。
4. **基準は版管理する。** `vote_triage_criteria.json` の `criteria_version`。基準を変えたら
   版を上げ、変更履歴をこのファイルに残す。
5. **弁別力の数値足切りをしない。** 「反対が1党だけだから除外」のような規則は置かない
   (少数政党の立場を系統的に消すため)。全会一致(反対0)だけを機械判定する。

## 単一ソース

- コードの定義 = `tools/vote_triage_criteria.json`(唯一の原本。votes.htmlの公開文面はここから生成)
- 機械規則 = `tools/agents/triage_votes.py`
- 人間の判定 = `tools/triage_overrides.json`(AI下書き→PR承認)
- 出力 = `tools/vote_triage.json`(votes.htmlが読む判定表。手で編集しない)

## 判定の優先順位

USED > PERSONNEL > ACCOUNTS > PROCEDURAL > NO_DIFF > (人間判定: AMBIGUOUS / REPRESENTED / TOO_NARROW / CANDIDATE)

類型による分類(人事・会計・院運営)を全会一致より先に適用する。全会一致かどうかは
「他の理由では設問候補になりえた採決」についてだけ意味を持つため。

## 段組み(ファネル)

- Stage 0 母集団の固定: 掲載会期は `build_party.py sessions_for()` が唯一の出どころ。
  会期を増減したら `triage_votes.py` を回し直す(③検証班が会期の不一致をFAILにする)。
- Stage 1-2 機械タグと決定論分類: 全会一致(全会派の反対0)・件名による類型
  (任命に関する件/決算・調書・計算書/規則・規程)・党別賛否パターン。
- Stage 3-5 人間判定: 残る議案の設問候補性(AMBIGUOUS/REPRESENTED/TOO_NARROW/CANDIDATE)。
  AIが `triage_overrides.json` を下書きし、運営者がPRで確定。既定は CANDIDATE
  (=候補として成立するが未採用。デフォルトを「除外」にしない)。

## 更新手順(会期が増えたとき)

1. `fetch_session_votes.py <会期>` で全件取得
2. `python agents/triage_votes.py` → 未判定(新規)の一覧が出る
3. AIが overrides の下書きを作り、PRで運営者が確定
4. `build_site.py` → `deploy_to_repo.py` → verify FAIL 0 を確認して公開

## 変更履歴

- 2026-07-v1: 初版(280件=第217回136/第219回31/第221回113)。
