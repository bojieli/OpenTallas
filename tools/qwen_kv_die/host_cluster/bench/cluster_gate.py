#!/usr/bin/env python3
"""KVJ-A3 cluster composition gate for every HOST-cluster child job (loop bench, run from the repo root at the job's
source commit): verilate the flat root qkd_host_root_admission and the committed cluster qkd_hr_cluster, link the
lock-step harness (gen_tb.py) and run it.

  cluster_gate.py exact  --out DIR                 # expect pass: CLUSTER_GATE PASS
  cluster_gate.py mutant --out DIR --child core_rx # expect fail: the child's reset input inverted at the parent
  cluster_gate.py rrmutant --out DIR --define M      # expect fail: the cluster built with `define M (a member wrapper's
                                                    # bench mutant, e.g. QKD_HR_PR_RR_MUTANT: core_prompt relays bypassed);
                                                    # the flat reference keeps the accepted wrappers

  cluster_gate.py mutant --out DIR --child cdc_host --port P  # expect fail: the child's input P inverted (~) at the
                                                   # parent (a child whose reset mutant the random stimulus cannot see)
  cluster_gate.py mutant --out DIR --unfix qkd_host_native_qm_debt  # expect fail: the leaf binds the shared original
                                                   # instead of its CDC fork (the reference keeps the fork)

The CDC leaves bind leaf-local CDC forks (rtl/qwen_sys/host_cluster_cdc_20261018/forks.json, KV-CDC2 10-18); the flat
reference is built with each fork in place of its original (module renamed back, original file dropped), so the
lock-step stays exact.

usage: cluster_gate.py {exact,mutant,rrmutant} --out DIR [--child C] [--port P] [--unfix M] [--define M] [--cycles N] [--verilator V]
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]   # repo root (tools/qwen_kv_die/host_cluster/bench)
HERE = Path(__file__).resolve().parent
CLUSTER_DIR = ROOT / 'rtl/qwen_sys/host_cluster_20261017'   # qkd_hr_cluster.v (parent) + one file per child
PORTS = HERE / 'root_ports.json'          # the flat root's ports (yosys, ENABLE_SERVICE/NATIVE/TOKEN=1, NL=2)
SOURCES = HERE / 'sources.txt'            # census source list (SRAM behavioural models + the root's RTL)
FLAT_WRAPS = HERE / 'flat_wraps.json'     # accepted member wrappers (gen_cluster --wrap): applied to the flat reference
FORKS_JSON = ROOT / 'rtl/qwen_sys/host_cluster_cdc_20261018/forks.json'


def forks():
    f = json.loads(FORKS_JSON.read_text()) if FORKS_JSON.is_file() else {}
    f.pop('_doc', None)
    return f


def sources():
    return [l.strip() for l in SOURCES.read_text().splitlines() if l.strip()]


def flat_sources(out):
    """the flat reference's sources with every accepted member wrapper substituted at its instance sites (overlay
    copies in OUT/flat_overlay; the committed flat RTL is unchanged); the wrapper files themselves are left as is"""
    wraps = json.loads(FLAT_WRAPS.read_text())['wraps'] if FLAT_WRAPS.exists() else {}
    ov = out / 'flat_overlay'
    ov.mkdir(exist_ok=True)
    res, n = [], 0
    for s in sources():
        f = ROOT / s
        t = f.read_text() if f.suffix in ('.v', '.sv') else None
        if t is None or any(re.search(r'^\s*module\s+' + w + r'\b', t, re.M) for w in wraps.values()):
            res.append(str(f))
            continue
        u = t
        for m_, w in wraps.items():
            u, k = re.subn(r'^(\s*)' + m_ + r'(?=\s*(?:#\s*\(|[A-Za-z_\\]))', lambda x: x.group(1) + w, u, flags=re.M)
            n += k
        if u != t:
            (ov / f.name).write_text(u)
            res.append(str(ov / f.name))
        else:
            res.append(str(f))
    print(f'flat reference: {n} member instance(s) wrapped per {FLAT_WRAPS.name} {sorted(wraps.items())}')
    return res


def run(cmd, log, cwd):
    with open(log, 'w') as f:
        r = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        sys.exit(f'CLUSTER_GATE ERROR {Path(log).name} rc={r.returncode}: ' + Path(log).read_text()[-1500:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['exact', 'mutant', 'rrmutant'])
    ap.add_argument('--define', default='QKD_HR_PR_RR_MUTANT')
    ap.add_argument('--out', required=True)
    ap.add_argument('--child', default='core_queue')
    ap.add_argument('--port', help='mutant: invert this child input binding instead of its reset')
    ap.add_argument('--unfix', help='mutant: the leaves bind this shared original module instead of its CDC fork')
    ap.add_argument('--cycles', type=int, default=20000)
    ap.add_argument('--verilator', default=str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    txt = ''.join(f.read_text() for f in sorted(CLUSTER_DIR.glob('qkd_hr_*.v')))
    FK = forks()
    if a.unfix:
        if a.mode != 'mutant' or a.unfix not in FK:
            sys.exit(f'CLUSTER_GATE ERROR --unfix {a.unfix}: mutant mode and one of {sorted(FK)}')
        n0 = len(re.findall(r'(?m)^\s+' + FK[a.unfix]['fork'] + r'\b', txt))
        if not n0:
            sys.exit(f'CLUSTER_GATE ERROR no instance of {FK[a.unfix]["fork"]}')
        txt = re.sub(r'(?m)^(\s+)' + FK[a.unfix]['fork'] + r'\b', lambda m: m.group(1) + a.unfix, txt)
        print(f'mutant: {n0} instance(s) of {FK[a.unfix]["fork"]} bind the original {a.unfix}')
    elif a.mode == 'mutant':
        m = re.search(r'\n  qkd_hr_' + a.child + r' u_' + a.child + r' \((.*?)\);', txt, re.S)
        mod = re.search(r'\nmodule qkd_hr_' + a.child + r'\(.*?\nendmodule', txt, re.S).group(0)
        scalars = re.findall(r'^\s*input\s+(\w+)\s*;', mod, re.M)
        cand = [x for x in scalars if x == 'host_rst_n'] + [x for x in scalars if re.search(r'por_n|rst', x)]
        sig = a.port or (cand or [x for x in scalars if not x.startswith('ck')])[0]
        if a.port and not re.search(r'^\s*input\s+(?:\[[^]]*\]\s*)?' + sig + r'\s*;', mod, re.M):
            sys.exit(f'CLUSTER_GATE ERROR u_{a.child} has no input {sig}')
        b = re.search(r'\.' + sig + r'\(([^()]+)\)', m.group(1)) if m else None
        if not b:
            sys.exit(f'CLUSTER_GATE ERROR no u_{a.child} {sig} input binding')
        body = m.group(0).replace(b.group(0), f'.{sig}(~({b.group(1).strip()}))' if a.port else
                                  f'.{sig}(!({b.group(1).strip()}))')
        print(f'mutant: u_{a.child}.{sig} inverted at the parent')
        txt = txt.replace(m.group(0), body)
    (out / 'qkd_hr_cluster_dut.v').write_text(txt)
    subprocess.run([sys.executable, str(HERE / 'gen_tb.py'), str(PORTS), str(out / 'tb.cpp')], check=True)
    V = a.verilator
    common = ['--cc', '-O2', '--x-assign', '0', '--x-initial', '0', '-Wno-fatal', '-Wno-lint', '-Wno-style',
              '-Wno-MULTIDRIVEN', '-Wno-UNOPTFLAT', '--no-timing', '-I' + str(ROOT / 'rtl'), '-CFLAGS', '-O1', '-j', '0']
    src = [str(ROOT / s) for s in sources()]
    # flat reference: each fork replaces its original (renamed back to the original module name)
    refdir = out / 'ref_forks'
    refdir.mkdir(exist_ok=True)
    drop, ref_src = {str(ROOT / v['original']) for v in FK.values()}, []
    for orig, v in FK.items():
        t = (ROOT / v['file']).read_text()
        if len(re.findall(r'\bmodule\s+' + v['fork'] + r'\b', t)) != 1:
            sys.exit(f'CLUSTER_GATE ERROR fork file {v["file"]} must define {v["fork"]} once')
        o = re.sub(r'//[^\n]*|/\*.*?\*/', '', (ROOT / v['original']).read_text(), flags=re.S)
        if re.findall(r'\bmodule\s+(\w+)', o) != [orig]:
            sys.exit(f'CLUSTER_GATE ERROR {v["original"]} must define only {orig}')
        (refdir / Path(v['file']).name).write_text(re.sub(r'\bmodule\s+' + v['fork'] + r'\b', 'module ' + orig, t))
        ref_src.append(str(refdir / Path(v['file']).name))
    flat_src = [x for x in flat_sources(out) if x not in drop] + ref_src
    clu_src = src + [str(ROOT / v['file']) for v in FK.values()]
    p1 = subprocess.Popen([V] + common + ['--prefix', 'Vflat', '--top-module', 'qkd_host_root_admission',
                                          '-GENABLE_SERVICE=1', '-GENABLE_NATIVE=1', '-GENABLE_TOKEN=1', '-GNL=2',
                                          '-Mdir', str(out / 'obj_flat')] + flat_src,
                          stdout=open(out / 'vl_flat.log', 'w'), stderr=subprocess.STDOUT)
    if a.mode == 'rrmutant':
        print(f'rrmutant: cluster built with -D{a.define} (flat reference unchanged)')
    p2 = subprocess.Popen([V] + common + (['-D' + a.define] if a.mode == 'rrmutant' else []) +
                          ['--prefix', 'Vclu', '--top-module', 'qkd_hr_cluster', '-Mdir',
                                          str(out / 'obj_clu')] + clu_src + [str(out / 'qkd_hr_cluster_dut.v')],
                          stdout=open(out / 'vl_clu.log', 'w'), stderr=subprocess.STDOUT)
    if p1.wait() or p2.wait():
        sys.exit('CLUSTER_GATE ERROR verilator: ' + (out / 'vl_flat.log').read_text()[-800:] + (out / 'vl_clu.log').read_text()[-800:])
    run(['make', '-s', '-j', '16', '-C', str(out / 'obj_flat'), '-f', 'Vflat.mk', 'Vflat__ALL.a', 'verilated.o',
         'verilated_threads.o'], out / 'mk_flat.log', out)
    run(['make', '-s', '-j', '16', '-C', str(out / 'obj_clu'), '-f', 'Vclu.mk', 'Vclu__ALL.a'], out / 'mk_clu.log', out)
    vr = subprocess.run([V, '--getenv', 'VERILATOR_ROOT'], capture_output=True, text=True).stdout.strip()
    run(['g++', '-O1', '-std=c++17', '-Iobj_flat', '-Iobj_clu', f'-I{vr}/include', f'-I{vr}/include/vltstd', 'tb.cpp',
         'obj_flat/Vflat__ALL.a', 'obj_clu/Vclu__ALL.a', 'obj_flat/verilated.o', 'obj_flat/verilated_threads.o',
         '-pthread', '-latomic', '-o', 'tb_lockstep'], out / 'link.log', out)
    ok = 0
    for seed in (1, 2, 3):
        for mode in (0, 1):
            r = subprocess.run(['./tb_lockstep', str(seed), str(mode), str(a.cycles)], cwd=out, capture_output=True, text=True)
            line = (r.stdout.strip().splitlines() or ['(no output)'])[-1]
            print(f'seed={seed} mode={mode}: {line}')
            ok += r.returncode == 0 and line.startswith('LOCKSTEP PASS')
    tag = f'{a.mode}' + ((f' unfix={a.unfix}' if a.unfix else f' child={a.child}' + (f' port={a.port}' if a.port else ''))
                         if a.mode == 'mutant' else '') + (f' define={a.define}' if a.mode == 'rrmutant' else '')
    print(f'CLUSTER_GATE {"PASS" if ok == 6 else "FAIL"} {tag} runs_pass={ok}/6 core_cycles={a.cycles}')
    shutil.rmtree(out / 'obj_flat', ignore_errors=True)
    shutil.rmtree(out / 'obj_clu', ignore_errors=True)


if __name__ == '__main__':
    main()
