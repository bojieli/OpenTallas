import json,statistics as st,sys
R,F=sys.argv[1],sys.argv[2]
mods={"ot_qwen_tile_romleaf":"romleaf","ot_qwen_tile_lsl_rawfault_m3":"rawleaf","ot_qwen_tile_node":"node"}
out={}
for t in ("nk","nl"):
  out[t]={}
  for C in ("TT","FF"):
    regs=[];ch={}
    for l in open(f"{R}/{t}/ins_{C}.txt"):
      f=l.split()
      if f[0]=="REG": regs.append(float(f[2]))
      else:
        k=mods[f[2]]; ci=json.load(open(f"{F}/{k}/ck_{C.lower()}.json"))["regs"]
        ch.setdefault(k,[]).append(dict(inst=f[1],pin=float(f[3]),tot_mean=float(f[3])+ci["mean"],tot_min=float(f[3])+ci["min"],tot_max=float(f[3])+ci["max"]))
    r=dict(parent_regs=dict(n=len(regs),mean=round(st.mean(regs),1),min=round(min(regs),1),max=round(max(regs),1)))
    for k,v in ch.items():
      p=[x["pin"] for x in v]
      r[k]=dict(n=len(v),pin_mean=round(st.mean(p),1),pin_min=round(min(p),1),pin_max=round(max(p),1),
                total_mean=round(st.mean(x["tot_mean"] for x in v),1),total_min=round(min(x["tot_min"] for x in v),1),total_max=round(max(x["tot_max"] for x in v),1))
    allf=regs+[x["tot_mean"] for v in ch.values() for x in v]
    r["all_endpoints_mean_basis"]=dict(min=round(min(allf),1),max=round(max(allf),1))
    out[t][C]=r
print(json.dumps(out,indent=1))
