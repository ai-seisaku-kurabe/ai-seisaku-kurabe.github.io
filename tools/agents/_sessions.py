# -*- coding: utf-8 -*-
"""掲載している会期の一覧を、表示側の定義から読む（監査と検証で共有する）。

会期を足したり減らしたりするのは `build_party.py` の `sessions_for()` で、
表示側3か所が同じ並びを使うようになっている。監査スクリプトが会期を
別に書き持つと、**サイトは3会期を出しているのに監査は2会期分の数字を出す**
という食い違いが起きる（⑧査読で実際に指摘された）。

数字の出どころは1つにする。
"""
import os, re

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)


def published_sessions():
    """掲載中の会期番号を、古い順に返す（例: ["217", "219", "221"]）。"""
    src = open(os.path.join(TOOLS, "build_party.py"), encoding="utf-8").read()
    m = re.search(r"def sessions_for\(.*?\n(?=\S)", src, re.S)
    if not m:
        raise SystemExit("build_party.py の sessions_for() が見つかりません。"
                         "会期の一覧の出どころが変わった可能性があります。")
    ses = re.findall(r'\("第(\d+)回"', m.group(0))
    if not ses:
        raise SystemExit("sessions_for() から会期を読み取れませんでした。")
    seen = []
    for s in ses:
        if s not in seen:
            seen.append(s)
    return seen
