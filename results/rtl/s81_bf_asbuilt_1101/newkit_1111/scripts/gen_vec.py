"""S81-FRAME-FIX-1 BF as-built measurement 11-11: compile ONE as-built die frame's full L0 field on the bound die top
(frame master col_h*_l4_lp_asb_*), keep the snapshot, and emit the BF_LEGACY measurement vector of its first full
attn.wo_a phase (xs_place.gen_bf --bf-measure).  Usage: gen_vec.py FRAME OUTDIR"""
from pathlib import Path
import hashlib, json, os, sys
from types import SimpleNamespace
D = Path('/srv/opentallas-scratch2/claude/s81-bfasb-1111')
W, R = D / 'code', D / 'root'
V = Path('/srv/opentallas-scratch2/claude/tok-verify-1')
FIX = V / 'fixtures/L0'
frame, out = sys.argv[1], Path(sys.argv[2])
# slice-source selection = the code checkout's default, as TOK-VERIFY-1 b2/b3 compile_layers (frame sources = own root)
os.environ.update(OT_S81_FRAME_SOURCE_ROOT=str(R), OT_S81_FRAME_ASBUILT_MANIFEST='physical/die_plan/s81/bind/frame_asbuilt.json',
                  OT_S81_FRAME_PLAN=str(R / 'physical/die_plan/s81/plan_h2_2249.json'),
                  OT_XS_ASB_SCHEDULE_DIR=str(D / 'sched'), OT_S81_BF_COL_FORM='base',
                  OT_S81_SELECTED_DEFINES=(V / 'defines.txt').read_text().strip())
sys.path[:0] = [str(W / 'tools'), str(W / 'tools/s81_dv'), str(W / 'tools/s81_dv/layer_prog')]
import dv_layer_compile as C
from layer_prog import xs_place as X
from layer_prog import bound_data as BD
TS5 = Path('/srv/opentallas-scratch2/claude/type-safe-5/cand')
B = BD.load_bind(TS5 / 'bind_s81', str(TS5 / 'asbuilt_bs.json'), C.ROOT)   # read only: the bind's die top + slice RTL
nl = R / 'physical/die_plan/s81/bind/inputs/die_b178.v'
print('NETLIST', B['netlist_path'], B['netlist_sha256'][:12], 'root die_b178', hashlib.sha256(nl.read_bytes()).hexdigest()[:12], flush=True)
die = C.Die(W, netlist=nl, netlist_sha=hashlib.sha256(nl.read_bytes()).hexdigest(), bound_rtl=Path(B['bound']) / 'rtl')
print('MASTER', frame, die.inst[frame]['master'], flush=True)
out.mkdir(parents=True, exist_ok=False)
rec, field = X.compile_frame(die, frame, FIX, X.XS_OPS['L0'] + X.BF_OPS['L0'])
(out / 'field.json').write_text(json.dumps(rec, indent=1) + '\n')
bf = [dict(phase=p['phase'], op=p['op'], rows=p['rows'], seg=p.get('seg'), nseg=p.get('nseg'), shape=p.get('shape'),
           calendar=p.get('calendar'), pairs=p.get('bf_pairs')) for p in rec['phases'] if p.get('fmt') == 'bf16']
(out / 'bf_phases.json').write_text(json.dumps(bf, indent=1) + '\n')
print('BF_PHASES', len(bf), json.dumps(bf[:3]), flush=True)
full = next(p for p in rec['phases'] if p.get('fmt') == 'bf16' and p['op'] == 'attn.wo_a' and p['rows'] == 6 and p['seg'] == 0)
a = SimpleNamespace(mutant=None, bf_measure=True, frame=frame, fixtures=FIX)
X.gen_bf(a, rec, field, full, out / 'vec', X.Fix(FIX))
print('GEN_DONE', frame, full['phase'], flush=True)
