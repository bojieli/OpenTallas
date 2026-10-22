import json,re,collections,sys
d=json.load(open(sys.argv[1])); md=d["masters_detail"]
V={1:"qfd_landh0d8_1_EW_16x16",3:"qfd_landh0d8_3_EW_17x17",10:"qfd_landh0d8_10_EW_19x19",32:"qfd_landh0d8_32_EW_28x26",
   107:"qfd_landh0d8g_107_EW_52x52",116:"qfd_landh0d8g_116_EW_52x52",151:"qfd_landh0d8s_151_EW_98x171",173:"qfd_landh0d8s_173_EW_98x171",
   174:"qfd_landh0d8s_174_EW_98x171",182:"qfd_landh0d8s_182_EW_98x171",183:"qfd_landh0d8s_183_EW_98x171"}
ws=sorted(V)
def dec(W):
  best=[None]*(W+1); best[0]=[]
  for x in range(1,W+1):
    for w in ws:
      if w<=x and best[x-w] is not None and (best[x] is None or len(best[x-w])+1<len(best[x])): best[x]=best[x-w]+[w]
  return sorted(best[W],reverse=True)
out={"source":sys.argv[1],"landh0":{},"other_unbound":{},"summary":{}}
cnt=collections.Counter()
for k,v in sorted(md.items()):
  m=re.match(r"qfd_(landh0|landh|rlyh0|rlyh)_(\d+)_([A-Z]+)_",k)
  if not m or v["bound"]: continue
  fam,w,dr=m.groups(); w=int(w)
  if fam=="landh0":
    if w in (514,516): comp="CB16 qfd_c_land_w257/r257 or w258/r258 pairs (CB16 lane)"; cnt["landh0_cb16"]+=v["instances"]
    else: comp=[V[x] for x in dec(w)]; cnt["landh0_d8_compose"]+=v["instances"]; cnt["landh0_d8_tiles"]+=v["instances"]*len(comp)
    out["landh0"][k]={"instances":v["instances"],"compose":comp}
  else:
    out["other_unbound"][k]=v["instances"]; cnt[fam]+=v["instances"]
out["summary"]=dict(cnt); out["summary"]["other_masters"]=len(out["other_unbound"])
json.dump(out,open(sys.argv[2],"w"),indent=1); print(json.dumps(out["summary"]))
for k in ["qfd_landh0_48_EW_65x30","qfd_landh0_512_EN_65x91","qfd_landh0_1088_EN_65x186","qfd_landh0_548_EN_65x97","qfd_landh0_520_NE_65x91"]:
  print(k,out["landh0"].get(k))
