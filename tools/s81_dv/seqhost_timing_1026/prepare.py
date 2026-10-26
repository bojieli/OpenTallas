#!/usr/bin/env python3
"""Materialize exact seqhost implementation closure from the current bind manifest.
Memory interface-only stubs are replaced only by their sibling functional view.
"""
import hashlib,json,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import bind_elab as E
out=Path(sys.argv[1])
if out.exists() and any(out.iterdir()):raise ValueError('preserve existing staged sources; select a fresh output')
out.mkdir(parents=True,exist_ok=True)
ab=json.loads((ROOT/'physical/die_plan/s81/bind/asbuilt_b178_coll.json').read_text())
files=[];impl={}
for name in ab['files']:
 p=ROOT/name
 if name.endswith('_bb.v') and name.startswith('physical/'):
  q=p.with_name(p.name.replace('_bb.v','.v'))
  if q.exists():impl[str(p)]=str(q)
 files.append(str(p))
# As-built elaboration blackboxes the whole seqhost. Its real implementation
# explicitly supplies this selected mux child, not needed by the header-only bind.
children=['rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bk_sel.sv', 'rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bkcol_leaves.sv', 'rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin.sv', 'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v', 'physical/asap7_memory_macros_v2/ot_sram_1r1w_1024x256_m2_r2c2/ot_sram_1r1w_1024x256_m2_r2c2.v']
files += [str(ROOT/p) for p in children]
files += list(impl.values())
prefer=[impl.get(str(ROOT/p),str(ROOT/p)) for p in ab['prefer']]
prefer+=list(impl.values())
idx=E.module_index([],files,ROOT)
top=sys.argv[2] if len(sys.argv)>2 else 'dsdv_hostb_seqhost_mux'
closure,missing=E.closure([top],idx,prefer)
if missing:raise ValueError('missing exact implementation sources '+str(missing))
record={};relative=[]
for name in closure:
 p=Path(name);rel=p.relative_to(ROOT);dest=out/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
 relative.append(str(rel));record[str(rel)]=hashlib.sha256(p.read_bytes()).hexdigest()
bench='tools/s81_dv/seqhost_timing_1026/tb_bk.sv' if top=='dsdv_bk_sel_vmtx' else 'tools/s81_dv/seqhost_timing_1026/tb.sv'
for name in [bench]:
 p=ROOT/name;dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
record['physical/die_plan/s81/bind/asbuilt_b178_coll.json']=hashlib.sha256((ROOT/'physical/die_plan/s81/bind/asbuilt_b178_coll.json').read_bytes()).hexdigest()
(out/'files.f').write_text('\n'.join(relative+[bench])+'\n')
(out/'source_record.json').write_text(json.dumps(dict(schema='opentallas.s81.seqhost_local_sources.v1',source_sha256=record,defines=ab['defines'],params=(dict(TX_SRAM=1) if top=='dsdv_bk_sel_vmtx' else dict(HOSTB_ENABLE=0,STATIC_KS6=0)),implementation_children=children,memory_implementations={str(Path(k).relative_to(ROOT)):str(Path(v).relative_to(ROOT)) for k,v in impl.items() if v in closure}),indent=1)+'\n')
(out/'defines.f').write_text('\n'.join('+define+'+d for d in ab['defines'])+'\n')
print('closure',len(closure), 'files',sum(Path(p).stat().st_size for p in closure))
