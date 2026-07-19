# 政策くらべ（比例区・投票ガイド）デプロイ手順

静的サイト（index / guide / shindan / shukei）＋ Firestore(集計) の構成です。
**Firebase未設定でも全ページ動きます**（結果送信と集計だけ無効）。

## ファイル
- index.html … トップ（政策パッケージ一覧＋各ページへの導線）
- guide.html … 政党で選ぶ（言と行）
- shindan.html … 相性診断（結果を Firestore に集計送信）
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
診断の各設問に、その争点のGoogle News見出しを表示します（同梱の news.json を読むだけ）。
- **手動更新**：`python update_news.py` を実行すると news.json が更新されます。更新後、フォルダを再アップロード。
- **自動更新（GitHub Actions・無料）**：このフォルダをGitHubリポジトリに置くと、同梱の
  `.github/workflows/news.yml` が**毎日自動で** news.json を更新します（Netlify/Cloudflare等をそのリポジトリに
  連携すれば、更新のたび自動で再公開）。※Netlify Dropの手動運用のままなら「手動更新」でOK。
- 見出し＋出典＋リンクのみ表示（本文は転載しません）。
