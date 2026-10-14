#!/usr/bin/env python3
"""el1013-hbm-seq-split: the qualification gate of the R25GQ sequencer split (rtl/hbm_accel/generic/tb/tb_hgi_seq_split.sv).

Side A is ALWAYS a mutant-free copy of the flat ot_hgi_seq.sv made here (module ot_hgi_seq_ref, helper
ot_hgi_seq_ref_hdly, every `ifdef OT_HGI_SEQ_MUT_* renamed to an undefined macro), so a global -D mutant reaches side B only.
Side B is --side-b (default ot_hgi_seq_split = ot_hgi_seq_split/_fe/_au/_be.sv + the helper ot_hgi_seq_hd.sv).

Runs (all in <out>/build, vectors copied from tb/hgi_seq*, the committed tb / conformance / DS images):
  positive            must PASS   (HGI_SEQ_SPLIT PASS ..., coverage, SPLIT_TPUT cycle ratios, DS mode-0 ratio <= 1.10)
  skew                must PASS   (+SKEW=7: side B's backpressure generators start from other seeds)
  corrupt 1..6        must FAIL   (bench-side corruption of one logged transaction of side B: the comparator can fail)
  one build a mutant  must FAIL   OT_HGI_SEQ_MUT_SEAM_CRED / _SEAM_QPOP / _SEAM_HOLD / _SEAM_RST (split children only;
                                  not applicable when side B is the flat module) and OT_HGI_SEQ_MUT_WAIT / _LOOP / _IDXL / _TOKX
A mutant that does not BUILD is not a kill (verdict build_error, gate fails); a mutant run that ends on the throughput
gate or the coverage refusal (every transaction matched) is not a kill either.
Writes <out>/gate.json and exits 0 only if both positives pass, every corruption fails and every applicable mutant fails.

  python3 tools/run_hgi_seq_split.py --out <dir> [--sim verilator|iverilog] [--side-b ot_hgi_seq_split|ot_hgi_seq]
                                     [--seed N] [--jobs N] [--src DIR] [--git-head SHA] [--only positive,skew,...]
"""
import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEAM_MUT = ['OT_HGI_SEQ_MUT_SEAM_CRED', 'OT_HGI_SEQ_MUT_SEAM_QPOP', 'OT_HGI_SEQ_MUT_SEAM_HOLD', 'OT_HGI_SEQ_MUT_SEAM_RST']
FLAT_MUT = ['OT_HGI_SEQ_MUT_WAIT', 'OT_HGI_SEQ_MUT_LOOP', 'OT_HGI_SEQ_MUT_IDXL', 'OT_HGI_SEQ_MUT_TOKX', 'OT_HGI_SEQ_MUT_DRAIN']
CORRUPT = {1: 'dispatch descriptor bit', 2: 'VM read address', 3: 'dropped dispatch', 4: 'completion token',
           5: 'fetch first address', 6: 'doorbell payload'}
ENV = dict(os.environ)
FAIL_RE = re.compile(r'HGI_SEQ_SPLIT FAIL|%Error|%Fatal|ERROR|\berror\b|Assertion|Aborted')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_ref(src, wd):
    """the flat reference: same text, other module names, mutant ifdefs dead"""
    t = (src / 'ot_hgi_seq.sv').read_text()
    n_mut = len(re.findall(r'`ifdef\s+OT_HGI_SEQ_MUT_', t))
    if n_mut != len(FLAT_MUT) or any(f'`ifdef {m}' not in t for m in FLAT_MUT):
        raise SystemExit(f'ot_hgi_seq.sv: expected the {len(FLAT_MUT)} flat mutant ifdefs, found {n_mut}')
    if "S_FEN = 5'd9" not in t:
        raise SystemExit("ot_hgi_seq.sv: S_FEN is no longer 5'd9 (the bench's FENCE coverage probe is hard-coded)")
    t = re.sub(r'\bot_hgi_seq_hdly\b', 'ot_hgi_seq_ref_hdly', t)
    t = re.sub(r'\bot_hgi_seq\b', 'ot_hgi_seq_ref', t)
    t = t.replace('OT_HGI_SEQ_MUT_', 'OT_HGI_SEQ_REF_NOMUT_')
    (wd / 'ot_hgi_seq_ref.sv').write_text(t)
    return wd / 'ot_hgi_seq_ref.sv'


def g24_vectors(wd):
    """the G24 LOOP-from-VM cases (the generator of tools/run_hgi_seq_g24.py), as the bench's set 3 (tag _g24)"""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import hgi_seq_vectors as S
    words, cases, vmi, vmw = [], [], [], []
    end = S.record(S.header('CTL', 'END', wait=0xFFFE), descs={'A': S.mdesc(space=1, fmt=5, base=0x8001, n=1)})
    body = S.record(S.header('DMA', 'LOAD'))
    first = 0
    for name, count, addr, nested, producer in [
            ('wait_snapshot', 3, 0x7000, False, True), ('65535_accepted', 65535, 0x7000, False, False),
            ('one', 1, 0x7000, False, False), ('nested_levels', 2, 0x7000, True, False), ('zero', 0, 0x7000, False, False),
            ('65536', 65536, 0x7000, False, False), ('all_bits', 0xffffffff, 0x7000, False, False),
            ('address_range', 2, 1 << 18, False, False), ('last_address', 2, (1 << 18) - 1, False, False)]:
        entry = len(words)
        prog = S.record(S.header('IDX', 'TOPK')) if producer else []
        if nested:
            prog += S.record(S.header('CTL', 'LOOP', param=2))
        prog += S.record(S.header('CTL', 'LOOP', param=(1 << 17) | (int(nested) << 16), imm_a=addr, wait=1 << 9 if producer else 0))
        if name != '65535_accepted':
            prog += body + S.record(S.header('CTL', 'ENDLOOP'))
        if nested:
            prog += S.record(S.header('CTL', 'ENDLOOP'))
        prog += end
        words += prog
        ci = len(cases)
        vm = {0x8001: 4242, addr: 1 if producer else count}

        def disp(k, u, o, addr=addr, count=count, producer=producer):
            return [(addr, count)] if producer and u == 'IDX' else []
        tr, cpl = S.Ref(words, entry, 1, 100, 0, 151936, 40960, vm, disp).run()
        for k, d in enumerate(tr):
            for a, v in disp(k, S.UNITS[d['unit']], None):
                vmw.append(((first + k) << 64) | (a << 32) | v)
        cases.append((entry, 1, 100, 0, 151936, 40960, len(tr), cpl[0], cpl[1], 0xffff, first, 0))
        first += len(tr)
        vmi += [(ci, 0x8001, 4242)] + ([(ci, addr, 1 if producer else count)] if addr < 1 << 18 else [])

    def write(n, lines):
        (wd / n).write_text('\n'.join(lines) + '\n')
    write('hgi_seq_image_g24.mem', [f'{v:032X}' for v in words])
    write('hgi_seq_cfg_g24.mem', [' '.join(f'{v:08X}' for v in c) for c in cases])
    write('hgi_seq_vmi_g24.mem', [f'{c:08X}{a:08X}{v:08X}' for c, a, v in vmi])
    write('hgi_seq_vmw_g24.mem', [f'{v:024X}' for v in vmw])
    write('hgi_seq_sizes_g24.svh', ['// GENERATED by tools/run_hgi_seq_split.py'] +
          [f'localparam integer G24_{k} = {v};' for k, v in dict(NCASE=len(cases), NW=len(words), NVMI=len(vmi)).items()])
    return dict(cases=len(cases), words=len(words), statuses=[c[8] for c in cases], dispatches=[c[6] for c in cases])


def side_b_files(src, side_b):
    if side_b == 'ot_hgi_seq':
        return [src / 'ot_hgi_seq.sv'], None
    kids = [src / f'ot_hgi_seq_{k}.sv' for k in ('fe', 'au', 'be')]
    # ot_hgi_seq_hd.sv: the children's hold-delay helper; ot_hgi_seq.sv only when a child still uses ot_hgi_seq_hdly
    files = [src / f'{side_b}.sv'] + kids + ([src / 'ot_hgi_seq_hd.sv'] if (src / 'ot_hgi_seq_hd.sv').exists() else [])
    if any(re.search(r'\bot_hgi_seq_hdly\b', k.read_text()) for k in kids if k.exists()):
        files.append(src / 'ot_hgi_seq.sv')
    miss = [str(f) for f in files if not f.exists()]
    if miss:
        raise SystemExit('side B sources missing: ' + ' '.join(miss))
    par = (src / f'{side_b}.sv').read_text()
    terms = []
    for k in ('fe', 'au', 'be'):
        if 'seam_err' in (src / f'ot_hgi_seq_{k}.sv').read_text():
            m = re.search(r'^\s*ot_hgi_seq_%s\b.*?^\s*(u_\w+)\s*\(|\bot_hgi_seq_%s\b[^;]*?\)\s*(u_\w+)\s*\(' % (k, k), par, re.S | re.M)
            if not m:
                raise SystemExit(f'{side_b}.sv: no instance of ot_hgi_seq_{k} found')
            terms.append(f'dut.{m.group(1) or m.group(2)}.seam_err')
    if not terms:
        raise SystemExit('no child declares seam_err: the bench cannot probe the seam (refused)')
    return files, '(' + '|'.join(terms) + ')'


def build(a, wd, tag, files, defs):
    log = wd / f'build_{tag}.log'
    t0 = time.time()
    if a.sim == 'verilator':
        od = wd / f'obj_{tag}'
        cmd = ['verilator', '--binary', '--timing', '-j', '8', '--top-module', 'tb_hgi_seq_split', '-Wno-fatal', '-Wno-lint',
               '-Wno-style', '--x-initial', 'unique', '-O3', '-CFLAGS', '-O1', '-I' + str(wd), '-I' + str(a.src), '--Mdir', str(od), '-o', 'sim']
        cmd += ['-D' + d for d in defs] + [str(f) for f in files]
        exe = [str(od / 'sim'), '+verilator+rand+reset+2', f'+verilator+seed+{a.seed + 17}', '+verilator+error+limit+1000']
    else:
        vvp = wd / f'sim_{tag}.vvp'
        cmd = ['iverilog', '-g2012', '-I' + str(wd), '-I' + str(a.src), '-s', 'tb_hgi_seq_split', '-o', str(vvp)]
        cmd += ['-D' + d for d in defs] + [str(f) for f in files]
        exe = ['vvp', '-n', str(vvp)]
    r = subprocess.run(cmd, cwd=wd, capture_output=True, text=True, env=ENV)
    log.write_text(' '.join(cmd) + '\n' + r.stdout + r.stderr)
    return (exe if r.returncode == 0 else None), round(time.time() - t0, 1)


def run(a, wd, exe, tag, plus):
    t0 = time.time()
    try:
        r = subprocess.run(exe + plus, cwd=wd, capture_output=True, text=True, timeout=a.timeout, env=ENV)
        out, rc = r.stdout + r.stderr, r.returncode
    except subprocess.TimeoutExpired as e:
        out, rc = (e.stdout or b'').decode(errors='replace') + '\nERROR runner timeout\n', 124
    (wd / f'run_{tag}.log').write_text(out)
    lines = out.splitlines()
    pas = next((ln for ln in lines if ln.startswith('HGI_SEQ_SPLIT PASS')), None)
    bad = [i for i, ln in enumerate(lines) if FAIL_RE.search(ln)]
    first = None
    if bad:      # the bench prints its detail lines ("  ...") right before the FAIL line
        i = bad[0]
        det = [ln for ln in lines[max(0, i - 9):i] if ln.startswith('  ')]
        first = '\n'.join(det + [lines[i]])
    return dict(tag=tag, passed=bool(pas) and rc == 0 and not bad, pass_line=pas, first_failure=first, returncode=rc,
                seconds=round(time.time() - t0, 1),
                cov=next((ln for ln in lines if ln.startswith('SPLIT_COV')), None),
                tput=[ln for ln in lines if ln.startswith('SPLIT_TPUT')])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--sim', choices=['verilator', 'iverilog'], default='verilator')
    ap.add_argument('--side-b', default='ot_hgi_seq_split')
    ap.add_argument('--src', default=str(ROOT / 'rtl/hbm_accel/generic'))
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--jobs', type=int, default=5)
    ap.add_argument('--timeout', type=int, default=6 * 3600)
    ap.add_argument('--git-head', default=None)
    ap.add_argument('--defs', default='', help='comma list of extra defines for every build (a job mutant bench: one seam mutant + --only positive)')
    ap.add_argument('--only', default=None, help='comma list of run names (positive, skew, corrupt, mutants)')
    a = ap.parse_args()
    a.src = Path(a.src).resolve()
    out = Path(a.out).resolve()
    wd = out / 'build'
    if wd.exists():
        shutil.rmtree(wd)
    wd.mkdir(parents=True)
    only = set(a.only.split(',')) if a.only else {'positive', 'skew', 'corrupt', 'mutants'}
    (wd / 'tmp').mkdir()
    ENV['TMPDIR'] = str(wd / 'tmp')        # iverilog / make need an existing TMPDIR (ot-heavy's may not exist)
    for p in (a.src / 'tb').glob('hgi_seq*'):
        shutil.copy(p, wd / p.name)
    g24 = g24_vectors(wd)
    ref = make_ref(a.src, wd)
    bfiles, seam = side_b_files(a.src, a.side_b)
    tb = a.src / 'tb/tb_hgi_seq_split.sv'
    files = [tb, ref] + bfiles
    defs = ['SEQ_A_MOD=ot_hgi_seq_ref', f'SEQ_B_MOD={a.side_b}'] + ([f'SEQ_B_SEAM_ERR={seam}'] if seam else []) + [d for d in a.defs.split(',') if d]
    seed = [f'+SEED={a.seed}']
    rec = dict(schema='opentallas.hbm.hgi_seq_split_gate.v1', side_a='ot_hgi_seq_ref (mutant-free copy of ot_hgi_seq.sv)',
               side_b=a.side_b, sim=a.sim, seed=a.seed, seam_err_probe=seam, g24_vectors=g24, runs={}, mutants={}, corrupt={})
    exe, bt = build(a, wd, 'pos', files, defs)
    rec['build_positive_s'] = bt
    if exe is None:
        rec['positive'] = dict(passed=False, first_failure='BUILD ERROR: ' + (wd / 'build_pos.log').read_text()[-3000:])
    else:
        todo = []
        if 'positive' in only:
            todo.append(('positive', seed))
        if 'skew' in only:
            todo.append(('skew', seed + ['+SKEW=7']))
        if 'corrupt' in only:
            todo += [(f'corrupt{k}', seed + [f'+CORRUPT={k}']) for k in CORRUPT]
        with cf.ThreadPoolExecutor(a.jobs) as ex:
            res = list(ex.map(lambda x: run(a, wd, exe, x[0], x[1]), todo))
        for r in res:
            if r['tag'].startswith('corrupt'):
                k = int(r['tag'][7:])
                rec['corrupt'][CORRUPT[k]] = dict(verdict='FAIL (as required)' if not r['passed'] else 'PASSED (comparator blind)',
                                                  killed=not r['passed'], first_failure=r['first_failure'])
            else:
                rec['runs'][r['tag']] = r
    muts = ([] if a.side_b == 'ot_hgi_seq' else SEAM_MUT) + FLAT_MUT

    def mutant(m):
        e, bt = build(a, wd, m, files, defs + [m])
        if e is None:
            return m, dict(verdict='build_error', killed=False, build_s=bt, first_failure=(wd / f'build_{m}.log').read_text()[-1500:])
        r = run(a, wd, e, m, seed)
        # a kill is a FUNCTIONAL failure: the throughput gate or the coverage refusal (which end a run whose every
        # transaction matched) do not count
        soft = bool(r['first_failure']) and re.search(r'HGI_SEQ_SPLIT FAIL (tput|coverage)', r['first_failure'].splitlines()[-1])
        if soft:
            return m, dict(verdict='SURVIVES (all transactions equal; run ended on: ' + r['first_failure'].splitlines()[-1] + ')',
                           killed=False, build_s=bt, seconds=r['seconds'], first_failure=r['first_failure'], pass_line=None)
        return m, dict(verdict='FAIL (as required)' if not r['passed'] else 'PASSED (mutant survives)', killed=not r['passed'],
                       build_s=bt, seconds=r['seconds'], first_failure=r['first_failure'], pass_line=r['pass_line'])
    if 'mutants' in only:
        with cf.ThreadPoolExecutor(a.jobs) as ex:
            rec['mutants'] = dict(ex.map(mutant, muts))
        rec['mutants_not_applicable'] = SEAM_MUT if a.side_b == 'ot_hgi_seq' else []
    pos = rec['runs'].get('positive')
    if pos:
        rec['positive_pass_line'] = pos['pass_line']
        rec['coverage'] = dict(kv.split('=') for kv in pos['cov'].split()[1:]) if pos['cov'] else None
        rec['cycle_ratios'] = pos['tput']
    srcs = sorted(set(a.src.glob('ot_hgi_seq*.sv')) | {a.src / 'ot_hgi_seq_seam.svh', a.src / 'ot_hgi_cp.sv', tb, Path(__file__).resolve(),
                   Path(__file__).resolve().parent / 'hgi_seq_vectors.py'} |
                  set((a.src / 'tb').glob('hgi_seq*.mem')) | set((a.src / 'tb').glob('hgi_seq_sizes*.svh')))
    rec['source_sha256'] = {str(p.relative_to(ROOT)) if ROOT in p.parents else str(p): sha(p) for p in srcs if p.exists()}
    head = a.git_head
    if head is None:
        g = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT, capture_output=True, text=True)
        head = g.stdout.strip() if g.returncode == 0 else 'unknown'
    rec['git_head'] = head
    ok = all(rec['runs'].get(k, {}).get('passed') for k in ('positive', 'skew') if k in only)
    ok = ok and all(v['killed'] for v in rec['corrupt'].values()) and all(v['killed'] for v in rec['mutants'].values())
    ok = ok and only >= {'positive', 'skew', 'corrupt', 'mutants'}
    rec['gate'] = 'PASS' if ok else 'FAIL'
    (out / 'gate.json').write_text(json.dumps(rec, indent=1) + '\n')
    for k, r in rec['runs'].items():
        print(k, ':', r['pass_line'] or r['first_failure'], f"({r['seconds']} s)")
    if pos and pos['cov']:
        print(pos['cov'])
        print('\n'.join(ln for ln in pos['tput'] if '.mode' in ln))
    for k, v in rec['corrupt'].items():
        print('corrupt', k, ':', v['verdict'], '|', (v['first_failure'] or '').splitlines()[-1:])
    for k, v in rec['mutants'].items():
        print('mutant', k, ':', v['verdict'], '|', (v['first_failure'] or '').splitlines()[-1:])
    print('GATE', rec['gate'], out / 'gate.json')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
