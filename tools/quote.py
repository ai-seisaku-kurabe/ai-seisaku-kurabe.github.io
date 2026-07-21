# -*- coding: utf-8 -*-
"""引用の切り出しを1か所にまとめる。

固定幅で切ると、「しましては、…」のように文の途中から始まる引用や、
「…というふうに」で途切れる引用が生まれる。原文の文字列ではあっても、
文の途中を切り出したものは読者に別の意味を与える。ルール2（引用は原文のまま）は、
文として成立していることまで含めて守る。**文の途中では絶対に切らない。**

同じ切り出し処理が fetch_session_speeches.py / fetch_oneissue.py / ss_pull.py /
energy_pull.py / econ_pull.py に別々に書かれ、同じ欠陥が5か所にあった。
1か所に集約して、直したら全部直るようにする。
"""
import re
import unicodedata

MINLEN, MAXLEN = 60, 260   # 短いと次の文を足す／長くても文の途中では切らない
SENT_END = "。？！"


def strip_speaker(body):
    """会議録の先頭表記「○山田委員　」を落とす。"""
    return re.sub(r"^○[^　]{1,14}　", "", str(body))


def sentences(body):
    b = re.sub(r"\s+", " ", strip_speaker(body)).strip()
    return [s.strip() for s in re.split(r"(?<=[。？！])", b) if s.strip()]


def snippet(body, term=None, minlen=MINLEN, maxlen=MAXLEN):
    """term を含む文を、文の切れ目で抜き出す。

    term が無い／見つからないときは、挨拶や前置きになりがちな1文目を避けて2文目から。
    """
    ss = sentences(body)
    if not ss:
        return ""
    idx = next((k for k, s in enumerate(ss) if term and term in s), None)
    if idx is None:
        idx = 1 if len(ss) > 2 else 0
    out = ss[idx]
    k = idx + 1
    # 短いときだけ後ろの文を足す。順序は原文のまま、中略は挟まない。
    while len(out) < minlen and k < len(ss) and len(out) + len(ss[k]) <= maxlen:
        out += ss[k]
        k += 1
    return out


def condense(text, limit=160):
    """長い引用の中間を、読点の切れ目で「…」に置き換える。

    文の切れ目に揃えると、国会答弁の1文は250字を超えることがある。
    そこで**文頭と文末は文の切れ目のまま保ち、中間だけを省く**。
    省略は必ず「…」で示し、残した断片は原文と同じ順序のままなので、
    ③検証班の断片順序の照合をそのまま通る（ルール2の作法どおり）。

    読点が無い文は、途中で切るくらいなら長いまま残す。
    """
    t = re.sub(r"\s+", " ", str(text)).strip()
    if len(t) <= limit:
        return t
    parts = [p for p in re.split(r"(?<=、)", t) if p]
    if len(parts) < 3:
        return t                      # 切れ目が無い。文の途中では切らない。
    half = limit * 0.5
    head, tail, hl, tl = [], [], 0, 0
    i, j = 0, len(parts) - 1
    while i <= j:
        if hl <= tl and hl + len(parts[i]) <= half:
            head.append(parts[i]); hl += len(parts[i]); i += 1
        elif tl + len(parts[j]) <= half:
            tail.insert(0, parts[j]); tl += len(parts[j]); j -= 1
        else:
            break
    if i > j or not head or not tail:
        return t                      # 省くところが無い
    out = "".join(head).rstrip("、") + "…" + "".join(tail)
    return re.sub(r"…+", "…", out)


def _packed(s):
    """空白を除いた文字列と、元の文字列における各文字の位置を返す。"""
    chars, pos = [], []
    for i, ch in enumerate(s):
        if not ch.isspace():
            chars.append(ch)
            pos.append(i)
    return "".join(chars), pos


def snap_to_sentences(body, quote):
    """既存の引用を、原文の文の切れ目まで外側に広げる。

    **どこを引くかという選定は編集判断なので変えない。**
    文の途中から始まっている引用を文の頭まで、途中で終わっている引用を文の終わりまで、
    伸ばすだけ。中略「…」を含む引用は、前後の端だけを動かして中略は保つ。

    戻り値: (直した引用, 直したか) ／ 原文に見つからないときは元のまま返す。
    """
    src = re.sub(r"\s+", " ", strip_speaker(body)).strip()
    packed, pos = _packed(src)
    nkey = unicodedata.normalize("NFKC", packed)
    if len(nkey) != len(packed):
        return quote, False          # 位置がずれるので触らない（稀）

    frags = [f for f in re.split(r"[…‥]+|\.{3,}", str(quote)) if f.strip()]
    if not frags:
        return quote, False
    first, _ = _packed(unicodedata.normalize("NFKC", frags[0]))
    last, _ = _packed(unicodedata.normalize("NFKC", frags[-1]))
    i = nkey.find(first)
    j = nkey.find(last, i if i >= 0 else 0)
    if i < 0 or j < 0:
        return quote, False          # 原文に見つからない（照合側が別途報告する）
    j += len(last)

    # 前へ: 直前の句点の次まで戻す
    s = i
    while s > 0 and nkey[s - 1] not in SENT_END + "」』":
        s -= 1
    # 後ろへ: 次の句点まで進める（句点は含める）
    e = j
    while e < len(nkey) and nkey[e - 1] not in SENT_END:
        e += 1

    fixed = src[pos[s]:pos[e - 1] + 1].strip()
    if len(frags) > 1:               # 中略は保つ
        mid = "…".join(f.strip() for f in frags[1:-1])
        head = src[pos[s]:pos[i + len(first) - 1] + 1].strip()
        tail = src[pos[j - len(last)]:pos[e - 1] + 1].strip()
        fixed = "…".join(x for x in (head, mid, tail) if x)
    return fixed, fixed != quote
