import sys, json, importlib.util, copy
s=importlib.util.spec_from_file_location("cc","/dev/shm/dkv98/kvcut/compose_cut.py"); cc=importlib.util.module_from_spec(s); s.loader.exec_module(cc)
pin,pout=sys.argv[1:3]; plan=json.load(open(pin)); pre=copy.deepcopy(plan)
for d in sys.argv[3:]:
    r=cc.apply_delta(plan,json.load(open(d)),d); print(d.split("/")[-1],"moves",len(r))
assert cc.strip(plan)==cc.strip(pre)
json.dump(plan,open(pout,"w"),indent=1); open(pout,"a").write("\n")
