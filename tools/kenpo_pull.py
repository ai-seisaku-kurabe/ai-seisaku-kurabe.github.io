# -*- coding: utf-8 -*-
"""憲法タブ用:憲法審査会の党別発言候補（行=採決は無いので言のみ）"""
import urllib.request, urllib.parse, json, time, collections
FROM, UNTIL = "2025-01-01", "2025-06-30"
API = "https://kokkai.ndl.go.jp/api/speech"
GOV_MARK = ["会長","委員長","事務","幹事","副会長"]  # 憲法審査会は委員の意見表明中心
def skip(s):
    blob=(s.get("speakerPosition") or "")+(s.get("speech") or "")[:16]
    return any(m in blob for m in GOV_MARK)
def norm(g):
    if not g: return "(無所属/不明)"
    for k in ["自由民主党","立憲民主党","公明党","日本維新の会","国民民主党","日本共産党",
              "れいわ","参政","社会民主党","沖縄","有志","保守","無所属"]:
        if k in g: return k
    return g
def fetch():
    recs,start=[],1
    while True:
        q=urllib.parse.urlencode({"nameOfMeeting":"憲法審査会","from":FROM,"until":UNTIL,
            "recordPacking":"json","maximumRecords":100,"startRecord":start})
        d=json.loads(urllib.request.urlopen(f"{API}?{q}",timeout=30).read().decode("utf-8"))
        recs.extend(d.get("speechRecord",[])); nxt=d.get("nextRecordPosition")
        if not nxt: break
        start=nxt; time.sleep(0.25)
    return recs
party=collections.defaultdict(list)
for s in fetch():
    if skip(s): continue
    p=norm(s.get("speakerGroup")); body=(s.get("speech") or "").replace("\r\n"," ").strip()
    if len(body)<50 or "会議録情報" in body: continue
    party[p].append({"date":s["date"],"who":s["speaker"],"meeting":s["nameOfMeeting"],
                     "text":body[:150],"url":s["speechURL"]})
out=[]
for p,lst in sorted(party.items(),key=lambda kv:-len(kv[1])):
    out.append(f"\n### {p}  ({len(lst)}件)")
    for e in lst[:3]:
        out.append(f'- {e["date"]} {e["who"]}（{e["meeting"]}）: {e["text"]}\n  {e["url"]}')
open("kenpo_speech_candidates.txt","w",encoding="utf-8").write("\n".join(out))
print("speeches:",sum(len(v) for v in party.values())," parties:",len(party))
print(" / ".join(f"{p}:{len(v)}" for p,v in sorted(party.items(),key=lambda kv:-len(kv[1]))))
