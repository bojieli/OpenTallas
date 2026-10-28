import json,sys,os,shutil
base,out=sys.argv[1],sys.argv[2]; kv=json.loads(sys.argv[3])
os.makedirs(out,exist_ok=True)
s=json.load(open(base+"/clock_spec.json")); s.update(kv)
json.dump(s,open(out+"/clock_spec.json","w"))
os.link(base+"/plan.json",out+"/plan.json") if not os.path.exists(out+"/plan.json") else None
