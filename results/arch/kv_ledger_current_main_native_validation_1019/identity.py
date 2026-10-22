from pathlib import Path
import hashlib,json,sys
lane=Path.cwd(); actual=Path('/srv/opentallas-scratch/claude/qwen-kvsys/wt-kvs14r-cda9d9f9d-gen8v4mub'); live=actual.with_name('kvs14r-cda9d9f9d-gen8v4mub')
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
rels=['rtl/qwen_sys/split_20261014/qkd_astk_phys.sv','rtl/lib/face_land/qkd_astk_rly_296_fl.sv','rtl/lib/ot_rst_relay.sv','rtl/lib/ot_pin_land.sv','rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_ctl_tb.sv','rtl/hdc/nearhbm/ot_qwen_tp8_pv_wide_pair.sv','physical/ref_tile/qkd_astk_rly_296/spec.json']
for name in ['qkd_astk_rly_296','qkd_astk_rly_296_fl']:
 rels += [str(p.relative_to(actual)) for p in (actual/'physical/ref_tile/qkd_astk_rly_296/views'/name).rglob('*') if p.is_file()]
frozen={r:sha(actual/r) for r in sorted(set(rels))}
for sub in ['tools/qwen_kv_die','tools/qwen_rom_fulldie.py']:
 p=actual/sub
 for q in ([p] if p.is_file() else p.rglob('*')):
  if q.is_file() and q.suffix in ('.py','.json','.sh','.svh'): frozen[str(q.relative_to(actual))]=sha(q)
liverels=['continuation.json','dependency_manifest.json','source_verified.json','prep_tail_sha256.txt','v3_manifest.json','port_bind_launch.json','expand.json','case_kv/die.v','case_kv/die.v.preexp','case_kv/die.v.params.json','case_kv/boot_ages.json']
record=dict(actual_root=str(actual),source_generated='5f2ce19bc',driver='cda9d9f9d',frozen_inputs=frozen,live_run=str(live),live_inputs={r:sha(live/r) if (live/r).is_file() else None for r in liverels})
(lane/sys.argv[1]).write_text(json.dumps(record,indent=2)+'\n')
