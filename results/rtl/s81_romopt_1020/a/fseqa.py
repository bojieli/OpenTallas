"""S81-ROMOPT-A (10-20): production-shape go-sequence bench of one op's COMPILED phases with the release compiler
defaults (xs_flags; O1 = OT_XS_QPAIRS=10 in the env) on the release frame exe of the frame's master (TOKSIM-S81C/FSEQ
v_* builds, Verilator 5.050).  Copy of results/rtl/s81_rate3_1020/fseq3.py plus mutants:
  positive  P (the compiler floor)                                     must PASS (bit-exact values + cycle-exact RET)
  P-1 / NEG calendar period below the floor (re-simulated)              must FAIL (ffn.down: P-1 has margin -> 125, 120)
  swap      two q elements' ROM images exchanged in the sequence dir (re-simulated at P)   must FAIL
  shift     the expected RET calendar +1 edge (checked against the positive run log)       must FAIL
usage (cwd = root): python3 fseqa.py OUT FRAME EXE_BUILD OP P [NEG ...]
"""
import hashlib, json, os, re, shutil, subprocess, sys
from pathlib import Path
from types import SimpleNamespace
R = Path.cwd(); sys.path.insert(0, str(R / 'tools/s81_dv/layer_prog'))
os.environ['PYTHONPATH'] = str(R / 'tools/s81_dv/layer_prog') + ':' + os.environ.get('PYTHONPATH', '')
import xs_place as X
import xs_topo as TP
import xs_flags as XO
import dv_layer_compile as C
O, FR, BLD, op, period = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5])
NEG = [int(x) for x in sys.argv[6:]] or [period - 1]
FX = '/srv/opentallas-scratch/claude/s81-calpipe/fixtures/L0'; DR = '/srv/opentallas-scratch/claude/toksim-s81b-fwoa/dieref'
Q = Path('/srv/opentallas-scratch/codex/s81-rom12-1020/fseq_src'); B = Path('/srv/opentallas-scratch/claude/toksim-s81c-fseq') / BLD
exe = B / 'obj/Vtb_toksim_fgu_seq'
die = C.Die(C.die_tree(None, DR))
name = op.split('.')[-1]; V = O / FR / name; V.mkdir(parents=True, exist_ok=True)
env = XO.describe()
rec, field = X.compile_frame(die, FR, FX, [op])
assert all(not p['faults'] for p in rec['phases'])
report = dict(rec, env=env, topo=TP.describe(), phases=[{k: v for k, v in p.items() if k != 'plan'} for p in rec['phases']])
(V / 'frame.json').write_text(json.dumps(report, indent=1, default=str) + '\n')
first = None
for ph in rec['phases']:
    if ph['op'] != op:
        continue
    first = first or ph
    out = V / f'p{ph["phase"]}'
    if not (out / 'meta.json').exists():
        X.gen_one(SimpleNamespace(fixtures=FX, frame=FR, mutant=None, bf_measure=False), rec, field, ph, out)
PV = op == 'ffn.down'
cmd = [sys.executable, str(Q / 'toksim_fseq_seqops.py'), '--vec', str(V), '--name', name, '--ops', op] + (['--phase-vm'] if PV else [])
r = subprocess.run(cmd, capture_output=True, text=True); (V / 'sequence_gen.log').write_text(r.stdout + r.stderr)
assert r.returncode == 0, r.stdout + r.stderr
_, sd, nph, K, rows, ph0 = r.stdout.strip().split(); sd = Path(sd); nph = int(nph)


def sim(P, sdir, tag):
    log = V / f'run_{tag}.log'
    args = [str(exe), f'+OT_ROM_DIR={sdir}', f'+T={nph * P + 1500}', f'+K={K}', f'+OPS={rows}', f'+PH={ph0}', f'+NPH={nph}',
            f'+PER={P}', '+RETIRE=1'] + (['+PHASE_VM=1'] if PV else [])
    with log.open('w') as f:
        rr = subprocess.run(args, stdout=f, stderr=subprocess.STDOUT)
    return rr.returncode, log


def check(P, vec, log, tag):
    outj = V / f'check_{tag}.json'
    chk = subprocess.run([sys.executable, str(Q / 'toksim_fgu_check.py'), 'seq', '--seq', str(sd), '--vec', str(vec), '--log', str(log),
                          '--out', str(outj), '--per', str(P), '--ref-go', '63'], capture_output=True, text=True)
    (V / f'check_{tag}.log').write_text(chk.stdout + chk.stderr)
    cj = json.loads(outj.read_text()) if outj.exists() else None
    return chk, cj


results = []


def record(kind, P, rc, chk, cj, expect_pass):
    ok = rc == 0 and chk.returncode == 0 and bool(cj and cj.get('pass'))
    results.append(dict(kind=kind, op=op, frame=FR, period=P, expect_pass=expect_pass, run_rc=rc, check_rc=chk.returncode,
                        PASS=ok, as_expected=ok == expect_pass, span=(cj or {}).get('go0_to_last_ret'),
                        checker_tail=chk.stdout.strip()[-300:]))
    print('FSEQA', FR, op, kind, 'P', P, 'nph', nph, 'PASS' if ok else 'FAIL', 'as_expected' if ok == expect_pass else 'UNEXPECTED',
          chk.stdout.strip()[-200:], flush=True)


rc, log = sim(period, sd, f'P{period}')
chk, cj = check(period, V, log, f'P{period}'); record('golden', period, rc, chk, cj, True)
for P in NEG:
    rc2, log2 = sim(P, sd, f'P{P}')
    chk2, cj2 = check(P, V, log2, f'P{P}'); record('period_below_floor', P, rc2, chk2, cj2, False)
# shift: expected RET +1 edge on every phase (no re-simulation: the golden run log must no longer match)
VS = V.parent / (name + '_shiftvec'); shutil.rmtree(VS, ignore_errors=True); VS.mkdir()
for p in V.glob('p*'):
    if p.is_dir() and (p / 'meta.json').exists():
        (VS / p.name).mkdir()
        m = json.loads((p / 'meta.json').read_text())
        m['plan']['ret'] = [[e + 1] + list(rest) for e, *rest in m['plan']['ret']]
        (VS / p.name / 'meta.json').write_text(json.dumps(m) + '\n')
        for f in p.iterdir():
            if f.name != 'meta.json' and f.is_file():
                os.link(f, VS / p.name / f.name)
chk3, cj3 = check(period, VS, log, 'shift'); record('shift', period, rc, chk3, cj3, False)
# swap: two q elements with different rows in the first phase exchange their ROM images
pl = first['placement']
r_of = {d['pair']: d['rows'] for d in pl}
e1, e2 = next((u, v) for u in rec['pairs'] for v in rec['pairs'] if u < v and u in r_of and v in r_of and r_of[u] != r_of[v])
SW = sd.parent / (sd.name + '_swap'); shutil.rmtree(SW, ignore_errors=True); shutil.copytree(sd, SW)
nsw = 0
for f in sorted(sd.glob('f_e*')):
    m = re.match(rf'^f_e({e1}|{e2})(b?_\d.*)$', f.name)
    if m:
        dst = f'f_e{e2 if int(m.group(1)) == e1 else e1}{m.group(2)}'
        shutil.copy(f, SW / dst); nsw += 1
assert nsw >= 2, nsw
rc4, log4 = sim(period, SW, 'swap')
chk4, cj4 = check(period, V, log4, 'swap'); record('swap', period, rc4, chk4, cj4, False)
verdict = all(x['as_expected'] for x in results)
srcs = (B / 'sources.sha256').read_text() if (B / 'sources.sha256').exists() else None
(V / 'summary.json').write_text(json.dumps(dict(VERDICT='PASS' if verdict else 'FAIL', env=env, topo=TP.describe(), nph=nph,
                                                frame_rows=[p['rows'] for p in rec['phases'] if p['op'] == op],
                                                swap_pairs=[e1, e2], swap_files=nsw, results=results,
                                                exe=str(exe), binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                                                rtl_sources_sha256=srcs,
                                                verilator=(B / 'verilator.version').read_text().strip()), indent=1) + '\n')
print('FSEQA_VERDICT', FR, op, 'PASS' if verdict else 'FAIL', 'span', results[0]['span'], flush=True)
