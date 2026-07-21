# -*- coding: utf-8 -*-
"""⑨文献調査班／照合の全数検査（audit_matching）

先行研究が指摘する2つの問題を、印象ではなく数で確かめるための検査。

  (1) Louwerse & Rosema (2014) — 助言は採用する空間モデルに依存する。
      StemWijzer の利用者の過半数は、別の空間モデルなら別の助言を受け取っていた。
  (2) Fröhle et al. (2026) — 設問と算出式の組み合わせ自体が、特定の立場の政党を
      不均衡に押し上げうる。運営者がどの党を支持するかとは無関係に起きる。

このサイトの「政策で照らす」は回答の入力空間が有限（10問 × 3択 × 重み2値）なので、
標本調査ではなく全数検査ができる。ありうる入力 3^10 × 2^10 = 60,466,176 通りを
すべて計算し、

  ・現行式で各党が1位になる入力が全体の何％か
  ・別の算出式に替えると1位の党が変わる入力が何％か
  ・党ごとの「判定に使われる設問数」の差（中立0が多い党ほど分母が小さくなる）
  ・賛否が釣り合った回答（いわゆる中道）でどの党が上がりやすいか

を出す。結果はサイトに載せるための JSON と、人が読むための表を出力する。

このスクリプトは判定を書き換えない。測るだけである（③検証班と同じ立場）。

使い方:
    cd tools && python agents/audit_matching.py            # 検査して state/ に出力
    cd tools && python agents/audit_matching.py --print    # 表示のみ（書き出さない）
"""
from __future__ import annotations
import argparse, io, itertools, json, os, sys, datetime
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
OUT_JSON = os.path.join(TOOLS, "state", "matching_audit.json")

WEIGHT_ON = 3   # 「◎ この争点を特に重視する」を押したときの重み（shindan.html と同じ）
WEIGHT_OFF = 1


# ---------------------------------------------------------------- データ取得
def load_shindan_data():
    """build_shindan.py から PARTIES / POLICY を読み出す。

    build_shindan.py は import すると shindan.html を書き出すので、
    定義部分だけを切り出して exec する（生成には触れない）。
    """
    src_path = os.path.join(TOOLS, "build_shindan.py")
    src = io.open(src_path, encoding="utf-8").read()
    # POLICY リテラルの終わりまでを取り出す（次の代入文の直前で切る）
    marker = "\n# 各設問の"
    cut = src.find(marker)
    if cut < 0:
        # 目印が変わっていたら、POLICY の閉じ括弧を探す
        cut = src.find("\n]\n", src.find("POLICY = ["))
        cut = cut + 3 if cut > 0 else len(src)
    ns: dict = {}
    exec(compile(src[:cut], src_path, "exec"), ns)
    parties, policy = ns.get("PARTIES"), ns.get("POLICY")
    if not parties or not policy:
        raise SystemExit("build_shindan.py から PARTIES / POLICY を読めませんでした")
    return parties, policy


# ---------------------------------------------------------------- 算出式
# どれも「あなたの回答（+1/0/-1）」と「その党の立場（+1/0/-1）」から一致度を出す。
# 現行式だけがサイトで使われているもので、残りは比較用（先行研究で使われる型）。
FORMULAS = {
    "current": {
        "label": "現行式（符号一致率）",
        "desc": "あなたも党も賛否がはっきりしている設問だけを分母にし、"
                "符号が一致した割合を出す。重視した設問は3倍。"
                "党が中立の設問は分母から落ちる。",
    },
    "proximity": {
        "label": "近接性（距離）型",
        "desc": "回答と党の立場の距離 |u−p| を足し上げ、近いほど高くする。"
                "党が中立の設問も距離1として数えるので、分母は回答したすべての設問になる。"
                "（3択では方向性モデル u×p と順位が完全に一致する。"
                "|u−p| = 1 − u×p が恒等的に成り立つため）",
    },
    "wahlomat": {
        "label": "点数合計型",
        "desc": "一致2点・どちらかが中立1点・不一致0点を足し上げる。割合にしない。"
                "ドイツ Wahl-O-Mat が採る型で、立場を多く示している党ほど点を積める。",
    },
    "current_noweight": {
        "label": "現行式・重みなし",
        "desc": "現行式から「◎ 重視する」の3倍を外したもの。",
    },
}


def scores(formula: str, A: np.ndarray, W: np.ndarray, P: np.ndarray):
    """一致度の行列を返す。

    A: (n, q) 回答 +1/0/-1        W: (n, q) 重み 1/3
    P: (p, q) 各党の立場 +1/0/-1
    戻り: (n, p) の float 配列。判定材料が無い組み合わせは NaN。
    """
    n, q = A.shape
    if formula == "current_noweight":
        W = np.ones_like(W)
    if formula in ("current", "current_noweight"):
        # 双方が非ゼロの設問だけ。符号一致で加点。
        out = np.full((n, P.shape[0]), np.nan, dtype=np.float32)
        for j in range(P.shape[0]):
            p = P[j]
            use = (A != 0) & (p != 0)              # (n, q)
            considered = (W * use).sum(axis=1)
            agree = (W * use * (np.sign(A) == np.sign(p))).sum(axis=1)
            with np.errstate(invalid="ignore", divide="ignore"):
                s = np.where(considered > 0, agree / np.maximum(considered, 1), np.nan)
            out[:, j] = s
        return out
    if formula == "proximity":
        # 回答した設問だけを分母にする（未回答=0 は入力していないので除く）
        out = np.empty((n, P.shape[0]), dtype=np.float32)
        answered = (A != 0)
        denom = (W * answered).sum(axis=1) * 2.0
        for j in range(P.shape[0]):
            d = (W * answered * np.abs(A - P[j])).sum(axis=1)
            with np.errstate(invalid="ignore", divide="ignore"):
                out[:, j] = np.where(denom > 0, 1.0 - d / np.maximum(denom, 1), np.nan)
        return out
    if formula == "wahlomat":
        # 一致2点／どちらかが中立1点／不一致0点。割合にしない（合計点で比べる）。
        out = np.empty((n, P.shape[0]), dtype=np.float32)
        answered = (A != 0)
        for j in range(P.shape[0]):
            p = P[j]
            pts = np.where(np.sign(A) == np.sign(p), 2, np.where(p == 0, 1, 0))
            out[:, j] = (W * answered * pts).sum(axis=1)
        return out
    raise ValueError(formula)


def considered_counts(A: np.ndarray, W: np.ndarray, P: np.ndarray):
    """現行式で「判定に使われた設問」の重み合計。同点の並べ替えに使われる。"""
    out = np.empty((A.shape[0], P.shape[0]), dtype=np.int32)
    for j in range(P.shape[0]):
        out[:, j] = (W * ((A != 0) & (P[j] != 0))).sum(axis=1)
    return out


def top_party(S: np.ndarray):
    """各入力で単独1位になる党の番号。同点は -1、全党で判定材料なしは -2。

    実装の並べ替え規則に検査結果が左右されないよう、ここでは同点を同点として数える。
    利用者が実際に画面の先頭で見る党は displayed_top() の方。
    """
    X = np.where(np.isnan(S), -np.inf, S)
    best = X.max(axis=1)
    hit = (X == best[:, None])
    cnt = hit.sum(axis=1)
    idx = np.argmax(hit, axis=1)
    idx = np.where(cnt == 1, idx, -1)
    idx = np.where(np.isneginf(best), -2, idx)
    return idx


def tied_top(S: np.ndarray):
    """同点1位の集合（各党について、1位タイに含まれたか）。"""
    X = np.where(np.isnan(S), -np.inf, S)
    best = X.max(axis=1)
    hit = (X == best[:, None])
    hit[np.isneginf(best)] = False
    return hit


def displayed_top(S: np.ndarray, C: np.ndarray):
    """shindan.html の並べ替え規則をそのまま再現したときに、先頭に出る党。

    JS 側: 一致度の降順 → 判定に使われた設問数(重み込み)の降順 → 元の並び順（安定ソート）。
    つまり同点は「立場を多く示している党」が上に来る。
    """
    n, p = S.shape
    X = np.where(np.isnan(S), -1.0, S.astype(np.float64))
    # 3つのキーを1つの数にまとめる。一致度の最小差(1/3600 以上)より十分小さい桁に下位キーを置く。
    comp = X * 1e9 + C.astype(np.float64) * 100.0 + (p - np.arange(p))[None, :]
    top = np.argmax(comp, axis=1)
    allnan = np.isnan(S).all(axis=1)
    return np.where(allnan, -2, top)


# ---------------------------------------------------------------- 入力空間
def build_space(q: int):
    """回答 3^q 通り × 重み 2^q 通りを、重みごとに分けて返す（メモリのため）。"""
    A = np.array(list(itertools.product([1, 0, -1], repeat=q)), dtype=np.int8)
    return A


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--print", dest="only_print", action="store_true")
    ap.add_argument("--weight-samples", type=int, default=0,
                    help="重みの組み合わせを全数でなく標本で回す場合の本数（0=全数）")
    args = ap.parse_args()

    parties, policy = load_shindan_data()
    q = len(policy)
    names = [p["short"] for p in parties]
    fulls = [p["full"] for p in parties]
    P = np.array([[pol["stance"].get(f, 0) for pol in policy] for f in fulls], dtype=np.int8)

    A = build_space(q)
    n = A.shape[0]
    wcombos = list(itertools.product([WEIGHT_OFF, WEIGHT_ON], repeat=q))
    if args.weight_samples:
        rng = np.random.default_rng(20260721)
        pick = rng.choice(len(wcombos), size=args.weight_samples, replace=False)
        wcombos = [wcombos[i] for i in sorted(pick)]
    total = n * len(wcombos)

    print(f"設問 {q} 問／政党 {len(parties)} 党")
    print(f"回答パターン {n:,} 通り × 重みパターン {len(wcombos):,} 通り = {total:,} 通りを検査します")

    # 集計器
    win = {f: np.zeros(len(parties) + 2, dtype=np.int64) for f in FORMULAS}   # 末尾2つ=引き分け/判定不能
    shown = np.zeros(len(parties) + 1, dtype=np.int64)     # 画面の先頭に出た党（同点は実装の規則で解決）
    tied = np.zeros(len(parties), dtype=np.int64)          # 1位タイに含まれた回数
    sum_pct = np.zeros(len(parties), dtype=np.float64)     # 現行式の平均一致度
    cnt_pct = np.zeros(len(parties), dtype=np.int64)
    flip = {f: 0 for f in FORMULAS if f != "current"}      # 現行式と1位が違った入力数
    flip_denom = 0

    # 中道（賛成と反対が同数）の回答だけを見るための目印
    balanced = (A > 0).sum(axis=1) == (A < 0).sum(axis=1)
    balanced &= (A != 0).any(axis=1)
    win_balanced = np.zeros(len(parties) + 2, dtype=np.int64)
    n_balanced = 0

    for k, w in enumerate(wcombos):
        W = np.broadcast_to(np.array(w, dtype=np.int8), (n, q))
        S = {f: scores(f, A, W, P) for f in FORMULAS}
        tops = {f: top_party(S[f]) for f in FORMULAS}
        for f in FORMULAS:
            t = tops[f]
            win[f] += np.bincount(np.where(t >= 0, t, np.where(t == -1, len(parties), len(parties) + 1)),
                                  minlength=len(parties) + 2)
        # 画面の先頭に出る党（同点は実装の規則＝判定に使われた設問数の多い党が上）。
        # 算出式の比較も、この「利用者が実際に見る1位」どうしで行う。
        C = considered_counts(A, W, P)
        disp = {f: displayed_top(S[f], C) for f in FORMULAS}
        d = disp["current"]
        ok = d >= 0
        flip_denom += int(ok.sum())
        for f in flip:
            flip[f] += int((ok & (disp[f] != d)).sum())
        shown += np.bincount(np.where(d >= 0, d, len(parties)), minlength=len(parties) + 1)
        tied += tied_top(S["current"]).sum(axis=0)
        v = S["current"]
        valid = ~np.isnan(v)
        sum_pct += np.where(valid, v, 0).sum(axis=0)
        cnt_pct += valid.sum(axis=0)
        tb = d[balanced]
        win_balanced += np.bincount(np.where(tb >= 0, tb, np.where(tb == -1, len(parties), len(parties) + 1)),
                                    minlength=len(parties) + 2)
        n_balanced += int(balanced.sum())
        if (k + 1) % 128 == 0 or k + 1 == len(wcombos):
            print(f"  {k+1}/{len(wcombos)} 重みパターン完了", flush=True)

    # ------------------------------------------------------------ まとめ
    nonzero = [int((P[j] != 0).sum()) for j in range(len(parties))]
    # 立場が10問すべてで同じ党の組。同じなら一致度は常に等しくなり、
    # どちらが上に出るかは並べ替えの規則だけで決まってしまう。
    same_pairs = [[names[a], names[b]]
                  for a in range(len(parties)) for b in range(a + 1, len(parties))
                  if np.array_equal(P[a], P[b])]
    res = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d"),
        "questions": q,
        "parties": len(parties),
        "answer_patterns": int(n),
        "weight_patterns": len(wcombos),
        "total_inputs": int(total),
        "formulas": {f: FORMULAS[f] for f in FORMULAS},
        "by_party": [],
        "ties": {f: int(win[f][len(parties)]) for f in FORMULAS},
        "undecidable": {f: int(win[f][len(parties) + 1]) for f in FORMULAS},
        "flip_rate": {f: round(flip[f] / flip_denom * 100, 1) for f in flip},
        "balanced_inputs": n_balanced,
        "identical_stance_pairs": same_pairs,
        "never_displayed": [],      # 下で埋める（1位として画面の先頭に一度も出ない党）
    }
    for j, nm in enumerate(names):
        res["by_party"].append({
            "short": nm, "full": fulls[j],
            "stance_nonzero": nonzero[j],
            "stance_neutral": q - nonzero[j],
            "top_share": {f: round(float(win[f][j]) / total * 100, 2) for f in FORMULAS},
            "shown_share": round(float(shown[j]) / total * 100, 2),
            "tied_share": round(float(tied[j]) / total * 100, 2),
            "mean_pct": round(float(sum_pct[j] / max(cnt_pct[j], 1)) * 100, 1),
            "top_share_balanced": round(float(win_balanced[j]) / max(n_balanced, 1) * 100, 2),
        })

    res["never_displayed"] = [r["short"] for r in res["by_party"] if r["shown_share"] == 0.0]

    # ------------------------------------------------------------ 表示
    if same_pairs:
        print("\n■ 立場が完全に同じ党の組（一致度が常に等しくなる）")
        for a, b in same_pairs:
            print("  {} ＝ {}".format(a, b))
    if res["never_displayed"]:
        print("■ どの入力でも画面の先頭に出ない党： " + "・".join(res["never_displayed"]))
    print("\n■ 現行式（全 {:,} 通りのうち）".format(total))
    print("  党     立場を示した設問  単独1位  同点1位に含む  画面の先頭に出る  中道回答での先頭")
    for r in sorted(res["by_party"], key=lambda r: -r["shown_share"]):
        print("  {:<6} {:>8}/{:<3}  {:>7}% {:>10}% {:>12}% {:>12}%".format(
            r["short"], r["stance_nonzero"], q,
            r["top_share"]["current"], r["tied_share"], r["shown_share"],
            r["top_share_balanced"]))
    print("  （単独1位が決まらない＝同点 {:.2f}%／判定材料なし {:.2f}%）".format(
        res["ties"]["current"] / total * 100, res["undecidable"]["current"] / total * 100))

    print("\n■ 算出式を替えると1位の党が変わる入力の割合")
    for f, v in res["flip_rate"].items():
        print("  {:<18} {:>5}%   {}".format(FORMULAS[f]["label"], v, FORMULAS[f]["desc"][:40] + "…"))

    print("\n■ 別の式での1位の割合")
    hdr = "  党    " + "".join("{:>14}".format(FORMULAS[f]["label"][:12]) for f in FORMULAS)
    print(hdr)
    for r in sorted(res["by_party"], key=lambda r: -r["top_share"]["current"]):
        print("  {:<6}".format(r["short"]) + "".join("{:>13}%".format(r["top_share"][f]) for f in FORMULAS))

    if not args.only_print:
        os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
        io.open(OUT_JSON, "w", encoding="utf-8").write(
            json.dumps(res, ensure_ascii=False, indent=1))
        print("\nwrote", os.path.relpath(OUT_JSON, TOOLS))


if __name__ == "__main__":
    main()
