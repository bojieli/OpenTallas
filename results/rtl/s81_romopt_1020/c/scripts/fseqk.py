"""S81-ROMOPT-C (10-20): production-shape go-sequence bench of one op's COMPILED k-slot phases (xs_place.compile_frame with
the release compiler options + OT_XS_KSLOT=k in the environment) on the RELEASE frame exe of the frame's master
(TOKSIM-S81C/FSEQ v_* builds = release 19bf4121e frame RTL, Verilator 5.050), at every period of PERS (sweep: the floor
P_k = the lowest PASS with every lower period FAIL), plus single-phase swap / shift mutants of MUT phases (must FAIL).
Copy of results/rtl/s81_rate3_1020/fseq3.py with a period list and the mutants.
usage (cwd = root): python3 fseqk.py OUT FRAME EXE_BUILD OP "PERS" "MUT_PHASES" """
import hashlib, json, os, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
R = Path.cwd(); sys.path.insert(0, str(R / 'tools/s81_dv/layer_prog'))
os.environ['PYTHONPATH'] = str(R / 'tools/s81_dv/layer_prog') + ':' + os.environ.get('PYTHONPATH', '')
import xs_place as X
import xs_topo as TP
import dv_layer_compile as C
O, FR, BLD, op = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
pers = [int(x) for x in sys.argv[5].split()]
muts = [int(x) for x in sys.argv[6].split()] if len(sys.argv) > 6 else []
FX = '/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0'; DR = '/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
Q = Path('/srv/opentallas-scratch/codex/s81-rom12-1020/fseq_src'); E = Path('/srv/opentallas-scratch/claude/toksim-s81c-fseq') / BLD
exe = E / 'obj/Vtb_toksim_fgu_seq'
die = C.Die(C.die_tree(None, DR))
name = op.split('.')[-1]; V = O / FR / name; V.mkdir(parents=True, exist_ok=True)
env = {k: os.environ.get(k) for k in ('OT_XS_QPAIRS', 'OT_XS_GU_MERGE', 'OT_XS_TOPO', 'OT_XS_PROP', 'OT_XS_CAL_SEGMENT', 'OT_XS_KSLOT', 'OT_XS_KSLOT_OPS')}
rec, field = X.compile_frame(die, FR, FX, [op])
opph = [p for p in rec['phases'] if p['op'] == op]
faults = sum(p['faults'] for p in opph)
cals = sorted({p['calendar'] for p in opph})
report = dict(rec, env=env, topo=TP.describe(), phases=[{k: v for k, v in p.items() if k != 'plan'} for p in rec['phases']])
(V / 'frame.json').write_text(json.dumps(report, indent=1, default=str) + '\n')
print('FSEQK_COMPILE', FR, op, 'phases', len(opph), 'rows', [p['rows'] for p in opph], 'faults', faults, 'calendar', cals,
      'ret_words', [p['ret_words'] for p in opph], flush=True)
assert faults == 0 and cals == ['measured_class'], ('legaliser faults or unmeasured calendar', faults, cals)
for ph in opph:
    out = V / f'p{ph["phase"]}'
    if not (out / 'meta.json').exists():
        X.gen_one(SimpleNamespace(fixtures=FX, frame=FR, mutant=None, bf_measure=False), rec, field, ph, out)
PV = op == 'ffn.down'     # each expert's down reads its own x (route_w): the tb reloads the phase's VM at its go (+PHASE_VM)
cmd = [sys.executable, str(Q / 'toksim_fseq_seqops.py'), '--vec', str(V), '--name', name, '--ops', op] + (['--phase-vm'] if PV else [])
r = subprocess.run(cmd, capture_output=True, text=True); (V / 'sequence_gen.log').write_text(r.stdout + r.stderr)
assert r.returncode == 0, r.stdout + r.stderr
_, sd, nph, K, rows, ph0 = r.stdout.strip().split(); sd = Path(sd); nph = int(nph)
results = []
for P in pers:
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
    results.append(dict(op=op, frame=FR, period=P, run_rc=rr.returncode, check_rc=chk.returncode, PASS=ok,
                        span=(cj or {}).get('go0_to_last_ret'), words=(cj or {}).get('words'), fixture_rows=(cj or {}).get('fixture_rows'),
                        errors=(cj or {}).get('errors', [])[:6]))
    print('FSEQK', FR, op, 'P', P, 'nph', nph, 'PASS' if ok else 'FAIL', chk.stdout.strip()[-260:], flush=True)
mres = []
for k_ in muts:
    ph = next(p for p in opph if p['phase'] == k_)
    for mu in ('none', 'swap', 'shift'):
        out = V / f'mut_{mu}_p{k_}'
        X.gen_one(SimpleNamespace(fixtures=FX, frame=FR, mutant=None if mu == 'none' else mu, bf_measure=False), rec, field, ph, out)
        args = (out / 'ARGS').read_text().split()
        log = out / 'run.log'
        with log.open('w') as f:
            rr = subprocess.run([str(exe)] + args + ['+RETIRE=0'], stdout=f, stderr=subprocess.STDOUT)
        rc = X.cmd_check(SimpleNamespace(dir=str(out), log=str(log), fixtures=FX))
        chk = json.loads((out / 'check.json').read_text())
        mres.append(dict(phase=k_, mutant=mu, PASS=chk['pass'], errors=len(chk['errors']), first=chk['errors'][:3]))
        print('FSEQK_MUT', FR, op, 'phase', k_, mu, 'PASS' if chk['pass'] else 'FAIL', len(chk['errors']), chk['errors'][:2], flush=True)
pas = [x['period'] for x in results if x['PASS']]
floor = min(pas) if pas else None
mono = floor is not None and all(x['PASS'] == (x['period'] >= floor) for x in results)
mut_ok = all(m['PASS'] == (m['mutant'] == 'none') for m in mres)
verdict = floor is not None and mono and mut_ok
srcs = (E / 'sources.sha256').read_text() if (E / 'sources.sha256').exists() else None
(V / 'summary.json').write_text(json.dumps(dict(VERDICT='PASS' if verdict else 'FAIL', env=env, topo=TP.describe(), nph=nph,
    frame_rows=[p['rows'] for p in opph], ret_words=[p['ret_words'] for p in opph], floor=floor, monotone=mono,
    span_at_floor=next((x['span'] for x in results if x['period'] == floor), None), results=results, mutants=mres,
    binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(), sources_sha256=srcs,
    verilator=(E / 'verilator.version').read_text().strip()), indent=1) + '\n')
print('FSEQK_VERDICT', FR, op, 'PASS' if verdict else 'FAIL', 'floor', floor, 'monotone', mono, 'mutants_ok', mut_ok, flush=True)
