# -*- coding: utf-8 -*-
"""ワンイシュー深掘り用: 各党のワンイシューに関わる国会発言を複数取得。
挨拶文でなく争点キーワード周辺を抜き出して oneissue_speech.json に保存。"""
import urllib.request, urllib.parse, json, time, re, sys, os
import quote
FROM, UNTIL = "2025-01-01", "2025-06-30"
API = "https://kokkai.ndl.go.jp/api/speech"
GOV = ["大臣","副大臣","大臣政務官","政府参考人","参考人","公述人","委員長","会長","局長","長官","主査","議長","副議長","事務総長"]
def is_gov(s):
    blob=(s.get("speakerPosition") or "")+(s.get("speech") or "")[:22]
    return any(m in blob for m in GOV)
# (党, 検索語, 会派キー, 話者しばり, [抜き出しキーワード], 期間の上書き or None)
# ※ 話者しばりは「その党の議員1人だけを集めた編集物」になるため、原則として使わない。
#    会派が存在しない会期をどうしても扱う必要がある場合に限る。
JOBS = [
 ("自由民主党","抑止力",  "自由民主党",None, ["抑止力","防衛力","反撃能力","防衛費","安全保障","国を守る"], None),
 ("立憲民主党","説明責任","立憲民主",  None, ["説明責任","透明","予算","政治とカネ","公文書","情報公開","国民に説明"], None),
 ("日本維新の会","歳出改革","日本維新の会",None,["歳出","身を切る","議員定数","行財政改革","無駄","身を切る改革","改革"], None),
 ("国民民主党","手取り",  "国民民主",  None, ["手取り","年収の壁","103万","減税","可処分所得","ガソリン","賃上げ"], None),
 ("公明党","処遇改善",   "公明党",    None, ["処遇改善","介護","保育","福祉","賃上げ","子育て","現場"], None),
 ("日本共産党","軍事費",  "日本共産党",None, ["軍事費","軍拡","大軍拡","暮らし","社会保障","増税","負担"], None),
 ("れいわ新選組","消費税","れいわ",   None, ["消費税","積極財政","廃止","デフレ","給付","財源"], None),
 # 参政党は第217回の時期に会派が無く、以前は議員1人を指定して集めていた。
 # 第221回で会派を結成したため、会派キーで複数の議員から集める形に改めた。
 ("参政党","消費税",     "参政",None,["消費税","減税","インボイス","財政","税収","負担"], ("2026-01-01","2026-07-20")),
]
def fetch(term, period=None):
    fr,un = period or (FROM, UNTIL)
    q=urllib.parse.urlencode({"any":term,"from":fr,"until":un,"recordPacking":"json","maximumRecords":90})
    return json.loads(urllib.request.urlopen(f"{API}?{q}",timeout=30).read().decode("utf-8")).get("speechRecord",[])
def snippet(body, kws):
    """争点キーワードを含む文を、文の切れ目で抜き出す（切り出しは quote.py に集約）。"""
    for kw in kws:
        if kw in quote.strip_speaker(body):
            return quote.condense(quote.snippet(body, kw)), True
    return quote.condense(quote.snippet(body)), False

# --only <党名> を付けると、その党だけ取り直して既存のJSONに差し替える
ONLY = sys.argv[sys.argv.index("--only")+1] if "--only" in sys.argv else None
out={}
if ONLY and os.path.exists("oneissue_speech.json"):
    out=json.load(open("oneissue_speech.json",encoding="utf-8"))
for full,term,gkey,speaker,kws,period in JOBS:
    if ONLY and full!=ONLY: continue
    prim=[]; sub=[]; seen=set()
    for s in fetch(term, period):
        if is_gov(s): continue
        g=s.get("speakerGroup") or ""; sp=s.get("speaker") or ""
        if speaker and speaker not in sp: continue
        if (not speaker) and gkey not in g: continue
        body=(s.get("speech") or "").replace("\r\n"," ").strip()
        if len(body)<70 or "会議録情報" in body: continue
        k=sp+body[:16]
        if k in seen: continue
        seen.add(k)
        text,hit=snippet(body,kws)
        rec={"who":sp,"meeting":s["nameOfMeeting"],"date":s["date"],"text":text,"url":s["speechURL"]}
        (prim if hit else sub).append(rec)
    got=(prim+sub)[:4]
    out[full]=got
    print(f"{full}: {len(got)} (キーワード一致 {len(prim)})")
    time.sleep(0.4)
json.dump(out,open("oneissue_speech.json","w",encoding="utf-8"),ensure_ascii=False,indent=1)
print("total:", sum(len(v) for v in out.values()))
