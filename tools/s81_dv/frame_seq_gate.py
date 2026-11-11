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
import re
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


QBANK_S = 'rtl/dsrom_sys/s81_fill2/gen19b/dsfd_qbank_S.sv'


def qbank_s_3flop(out):
    """bench-only copy of dsfd_qbank_S with ONE more register on every output (o_x0 / o_x1 / o_go / o_cfg), the
    qbank pin-cycle form: x, go and cfg reach the element one edge later together, go_tag (cfg7_seq -> element, no
    qbank) does not, so the go_tag lead over go grows 2 -> 3 on every element"""
    src = (ROOT / QBANK_S).read_text()
    for n in ('cfg', 'go', 'x0', 'x1'):
        old = f'else r_{n} <= l_{n};'
        assert src.count(old) == 1, n
        w = re.search(rf'reg (\[\d+:0\] )?l_{n}\b', src).group(1) or ''
        L = src.split('\n')
        i = next(k for k, ln in enumerate(L) if old in ln)
        L[i] = L[i].replace(old, f'else r_{n} <= p_{n};')
        L.insert(i, f'    reg {w}p_{n}; always @(posedge ck[0] or negedge rn) if (!rn) p_{n} <= 0; else p_{n} <= l_{n};')
        src = '\n'.join(L)
    f = out / 'dsfd_qbank_S_3flop.sv'
    f.write_text(src)
    fl = out / 'frame_bench_qb3.f'
    lines = (ROOT / 'tools/s81_dv/frame_bench.f').read_text().splitlines()
    assert sum(ln.strip() == QBANK_S for ln in lines) == 1
    fl.write_text('\n'.join(str(f) if ln.strip() == QBANK_S else ln for ln in lines) + '\n')
    return fl


def build(out, flist='tools/s81_dv/frame_bench.f', defines=()):
    obj = out / 'build/obj'
    exe = obj / 'Vtb_toksim_fgu_seq'
    if exe.exists():
        return exe
    obj.mkdir(parents=True, exist_ok=True)
    cmd = [str(VERILATOR), '--binary', '--timing', '-O1', '-Wno-fatal', '-Wno-WIDTH', '-Wno-TIMESCALEMOD', '-Wno-lint',
           '-Wno-style', '-Wno-MULTIDRIVEN', '-DLK=2', '-DTB_FWD_GATE', '-DTB_LDLY=0', '-DFRAME=col_h10_l4_b',
           '-DDSFD_PQ_STATIC_X2', '-DDSFD_PQ_HAS_BF_X2',
           *defines, '--top-module', 'tb_toksim_fgu_seq', '-Mdir', str(obj), '-f', str(flist),
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


def gen(out, fx, op, wrong, depth=None, name=None):
    V = out / (name or ('vec_wrongdepth' if wrong else 'vec')) / op.split('.')[-1]
    e = env()
    if wrong:
        e['OT_S81_STATION_DEPTH_OVERRIDE'] = json.dumps(WRONG_DEPTH)
    if depth:
        e['OT_S81_STATION_DEPTH_OVERRIDE'] = json.dumps(depth)
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


def run(exe, V, P, tag, sfx=''):
    sd = next(V.glob('seq_*'))
    s = json.loads((sd / 'seq.json').read_text())
    nph = len(s['phases'])
    log = V / f'run_P{P}{sfx}.log'
    args = [str(exe), f'+OT_ROM_DIR={sd}', f'+T={nph * (P + 160) + 3000}', f'+K={s["K"]}', f'+OPS={max(s["rows"])}',
            f'+PH={s["phases"][0]}', f'+NPH={nph}', f'+PER={P}', '+RETIRE=1', f'+PHASE_VM={1 if s.get("phase_vm") else 0}']
    with log.open('w') as f:
        r = subprocess.run(args, cwd=ROOT, stdout=f, stderr=subprocess.STDOUT, timeout=3600)
    txt = log.read_text()
    faults = sum(1 for ln in txt.splitlines() if ln.startswith('FAULT'))
    end = sum(1 for ln in txt.splitlines() if ln.startswith('END'))
    chk = subprocess.run([sys.executable, str(SRC / 'toksim_fgu_check.py'), 'seq', '--seq', str(sd), '--vec', str(V),
                          '--log', str(log), '--out', str(V / f'check_P{P}{sfx}.json'), '--per', str(P), '--ref-go', '63'],
                         cwd=ROOT, env=env(), capture_output=True, text=True)
    last = (chk.stdout.strip().splitlines() or [''])[-1]
    ok = r.returncode == 0 and faults == 0 and end == 1 and chk.returncode == 0 and ' PASS ' in f' {last} '
    return dict(case=tag, op=V.name, period=P, rc=r.returncode, faults=faults, end=end, check_rc=chk.returncode,
                check=last[:300], clean=ok, log=str(log))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--fixtures', required=True)
    ap.add_argument('--out', required=True, type=Path)
    ap.add_argument('--go-tag-lead3', action='store_true',
                    help='go_tag skew proof (summary_lead3.json): bench with a 3-flop dsfd_qbank_S (go_tag leads go by 3)')
    a = ap.parse_args()
    if a.go_tag_lead3:
        return lead3(a)
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


# experts_gu at its floor P145 FAULTs 11 on the lead-3 build (cfg7 load overrun: the element's bank_free / sh_free reach
# cfg7_seq one edge later through the extra element-side register, so the go spacing floor moves +1); P146 is the form's
# floor point.  That is a floor cost of the pin cycle, not a go_tag effect (the P145 run has no calendar mismatch).
def ret_tags(log):
    """the PQ op tag of every RET word in edge order: row id bits [15:14] (frame_return_plan OPTAG field) = word bits
    [29:28].  The per-phase calendar check (xs_place check) compares the compiled OPTAG-free row, so the element's
    sampled go_tag is checked here, against the bound-depth build on the same op / period."""
    return [(int(m.group(2), 16) >> 28) & 3 for m in re.finditer(r'^RET (\d+) ([0-9a-fA-F]+)\s*$', Path(log).read_text(), re.M)]


LEAD3_POS = [('attn.wq_b', 128), ('ffn.experts_gu', 146)]


def lead3(a):
    """S81-FRAME-FIX-1 11-11 (COORD item 3, qbank pin cycle): go_tag-to-go lead 3 proof.  The element captures go_tag
    in the same pin register stage as go (ot_v41_rom_elem_qx_pq_w10 b_go_tag / r_go_tag beside go), and cfg7_seq launches
    go_tag = the op tag from the go edge on (tag advances on go_x; ot_s81_cfg7_seq.sv:271/309), held until the next go,
    so any lead 1 <= L < go spacing samples the same tag.  Bench: every element on a 3-flop qbank_S (lead 3):
      positive   compiled at qbank_S depth 3 (the RTL copy)      -> must be clean (strict calendar + tag check)
      negative   compiled at the bound depth 2 (calendar 1 early) -> must FAULT / mismatch
      tag ctrl   lead-3 build with OT_S81_CFG7_MUT_TAG (tag one op ahead), compiled at depth 3 -> must FAIL
      tag check  the strict calendar checker does not compare the op tag (bits [29:28] of a RET word), so the RET tag
                 sequence of every lead-3 run must equal the bound (lead 2) build's on the same op / period, and the
                 MUT_TAG run's must differ"""
    a.out.mkdir(parents=True, exist_ok=True)
    fx = Path(a.fixtures)
    fl = qbank_s_3flop(a.out)
    d3 = {'dsfd_qbank_S': 3}
    with cf.ThreadPoolExecutor(8) as ex:
        b3 = ex.submit(build, a.out / 'lead3', fl)
        bt = ex.submit(build, a.out / 'lead3_mut_tag', fl, ('-DOT_S81_CFG7_MUT_TAG',))
        ops = sorted({o for o, _ in LEAD3_POS})
        v3 = {o: ex.submit(gen, a.out, str(fx), o, False, d3, 'vec_qb3') for o in ops}
        v2 = ex.submit(gen, a.out, str(fx), 'attn.wq_b', False, None, 'vec_qb2')
        bb = ex.submit(build, a.out)
        e3, et, eb = b3.result(), bt.result(), bb.result()
        runs = [ex.submit(run, e3, v3[o].result(), P, 'positive_lead3', '_lead3') for o, P in LEAD3_POS]
        runs += [ex.submit(run, e3, v3['ffn.experts_gu'].result(), 145, 'floor_lead3', '_lead3')]
        runs += [ex.submit(run, e3, v2.result(), 128, 'negative_depth2_on_lead3', '_lead3')]
        runs += [ex.submit(run, et, v3['attn.wq_b'].result(), 128, 'negative_mut_tag_lead3', '_mut_tag')]
        refs = {(o, P): ex.submit(run, eb, v2.result() if o == 'attn.wq_b' else
                                  ex.submit(gen, a.out, str(fx), o, False, None, 'vec_qb2').result(), P, 'bound_lead2', '_bound')
                for o, P in LEAD3_POS}
        res = [r.result() for r in runs]
        refs = {k: v.result() for k, v in refs.items()}
    for r in res:
        key = next(((o, P) for o, P in LEAD3_POS if o.endswith(r['op']) and P == r['period']), None)
        if key is None:
            continue
        ref = refs[key]
        same = ret_tags(r['log']) == ret_tags(ref['log']) and bool(ret_tags(ref['log'])) and ref['clean']
        r['tags_equal_bound'] = same
        if r['case'] == 'negative_mut_tag_lead3':
            r['clean'] = r['clean'] and same          # a tag change the calendar checker misses is caught here
        elif r['case'] == 'positive_lead3':
            r['clean'] = r['clean'] and same
    res += list(refs.values())
    pos_ok = all(r['clean'] for r in res if r['case'].startswith(('positive', 'bound')))
    neg_ok = all(not r['clean'] for r in res if r['case'].startswith('negative'))
    verdict = 'PASS' if pos_ok and neg_ok else 'FAIL'
    # floor_lead3 (experts_gu P145) is reported, not gated: it measures the form's floor cost
    summary = dict(schema='opentallas.s81.frame_seq_gate.lead3.v1', verdict=verdict, go_tag_lead=3,
                   positive_clean=pos_ok, negative_detected=neg_ok, runs=res,
                   qbank_s_3flop_sha256=hashlib.sha256((a.out / 'dsfd_qbank_S_3flop.sv').read_bytes()).hexdigest(),
                   head=subprocess.run(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], capture_output=True,
                                       text=True).stdout.strip())
    (a.out / 'summary_lead3.json').write_text(json.dumps(summary, indent=1) + '\n')
    for r in res:
        print('FRAME_SEQ_LEAD3', r['case'], r['op'], 'P', r['period'], 'faults', r['faults'], 'clean', r['clean'],
              'tags_equal_bound', r.get('tags_equal_bound'), '|',
              r['check'][:160])
    print('FRAME_SEQ_GATE_LEAD3', verdict, 'positive_clean', pos_ok, 'negative_detected', neg_ok)
    return 0 if verdict == 'PASS' else 1


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT / 'tools/s81_dv'))
    sys.exit(main())
