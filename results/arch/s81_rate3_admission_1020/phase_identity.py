"""Compile a real eighth frame and compare production shared calendar phase IDs; no timing/RTL claim."""
import hashlib,json,sys
from pathlib import Path
R=Path.cwd();sys.path.insert(0,str(R/'tools/s81_dv/layer_prog'))
import xs_place as X
import dv_layer_compile as C
D=C.Die(C.die_tree(None,'/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'))
O=Path(sys.argv[1]);O.mkdir(parents=True,exist_ok=False)
rec,field=X.compile_frame(D,'u_f_0R03','/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0',['attn.wq_b'],only=set())
calfile=R/'results/rtl/s81_rate3_1020/compile/prop2_s0/L0/field_calendar.json'
cal=json.loads(calfile.read_text());expected=[p['phase'] for p in cal['ops']['attn.wq_b']['phases']]
actual=[p['phase'] for p in rec['phases'] if p['op']=='attn.wq_b']
r=dict(scope='ACTUAL_SOURCE_PHASE_IDENTITY_AUDIT_ONLY; plans not legalised',source='012a3a074',
 frame=rec['frame'],master=rec['master'],physical_slice=rec['slice'],a_proj_present=any(p['op']=='attn.a_proj' for p in rec['phases']),
 actual_frame_field_phase_ids=actual,shared_first_frame_calendar_phase_ids=expected,
 phase_identity_PASS=actual==expected,full_stage_qualified=False,
 actual_cfg_count=len(field.cfg),frame_rows=[p['rows'] for p in rec['phases']],
 calendar_sha256=hashlib.sha256(calfile.read_bytes()).hexdigest(),
 xp_sha256=hashlib.sha256(Path(X.__file__).read_bytes()).hexdigest(),
 mechanism='empty a_proj skips I.add_phase; subsequent cfg bank indices differ from shared calendar. This is separate from missing phase0 rows on six-frame slices.')
assert actual==list(range(11)) and expected==list(range(1,12)),r
(O/'phase_identity.json').write_text(json.dumps(r,indent=1)+'\n');print('PHASE_IDENTITY',json.dumps(r),flush=True)
