import odb,json
D=odb.dbDatabase.create();odb.read_db(D,'routes/gate/work/orfs/results/asap7/opentallas_qfd_d2d_static_ovl_sf7_asap7_ref_gate/base/5_1_grt.odb');b=D.getChip().getBlock()
for n in ['clkload34','clkload76','clkload160','clkload82','clkload161','clkload164','clkload102']:
 i=b.findInst(n);print(n,i.getMaster().getName())
 for t in i.getITerms():
  net=t.getNet();print(t.getMTerm().getName(),str(t.getMTerm().getIoType()),None if net is None else net.getName(),[] if net is None else [(x.getInst().getName(),x.getMTerm().getName()) for x in net.getITerms()][:8])
