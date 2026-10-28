import json,sys,collections
sys.path.insert(0,sys.argv[1]); import count_align_plan as C
Q="/srv/opentallas-scratch2/claude/die-qc11-1028/ca/t10"; pr=sys.argv[2]
rows=C.load_rows(Q+"/grp_spice_xing_lpo.json","TT_droop-regions_corelat250,FF_droop-regions_corelat202.5")
ctx=C.clock_contexts(pr,"/srv/opentallas-scratch2/claude/codex-die-qc-0359-1028/build_inputs/event/qc_k2b_phase12.json",["TT","FF"],"spice","table","shared",pr+"/droop_regions.json",202.5)
root,E,info=C.clock_start_edges(rows,ctx,clean_by="width",retime_up=True)
inc=collections.Counter(e["dst"] for e in E); dup=[k for k,v in inc.items() if v>1]
print("edges",len(E),"fail",sum(not e["clean_ok"] for e in E),"dup dst",len(dup),dup[:5])
for e in E:
    if e["dst"] in dup[:2]: print(e["port"],e["launch"],e["capture"])
c0=ctx["TT"]
ups=[e for e in E if e["retime"] and not e["launch"].startswith("__st__") and C._lcp(c0["taps"][e["launch"]]["tree_path"], e["capture"][6:])==e["capture"][6:]]
w=sorted(round(e["p_up_ps"]+e["p_dn_ps"],1) for e in ups)
print("climb-up segments",len(ups),"width min/med/max",w[:1],w[len(w)//2] if w else None,w[-3:], "limit 208.25")
