import json,sys,hashlib
pj,ref,out=sys.argv[1:4]
raw=open(pj,"rb").read();d=json.loads(raw);m=d["modules"]["qfd_tt_ctlm_dv_lpf_hp13_lp"]["netnames"]
r=json.load(open(ref))
nn={k:m[k]["bits"] for k in r["netnames"]}
o=dict(source_path=pj,source_sha256=hashlib.sha256(raw).hexdigest(),source_top="qfd_tt_ctlm_dv_lpf_hp13_lp",netnames=nn)
json.dump(o,open(out,"w"),indent=2);print("same_as_ref" if nn==r["netnames"] else "DIFFERS", sum(len(v) for v in nn.values()))
