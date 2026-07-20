# -*- coding: utf-8 -*-
"""外交・安保タブ用データ収集:①会議録の党別発言候補 ②参院の外交安保法案リスト"""
import urllib.request, urllib.parse, json, time, collections, re, html

FROM, UNTIL = "2025-01-01", "2025-06-30"
KEYWORDS = ["防衛費","防衛力","反撃能力","日米同盟","抑止力","安全保障環境","集団的自衛権","在日米軍"]
API = "https://kokkai.ndl.go.jp/api/speech"

GOV_MARK = ["大臣","副大臣","大臣政務官","政府参考人","参考人","公述人","委員長","会長","局長","長官","主査","議長","副議長"]
def is_gov(s):
    blob = (s.get("speakerPosition") or "")+(s.get("speakerRole") or "")+(s.get("speech") or "")[:22]
    return any(m in blob for m in GOV_MARK)
def norm(g):
    if not g: return "(無所属/不明)"
    for k in ["自由民主党","立憲民主党","公明党","日本維新の会","国民民主党","日本共産党",
              "れいわ","参政","社会民主党","沖縄","無所属"]:
        if k in g: return k
    return g

def fetch(term):
    recs, start = [], 1
    while True:
        q = urllib.parse.urlencode({"any":term,"from":FROM,"until":UNTIL,
            "recordPacking":"json","maximumRecords":100,"startRecord":start})
        data = json.loads(urllib.request.urlopen(f"{API}?{q}",timeout=30).read().decode("utf-8"))
        recs.extend(data.get("speechRecord",[]))
        nxt = data.get("nextRecordPosition")
        if not nxt: break
        start = nxt; time.sleep(0.25)
    return recs

by_id = {}
for kw in KEYWORDS:
    for r in fetch(kw): by_id[r["speechID"]] = r
    time.sleep(0.25)

party = collections.defaultdict(list)
for s in by_id.values():
    if is_gov(s): continue
    p = norm(s.get("speakerGroup"))
    body = (s.get("speech") or "").replace("\r\n"," ").strip()
    if len(body) < 40: continue
    party[p].append({"date":s["date"],"who":s["speaker"],"meeting":s["nameOfMeeting"],
                     "text":body[:120],"url":s["speechURL"]})

out=[]
for p, lst in sorted(party.items(), key=lambda kv:-len(kv[1])):
    out.append(f"\n### {p}  ({len(lst)}件)")
    for e in lst[:3]:
        out.append(f'- {e["date"]} {e["who"]}（{e["meeting"]}）: {e["text"]}\n  {e["url"]}')
open("diplo_speech_candidates.txt","w",encoding="utf-8").write("\n".join(out))
print("speeches:", sum(len(v) for v in party.values()), " parties:", len(party))

# 参院 外交安保 関連法案の抽出
t = open("vote217.html","rb").read().decode("utf-8")
links = re.findall(r'<a\s+href="([^"]+)"[^>]*>(.*?)</a>', t, flags=re.S|re.I)
bills = [(h, re.sub(r'<[^>]+>','',x).strip()) for h,x in links if re.match(r'217-',h)]
DK = ["条約","協定","防衛","自衛隊","安全保障","米軍","北朝鮮","制裁","外国為替","駐留","地位協定","経済安保"]
dip = [(h,n) for h,n in bills if any(k in n for k in DK)]
open("diplo_bills.txt","w",encoding="utf-8").write("\n".join(f"{h}  ||  {n}" for h,n in dip))
print("diplo bills:", len(dip))
