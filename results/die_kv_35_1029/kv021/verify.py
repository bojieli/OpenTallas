import json,sys
sys.path.insert(0,"/srv/opentallas-scratch2/claude/wt/die-kv-33-leaf/tools/die_plan")
import count_align_bind as B
b=json.load(open(sys.argv[1])); v=B.verify(b,samples=int(sys.argv[2]))
json.dump(v,open(sys.argv[1]+".verify.json","w"),indent=1)
print(json.dumps({k:v[k] for k in v if k!="sim_worst_ports"}))
