#!/usr/bin/env python3
"""One pinned rank-element executable; runtime distinct ranks, never an array.

Invoke each costly phase through the unchanged fleet admission guard. This
driver does not launch itself, change reservations, or regenerate references.
"""
import argparse
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from hbm_index_path_sources import RTL
from hbm_index_tp96_producer import ROOT, TB, compare, sha, write_json


def build(out):
    out.mkdir(parents=True,exist_ok=False)
    argv=[os.environ.get('VERILATOR','verilator'),'--binary','--timing','-j','16','-O2',
          '--output-split','20000','--output-split-cfuncs','20000','-Wno-fatal',
          '--top-module','tb_hbm_index_connected','-Mdir',str(out/'obj'),
          *[str(ROOT/p) for p in RTL+[TB]]]
    write_json(out/'build_argv.json',argv)
    write_json(out/'source.json',dict(source_pins={p:sha(ROOT/p) for p in RTL+[TB]}))
    with (out/'build.log').open('x') as f:
        rc=subprocess.call(argv,stdout=f,stderr=subprocess.STDOUT)
    (out/'build.exit').write_text(str(rc)+'\n')
    return rc


def run_rank(rank,build_dir,inputs,original,native,out,negative=False):
    source=json.loads((build_dir/'source.json').read_text())
    if any(source['source_pins'].get(p)!=sha(ROOT/p) for p in RTL+[TB]):
        raise ValueError('built source pins changed')
    directory=inputs/f'rank{rank:02d}'
    if json.loads((directory/'inputs.json').read_text())['rank']!=rank:
        raise ValueError('actual fixture rank differs')
    out.mkdir(parents=True,exist_ok=False)
    scores=directory/'scores.mem'
    if negative:
        # Independent comparator control: corrupt one reference, no DUT operand.
        lines=scores.read_text().splitlines();lines[0]=f'{int(lines[0],16)^1:04x}'
        scores=out/'negative_scores.mem';scores.write_text('\n'.join(lines)+'\n')
    executable=build_dir/'obj/Vtb_hbm_index_connected'
    source.update(executable_sha256=sha(executable),rank=rank,
        inputs={str(p):sha(p) for p in (directory/'keys.mem',directory/'scores.mem',
                directory/'inputs.json',original,native)},negative_reference=negative)
    write_json(out/'source.json',source)
    argv=[str(executable),f'+RANK={rank}',f'+ORIGINAL={original}',f'+NATIVE={native}',
          f'+KEYS={directory/"keys.mem"}',f'+SCORES={scores}']
    write_json(out/'runtime_argv.json',argv)
    with (out/'runtime.log').open('x') as f:
        rc=subprocess.call(argv,cwd=out,stdout=f,stderr=subprocess.STDOUT)
    (out/'runtime.exit').write_text(str(rc)+'\n')
    if negative:
        passed=rc!=0 and 'actual score mismatch' in (out/'runtime.log').read_text()
        write_json(out/'negative.json',dict(expected_failure_caught=passed,returncode=rc,
            DUT_operands_changed=False,reference_bit_changed=0))
        return 0 if passed else 1
    if rc:return rc
    try:result=compare(out,directory)[1]
    except Exception as e:
        (out/'comparison_failure.txt').write_text(str(e)+'\n');return 1
    write_json(out/'comparison.json',result)
    return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    a=sub.add_parser('build');a.add_argument('--out',type=Path,required=True)
    a=sub.add_parser('run')
    for n in ('build','inputs','original','native','out'):a.add_argument('--'+n,type=Path,required=True)
    a.add_argument('--ranks',type=int,nargs='+',required=True)
    a.add_argument('--workers',type=int,default=1);a.add_argument('--negative',action='store_true')
    a=p.parse_args()
    if a.mode=='build':return build(a.out.resolve())
    if not 1<=a.workers<=16 or len(set(a.ranks))!=len(a.ranks) or any(not 1<=r<96 for r in a.ranks):
        raise ValueError('distinct nonzero TP96 ranks, 1..16 workers; reuse rank0 PASS')
    a.out.mkdir(parents=True,exist_ok=False)
    with ThreadPoolExecutor(a.workers) as pool:
        rc=list(pool.map(lambda r:run_rank(r,a.build.resolve(),a.inputs.resolve(),
            a.original.resolve(),a.native.resolve(),a.out/f'rank{r:02d}',a.negative),a.ranks))
    write_json(a.out/'runtime_results.json',dict(ranks=a.ranks,returncodes=rc))
    return 0 if all(r==0 for r in rc) else 1


if __name__=='__main__':raise SystemExit(main())
