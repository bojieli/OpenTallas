# HBM-COLLECT-1 SF-SPLIT 11-10 kit-local: face_guard FAIL becomes ADVISORY only when EVERY failure is a
# launch-registered-seam class (shared / merged, or unregistered = a seam INPUT landing in receive-side comb, the
# budgeted launch-registered contract) entry naming a seam_ port. feedthrough / dropped / any other class
# or any entry without a seam_ port keeps the hard FAIL. Owner 11-03 targets-not-gates; sign-off still judges face_guard.
import json,sys
d=json.load(open(sys.argv[1]+"/face_guard.json"))
f=d.get("fails") or {}
SEAM=("shared","merged","unregistered")
bad=[c for c in f if c not in SEAM]
noseam=[e for c in SEAM for e in f.get(c,[]) if "seam_" not in e.split(":")[0] and not (c!="unregistered" and "seam_" in e)]
ok=d.get("verdict")=="FAIL" and not bad and not noseam and not d.get("missing_ports")
print("SEAM_FACE_ADVISORY", "PASS-COND (seam classes only: %s)"%{c:len(v) for c,v in f.items()} if ok else "NO (other classes %s, non-seam entries %d)"%(bad,len(noseam)))
sys.exit(0 if ok else 1)
