import odb,hashlib,json,pathlib
root=pathlib.Path('/work');base=root/'run/results/asap7/kq_qfd_dv_s8x_vmr_f4a_m0/base';op=root/'eco_out/6_final.odb';np=root/'eco_out/6_final_logic.v'
masters=['TAPCELL_ASAP7_75t_R','FILLER_ASAP7_75t_R','FILLERxp5_ASAP7_75t_R']
db=odb.dbDatabase.create();odb.read_db(db,str(op));b=db.getChip().getBlock();bad=[];counts={m:0 for m in masters}
for inst in b.getInsts():
 m=inst.getMaster().getName()
 if m not in counts:continue
 counts[m]+=1
 for it in inst.getITerms():
  if it.getMTerm().getSigType() not in ('POWER','GROUND'):bad.append([inst.getName(),it.getMTerm().getName(),it.getMTerm().getSigType()])
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
 return h.hexdigest()
r={'schema':'opentallas.logical_export.v1','odb_sha256':sha(op),'netlist_sha256':sha(np),'command':'write_verilog -remove_cells {'+' '.join(masters)+'} /work/eco_out/6_final_logic.v','excluded_masters':masters,'excluded_signal_iterms':len(bad),'excluded_instances':counts,'signal_exceptions':bad[:10]}
(base/'6_final_logic.v.export.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));assert not bad
