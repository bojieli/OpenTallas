import odb
D=odb.dbDatabase.create();D=odb.read_db(D,"/out/jp_grt.odb");b=D.getChip().getBlock();u=b.getDbUnitsPerMicron()
f=open("/out/clk_cells.tsv","w")
for i in b.getInsts():
  n=i.getName();m=i.getMaster()
  bb=i.getBBox();x=(bb.xMin()+bb.xMax())/2/u;y=(bb.yMin()+bb.yMax())/2/u
  if m.isBlock(): k="macro"
  elif n.startswith("ot_ms_jp_"): k="pad_new"
  elif n.startswith("ot_ms_") and n.endswith("_tap"): k="tap"
  elif n.startswith("ot_ms_"): k="trunk"
  elif "DFF" in m.getName(): k="ff"
  else: continue
  f.write(f"{k}\t{n}\t{x:.2f}\t{y:.2f}\t{(bb.xMax()-bb.xMin())/u:.2f}\t{(bb.yMax()-bb.yMin())/u:.2f}\n")
