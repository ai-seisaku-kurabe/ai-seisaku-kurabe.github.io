/* ===== Firebase 設定 =====
   Firebaseコンソール > プロジェクト設定 > 「マイアプリ(ウェブ)」で発行される値を貼り付けてください。
   未設定のままでもサイトは動作します(結果送信と集計だけ無効になります)。 */
var FIREBASE_CONFIG = {
  apiKey: "AIzaSyDBZBjGT456mpQOgQF9cF4-mCB6r1TWPyA",
  authDomain: "aipolitics-9c657.firebaseapp.com",
  projectId: "aipolitics-9c657"
};
/* ======================== */
/* App Check（bot・不正投稿対策・任意）。使う場合は reCAPTCHA v3 のサイトキーを入れる。空なら無効。
   ※コンソールで「適用(enforce)」する前に、キーを入れて動作確認すること（順序はREADME参照）。 */
var RECAPTCHA_SITE_KEY = "";
var PARTY_ID = {"自由民主党": "jimin", "立憲民主党": "rikken", "日本維新の会": "ishin", "国民民主党": "kokumin", "公明党": "komei", "日本共産党": "kyosan", "れいわ新選組": "reiwa", "参政党": "sansei", "none": "none"};
window.KG = (function(){
  var db=null, ready=false;
  try{
    if(FIREBASE_CONFIG.apiKey && FIREBASE_CONFIG.apiKey.indexOf("PASTE")<0 && window.firebase){
      firebase.initializeApp(FIREBASE_CONFIG);
      try{ if(RECAPTCHA_SITE_KEY && firebase.appCheck){ firebase.appCheck().activate(RECAPTCHA_SITE_KEY, true); } }catch(e){}
      db=firebase.firestore(); ready=true;
    }
  }catch(e){ ready=false; }
  function inc(){ return firebase.firestore.FieldValue.increment(1); }
  return {
    enabled:function(){return ready;},
    sendResult:function(pickFull, answers, weights){
      if(!ready) return;
      var pid = PARTY_ID[pickFull] || "other";
      var upd = { responses: inc() }; upd["oi_"+pid]=inc();
      (answers||[]).forEach(function(a,i){ var k=a>0?"agree":(a<0?"oppose":"neutral"); upd["p"+i+"_"+k]=inc(); });
      (weights||[]).forEach(function(w,i){ if(w>1) upd["wt"+i]=inc(); });  // ◎重視された争点
      db.doc("aggregates/summary").set(upd,{merge:true}).catch(function(){});
    },
    loadAgg: async function(){
      if(!ready) return null;
      try{ var s=await db.doc("aggregates/summary").get(); return s.exists? s.data(): null; }
      catch(e){ return null; }
    }
  };
})();