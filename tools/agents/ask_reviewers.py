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

# モデル名は驚くほど頻繁に変わる。実際に初回の設定で3種類の失敗を踏んだ:
#   404 … そのモデルが新規利用者に提供されなくなった
#   429 … 無料枠にそのモデルが含まれていない（limit: 0）
#   503 … 一時的な混雑
# 1つ目が駄目なら次を試す。順に「使いたい順」で書く。
# 環境変数で上書きでき、カンマ区切りで複数指定できる。
PROVIDERS = {
    "Gemini": {
        "key_env": "GEMINI_API_KEY",
        "model_env": "GEMINI_MODEL",
        "models": ["gemini-3.5-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"],
        "list_url": "https://generativelanguage.googleapis.com/v1beta/models",
    },
    "ChatGPT": {
        "key_env": "OPENAI_API_KEY",
        "model_env": "OPENAI_MODEL",
        "models": ["gpt-5.5", "gpt-5.1", "gpt-4.1"],
        "base": "https://api.openai.com/v1",
    },
    # Groq と Grok は合議から外した（2026-07-21）。
    #   Groq … 無料枠がトークン毎分8,000。実際の依頼文は約18,000で、範囲を分けない限り
    #           送れない。分ければ全体を見た判断ができず、査読の意味が薄れる。
    #   Grok … チームにクレジットが無く 403。課金しない限り応答しない。
    # 鍵が余っているからと形だけ並べると、「4社に聞いた」ように見えて実際は2社という
    # 誤解を生む。**動かない査読者は置かない。** 復帰させるときはここに戻す。
}


# urllib の既定のUser-Agentは、CDNに自動化とみなされて弾かれることがある
# （Groqは 403 error code: 1010 を返した）。名乗れば通る。
UA = "seisaku-kurabe-reviewer/1.0 (+https://ai-seisaku-kurabe.github.io)"


def post(url, payload, headers, timeout=180):
    """1回だけ再試行する。混雑（429）と一時的な障害（5xx）は待てば直ることが多い。"""
    body = json.dumps(payload).encode("utf-8")
    for attempt in (1, 2):
        try:
            req = urllib.request.Request(url, data=body, method="POST",
                                         headers={"Content-Type": "application/json",
                                                  "User-Agent": UA, **headers})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:600]
            # 残高切れ・枠外は待っても直らない。429でも再試行しない。
            permanent = "insufficient_quota" in detail or "limit: 0" in detail
            if e.code in (429, 500, 502, 503, 504) and attempt == 1 and not permanent:
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


def ask_openai_compatible(base):
    """OpenAI互換のAPI（OpenAI本家・xAI等）は同じ呼び方で済む。"""
    def ask(model, key, prompt):
        d = post(f"{base}/chat/completions",
                 {"model": model, "messages": [{"role": "user", "content": prompt}]},
                 {"Authorization": f"Bearer {key}"})
        return d["choices"][0]["message"]["content"].strip()
    return ask


def asker_for(name, cfg):
    if name == "Gemini":
        return ask_gemini
    return ask_openai_compatible(cfg["base"])


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

    results, asked, nokey, failed = {}, 0, [], []
    for name, cfg in PROVIDERS.items():
        key = os.environ.get(cfg["key_env"])
        if not key:
            print(f"— {name}: {cfg['key_env']} が未設定のため飛ばします")
            results[name] = ("未実施", f"{cfg['key_env']} が未設定")
            nokey.append(name)
            continue

        # GroqとGrokは名前が似ていて取り違えが起きる（実際に起きた）。
        # 鍵の頭を見れば分かるので、送る前に知らせる。形式は変わりうるので警告に留める。
        pref = cfg.get("key_prefix")
        if pref and not key.startswith(pref):
            print(f"⚠ {name}: {cfg['key_env']} が {pref}… で始まっていません"
                  "（別の提供元の鍵かもしれません。Groq=gsk_ ／ Grok(xAI)=xai-）")

        override = os.environ.get(cfg["model_env"])
        models = [m.strip() for m in override.split(",")] if override else cfg["models"]
        errors = []
        for model in models:
            print(f"→ {name} ({model}) に問い合わせ中 …", flush=True)
            try:
                text = asker_for(name, cfg)(model, key, prompt)
                results[name] = (verdict_of(text), f"（モデル: {model}）\n\n{text}")
                asked += 1
                print(f"   判定: {results[name][0]}")
                break
            except Exception as e:
                # 1モデルが駄目でも次を試す。1社が落ちても、もう1社の査読は残す。
                errors.append(f"{model}: {e}")
                print(f"   使えません（次を試します）: {e}")
        else:
            results[name] = ("エラー", "\n\n".join(errors))
            failed.append(name)

    if asked == 0:
        print("\n査読できませんでした（記録は作りません）。")
        if nokey:
            print(f"  未設定: {', '.join(nokey)}")
            print("    Gemini … https://aistudio.google.com/apikey で取得し GEMINI_API_KEY に設定")
            print("    ChatGPT … https://platform.openai.com/api-keys で取得し OPENAI_API_KEY に設定")
        if failed:
            print(f"  鍵はあるが応答が得られなかった: {', '.join(failed)}")
            print("    上のエラーを確認してください。よくある原因:")
            print("      429 insufficient_quota … 残高切れ（課金の設定が要る）")
            print("      429 limit: 0           … そのモデルが無料枠の対象外")
            print("      404 no longer available … モデルが廃止された"
                  f"（{'/'.join(c['model_env'] for c in PROVIDERS.values())} で差し替え可）")
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
        if asked < 2:
            f.write(f"\n**実際に査読できたのは {asked} 社だけ。"
                    "独立した点検が2つ以上ないため、これは合議ではなく1社の意見。**\n")
        for n, (v, t) in results.items():
            f.write(f"\n## {n} — {v}\n\n{t}\n")
        f.write("\n---\n\nPASS は「異議なし」であって承認ではない。"
                "承認は③検証班のCIと、人がマージ（または公開）することの2つだけ。\n")

    print(f"\n記録: {os.path.relpath(path, os.path.join(HERE, '..', '..'))}")
    print("=" * 60)
    for n, (v, _) in results.items():
        print(f"  {n}: {v}")
    print("=" * 60)
    # 何社が見たのかを黙らせない。1社だけの査読を、全社が見たことにしない。
    expected = len(PROVIDERS) - len(nokey)
    if failed:
        print(f"⚠ 鍵はあるのに応答が無かった提供元があります: {', '.join(failed)}")
    if asked < 2:
        print(f"⚠ 実際に査読できたのは {asked} 社だけです。"
              "**独立した点検が2つ以上ないと合議になりません。**"
              "この状態で進めるなら、査読は「1社の意見」として扱ってください。")
    elif asked < expected:
        print(f"⚠ 査読できたのは {asked}/{expected} 社です。")

    blocked = [n for n, (v, _) in results.items() if v in ("BLOCK", "不明")]
    if blocked:
        print(f"BLOCK/不明 があります（{', '.join(blocked)}）。記録を読んでから判断してください。")
        return 1
    print("BLOCK なし。ただし PASS は承認ではないので、公開の判断は人が行うこと。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
