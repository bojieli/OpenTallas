import odb,json
from pathlib import Path
D=odb.dbDatabase.create()
p=Path("routes/gate/work/orfs/results/asap7/opentallas_qfd_c_b16_reg1_asap7_ref_gate/base/3_place.odb")
odb.read_db(D,str(p)); b=D.getChip().getBlock()
ports=["lrst_dn1_rly3_w","lrst_dn1_rly6_r","bc","la_i[0]"]
r={"odb":str(p),"size":p.stat().st_size,"ports":[]}
for name in ports:
 bt=b.findBTerm(name);row={"port":name,"exists":bt is not None}
 if bt:
  n=bt.getNet(); row["net"]=n.getName() if n else None
  row["by_name_net_exists"]=b.findNet(name) is not None
  row["connections"]=[]
  for it in n.getITerms() if n else []:
   inst=it.getInst();m=inst.getMaster()
   row["connections"].append({"instance":inst.getName(),"master":m.getName(),"pin":it.getMTerm().getName(),"dir":str(it.getMTerm().getIoType()),"master_clock_pins":[mt.getName() for mt in m.getMTerms() if str(mt.getSigType())=="CLOCK"],"candidate_clock_names":[mt.getName() for mt in m.getMTerms() if mt.getName() in ["ck","CLK","clk"]]})
 
  q=[(n,0,[])];seen=set();ends=[];bufs=[]
  while q:
   net,depth,path=q.pop(0)
   if net.getId() in seen:continue
   seen.add(net.getId())
   for it in net.getITerms():
    if str(it.getMTerm().getIoType())!="INPUT":continue
    inst=it.getInst();master=inst.getMaster();rec={"instance":inst.getName(),"master":master.getName(),"pin":it.getMTerm().getName(),"depth":depth}
    if master.getName().startswith(("BUF","HB","INV")):
     bufs.append(rec)
     for op in inst.getITerms():
      if str(op.getMTerm().getIoType())=="OUTPUT" and op.getNet():q.append((op.getNet(),depth+1,path+[master.getName()]))
    else:
     rec["candidate_clock_names"]=[mt.getName() for mt in master.getMTerms() if mt.getName() in ["ck","CLK","clk"]];rec["transparent_path"]=path;ends.append(rec)
  row["transparent_buffers"]=bufs;row["terminal_inputs"]=ends
 r["ports"].append(row)
print(json.dumps(r,indent=2))
