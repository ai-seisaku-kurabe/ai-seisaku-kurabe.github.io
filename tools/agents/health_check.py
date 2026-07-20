# -*- coding: utf-8 -*-
"""⑥運用班 — 公開中のサイトが壊れていないかを外から監視する。

「直す」ことはしない。壊れていることに気づいて知らせるだけ。
点検項目は、これまで実際に起きた事故から逆算して決めている:

  - viewport メタの欠落 … 過去に全ページで抜けており、スマホが約980px幅で描画されていた
  - firebase.js のプレースホルダ化 … ビルド生成物で本番設定を上書きすると集計とApp Checkが死ぬ
  - news.json の停止 … GitHub Actions が止まるとニュースが古いまま気づけない
  - ページの消失・構造崩れ … 生成の失敗に気づけない

使い方:
    python agents/health_check.py                       # 本番サイトを点検
    python agents/health_check.py --base http://localhost:8000
    python agents/health_check.py --max-news-age 3
終了コード: 0=正常 / 1=異常（CIを落として通知する）
"""
import argparse, datetime, json, re, sys, urllib.error, urllib.request

BASE = "https://tsuruwa2.netlify.app"
UA = {"User-Agent": "seisaku-kurabe-healthcheck/1.0 (+https://tsuruwa2.netlify.app)"}

PAGES = ["index.html", "guide.html", "oneissue.html", "shindan.html",
         "shukei.html", "about.html", "mynote.html", "feedback.html"]

# ページごとに「これが消えていたら生成が壊れている」という目印
MARKERS = {
    "index.html":    ["政策で照らす", "政党で選ぶ", "pcard"],
    "guide.html":    ["言 ／ 国会での発言", "行 ／ 参院", "dtab"],
    "oneissue.html": ["oi-sec", "oi-filter", "ワンイシュー"],
    "shindan.html":  ["prog-fill", "対立軸", "oi-item"],
    "shukei.html":   ["みんなの結果"],
    "about.html":    ["rulebook", "運用ルール"],
    "mynote.html":   ["noteRoot", "マイノート"],
    # data-netlify は Netlify がデプロイ時に除去するため、公開HTMLでは目印にできない
    "feedback.html": ["fbform", 'name="form-name"', "ご意見"],
}

problems, notes = [], []
def bad(msg): problems.append(msg)
def ok(msg): notes.append(msg)

def get(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode("utf-8", "ignore")

def check_pages(base):
    for p in PAGES:
        url = f"{base}/{p}"
        try:
            status, html = get(url)
        except urllib.error.HTTPError as e:
            bad(f"{p}: HTTP {e.code}"); continue
        except Exception as e:
            bad(f"{p}: 到達不可 ({e})"); continue
        if status != 200:
            bad(f"{p}: HTTP {status}"); continue
        # スマホ表示の生命線
        if 'name="viewport"' not in html:
            bad(f"{p}: viewport メタが無い（スマホで縮小表示になる）")
        # 生成物の構造
        missing = [m for m in MARKERS.get(p, []) if m not in html]
        if missing:
            bad(f"{p}: 目印が消えている {missing}")
        ok(f"{p}: 正常 ({len(html):,} bytes)")

def check_firebase(base):
    """本番設定がプレースホルダで上書きされていないか（過去に踏みかけた地雷）。"""
    try:
        _, js = get(f"{base}/firebase.js")
    except Exception as e:
        bad(f"firebase.js: 取得できない ({e})"); return
    # 「PASTE」はプレースホルダ判定コード自身にも出てくるので、代入部分だけを見る
    if re.search(r'apiKey:\s*"PASTE', js):
        bad("firebase.js: プレースホルダのまま公開されている（集計とApp Checkが死ぬ）")
    if not re.search(r'apiKey:\s*"AIza', js):
        bad("firebase.js: apiKey が設定されていない")
    if not re.search(r'appId:\s*"1:', js):
        bad("firebase.js: appId が無い（App Check が 400 で落ちる）")
    if not re.search(r'RECAPTCHA_SITE_KEY\s*=\s*"6L', js):
        bad("firebase.js: reCAPTCHA サイトキーが未設定（App Check が無効）")
    ok("firebase.js: 本番設定を確認")

def check_news(base, max_age_days):
    """ニュース自動更新（GitHub Actions）が生きているか。"""
    try:
        _, raw = get(f"{base}/news.json")
        data = json.loads(raw)
    except Exception as e:
        bad(f"news.json: 取得/解析に失敗 ({e})"); return
    updated = data.get("updated")
    n_topics = sum(len(v) for v in (data.get("topics") or {}).values())
    n_parties = sum(len(v) for v in (data.get("parties") or {}).values())
    if not updated:
        bad("news.json: updated が無い"); return
    try:
        d = datetime.datetime.strptime(updated[:10], "%Y-%m-%d").date()
    except ValueError:
        bad(f"news.json: updated の形式が不正 ({updated})"); return
    age = (datetime.date.today() - d).days
    if age > max_age_days:
        bad(f"news.json: {age}日間更新されていない（更新ワークフローが止まっている可能性）")
    if n_topics + n_parties == 0:
        bad("news.json: 見出しが0件（取得に失敗している）")
    ok(f"news.json: {updated} 更新 / 見出し {n_topics + n_parties} 件")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--max-news-age", type=int, default=3, help="news.json の許容鮮度(日)")
    a = ap.parse_args()
    base = a.base.rstrip("/")

    print(f"⑥運用班 — {base} を点検します\n")
    check_pages(base)
    check_firebase(base)
    check_news(base, a.max_news_age)

    for n in notes:
        print(f"  ✅ {n}")
    print("\n" + "=" * 60)
    if problems:
        for p in problems:
            print(f"❌ {p}")
        print("=" * 60)
        print(f"異常 {len(problems)} 件")
        sys.exit(1)
    print("✅ 異常なし。サイトは正常に稼働しています。")
    print("=" * 60)

if __name__ == "__main__":
    main()
