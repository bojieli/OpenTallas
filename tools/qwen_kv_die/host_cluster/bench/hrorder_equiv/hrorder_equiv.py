#!/usr/bin/env python3
"""HRORDER 10-18 equivalence bench (run from the repo root): the restructured qkd_host_ingest_map, qkd_host_commit_order,
qkd_host_commit_order_debt and qkd_host_boot_dispatch_debt in lock-step against verbatim copies of their previous forms
(ref/*_ref.sv), Verilator --binary, 3 seeds.

  hrorder_equiv.py exact  --out DIR            # expect: HRORDER_EQUIV PASS exact runs_pass=3/3
  hrorder_equiv.py mutant --out DIR --m NAME   # expect: HRORDER_EQUIV FAIL mutant NAME (a bypass of the new head registers dropped)
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HERE = Path(__file__).resolve().parent
RTL = ROOT / 'rtl/qwen_sys/host_20261013'
DUT = ['qkd_host_ingest_map.sv', 'qkd_host_commit_order.sv', 'qkd_host_commit_order_debt.sv', 'qkd_host_boot_dispatch_debt.sv']
REF = [HERE / 'ref' / f.replace('.sv', '_ref.sv') for f in DUT]
TB = HERE / 'tb_hrorder_equiv.sv'
# mutant name -> (file, old text, new text): each drops one write-bypass / advance term of a new head register
MUTANTS = {
    'map_hold_bypass': ('qkd_host_ingest_map.sv', 'else hd<=(wr&&wp==rp)?iq_dec[8:0]:q[rp][8:0];', 'else hd<=q[rp][8:0];'),
    'map_adv_bypass': ('qkd_host_ingest_map.sv', 'if(adv)hd<=(wr&&wp==rp1)?iq_dec[8:0]:q[rp1][8:0];', 'if(adv)hd<=q[rp1][8:0];'),
    'order_hold_bypass': ('qkd_host_commit_order.sv', 'head_hold=(v3&&fw==fr)?s3:front[fr];', 'head_hold=front[fr];'),
    'order_adv_bypass': ('qkd_host_commit_order.sv', 'head_adv=(v3&&fw==fr1)?s3:front[fr1]', 'head_adv=front[fr1]'),
    'disp_hold_bypass': ('qkd_host_boot_dispatch_debt.sv', 'else hd<=(wr&&wp==rp)?id_dec:qd[rp];', 'else hd<=qd[rp];'),
    'disp_order_adv': ('qkd_host_commit_order_debt.sv', 'head_adv=(v3&&fw==fr1)?s3:front[fr1]', 'head_adv=front[fr]'),
}
SEEDS = [1, 2, 3]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['exact', 'mutant'])
    ap.add_argument('--out', required=True)
    ap.add_argument('--sram', action='store_true')
    ap.add_argument('--sram-mut',type=int,default=0)
    ap.add_argument('--m', choices=sorted(MUTANTS))
    ap.add_argument('--cycles', type=int, default=200000)
    ap.add_argument('--verilator', default=str(Path.home() / '.local/opentallas-tools/verilator-5.050/bin/verilator'))
    a = ap.parse_args()
    out = Path(a.out).resolve()
    (out / 'src').mkdir(parents=True, exist_ok=True)
    srcs = []
    for f in DUT:
        t = (RTL / f).read_text()
        if a.mode == 'mutant' and MUTANTS[a.m][0] == f:
            old, new = MUTANTS[a.m][1:]
            if t.count(old) != 1:
                sys.exit(f'HRORDER_EQUIV ERROR mutant {a.m}: anchor not found once in {f}')
            t = t.replace(old, new)
        (out / 'src' / f).write_text(t)
        srcs.append(str(out / 'src' / f))
    srcs += [str(p) for p in REF] + [str(TB)]
    if a.sram:
        srcs += [str(ROOT/'rtl/qwen_sys/host_20261013/qkd_host_boot_fifo8_sram.sv'),str(ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1_p192/ot_sram_1r1w_32x128_m1_p192.v')]
    ver = subprocess.run([a.verilator, '--version'], capture_output=True, text=True).stdout.strip()
    print('HRORDER_EQUIV verilator', ver, flush=True)
    cmd = [a.verilator, '--binary', '--timing', '-O2', '--x-assign', '0', '--x-initial', '0', '-Wno-fatal', '-Wno-lint',
           '-Wno-style', '-j', '4', '--top-module', 'tb_hrorder_equiv', '-Mdir', str(out / 'obj'), '-o', 'tb'] + (['-DOT_HOST_BOOT_FIFO_DEFAULT=1',f'-DOT_HOST_BOOT_FIFO_MUT={a.sram_mut}'] if a.sram else []) + srcs
    with open(out / 'vl.log', 'w') as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    if r.returncode:
        sys.exit('HRORDER_EQUIV ERROR verilator:\n' + (out / 'vl.log').read_text()[-3000:])
    npass = 0
    for s in SEEDS:
        r = subprocess.run([str(out / 'obj' / 'tb'), f'+seed={s}', f'+cycles={a.cycles}'], capture_output=True, text=True)
        txt = r.stdout + r.stderr
        print(txt.strip(), flush=True)
        m = re.search(r'HRORDER_EQUIV (PASS|FAIL) seed=\d+ cycles=(\d+) mismatches=\d+ map_emits=(\d+) order_pops=(\d+) '
                      r'disp_sends=(\d+) disp_pops=(\d+)', txt)
        # a PASS must have exercised every unit (no vacuous lock-step)
        if m and m.group(1) == 'PASS' and min(int(x) for x in m.group(3, 4, 5, 6)) > 1000:
            npass += 1
    tag = 'exact' if a.mode == 'exact' else f'mutant {a.m}'
    if npass == len(SEEDS):
        print(f'HRORDER_EQUIV PASS {tag} runs_pass={npass}/{len(SEEDS)}')
    else:
        print(f'HRORDER_EQUIV FAIL {tag} runs_pass={npass}/{len(SEEDS)}')
        sys.exit(1)


if __name__ == '__main__':
    main()
