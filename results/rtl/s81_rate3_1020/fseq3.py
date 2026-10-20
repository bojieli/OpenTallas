"""S81-RATE3 (10-20): production-shape go-sequence bench of one op's COMPILED phases (xs_place.compile_frame with the
release compiler options in the environment: OT_XS_QPAIRS=12 OT_XS_GU_MERGE=1 OT_XS_TOPO=1 [OT_XS_PROP=1]) on the
release frame exe of the frame's master (TOKSIM-S81C/FSEQ v_* builds, Verilator 5.050), at the floor P (positive) and
P-1 (negative, must FAIL).  Copy of codex fseq12.py (results/rtl/s81_rom12_codex_1020) with frame / exe / op args.
usage (cwd = root): python3 fseq3.py OUT FRAME EXE_BUILD OP P
"""
import hashlib, json, os, pickle, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
R = Path.cwd(); sys.path.insert(0, str(R / 'tools/s81_dv/layer_prog'))
os.environ['PYTHONPATH'] = str(R / 'tools/s81_dv/layer_prog') + ':' + os.environ.get('PYTHONPATH', '')
import xs_place as X
import xs_topo as TP
import dv_layer_compile as C
O, FR, BLD, op, period = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
FX = '/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0'; DR = '/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
Q = Path('/srv/opentallas-scratch/codex/s81-rom12-1020/fseq_src'); exe = Path('/srv/opentallas-scratch/claude/toksim-s81c-fseq') / BLD / 'obj/Vtb_toksim_fgu_seq'
die = C.Die(C.die_tree(None, DR))
name = op.split('.')[-1]; V = O / FR / name; V.mkdir(parents=True, exist_ok=True)
env = {k: os.environ.get(k) for k in ('OT_XS_QPAIRS', 'OT_XS_GU_MERGE', 'OT_XS_TOPO', 'OT_XS_PROP', 'OT_XS_CAL_SEGMENT')}
rec, field = X.compile_frame(die, FR, FX, [op])
assert all(not p['faults'] for p in rec['phases'])
report = dict(rec, env=env, topo=TP.describe(), phases=[{k: v for k, v in p.items() if k != 'plan'} for p in rec['phases']])
(V / 'frame.json').write_text(json.dumps(report, indent=1, default=str) + '\n')
nph_op = 0
for ph in rec['phases']:
    if ph['op'] != op:
        continue
    nph_op += 1
    out = V / f'p{ph["phase"]}'
    if not (out / 'meta.json').exists():
        X.gen_one(SimpleNamespace(fixtures=FX, frame=FR, mutant=None, bf_measure=False), rec, field, ph, out)
PV = op == 'ffn.down'     # each expert's down reads its own x (route_w): the tb reloads the phase's VM at its go (+PHASE_VM)
cmd = [sys.executable, str(Q / 'toksim_fseq_seqops.py'), '--vec', str(V), '--name', name, '--ops', op] + (['--phase-vm'] if PV else [])
r = subprocess.run(cmd, capture_output=True, text=True); (V / 'sequence_gen.log').write_text(r.stdout + r.stderr)
assert r.returncode == 0, r.stdout + r.stderr
_, sd, nph, K, rows, ph0 = r.stdout.strip().split(); sd = Path(sd); nph = int(nph)
results = []
for P in [period, period - 1]:
    log = V / f'run_P{P}.log'
    args = [str(exe), f'+OT_ROM_DIR={sd}', f'+T={nph * P + 1500}', f'+K={K}', f'+OPS={rows}', f'+PH={ph0}', f'+NPH={nph}', f'+PER={P}', '+RETIRE=1'] + (['+PHASE_VM=1'] if PV else [])
    with log.open('w') as f:
        rr = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT)
    outj = V / f'check_P{P}.json'
    chk = subprocess.run([sys.executable, str(Q / 'toksim_fgu_check.py'), 'seq', '--seq', str(sd), '--vec', str(V), '--log', str(log),
                          '--out', str(outj), '--per', str(P), '--ref-go', '63'], capture_output=True, text=True)
    (V / f'check_P{P}.log').write_text(chk.stdout + chk.stderr)
    cj = json.loads(outj.read_text()) if outj.exists() else None
    ok = rr.returncode == 0 and chk.returncode == 0 and bool(cj and cj.get('pass'))
    results.append(dict(op=op, frame=FR, period=P, positive=P == period, run_rc=rr.returncode, check_rc=chk.returncode,
                        PASS=ok, span=(cj or {}).get('go0_to_last_ret'), checker=cj))
    print('FSEQ3', FR, op, 'P', P, 'nph', nph, 'PASS' if ok else 'FAIL', chk.stdout.strip()[-300:], flush=True)
verdict = results[0]['PASS'] and not results[1]['PASS']
(V / 'summary.json').write_text(json.dumps(dict(VERDICT='PASS' if verdict else 'FAIL', env=env, topo=TP.describe(), nph=nph,
                                                frame_rows=[p['rows'] for p in rec['phases'] if p['op'] == op], results=results,
                                                binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                                                verilator=(exe.parent.parent / 'verilator.version').read_text().strip()), indent=1) + '\n')
print('FSEQ3_VERDICT', FR, op, 'PASS' if verdict else 'FAIL', flush=True)
