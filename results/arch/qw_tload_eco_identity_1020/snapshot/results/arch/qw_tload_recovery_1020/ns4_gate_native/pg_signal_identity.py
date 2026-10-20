import odb,json,hashlib
from pathlib import Path
root=Path('/audit');src=root/'routes/gate/work/orfs/results/asap7/opentallas_qfd_dv_slice_tload_asap7_ref_gate/base/5_1_grt.odb';dst=root/'5_1_grt_gc_copy.odb'
def snapshot(p):
 d=odb.dbDatabase.create();odb.read_db(d,str(p));b=d.getChip().getBlock();cells={};pg=0
 for i in b.getInsts():
  pins={}
  for it in i.getITerms():
   if str(it.getMTerm().getSigType())in ['POWER','GROUND']:
    pg+=it.getNet() is None;continue
   n=it.getNet();pins[it.getMTerm().getName()]=n.getName() if n else None
  cells[i.getName()]={'master':i.getMaster().getName(),'signal_pins':pins,'location':list(i.getLocation()),'orientation':str(i.getOrient())}
 terms={t.getName():{'io':str(t.getIoType()),'type':str(t.getSigType()),'net':t.getNet().getName()if t.getNet()else None}for t in b.getBTerms()}
 return cells,terms,pg
before=hashlib.sha256(src.read_bytes()).hexdigest();a,at,ap=snapshot(src);b,bt,bp=snapshot(dst)
r={'original_odb_sha256':before,'copy_odb_sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'same_original_SHA_after':before==hashlib.sha256(src.read_bytes()).hexdigest(),'original_cells':len(a),'copy_cells':len(b),'all_cell_masters_signal_clock_reset_pins_placement_identical':a==b,'all_top_BTerms_identical':at==bt,'raw_unbound_PG':ap,'copy_unbound_PG':bp,'operation':'Ordinaryglobal_connect ondisposableinmemorycopy; originalODB preserved. No protected/fixed repairor signal change. No finalPG conductor/via/short continuity proof.'};r['PASS']=r['same_original_SHA_after']and a==b and at==bt and bp==0;(root/'pg_signal_identity.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));assert r['PASS']
