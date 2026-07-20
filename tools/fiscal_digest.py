# -*- coding: utf-8 -*-
"""
検証可能性インフラ 試作 v0.1
財政(持続可能性)ドメイン / 党(会派)単位の集計 + 証拠リンク
- 点数化しない。発言の「量」と「証拠リンク」だけを出す。
- キーワード群は設計判断(価値観が入る)。透明化のため明示。
Source: 国会会議録検索システム API (国立国会図書館) https://kokkai.ndl.go.jp/api.html
"""
import urllib.request, urllib.parse, json, time, collections

# --- 設計判断: 財政"持続可能性"に関する実質語のバスケット(恣意性を認めて明示) ---
KEYWORDS = [
    "基礎的財政収支", "プライマリーバランス", "財政健全化", "財政規律",
    "債務残高", "国債残高", "財政再建", "歳出改革",
]
FROM, UNTIL = "2025-01-01", "2025-06-30"   # 第217回 常会(予算審議期)
API = "https://kokkai.ndl.go.jp/api/speech"

def fetch(term):
    recs, start = [], 1
    while True:
        q = urllib.parse.urlencode({
            "any": term, "from": FROM, "until": UNTIL,
            "recordPacking": "json", "maximumRecords": 100, "startRecord": start,
        })
        with urllib.request.urlopen(f"{API}?{q}", timeout=30) as r:
            data = json.loads(r.read().decode("utf-8"))
        recs.extend(data.get("speechRecord", []))
        nxt = data.get("nextRecordPosition")
        if not nxt:
            break
        start = nxt
        time.sleep(0.3)
    return recs

# --- 収集 & speechIDで重複排除 ---
by_id = {}
for kw in KEYWORDS:
    for rec in fetch(kw):
        by_id[rec["speechID"]] = rec
    time.sleep(0.3)

speeches = list(by_id.values())

# 答弁側(政府)/参考人/公述人 か、質問側(議員)かを判定
GOV_MARK = ["大臣", "副大臣", "大臣政務官", "政府参考人", "参考人", "公述人",
            "委員長", "会長", "局長", "長官", "主査", "議長", "副議長", "君主査"]
def is_gov(s):
    pos = (s.get("speakerPosition") or "") + (s.get("speakerRole") or "")
    head = (s.get("speech") or "")[:22]   # 「○政府参考人（…」「○内閣総理大臣（…」等の冒頭
    blob = pos + head
    return any(m in blob for m in GOV_MARK)

# 会派名の正規化(短縮)
def norm(g):
    if not g: return "(無所属/不明)"
    for key in ["自由民主党", "立憲民主党", "公明党", "日本維新の会", "国民民主党",
                "日本共産党", "れいわ", "参政党", "社会民主党", "無所属"]:
        if key in g: return key
    return g

# --- 党単位の集計(質問側議員のみを"熟議"としてカウント) ---
party = collections.defaultdict(lambda: {"nq": 0, "ng": 0, "speakers": set(),
                                          "meetings": set(), "ex": []})
n_gov_total = 0
for s in speeches:
    gov = is_gov(s)
    n_gov_total += 1 if gov else 0
    p = norm(s.get("speakerGroup"))
    d = party[p]
    if gov:
        d["ng"] += 1          # 答弁・参考人など(非・質問側)
    else:
        d["nq"] += 1          # 質問側議員の発言
        d["speakers"].add(s.get("speaker"))
        d["meetings"].add(s.get("nameOfMeeting"))
        if len(d["ex"]) < 4:
            body = (s.get("speech") or "").replace("\r\n", " ").strip()
            d["ex"].append({"date": s["date"], "speaker": s["speaker"],
                            "meeting": s["nameOfMeeting"], "snippet": body[:90],
                            "url": s["speechURL"]})

# --- JSON出力(artifact用の確定データ) 質問側発言数nqで降順 ---
out = {"from": FROM, "until": UNTIL, "keywords": KEYWORDS,
       "total": len(speeches), "gov_total": n_gov_total, "parties": []}
for p, d in sorted(party.items(), key=lambda kv: -kv[1]["nq"]):
    n_sp = len(d["speakers"])
    if d["nq"] == 0:
        continue
    out["parties"].append({
        "party": p, "nq": d["nq"], "ng": d["ng"], "speakers": n_sp,
        "per_capita": round(d["nq"] / n_sp, 1) if n_sp else 0,
        "meetings": sorted(d["meetings"]), "evidence": d["ex"],
    })
with open("fiscal_data.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("WROTE fiscal_data.json  total=", len(speeches),
      " gov/answer=", n_gov_total, " questioner=", len(speeches) - n_gov_total,
      " parties=", len(out["parties"]))
for pp in out["parties"]:
    print(f'  {pp["party"]:<20} 質問{pp["nq"]:>3}  議員{pp["speakers"]:>3}  '
          f'一人当{pp["per_capita"]:>4}  (答弁側{pp["ng"]})')
