import json,sys
# DIE-HBM-82-EP6 d44v part 49: take station_resite.py chains only where the wbq_sw/aqhi move touched them (a register newly inside a
# moved/grown core body+halo, or a chain ending on a moved core); every other chain stays byte-same.
# usage: hyb.py MOVED.json RESITED.json BASE.json OUT.json
# keep mv/new chains; take station_resite's chain only where the move touched it
N=json.load(open(sys.argv[1])); R=json.load(open(sys.argv[2])); B=json.load(open(sys.argv[3]))
for tn in ("q_hub_nw","q_hub_ne"):
  tN,tR,tB=N["partition_types"][tn],R["partition_types"][tn],B["partition_types"][tn]
  bb={c["inst"]:c for c in tB["hard_cores"]}
  moved=[c for c in tN["hard_cores"] if (c["origin_um"],c["outline_um"])!=(bb[c["inst"]]["origin_um"],bb[c["inst"]]["outline_um"])]
  bx=lambda c:(c["origin_um"][0]-4.32,c["origin_um"][1]-4.32,c["origin_um"][0]+c["outline_um"][0]+4.32,c["origin_um"][1]+c["outline_um"][1]+4.32)
  bo=lambda c:(c["origin_um"][0]+.01,c["origin_um"][1]+.01,c["origin_um"][0]+c["outline_um"][0]-.01,c["origin_um"][1]+c["outline_um"][1]-.01)
  pairs=[(bx(c),bo(bb[c["inst"]])) for c in moved]
  ins=lambda q,r:r[0]<q[0]<r[2] and r[1]<q[1]<r[3]
  names=set(c["inst"] for c in moved)
  assert len(tN["internal_stations"])==len(tR["internal_stations"])
  take=0; cyc=[]
  for i,(sn,sr) in enumerate(zip(tN["internal_stations"],tR["internal_stations"])):
    hit=any(ins(q,nb) and not ins(q,ob) for q in sn.get("regs_um",[]) for nb,ob in pairs)
    ends=any(n in sn.get("conn","") for n in names)
    if (hit or ends) and sn!=sr:
      tN["internal_stations"][i]=sr; take+=1
      if len(sr.get("regs_um",[]))!=len(sn.get("regs_um",[])): cyc.append((sn["conn"],len(sn.get("regs_um",[])),len(sr.get("regs_um",[]))))
  print(tn,"moved",sorted(names),"chains taken from station_resite",take,"count changes",cyc)
json.dump(N,open(sys.argv[4],"w"))
