#!/usr/bin/env python3
"""KVJ-A3 cluster composition gate for every HOST-cluster child job (loop bench, run from the repo root at the job's
source commit): verilate the flat root qkd_host_root_admission and the committed cluster qkd_hr_cluster, link the
lock-step harness (gen_tb.py) and run it.

  cluster_gate.py exact  --out DIR                 # expect pass: CLUSTER_GATE PASS
  cluster_gate.py mutant --out DIR --child core_rx # expect fail: the child's reset input inverted at the parent

usage: cluster_gate.py {exact,mutant} --out DIR [--child C] [--cycles N] [--verilator V]
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = Path(__file__).resolve().parent
CLUSTER = ROOT / 'rtl/qwen_sys/host_cluster_20261017/qkd_hr_cluster.v'
CENSUS_YS = ROOT / 'results/arch/qwen_split_1014/host_root_cluster/census/elab.ys'
PORTS = ROOT / 'results/arch/qwen_split_1014/host_root_cluster/root_ports.json'


def sources():
    toks = ' '.join(CENSUS_YS.read_text().splitlines()[:2]).split()
    files = [t[len('src/'):] for t in toks if t.startswith('src/') and not t.endswith('_bb.v')]
    srams = sorted(str(p.relative_to(ROOT)) for p in ROOT.glob('physical/asap7_memory_macros/ot_sram_*/ot_sram_*.v')
                   if not p.name.endswith('_bb.v'))
    return srams + files


def run(cmd, log, cwd):
    with open(log, 'w') as f:
        r = subprocess.run(cmd, cwd=cwd, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        sys.exit(f'CLUSTER_GATE ERROR {Path(log).name} rc={r.returncode}: ' + Path(log).read_text()[-1500:])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['exact', 'mutant'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--child', default='core_queue')
    ap.add_argument('--cycles', type=int, default=20000)
    ap.add_argument('--verilator', default=str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
    a = ap.parse_args()
    out = Path(a.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    txt = CLUSTER.read_text()
    if a.mode == 'mutant':
        m = re.search(r'\n  qkd_hr_' + a.child + r' u_' + a.child + r' \((.*?)\);', txt, re.S)
        mod = re.search(r'\nmodule qkd_hr_' + a.child + r'\(.*?\nendmodule', txt, re.S).group(0)
        sig = 'host_rst_n' if re.search(r'^\s*input\s+host_rst_n\s*;', mod, re.M) else 'por_n'
        if not m or f'.{sig}({sig})' not in m.group(1):
            sys.exit(f'CLUSTER_GATE ERROR no u_{a.child} {sig} input binding')
        body = m.group(0).replace(f'.{sig}({sig})', f'.{sig}(!{sig})')
        print(f'mutant: u_{a.child}.{sig} inverted at the parent')
        txt = txt.replace(m.group(0), body)
    (out / 'qkd_hr_cluster_dut.v').write_text(txt)
    subprocess.run([sys.executable, str(HERE / 'gen_tb.py'), str(PORTS), str(out / 'tb.cpp')], check=True)
    V = a.verilator
    common = ['--cc', '-O2', '--x-assign', '0', '--x-initial', '0', '-Wno-fatal', '-Wno-lint', '-Wno-style',
              '-Wno-MULTIDRIVEN', '-Wno-UNOPTFLAT', '--no-timing', '-I' + str(ROOT / 'rtl'), '-CFLAGS', '-O1', '-j', '0']
    src = [str(ROOT / s) for s in sources()]
    p1 = subprocess.Popen([V] + common + ['--prefix', 'Vflat', '--top-module', 'qkd_host_root_admission',
                                          '-GENABLE_SERVICE=1', '-GENABLE_NATIVE=1', '-GENABLE_TOKEN=1', '-GNL=2',
                                          '-Mdir', str(out / 'obj_flat')] + src,
                          stdout=open(out / 'vl_flat.log', 'w'), stderr=subprocess.STDOUT)
    p2 = subprocess.Popen([V] + common + ['--prefix', 'Vclu', '--top-module', 'qkd_hr_cluster', '-Mdir',
                                          str(out / 'obj_clu')] + src + [str(out / 'qkd_hr_cluster_dut.v')],
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
    tag = f'{a.mode}' + (f' child={a.child}' if a.mode == 'mutant' else '')
    print(f'CLUSTER_GATE {"PASS" if ok == 6 else "FAIL"} {tag} runs_pass={ok}/6 core_cycles={a.cycles}')
    shutil.rmtree(out / 'obj_flat', ignore_errors=True)
    shutil.rmtree(out / 'obj_clu', ignore_errors=True)


if __name__ == '__main__':
    main()
