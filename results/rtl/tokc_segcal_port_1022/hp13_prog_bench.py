#!/usr/bin/env python3
"""TOKc-SEGCAL 10-22: run the dv-form compiled-image bench checker (tt_ctlm_prog_bench.py of the TOKEN PASS source
assembly c0f8097f3, the 'head' stage bench) on a different DUT tb, unchanged otherwise.

    hp13_prog_bench.py --bench REF_TREE/rtl/test/qwen_dv/tt_ctlm_prog_bench.py --root ROOT --tb TB.sv --sources F
                       [--trace] [--lockstep] -- <tt_ctlm_prog_bench args: --img --decode --hard --segcal --mut --bmut --work>

  ROOT     source root the sources file is relative to (die form: the materialized HP13 set; dv form: the assembly tree)
  TB       tb module tb_qfd_tt_ctlm_prog (die form: tb_qfd_tt_ctlm_prog_hp13.sv; dv form: the assembly tb + trace patch)
  --trace  +define+TB_TRACE (per-cycle output vector -> WORK/trace.txt); --lockstep  +define+TB_LANDED (die form: hp13 lp)
The checker, stimulus generator and every expectation are the reference bench's own functions (imported, not copied).
"""
import argparse, importlib.util, shutil, sys
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument('--bench', required=True); ap.add_argument('--root', required=True); ap.add_argument('--tb', required=True)
ap.add_argument('--sources', required=True); ap.add_argument('--trace', action='store_true'); ap.add_argument('--lockstep', action='store_true')
a, rest = ap.parse_known_args()
spec = importlib.util.spec_from_file_location('ref_bench', a.bench)
B = importlib.util.module_from_spec(spec); spec.loader.exec_module(B)
rest = [x for x in rest if x != '--']
sys.argv = [a.bench] + rest
# reference bench argument parser (same defaults), then point it at this DUT
bp = argparse.ArgumentParser()
for opt, kw in (('--img', dict(required=True)), ('--mut', dict(type=int, default=0)), ('--bmut', dict(type=int, default=0)),
                ('--hra', dict(type=int, default=0)), ('--decode', dict(type=int, default=2)), ('--hard', dict(type=int, default=0)),
                ('--work', dict(default='/tmp/qlbprog_bench')), ('--landed', dict(type=int, default=0)),
                ('--lmut', dict(type=int, default=0)), ('--defs', dict(nargs='*', default=[])), ('--segcal', dict(type=int, default=1))):
    bp.add_argument(opt, **kw)
ba = bp.parse_args(rest)
ba.defs = list(ba.defs) + (['TB_TRACE'] if a.trace else []) + (['TB_LANDED'] if a.lockstep else [])
if 'hp13' in Path(a.tb).name:   # die-form tb: u_go SEG_CAL / MUT 37 by define (Verilator defparam needs literals)
    ba.defs += (['TB_GO_SEG0'] if ba.segcal == 0 else []) + (['TB_GO_MUT37'] if ba.mut == 37 else [])
work = Path(ba.work).resolve(); here = work / 'bench_here'; here.mkdir(parents=True, exist_ok=True)
shutil.copy(Path(a.tb), here / 'tb_qfd_tt_ctlm_prog.sv')
shutil.copy(Path(a.bench).parent / 'main2.cpp', here / 'main2.cpp')
shutil.copy(Path(a.sources), here / 'tt_ctlm_dv_sources.f')
B.HERE, B.ROOT = here, Path(a.root).resolve()
# the ROM-word decoder reads tools/qwen_split/hr_contract.py: always the reference tree's (the slice contract)
sys.path.insert(0, str(Path(a.bench).resolve().parents[3] / 'tools' / 'qwen_split'))
ok, n, errs, info = B.run(ba)
v = 'PASS' if (ok == n and not errs) else 'FAIL'
print(f'CTLM_PROG MUT={ba.mut} BMUT={ba.bmut} HARD_HR={ba.hard} SEG_CAL={ba.segcal} DECODE={ba.decode} DEFS={ba.defs}: {v} {ok}/{n}  '
      f'rom_go-issue {info.get("rom_go_minus_issue")} nat_go-issue {info.get("nat_go_minus_issue")} csr@{info.get("csr")} '
      f'stage1_xt1 {info.get("stage1_matches_xt1_ops")}')
for e in errs[:12]:
    print('   ', e)
for line in open(sorted(work.glob(f'log_m{ba.mut}_b{ba.bmut}*.txt'), key=lambda p: p.stat().st_mtime)[-1]):
    if 'LANDED_' in line:
        print('   ', line.strip())
