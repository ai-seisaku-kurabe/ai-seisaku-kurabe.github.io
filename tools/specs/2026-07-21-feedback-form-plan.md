# ご意見フォーム 実装計画

> **作業者向け:** 設計は `tools/specs/2026-07-21-feedback-form-design.md`。
> 各ステップはチェックボックスで進捗を追う。**タスクの順番を入れ替えないこと**
> （Task 1 でルールを閉じる前にフォームを公開すると、意見が全世界から読める）。

**目的:** GitHubアカウントを持たない人が、このサイトに直接ご意見を送れるようにする。

**方式:** 静的サイトのフォームから Firestore の `feedback` コレクションへ直接書き込む。
読み取りはルールで全面禁止し、運営者は Firebase コンソールでのみ読む。新着は
GitHub Actions が週次で**件数だけ**数える。

**技術:** Firebase Firestore（Spark プラン・App Check 適用済み）／Firestore REST API ＋
サービスアカウント（`FIREBASE_SA_KEY`）／GitHub Actions ／ 生成は `tools/build_site.py`。

## 全体の制約

これは全タスクに適用される。各タスクの要件に暗黙に含まれる。

- **このリポジトリには単体テストの枠組みが無い。** 検証は ①`agents/verify_content.py`
  ②`agents/health_check.py` ③ブラウザでの実測、で行う。pytest 等を新規に導入しない。
- **HTML を直接編集しない。** `feedback.html` などの生成物は `tools/build_site.py` から
  作り、`tools/deploy_to_repo.py` で配布する。
- **`firebase.js` と `news.json` は `deploy_to_repo.py` が配布しない。**
  `firebase.js` はリポジトリのものを直接編集する（本番の apiKey / appId が入っている）。
- **push の前に `PYTHONIOENCODING=utf-8 python agents/verify_content.py` を通す**（FAIL 0）。
  cp932 環境では環境変数が無いと UnicodeEncodeError で落ちる。
- **`about.html` の変更（Task 6）は憲法にあたるため、直接 push せず PR で人の承認を待つ。**
  Task 1〜5 は直接 push してよい。
- **評価語を使わない。** 画面に出す文言に「素晴らしい」「無責任」等を入れない
  （`agents/verify_content.py` の `BANNED` が検査する）。
- **個人情報を保存しない。** メールアドレス・IP・User-Agent を受け取るコードを書かない。
- 作業ブランチ: `docs/feedback-form-design`（worktree で作業する。共有クローン
  `C:\Users\madak\,politics\seisaku-kurabe` は別セッションが使っているので触らない）。

---

### Task 1: Firestore のルールを閉じたまま開ける

**ファイル:**
- 変更: `firestore.rules`
- 人の操作: Firebase コンソール → Firestore Database → ルール

**インターフェース:**
- 提供: `feedback` コレクションへの `create` のみ許可。`text`(1〜2000字) / `from`(40字以内) /
  `at`(サーバー時刻) の3項目に限定。`read` `update` `delete` は全面禁止。

**このタスクだけは、リポジトリへのコミットでは反映されない。** `firestore.rules` は
リポジトリ内の控えで、実際に効くのは Firebase コンソールに貼り付けたものになる。

- [ ] **Step 1: 現状で書き込みが拒否されることを確認する**

公開サイトの `shindan.html` は Firebase SDK を読み込んでいるので、そこで試す。
ブラウザで `https://ai-seisaku-kurabe.github.io/shindan.html` を開き、開発者ツールの
コンソールで実行する。

```js
firebase.firestore().collection('feedback')
  .add({text:'テスト', from:'manual', at: firebase.firestore.FieldValue.serverTimestamp()})
  .then(()=>console.log('書けた（想定外）')).catch(e=>console.log('拒否:', e.code));
```

期待: `拒否: permission-denied`（現在のルールは `aggregates/summary` 以外を全部禁止している）

- [ ] **Step 2: `firestore.rules` を書き換える**

`firestore.rules` を次の内容にする。既存の `aggregates/summary` のコメントは
App Check 適用済みの実態に合わせて直す。

```
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 集計カウンター。読み取り自由 / aggregates/summary の更新のみ許可 / 削除禁止。
    // 悪用対策は App Check（reCAPTCHA v3）を 2026-07-20 に適用済み。
    match /aggregates/summary {
      allow read: if true;
      allow create, update: if true;
      allow delete: if false;
    }

    // ご意見。書き込めるが、誰も読めない。
    // 運営者が読む経路は Firebase コンソールと、ルールを迂回できる
    // サービスアカウント（件数の集計）の2つだけ。
    match /feedback/{id} {
      allow create: if request.resource.data.keys().hasOnly(['text','from','at'])
                 && request.resource.data.text is string
                 && request.resource.data.text.size() > 0
                 && request.resource.data.text.size() <= 2000
                 && request.resource.data.from is string
                 && request.resource.data.from.size() <= 40
                 && request.resource.data.at == request.time;
      allow read, update, delete: if false;
    }

    match /{document=**} { allow read, write: if false; }
  }
}
```

- [ ] **Step 3: Firebase コンソールに貼り付けて公開する（人の操作）**

Firebase コンソール → プロジェクト `aipolitics-9c657` → Firestore Database → 「ルール」
タブ → 上記を貼り付け → 「公開」。反映まで最大1分ほどかかる。

- [ ] **Step 4: 書き込めるようになったことを確認する**

Step 1 と同じコンソールで、同じコードを再実行する。

期待: `書けた（想定外）` と表示される（このステップでは想定内）

- [ ] **Step 5: 読み取りが拒否されることを確認する（最重要）**

```js
firebase.firestore().collection('feedback').get()
  .then(s=>console.log('読めた（重大な誤り）:', s.size)).catch(e=>console.log('拒否:', e.code));
```

期待: `拒否: permission-denied`

**ここで「読めた」と出たら、絶対に先へ進まないこと。** ルールを貼り直して Step 5 をやり直す。

- [ ] **Step 6: 制限が効いていることを確認する**

```js
var db=firebase.firestore(), TS=firebase.firestore.FieldValue.serverTimestamp();
db.collection('feedback').add({text:'あ'.repeat(2001), from:'manual', at:TS})
  .then(()=>console.log('2001字が通った（誤り）')).catch(e=>console.log('2001字: 拒否', e.code));
db.collection('feedback').add({text:'ok', from:'manual', at:TS, email:'a@example.com'})
  .then(()=>console.log('余計な項目が通った（誤り）')).catch(e=>console.log('余計な項目: 拒否', e.code));
```

期待: 2行とも `拒否 permission-denied`

- [ ] **Step 7: テストで作った文書を消す**

Firebase コンソール → Firestore Database → データ → `feedback` コレクション →
Step 4 で作られた文書を削除する。

- [ ] **Step 8: コミット**

```bash
git add firestore.rules
git commit -m "feat(ご意見): Firestore に feedback コレクションを開ける（読み取りは全面禁止）"
```

---

### Task 2: 送信関数を firebase.js に足す

**ファイル:**
- 変更: `firebase.js`（`loadAgg` の後ろに追加）

**インターフェース:**
- 提供: `KG.sendFeedback(text, from)` → `Promise`。成功で resolve、失敗で reject。
  `text` は呼び出し側で trim 済みでなくてよい（内部で trim する）。
  `from` は40字に切り詰める。`at` はサーバー時刻を入れる。

**注意:** App Check の reCAPTCHA はドメインに紐づいているため、**ローカルのファイルを
開いても検証できない**。push して公開サイトで確認する。この Task の変更は既存機能に
触れない追加のみなので、単独で push して差し支えない。

- [ ] **Step 1: 関数が無いことを確認する**

ブラウザで `https://ai-seisaku-kurabe.github.io/shindan.html` を開き、コンソールで実行する。

```js
console.log(typeof KG.sendFeedback);
```

期待: `undefined`

- [ ] **Step 2: `firebase.js` に追加する**

`loadAgg: async function(){ … }` の閉じ括弧の後ろにカンマを付け、続けて次を書く。

```js
    sendFeedback: function(text, from){
      if(!ready) return Promise.reject(new Error("not-ready"));
      var t = String(text||"").trim();
      if(!t) return Promise.reject(new Error("empty"));
      if(t.length > 2000) return Promise.reject(new Error("too-long"));
      // 保存するのは本文と送信元ページ名だけ。個人を特定できる情報は受け取らない。
      return db.collection("feedback").add({
        text: t,
        from: String(from||"").slice(0,40),
        at: firebase.firestore.FieldValue.serverTimestamp()
      });
    }
```

- [ ] **Step 3: コミットして push する**

```bash
git add firebase.js
git commit -m "feat(ご意見): KG.sendFeedback を追加した"
git push origin HEAD:docs/feedback-form-design
```

**push しただけでは公開されない**（このブランチはまだ main ではない）。公開サイトで
確認するため、この Task 以降の確認は Task 5 まで進めてから main に入れて行うか、
一時的に main へ入れて確認する。**Task 1 の Step 5 で読み取り禁止を確認済みなので、
先に公開しても意見が漏れることはない。**

- [ ] **Step 4: 公開サイトで送信できることを確認する**

main に入った後、`https://ai-seisaku-kurabe.github.io/shindan.html` のコンソールで実行する。

```js
KG.sendFeedback('動作確認です', 'manual').then(()=>console.log('送信できた')).catch(e=>console.log('失敗', e));
```

期待: `送信できた` と表示され、Firebase コンソールの `feedback` に1件現れる。
確認したらコンソールから削除する。

---

### Task 3: feedback.html をフォームに差し替える

**ファイル:**
- 変更: `tools/build_site.py:260-297`（`FEEDBACK_CSS` / `FEEDBACK_FORM` / `FEEDBACK_JS`）
- 変更: `config.json`（`feedback_enabled` と `feedback_notice` を追加）

**インターフェース:**
- 消費: `KG.sendFeedback(text, from)`（Task 2）
- 提供: `feedback.html` に `id="fbForm"` `id="fbText"` `id="fbBtn"` `id="fbMsg"`
  `id="fbWrap"` を持つフォーム。Task 4 の監視がこの id を目印にする。

- [ ] **Step 1: 現状の目印を確認する**

```bash
cd tools && python build_site.py && grep -c "fbForm" site/feedback.html
```

期待: `0`

- [ ] **Step 2: `config.json` にスイッチを足す**

`config.json` に2つのキーを追加する（既存の `election_mode` は残す）。

```json
{
  "election_mode": false,
  "feedback_enabled": true,
  "feedback_notice": "荒らしへの対応のため、ご意見フォームを一時的に停止しています。GitHub の Issue からはお送りいただけます。",
  "_comment": "選挙期間中(公示日〜投票日)は election_mode を true にしてください。公職選挙法第138条の3(人気投票の経過・結果の公表禁止)に抵触する恐れがあるため、集計とアーカイブの公開を止めます。feedback_enabled を false にするとご意見フォームの受付を止めます。どちらもこのファイルを書き換えてコミットするだけで反映され、再ビルドは不要です。",
  "election_notice": "現在は選挙期間中のため、集計結果の公開を一時的に停止しています。公職選挙法により、選挙に関する人気投票の経過・結果の公表が禁じられているためです。投票日の翌日以降に再開します。"
}
```

- [ ] **Step 3: `FEEDBACK_CSS` に3行足す**

`tools/build_site.py` の `FEEDBACK_CSS`（261行目からの三重引用符の中）の末尾、
`a.src{...}` の行の後ろに追加する。

```css
.fb-msg{ font-size:13px; color:var(--muted); margin:0; min-height:1.2em; }
.fb-msg.err{ color:#c1704f; font-weight:600; }
.fb-count{ font-size:11.5px; color:var(--muted); align-self:flex-end; }
```

- [ ] **Step 4: `FEEDBACK_FORM` を差し替える**

278〜293行目の `FEEDBACK_FORM = (…)` 全体を次で置き換える。

```python
FEEDBACK_FORM = ('  <p class="eyebrow">ご意見・お問い合わせ</p>'
  '<h1>このサイトへのご意見をお寄せください</h1>'
  '<p class="lede">誤りの指摘・機能の要望・感想など、なんでも歓迎です。いただいた声は<b>サイトの改善に活用</b>します。</p>'
  '<div id="fbWrap">'
  '<form class="fb" id="fbForm">'
  '<label>ご意見<span class="req">必須</span>'
  '<textarea id="fbText" maxlength="2000" required '
  'placeholder="例：〇〇党の△△の分野で、引用されている発言が議事録と違うようです。"></textarea></label>'
  '<span class="fb-count" id="fbCount">0 / 2000 字</span>'
  '<button class="fb-btn" id="fbBtn" type="submit">送信する</button>'
  '<p class="fb-msg" id="fbMsg"></p>'
  '</form></div>'
  '<p class="fb-note">'
  '・<b>いただいた内容は公開しません。</b>運営者だけが読み、サイトの改善に使います。<br>'
  '・<b>お名前・メールアドレス・電話番号などは書かないでください。</b>'
  'このフォームは本文と送信元のページ名しか保存せず、連絡先を受け取る作りになっていません。'
  'そのため<b>個別の返信はできません</b>。<br>'
  '・公開の場で議論したい場合や、返信のやり取りが必要な場合は'
  '<a class="src" href="https://github.com/ai-seisaku-kurabe/ai-seisaku-kurabe.github.io/issues/new" '
  'target="_blank" rel="noopener">GitHub の Issue</a>をお使いください（GitHubのアカウントが必要です）。<br>'
  '・<b>このサイトのソースコードは公開しています。</b>掲載データ・生成スクリプト・'
  '運用ルールのすべてを<a class="src" href="https://github.com/ai-seisaku-kurabe/ai-seisaku-kurabe.github.io" target="_blank" rel="noopener">'
  'リポジトリ</a>で確認でき、誤りがあればIssueやPull Requestで直接指摘できます。</p>')
```

- [ ] **Step 5: `FEEDBACK_JS` を書く**

294行目の `FEEDBACK_JS = ""` の行を、次で置き換える。

```python
FEEDBACK_JS = FB_TAGS + """
<script>(function(){
  var wrap=document.getElementById('fbWrap'), form=document.getElementById('fbForm'),
      ta=document.getElementById('fbText'), btn=document.getElementById('fbBtn'),
      msg=document.getElementById('fbMsg'), cnt=document.getElementById('fbCount');
  var LIMIT=2000, WAIT=60*1000, KEY='kg_fb_last', sending=false;
  if(!form || !ta) return;
  function say(t, err){ msg.textContent=t; msg.className = err ? 'fb-msg err' : 'fb-msg'; }
  function done(html){ wrap.innerHTML='<div class="fb-thanks">'+html+'</div>'; }
  ta.addEventListener('input', function(){ cnt.textContent = ta.value.length + ' / ' + LIMIT + ' 字'; });
  // 受付の停止スイッチ（config.json を書き換えるだけで効く。再ビルド不要）
  fetch('config.json').then(function(r){ return r.json(); }).then(function(cfg){
    if(cfg && cfg.feedback_enabled === false){
      done('<b>ご意見の受付を一時停止しています。</b><br>' + (cfg.feedback_notice || ''));
    }
  }).catch(function(){});
  form.addEventListener('submit', function(e){
    e.preventDefault();
    if(sending) return;
    var t=(ta.value||'').trim();
    if(!t){ say('本文が空です。', true); return; }
    if(t.length > LIMIT){ say(LIMIT+'字までです（現在 '+t.length+' 字）。', true); return; }
    var last = Number(localStorage.getItem(KEY) || 0);
    if(Date.now() - last < WAIT){
      say('続けて送信することはできません。1分ほどおいてからお試しください。', true); return;
    }
    if(!window.KG || !KG.enabled() || !KG.sendFeedback){
      say('送信できませんでした。下の GitHub の Issue からお送りください。', true); return;
    }
    sending=true; btn.disabled=true; say('送信しています…');
    KG.sendFeedback(t, 'feedback').then(function(){
      localStorage.setItem(KEY, String(Date.now()));
      done('<b>お送りいただき、ありがとうございます。</b><br>'
         + 'いただいた内容はサイトの改善に使わせていただきます。個別の返信はできません。');
    }).catch(function(){
      sending=false; btn.disabled=false;
      say('送信できませんでした。時間をおいて試すか、下の GitHub の Issue からお送りください。', true);
    });
  });
})();</script>"""
```

- [ ] **Step 6: 生成して目印が入ったことを確認する**

```bash
cd tools && python build_site.py && grep -c "fbForm" site/feedback.html
```

期待: `1`

- [ ] **Step 7: 配布して検証を通す**

```bash
cd tools && python deploy_to_repo.py && PYTHONIOENCODING=utf-8 python agents/verify_content.py
```

期待: `反映しました: feedback.html` を含み、`FAIL 0 件`

- [ ] **Step 8: コミット**

```bash
git add tools/build_site.py config.json feedback.html
git commit -m "feat(ご意見): GitHubアカウント不要のフォームに差し替えた"
```

- [ ] **Step 9: main に入った後、連投制限が効くことを確認する**

`https://ai-seisaku-kurabe.github.io/feedback.html` を開き、1件送信する（お礼が出る）。
ページを再読み込みし、続けてもう1件送信しようとする。

期待: 「続けて送信することはできません。1分ほどおいてからお試しください。」が表示され、
Firebase コンソールの `feedback` が増えない。確認したらテストの1件を削除する。

- [ ] **Step 10: main に入った後、停止スイッチが効くことを確認する**

`config.json` の `feedback_enabled` を `false` にしてコミットし push する
（**再ビルドはしない**。ここが確認したい点）。

```bash
git add config.json && git commit -m "chore: 受付停止スイッチの動作確認" && git push
```

`feedback.html` を再読み込みする。

期待: フォームが消え、「ご意見の受付を一時停止しています。」と `feedback_notice` の
文言が出る。GitHub の Issue への案内は残っている。

確認できたら `true` に戻して push し、フォームが戻ることを確認する。

---

### Task 4: 壊れている監視を直す

**ファイル:**
- 変更: `tools/agents/health_check.py:38`

**インターフェース:**
- 消費: Task 3 が生成する `fbForm` / `fbText` の id

**⑥運用班の health-check は現在 failure で止まっている。** `feedback.html` の目印が
Netlify Forms 時代の `fbform` `name="form-name"` のままで、Issues 案内に変えたときに
更新し忘れたため。**番犬が古い基準で吠えている状態**なので、本物の警告が出ても
気づけない。フォームの追加と同時に直す。

- [ ] **Step 1: いま失敗していることを確認する**

```bash
cd tools && python agents/health_check.py
```

期待: `feedback.html: 目印が消えている ['fbform', 'name="form-name"']` が出る
（公開サイトを見にいくので、Task 3 が main に入る前は失敗のままで正しい）

- [ ] **Step 2: 目印を新しいフォームのものに直す**

`tools/agents/health_check.py` の 37〜38行目を置き換える。

```python
    # ご意見フォームが生成から抜け落ちると、受付が黙って消える
    "feedback.html": ["fbForm", "fbText", "ご意見"],
```

- [ ] **Step 3: コミット**

```bash
git add tools/agents/health_check.py
git commit -m "fix(⑥運用班): ご意見ページの目印がNetlify時代のままで、監視が常時失敗していた"
```

- [ ] **Step 4: main に入った後で、監視が通ることを確認する**

```bash
cd tools && python agents/health_check.py
```

期待: `feedback.html: 正常` が出て、全体が成功で終わる

---

### Task 5: 新着件数だけを数える

**ファイル:**
- 作成: `tools/agents/feedback_count.py`
- 作成: `.github/workflows/feedback-count.yml`
- 作成: `tools/state/feedback_state.json`

**インターフェース:**
- 消費: 環境変数 `FIREBASE_SA_KEY`（GitHub Secrets に登録済み・`snapshot_archive.py` と同じもの）
- 提供: `tools/state/feedback_state.json` = `{"last_checked": ISO8601, "last_new": int, "checked_at": ISO8601}`

**総件数の差分では数えない。** 読んだ意見をコンソールから削除すると総件数が減り、
差分がマイナスになって新着を検知できなくなるため、**「前回確認した時刻より後に届いた件数」**
を数える。

- [ ] **Step 1: `tools/agents/feedback_count.py` を作る**

```python
# -*- coding: utf-8 -*-
"""ご意見の新着件数だけを数える（本文は取得しない）。

App Check を「適用」にしているため、認証のないクライアントからは Firestore を読めない。
サービスアカウントで REST API の集計クエリ（COUNT）を叩く。

**本文は取得しない。** GitHub Actions のログや成果物に意見の中身が残ると、
非公開にした意味がなくなるため、取得するのは件数だけにする。

総件数の差分では数えない。読んだ意見をコンソールから削除すると総件数が減り、
差分がマイナスになって新着を検知できなくなる。「前回確認した時刻より後に届いた件数」
を数えるので、削除の影響を受けない。

環境変数:
    FIREBASE_SA_KEY   … サービスアカウントのJSON（GitHub Secrets から渡す）
    FIREBASE_PROJECT  … 省略時は 'aipolitics-9c657'

使い方:
    python agents/feedback_count.py            # 数えて state を更新する
    python agents/feedback_count.py --dry-run  # 数えるだけ（state を更新しない）
"""
import datetime, json, os, sys, urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, ".."))
PROJECT = os.environ.get("FIREBASE_PROJECT", "aipolitics-9c657")
STATE = os.path.join(TOOLS, "state", "feedback_state.json")


def access_token(sa_json):
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
    creds = service_account.Credentials.from_service_account_info(
        json.loads(sa_json), scopes=["https://www.googleapis.com/auth/datastore"])
    creds.refresh(Request())
    return creds.token


def count_since(token, since_iso):
    \"\"\"since_iso より後に届いた件数を返す。本文は取得しない。\"\"\"
    url = (f"https://firestore.googleapis.com/v1/projects/{PROJECT}"
           f"/databases/(default)/documents:runAggregationQuery")
    body = {"structuredAggregationQuery": {
        "structuredQuery": {
            "from": [{"collectionId": "feedback"}],
            "where": {"fieldFilter": {
                "field": {"fieldPath": "at"},
                "op": "GREATER_THAN",
                "value": {"timestampValue": since_iso}}}},
        "aggregations": [{"alias": "n", "count": {}}]}}
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"})
    rows = json.loads(urllib.request.urlopen(req, timeout=30).read().decode("utf-8"))
    for row in rows:
        r = row.get("result")
        if r:
            return int(r["aggregateFields"]["n"]["integerValue"])
    return 0


def load_state():
    if os.path.exists(STATE):
        try:
            return json.load(open(STATE, encoding="utf-8"))
        except Exception:
            pass
    # 初回は7日前を起点にする（全期間だと過去のぶんが一度に新着として出るため）
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=7)
    return {"last_checked": since.strftime("%Y-%m-%dT%H:%M:%SZ"), "last_new": 0}


def main():
    dry = "--dry-run" in sys.argv
    sa = os.environ.get("FIREBASE_SA_KEY")
    if not sa:
        raise SystemExit("FIREBASE_SA_KEY が設定されていません（GitHub Secrets を確認）。")

    state = load_state()
    since = state["last_checked"]
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    n = count_since(access_token(sa), since)
    line = (f"ご意見の新着 {n} 件（{since} 以降）" if n
            else f"ご意見の新着はありません（{since} 以降）")
    print(line)
    print("※本文は取得していません。読むには Firebase コンソールを開いてください。")

    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("### " + line + "\\n\\n本文は取得していません。\\n")

    if dry:
        return
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump({"last_checked": now, "last_new": n, "checked_at": now},
              open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"state を更新しました: {STATE}")


if __name__ == "__main__":
    main()
```

（`count_since` の docstring は、実ファイルでは `"""` に直すこと。この計画書の
コードブロック内でのみ `\"\"\"` とエスケープしている。）

- [ ] **Step 2: 鍵が無い状態で正しく止まることを確認する**

```bash
cd tools && python agents/feedback_count.py
```

期待: `FIREBASE_SA_KEY が設定されていません（GitHub Secrets を確認）。` で終了

- [ ] **Step 3: ワークフローを作る**

`.github/workflows/feedback-count.yml`:

```yaml
name: feedback-count
# ⑥運用班: ご意見の新着件数だけを数える（本文は取得しない）
on:
  schedule:
    - cron: '0 21 * * 0'   # 毎週月曜 JST 6:00
  workflow_dispatch:
permissions:
  contents: write
jobs:
  count:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install --quiet google-auth requests
      - name: 新着件数を数える
        env:
          FIREBASE_SA_KEY: ${{ secrets.FIREBASE_SA_KEY }}
        working-directory: tools
        run: python agents/feedback_count.py
      - name: 件数をコミットに残す
        run: |
          git config user.name "github-actions"
          git config user.email "actions@github.com"
          N=$(python -c "import json;print(json.load(open('tools/state/feedback_state.json'))['last_new'])")
          git add tools/state/feedback_state.json
          git commit -m "chore(ご意見): 新着 ${N} 件" || echo "no changes"
          git push
```

- [ ] **Step 4: コミットして push し、手動実行する**

```bash
git add tools/agents/feedback_count.py .github/workflows/feedback-count.yml
git commit -m "feat(⑥運用班): ご意見の新着件数だけを週次で数える"
git push origin HEAD:docs/feedback-form-design
```

main に入った後、手動実行する。

```bash
gh workflow run feedback-count.yml
gh run list --workflow=feedback-count.yml --limit 1
```

- [ ] **Step 5: 削除しても壊れないことを確認する（この Task の要）**

1. 公開サイトのフォームから3件送る
2. `gh workflow run feedback-count.yml` → 実行サマリが `新着 3 件`
3. Firebase コンソールで**1件だけ削除**する
4. もう1件送る
5. `gh workflow run feedback-count.yml` → 実行サマリが `新着 1 件`

期待: 5 で `1 件`。総件数の差分方式なら 4−3=1 と偶然合ってしまうので、
**3 で2件削除して 5 が `1 件` になること**まで見ると確実に区別できる。

- [ ] **Step 6: 実行ログに本文が出ていないことを確認する**

```bash
gh run view --log --workflow=feedback-count.yml | grep -i "text\|ご意見の本文" | head
```

期待: 送信した本文の文字列がログに一切現れないこと

---

### Task 6: about.html に「ご意見の扱い」を開示する（PR が必要）

**ファイル:**
- 変更: `tools/build_site.py:651-658`（セクション09「誤りの指摘と修正」）

**これは方法論への追記＝憲法にあたる変更。** `EDITOR.md` の規定により、直接 push せず
PR を出して人の承認を待つ。Task 1〜5 とは別のコミットにし、PR の説明で「この Task だけが
承認を要する」と明示する。

- [ ] **Step 1: セクション09に段落を足す**

654〜655行目の `'内容を確認し、必要なら修正します。</p>'` の直後に挿入する。

```python
  '<p class="ab-b"><b>ご意見フォームで送られた内容は、公開しません。</b>'
  '運営者だけが読み、サイトの改善に使います。保存するのは<b>本文と送信元のページ名だけ</b>で、'
  'お名前・メールアドレス・IPアドレス・ブラウザの情報は受け取っていません。'
  'そのため個別の返信はできません。公開の場で記録を残して議論したい場合は、'
  'GitHub の Issue をお使いください。</p>'
```

- [ ] **Step 2: 生成して文言が入ったことを確認する**

```bash
cd tools && python build_site.py && python deploy_to_repo.py && grep -c "公開しません" ../about.html
```

期待: `1` 以上

- [ ] **Step 3: 検証を通す**

```bash
cd tools && PYTHONIOENCODING=utf-8 python agents/verify_content.py
```

期待: `FAIL 0 件`

- [ ] **Step 4: コミットして PR を出す**

```bash
git add tools/build_site.py about.html
git commit -m "docs: ご意見の扱い（非公開・個人情報を保存しない・返信不可）を開示する"
git push origin HEAD:docs/feedback-form-design
gh pr create --base main --head docs/feedback-form-design \
  --title "feat: GitHubアカウント不要のご意見フォーム" --body-file -
```

PR の説明には、設計書へのリンク、③検証班の結果、⑧査読の記録、そして
**「about.html の変更を含むため人の承認が必要」**を書く。

- [ ] **Step 5: 完成後に⑧査読へ回す**

```bash
cd tools && PYTHONIOENCODING=utf-8 python agents/ask_reviewers.py --base origin/main \
  --paths tools/build_site.py firebase.js firestore.rules tools/agents/feedback_count.py
```

**生成HTMLは渡さない**（1行が長く、差分が数十万文字になって分割送信で止まる）。
公開される文言は `build_site.py` の文字列そのものなので、査読の材料は落ちない。

---

## 実装後に残る手作業

- **意見を読む**のは Firebase コンソール（`feedback` コレクション）。読んだら削除する。
- **荒らされたとき（緊急停止）** — `config.json` の `feedback_enabled` を `false` に
  してコミットするのは**利用者への告知**であって防御ではない。`firebase.js` の
  設定は公開HTMLに同梱されているため、`config.json` を false にしても Firestore への
  書き込みは1件も止まらない（詳細は設計書「停止スイッチの限界」）。
  **書き込みを実際に止めるには、Firebase コンソール → Firestore Database → ルール で
  `feedback` の `allow create` を `if false` に書き換えて公開する。**
  手順は 1) コンソールでルールを閉じる（唯一の確実な停止手段） 2) `config.json` の
  `feedback_enabled` を `false` にしてコミットする（告知。fail-open のため即座には
  全員に効かない） 3) 収束後にルールと `config.json` を元に戻す。
