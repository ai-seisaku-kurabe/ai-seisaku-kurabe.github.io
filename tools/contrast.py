# -*- coding: utf-8 -*-
"""色のコントラスト比（WCAG 2.1）を計算する。

**政党の色は変えない。** 政党の識別に関わるので、読みやすさのために色そのものを
いじると別の問題になる。変えてよいのは、その色の上に載せる文字の色のほう。

以前は明るさ（YIQ）のしきい値で白か濃色かを決めていたが、これは実際の
コントラスト比とずれる。実測すると4党が基準（4.5:1）を下回っていた:
  チームみらい #00B8C4 + 白 = 2.43 / 公明 #F55881 + 白 = 3.18
  維新 #12A150 + 白 = 3.37 / 参政 #E8630A + 白 = 3.38
比で選び直すと、10党すべてが 4.56 以上になる（この4党は濃色の文字になる）。

build_site.py / build_party.py / agents/verify_content.py が共有する。
写しを作らない（片方だけ直すと、ページごとに文字色が食い違う）。
"""

AA_SMALL = 4.5      # 通常の文字（WCAG 2.1 AA）
AA_LARGE = 3.0      # 大きな文字・UI部品の境界

DARK_TEXT = "#1b2130"
LIGHT_TEXT = "#ffffff"


def _channel(v):
    v = v / 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luminance(hx):
    """相対輝度（WCAG の定義）。"""
    hx = hx.lstrip("#")
    r, g, b = (int(hx[i:i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * _channel(r) + 0.7152 * _channel(g) + 0.0722 * _channel(b)


def ratio(a, b):
    """2色のコントラスト比（1〜21）。"""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def best_text(bg):
    """背景色に対して、コントラスト比が高いほうの文字色を返す。"""
    return DARK_TEXT if ratio(DARK_TEXT, bg) >= ratio(LIGHT_TEXT, bg) else LIGHT_TEXT


def _mix(a, b, t):
    """色aを色bへ t の割合だけ寄せる。"""
    a, b = a.lstrip("#"), b.lstrip("#")
    out = []
    for i in (0, 2, 4):
        ca, cb = int(a[i:i + 2], 16), int(b[i:i + 2], 16)
        out.append(round(ca + (cb - ca) * t))
    return "#%02x%02x%02x" % tuple(out)


def readable_on(color, bg, target=AA_SMALL):
    """その色を**文字色として**地の色の上に置けるところまで濃く（暗い地なら明るく）する。

    党の色をそのまま文字色に使うと、明るい色は地に沈む
    （国民 #F2B200 は白地で1.88:1、チームみらい #00B8C4 は2.43:1 でほぼ読めない）。
    かといって色を捨てると党の見分けがつかなくなるので、**色相は保ったまま**
    地の色から遠い方向へ少しずつ寄せ、基準を満たした時点で止める。

    背景として使うとき（`best_text`）とは別の用途。混同しないこと。
    """
    if ratio(color, bg) >= target:
        return color.lower()
    toward = "#000000" if luminance(bg) > 0.18 else "#ffffff"
    cur = color
    for i in range(1, 21):
        cur = _mix(color, toward, i * 0.05)
        if ratio(cur, bg) >= target:
            return cur
    return cur
