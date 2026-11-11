#!/usr/bin/env python3
"""frame_seq_gate.py -- S81-FRAME-FIX-1 (11-11): the S81 frame sequence bench as a merge gate.

Why: dc23a738f3 (10-24) made the frame pass-through stations 2 flops deep; the field compiler kept the 1-flop calendar
and the frame bench FAULTed on every main for 17 days without any gate noticing (TOK-VERIFY-1 bisect 11-11).  This gate
compiles real ops with the CURRENT compiler for the CURRENT frame RTL and runs them cycle-exact:

  positive  attn.wq_b at its floor P127 and P128, ffn.experts_gu (dense) at its floor P145: 0 FAULT, END reached,
            strict calendar checker PASS (every frame ret word on its compiled edge with its golden value);
  negative  attn.wq_b P127 compiled with a WRONG station depth (OT_S81_STATION_DEPTH_OVERRIDE: every 2-flop station
            priced as 1 flop = the pre-fix calendar) on the same binary: must FAULT or fail the checker;
  floor     attn.wq_b at P126 (floor - 1, xs_field_calendar.FLOORS) must FAULT: the measured floor is still the floor.
  (COORD asked for wq_b P126/P125: on 2-flop stations both FAULT 11 = cfg7 load overrun, so the floor moved to 127.)

Bench = tb_toksim_fgu_seq (results/rtl/s81_rom12_codex_1020/fseq_src, source-checked 10-20) on the die's frame form
col_h10_l4_b (dsfd_cfifo_crs4 landing, LK 2, forwarded-lane gate; the compiler's master col_h10_l4 -- NOT the crs frame
col_h10, whose x ingress is 4 edges later than the l4 calendar), Verilator 5.050; vectors = xs_place.compile_frame
+ gen_one + toksim_fseq_seqops on frame u_f_0L01 of the die at HEAD.  Heavy: run through ot-run (~16 threads, 24 GB).

    ot-run --mem 24 --threads 16 --dir <tree> -- python3 -I tools/s81_dv/frame_seq_gate.py --fixtures <L0> --out <dir>

Fixtures: the L0 decode fixture set (74 MB, not committed; manifest.sha256 is checked).  Known copies:
intel1 /srv/opentallas-scratch2/claude/tok-verify-1/fixtures/L0, epyc9 /srv/opentallas-scratch2/claude/s81-frame-fix-1/fixtures/L0.
Exit 0 only on PASS; summary.json in --out."""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'results/rtl/s81_rom12_codex_1020/fseq_src'
FRAME = 'u_f_0L01'
POS = [('attn.wq_b', 127), ('attn.wq_b', 128), ('ffn.experts_gu', 145)]
NEG = [('attn.wq_b', 127)]
FLOOR_M1 = [('attn.wq_b', 126)]
WRONG_DEPTH = {m: 1 for m in ('dsfd_qbank_N', 'dsfd_qbank_S', 'dsfd_rstg', 'ot_s81_sstn_base566',
                              'ot_s81_sstn_payload536')}
PHASE_VM = ('ffn.down', 'attn.wo_a')
VERILATOR = Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'


def env():
    e = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
             PYTHONPATH=f'{ROOT}/tools/s81_dv/layer_prog:{ROOT}/tools/s81_dv')
    e.pop('OT_S81_STATION_DEPTH_OVERRIDE', None)
    return e


def build(out):
    obj = out / 'build/obj'
    exe = obj / 'Vtb_toksim_fgu_seq'
    if exe.exists():
        return exe
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [str(VERILATOR), '--binary', '--timing', '-O1', '-Wno-fatal', '-Wno-WIDTH', '-Wno-TIMESCALEMOD', '-Wno-lint',
           '-Wno-style', '-Wno-MULTIDRIVEN', '-DLK=2', '-DTB_FWD_GATE', '-DTB_LDLY=0', '-DFRAME=col_h10_l4_b',
           '-DDSFD_PQ_STATIC_X2', '-DDSFD_PQ_HAS_BF_X2',
           '--top-module', 'tb_toksim_fgu_seq', '-Mdir', str(obj), '-f', 'tools/s81_dv/frame_bench.f',
           'rtl/dsrom_sys/s81_dv/frame_l4/col_h10_l4.sv', 'rtl/dsrom_sys/s81_dv/frame_l4/col_h10_l4_b.sv',
           'rtl/dsrom_sys/s81_dv/land/dsfd_cfifo_crs4.sv', 'rtl/dsrom_sys/s81_dv/land/ot_s81_land.sv',
           'rtl/dsrom_sys/s81_dv/frame/dsfd_rly_frame_exact.sv',
           str(SRC / 'tb_toksim_fgu_seq.sv'), '--build-jobs', '16', '-MAKEFLAGS', 'OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0']
    with (out / 'build.log').open('w') as f:
        r = subprocess.run(cmd, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT)
    assert r.returncode == 0 and exe.exists(), f'bench build failed (rc {r.returncode}), see {out}/build.log'
    return exe


GEN = r'''
import json, pickle, sys
from pathlib import Path
from types import SimpleNamespace
import xs_place as X, dv_layer_compile as C
V, FX, frame, op, die_cache = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
die = C.Die(C.die_tree(ref='HEAD', cache=die_cache))
rec, field = X.compile_frame(die, frame, FX, [op])
assert all(not p['faults'] for p in rec['phases']), [p['faults'] for p in rec['phases'] if p['faults']][:2]
V.mkdir(parents=True, exist_ok=True)
(V / 'frame.json').write_text(json.dumps(dict(rec, phases=[{k: v for k, v in p.items() if k != 'plan'} for p in rec['phases']]), indent=1) + '\n')
for ph in rec['phases']:
    if ph['op'] == op:
        X.gen_one(SimpleNamespace(fixtures=FX, frame=frame, mutant=None, bf_measure=False), rec, field, ph, V / f'p{ph["phase"]}')
'''


def gen(out, fx, op, wrong):
    V = out / ('vec_wrongdepth' if wrong else 'vec') / op.split('.')[-1]
    e = env()
    if wrong:
        e['OT_S81_STATION_DEPTH_OVERRIDE'] = json.dumps(WRONG_DEPTH)
    log = V.parent / f'{op}.gen.log'
    V.parent.mkdir(parents=True, exist_ok=True)
    with log.open('w') as f:
        r = subprocess.run([sys.executable, '-c', GEN, str(V), fx, FRAME, op, str(out / 'dieref')], cwd=ROOT, env=e,
                           stdout=f, stderr=subprocess.STDOUT)
    assert r.returncode == 0, f'vector generation failed for {op} wrong={wrong}: {log}'
    cmd = [sys.executable, str(SRC / 'toksim_fseq_seqops.py'), '--vec', str(V), '--name', op.split('.')[-1], '--ops', op]
    if op in PHASE_VM:
        cmd.append('--phase-vm')
    r = subprocess.run(cmd, cwd=ROOT, env=e, capture_output=True, text=True)
    (V / 'sequence_gen.log').write_text(r.stdout + r.stderr)
    assert r.returncode == 0, r.stdout + r.stderr
    return V


def run(exe, V, P, tag):
    sd = next(V.glob('seq_*'))
    s = json.loads((sd / 'seq.json').read_text())
    nph = len(s['phases'])
    log = V / f'run_P{P}.log'
    args = [str(exe), f'+OT_ROM_DIR={sd}', f'+T={nph * (P + 160) + 3000}', f'+K={s["K"]}', f'+OPS={max(s["rows"])}',
            f'+PH={s["phases"][0]}', f'+NPH={nph}', f'+PER={P}', '+RETIRE=1', f'+PHASE_VM={1 if s.get("phase_vm") else 0}']
    with log.open('w') as f:
        r = subprocess.run(args, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=3600)
    txt = log.read_text()
    faults = sum(1 for ln in txt.splitlines() if ln.startswith('FAULT'))
    end = sum(1 for ln in txt.splitlines() if ln.startswith('END'))
    chk = subprocess.run([sys.executable, str(SRC / 'toksim_fgu_check.py'), 'seq', '--seq', str(sd), '--vec', str(V),
                          '--log', str(log), '--out', str(V / f'check_P{P}.json'), '--per', str(P), '--ref-go', '63'],
                         cwd=ROOT, env=env(), capture_output=True, text=True)
    last = (chk.stdout.strip().splitlines() or [''])[-1]
    ok = r.returncode == 0 and faults == 0 and end == 1 and chk.returncode == 0 and ' PASS ' in f' {last} '
    return dict(case=tag, op=V.name, period=P, rc=r.returncode, faults=faults, end=end, check_rc=chk.returncode,
                check=last[:300], clean=ok, log=str(log))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    fx = Path(a.fixtures)
    man = (fx / 'manifest.sha256').read_text().split('\n')
    bad = [ln.split()[1] for ln in man if ln.strip() and
           hashlib.sha256((fx / ln.split()[1]).read_bytes()).hexdigest() != ln.split()[0]]
    assert not bad, f'fixture manifest mismatch: {bad[:4]}'
    with cf.ThreadPoolExecutor(8) as ex:
        fb = ex.submit(build, a.out)
        ops = sorted({o for o, _ in POS})
        vf = {o: ex.submit(gen, a.out, str(fx), o, False) for o in ops}
        vn = {o: ex.submit(gen, a.out, str(fx), o, True) for o in sorted({o for o, _ in NEG})}
        exe = fb.result()
        runs = [ex.submit(run, exe, vf[o].result(), P, 'positive') for o, P in POS]
        runs += [ex.submit(run, exe, vn[o].result(), P, 'negative_wrong_depth') for o, P in NEG]
        runs += [ex.submit(run, exe, vf[o].result(), P, 'negative_floor_minus_1') for o, P in FLOOR_M1]
        res = [r.result() for r in runs]
    pos_ok = all(r['clean'] for r in res if r['case'] == 'positive')
    neg_ok = all(not r['clean'] for r in res if r['case'] != 'positive')
    verdict = 'PASS' if pos_ok and neg_ok else 'FAIL'
    import station_depth as SD
    summary = dict(schema='opentallas.s81.frame_seq_gate.v1', verdict=verdict, positive_clean=pos_ok,
                   negative_detected=neg_ok, station_depth=SD.fingerprint(), runs=res,
                   binary_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                   head=subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True,
                                       text=True).stdout.strip())
    (a.out / 'summary.json').write_text(json.dumps(summary, indent=1) + '\n')
    for r in res:
        print('FRAME_SEQ', r['case'], r['op'], 'P', r['period'], 'faults', r['faults'], 'end', r['end'],
              'clean', r['clean'], '|', r['check'][:160])
    print('FRAME_SEQ_GATE', verdict, 'positive_clean', pos_ok, 'negative_detected', neg_ok)
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
    sys.exit(main())
