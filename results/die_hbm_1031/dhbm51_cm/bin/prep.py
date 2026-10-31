import json,os,shutil,sys,hashlib
src="/srv/opentallas-scratch2/claude/die-hbm-48/plan/d44g"; cmf="/srv/opentallas-scratch2/claude/die-hbm-48/kits/plan_d44f_cm/core_macros.json"
out=sys.argv[1]; S=json.load(open(sys.argv[2]))
if os.path.exists(out): shutil.rmtree(out)
os.makedirs(out)
for f in os.listdir(src):
    if f=="core_macros.json" or f.startswith("g0"): continue
    s=os.path.join(src,f)
    shutil.copytree(s,os.path.join(out,f),copy_function=os.link) if os.path.isdir(s) else os.link(s,os.path.join(out,f))
cm=json.load(open(cmf))
for c in S:
    e=cm["cores"][c]
    if e.get("status")=="KNOWN" and e.get("macros"):
        cm["cores"][c]={"status":"UNKNOWN","outline_um":e["outline_um"],"why":"DIE-HBM-49 re-site (macro_channels FAIL): was KNOWN basis %r, %d macros, core_macros sha %s"%(str(e.get("basis"))[:80],len(e["macros"]),hashlib.sha256(open(cmf,"rb").read()).hexdigest()[:12]),"recipe_macros":e.get("recipe_macros")}
json.dump(cm,open(os.path.join(out,"core_macros.json"),"w"),indent=1)
print("prep ok",len(S))
