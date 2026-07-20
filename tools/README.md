# tools/ — サイト生成系と、運用を分担するエージェント

このフォルダには「政策くらべ」を**再生成するための一式**と、
運用を分担する**エージェント（班）**が入っています。

> ここが無いとサイトは二度と再生成できません。以前は生成スクリプトが
> 作業用の一時フォルダにしか存在せず、失われる寸前でした。

## 班の構成と、承認ゲートの位置

| 班 | 実体 | 実行 | 人の承認 |
|---|---|---|---|
| ① 収集 | `agents/watch_sources.py` | 週次 (Actions) | 不要（読むだけ） |
| ② 編集 | `agents/EDITOR.md`（AIへの指示書） | 人が起動 | **必要**（PRをマージ） |
| ③ 検証 | `agents/verify_content.py` | PR時・週次 (Actions) | 不要（止めるだけ） |
| ⑥ 運用 | `agents/health_check.py` | 日次 (Actions) | 不要（知らせるだけ） |
| ⑧ 査読 | `agents/REVIEW_CHARTER.md` ＋ `agents/make_review_request.py` | 人がPRごとに起動 | **必要**（BLOCKを裁く） |

設計の要点は4つです。

1. **決定論的な処理はActionsへ、判断が要る処理だけAIへ。**
   ①③⑥はただのPythonで、AIもAPIキーも要りません（無料で動き、結果が再現します）。
   ②⑧だけがAIの仕事です。
2. **書いた本人に採点させない。** ②編集班の出力は必ず③検証班が点検します。
3. **機械で落とせないものは、別のAIに点検させる。** ③をすり抜ける「判断の誤り」は、
   ⑧査読班が複数のAIに独立して見せて拾います。**多数決はせず、最終判断は人**です。
4. **状態はGitに置く。** 誰が何を変えたか全部追えます。

## mainへの反映（2026-07-21に変更）

**Claudeは `main` へ直接プッシュしてよい。** 以前は全変更をPRで止めて人がマージしていましたが、
typo修正のたびに人手が要るのは割に合わないため、ユーザーの判断で変更しました。

規律は「AIの出力は、**機械的検証を通るか、人間が承認するか**のどちらかを経ずに公開しない」
（`docs/ai_review.md`）。PRを経ないなら、機械的検証の方を先に通します。

| 変更の種類 | 反映のしかた |
|---|---|
| コード・ツール・CI・文言の修正 | **手元で③検証班を通してから直接プッシュ** |
| 掲載データ・編集判断を含む変更 | 同上。ただし⑧査読班に回してからにする |
| **憲法8条・掲載方針の変更** | **PRで止めて人の承認を待つ**（土台を動かす判断のため） |

`verify-content.yml` は `main` へのプッシュでも走りますが、**それは公開の後**です。
CIは取りこぼしの保険であって、ゲートではありません。**押す前に手元で通してください。**

## サイトの再生成

```bash
cd tools
python build_site.py        # site/ に全ページを生成
python deploy_to_repo.py    # site/*.html だけを ../ へ反映
cd .. && git diff           # 差分を確認してからコミット
```

生成の依存関係:

```
build_guide.py    … 46件の発言＋採決データ（すべての元）
   └ build_party.py   … 政党タブ主体のガイドを生成（ワンイシュー/政策パッケージ）
build_shindan.py  … 「政策で照らす」11問
build_shukei.py   … 「みんなの結果」
   └ build_site.py    … 上記を実行し、トップ/ワンイシュー/サイトについて/マイノートを追加生成
```

## ⚠️ 絶対にやってはいけないこと

- **`firebase.js` を `site/` の生成物で上書きしない。**
  `build_site.py` はプレースホルダ版を生成します。これを配ると本番の
  `apiKey` / `appId` が消え、集計もApp Checkも壊れます。
  → **必ず `deploy_to_repo.py` を使ってください**（HTML以外をコピーしない設計です）。
- **`news.json` を手元のスナップショットで上書きしない。**
  GitHub Actions（`news.yml`）が毎日自動更新しています。

## 各エージェントの使い方

```bash
# ① 未掲載の新しい一次情報を探す
python agents/watch_sources.py
python agents/watch_sources.py --update-state   # 確認済みとして記録

# ③ 掲載内容がルールを守れているか点検（引用の原文照合・リンク・評価語・憲法）
python agents/verify_content.py
python agents/verify_content.py --offline       # 通信なしの項目だけ（速い）

# ⑥ 公開サイトが壊れていないか外から点検
python agents/health_check.py

# ⑧ 他のAIに貼る査読依頼文をつくる（憲法8条＋差分を一枚にまとめる）
python agents/make_review_request.py --out review.txt
```

## データ取得スクリプト（②編集班が新会期を足すときの参考）

`fetch_votes.py`（参院記名投票）、`fiscal_digest.py` / `diplo_pull.py` / `ss_pull.py` /
`energy_pull.py` / `econ_pull.py` / `kenpo_pull.py`（分野別の発言）、
`fetch_oneissue.py`（ワンイシュー深掘り用の発言）。

## 既知の課題

`agents/watch_sources.py` が示すとおり、掲載範囲は**第217回国会**のままで、
第219回・第221回の採決と、それ以降の大量の発言が未掲載です。
これがこのサイト最大のリスク（データの陳腐化）であり、②編集班の最優先課題です。
