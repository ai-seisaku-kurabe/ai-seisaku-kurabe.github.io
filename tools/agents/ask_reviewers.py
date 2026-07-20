# -*- coding: utf-8 -*-
"""⑧査読班（自動） — 依頼文を複数のAIに送り、判定を集めて記録する。

人が入力欄に貼る手間をなくすためのもの。**判断は自動化しない。**
BLOCK を退けるのも、公開するのも人の仕事のままで、この班は集めて並べるだけ。

APIを使うと、会話の履歴が無い状態で1回ずつ問い合わせることになるので、
「AIごとに新しい会話で聞く」（先に出た意見に引きずられない）が自然に守られる。

必要な鍵（環境変数。無い提供元は自動で飛ばす）:
    GEMINI_API_KEY   … https://aistudio.google.com/apikey
    OPENAI_API_KEY   … https://platform.openai.com/api-keys

使い方:
    python agents/ask_reviewers.py                    # main との差分を査読させる
    python agents/ask_reviewers.py --paths guide.html
    python agents/ask_reviewers.py --base HEAD~1
    python agents/ask_reviewers.py --dry-run          # 送らずに送信内容だけ見る
終了コード: 0=BLOCKなし / 1=BLOCKあり（押す前に人が読む） / 2=査読できなかった
"""
import argparse, datetime, json, os, re, sys, time
import urllib.error, urllib.request

import make_review_request as mrr   # 依頼文の組み立ては1か所に置く（写しを作らない）

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
RECORDS = os.path.join(HERE, "..", "state", "reviews")

# モデル名は変わるので、環境変数で差し替えられるようにしておく。
PROVIDERS = {
    "Gemini": {
        "key_env": "GEMINI_API_KEY",
        "model_env": "GEMINI_MODEL",
        "model": "gemini-2.5-pro",
    },
    "ChatGPT": {
        "key_env": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
        "model": "gpt-5",
    },
}


def post(url, payload, headers, timeout=180):
    """1回だけ再試行する。混雑（429）と一時的な障害（5xx）は待てば直ることが多い。"""
    body = json.dumps(payload).encode("utf-8")
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(url, data=body, method="POST",
                                         headers={"Content-Type": "application/json", **headers})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:600]
            if e.code in (429, 500, 502, 503, 504) and attempt == 1:
                time.sleep(20)
                continue
            raise RuntimeError(f"HTTP {e.code}: {detail}")
        except urllib.error.URLError as e:
            if attempt == 1:
                time.sleep(10)
                continue
            raise RuntimeError(f"接続できません: {e.reason}")


def ask_gemini(model, key, prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    d = post(url, {"contents": [{"parts": [{"text": prompt}]}]}, {"x-goog-api-key": key})
    return "".join(p.get("text", "")
                   for p in d["candidates"][0]["content"]["parts"]).strip()


def ask_openai(model, key, prompt):
    d = post("https://api.openai.com/v1/chat/completions",
             {"model": model, "messages": [{"role": "user", "content": prompt}]},
             {"Authorization": f"Bearer {key}"})
    return d["choices"][0]["message"]["content"].strip()


ASKERS = {"Gemini": ask_gemini, "ChatGPT": ask_openai}


def verdict_of(text):
    """返答から判定を読む。読めなければ「不明」— 勝手にPASS扱いにしない。"""
    m = re.search(r"判定\s*[:：]\s*(PASS|BLOCK)", text, re.I)
    if m:
        return m.group(1).upper()
    if re.search(r"\bBLOCK\b", text):
        return "BLOCK"
    return "不明"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", help="比較元（既定: origin/main との分岐点）")
    ap.add_argument("--paths", nargs="*", default=[], help="この範囲だけ査読にかける")
    ap.add_argument("--max-chars", type=int, default=200000,
                    help="1通あたりの差分の上限。APIは入力欄より余裕があるので既定を大きくしてある")
    ap.add_argument("--dry-run", action="store_true", help="送らずに送信内容だけ表示する")
    a = ap.parse_args()

    base = mrr.base_ref(a.base)
    units = mrr.changed_files(base, a.paths)
    if not units:
        print("差分がありません。査読するものがありません。")
        return 0

    groups = mrr.chunk(units, a.max_chars)
    if len(groups) > 1:
        print(f"⚠ 差分が大きいため {len(groups)} 通に分かれます。"
              "APIでは分割送信の追従ができないので、--paths で範囲を分けて実行してください。")
        return 2
    prompt = mrr.build(groups[0], base, 1, 1)

    print(f"比較元: {base}")
    print(f"対象: {len(units)} ファイル / 依頼文 {len(prompt)} 文字\n")
    if a.dry_run:
        print(prompt)
        return 0

    results, asked = {}, 0
    for name, cfg in PROVIDERS.items():
        key = os.environ.get(cfg["key_env"])
        if not key:
            print(f"— {name}: {cfg['key_env']} が未設定のため飛ばします")
            results[name] = ("未実施", f"{cfg['key_env']} が未設定")
            continue
        model = os.environ.get(cfg["model_env"], cfg["model"])
        print(f"→ {name} ({model}) に問い合わせ中 …", flush=True)
        try:
            text = ASKERS[name](model, key, prompt)
            results[name] = (verdict_of(text), text)
            asked += 1
            print(f"   判定: {results[name][0]}")
        except Exception as e:
            # 1社が落ちても、もう1社の査読は残す。
            results[name] = ("エラー", str(e))
            print(f"   失敗: {e}")

    if asked == 0:
        print("\n査読できませんでした。APIキーが設定されていません（記録は作りません）。")
        print("  Gemini … https://aistudio.google.com/apikey で取得し GEMINI_API_KEY に設定")
        print("  ChatGPT … https://platform.openai.com/api-keys で取得し OPENAI_API_KEY に設定")
        return 2

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    os.makedirs(RECORDS, exist_ok=True)
    path = os.path.join(RECORDS, f"{stamp}.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# ⑧査読の記録 {stamp}\n\n比較元: `{base}`\n\n")
        f.write("対象ファイル:\n\n" + "".join(f"- `{p}`\n" for p, _ in units) + "\n")
        f.write("| AI | 判定 |\n|---|---|\n")
        for n, (v, _) in results.items():
            f.write(f"| {n} | {v} |\n")
        for n, (v, t) in results.items():
            f.write(f"\n## {n} — {v}\n\n{t}\n")
        f.write("\n---\n\nPASS は「異議なし」であって承認ではない。"
                "承認は③検証班のCIと、人がマージ（または公開）することの2つだけ。\n")

    print(f"\n記録: {os.path.relpath(path, os.path.join(HERE, '..', '..'))}")
    print("=" * 60)
    for n, (v, _) in results.items():
        print(f"  {n}: {v}")
    print("=" * 60)

    blocked = [n for n, (v, _) in results.items() if v in ("BLOCK", "不明")]
    if blocked:
        print(f"BLOCK/不明 があります（{', '.join(blocked)}）。記録を読んでから判断してください。")
        return 1
    print("BLOCK なし。ただし PASS は承認ではないので、公開の判断は人が行うこと。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
