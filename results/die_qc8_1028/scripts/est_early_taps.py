import json,collections,statistics as st
D=json.load(open("/tmp/qc8_est_rows.json"))
reg=json.load(open("/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/part_region.json"))["part_region"]
TT=D["TT"]["rows"];FF=D["FF"]["rows"]
G=collections.defaultdict(list)
for p,r in TT.items(): G[reg[r["part"]]].append(p)
def kls(g): return "c" if g.startswith("c_") else ("su_c" if g.endswith("su_c") else g.split("_")[0])
res=collections.defaultdict(list)
for g,ps in G.items():
  k=kls(g)
  e2t_tt={p:TT[p]["tree"]-TT[p]["ent_arr"] for p in ps}; e2t_ff={p:FF[p]["tree"]-FF[p]["ent_arr"] for p in ps}
  rho=st.median(e2t_ff[p]/e2t_tt[p] for p in ps)
  # S1: early taps exact at TT; FF gets rho*early_TT
  b1t={p:TT[p]["tree"]+250.0 for p in ps}
  b1f={p:FF[p]["tree"]+FF[p]["lat"]-rho*(TT[p]["lat"]-250.0) for p in ps}
  grid=[p for p in ps if not TT[p]["core"]];core=[p for p in ps if TT[p]["core"]]
  sp=lambda d,L: (max(d[p] for p in L)-min(d[p] for p in L)) if L else 0
  tt0={p:TT[p]["base"] for p in ps};ff0={p:FF[p]["base"] for p in ps}
  ocv_t=0.062*max(e2t_tt.values());ocv_f=0.062*max(e2t_ff.values())
  res[k].append(dict(g=g,n=len(ps),now=(sp(tt0,ps),sp(ff0,ps)),s1=(sp(b1t,ps),sp(b1f,ps)),grid_tree=sp(b1t,grid),core_tree=sp(b1t,core),
      e2t=(min(e2t_tt.values()),max(e2t_tt.values())),ocv=(ocv_t,ocv_f),rho=rho))
for k,L in sorted(res.items()):
  f=lambda key,i: (st.median(x[key][i] for x in L),max(x[key][i] for x in L))
  print(f"{k:9s} regs {len(L):3d} now TT {f('now',0)[0]:.0f}/{f('now',0)[1]:.0f} FF {f('now',1)[0]:.0f}/{f('now',1)[1]:.0f} | S1 early-tap TT {f('s1',0)[0]:.0f}/{f('s1',0)[1]:.0f} FF {f('s1',1)[0]:.0f}/{f('s1',1)[1]:.0f} | grid-only tree max {max(x['grid_tree'] for x in L):.0f} core-only {max(x['core_tree'] for x in L):.0f} | e2t {min(x['e2t'][0] for x in L):.0f}-{max(x['e2t'][1] for x in L):.0f} ocv~{max(x['ocv'][0] for x in L):.0f}/{max(x['ocv'][1] for x in L):.0f} rho {st.median(x['rho'] for x in L):.3f}")
  over=[x for x in L if x["s1"][0]+x["ocv"][0]>150 or x["s1"][1]+x["ocv"][1]>150]
  print(f"   S1+OCV>150: {len(over)}/{len(L)} regions")
json.dump(res,open("/tmp/qc8_est_s1.json","w"))
