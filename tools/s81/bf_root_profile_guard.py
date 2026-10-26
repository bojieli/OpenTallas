#!/usr/bin/env python3
"""Derive actual supported/unsupported column RTL with SYNTHESIS defined."""
import argparse
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[2]


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--work',type=Path,required=True)
    a=p.parse_args();w=a.work.resolve();w.mkdir(parents=True,exist_ok=True)
    spec=json.loads((ROOT/'physical/ref_tile_specs/s81_bf_native_1015/lane4_boundary_r2/spec.json').read_text())
    sources=[ROOT/s for s in spec['sources']]
    sources += [ROOT/'rtl/v41rom'/n for n in ['ot_v41_bf16_lanes3_roots.sv','ot_v41_bf_col_roots.sv','ot_v41_bf_reduce.sv','ot_v41_bf_fp4_leaves.sv','ot_v41_bf_segment_leaf.sv']]
    wrapper=ROOT/'rtl/dsrom_sys/s81_die_bind/dsfd_bf_col_roots.sv';sources.append(wrapper)
    bad=w/'bad_profile.sv';s=wrapper.read_text()
    assert s.count('.BXST(2)')==1
    bad.write_text(s.replace('module dsfd_bf_col_roots #(','module bad_profile #(').replace('.BXST(2)','.BXST(0)'))
    cmd=['/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator','--lint-only','-DSYNTHESIS','-Wno-fatal','-Wno-lint','-Wno-style','-Wno-TIMESCALEMOD','-Wno-MULTIDRIVEN']
    records={}
    for name,top,extra in [('production','dsfd_bf_col_roots',[]),('unsupported_BXST0','bad_profile',[bad])]:
        r=subprocess.run(cmd+['--top-module',top]+list(map(str,sources+extra)),cwd=ROOT,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (w/(name+'.log')).write_text(r.stdout)
        ok=r.returncode==0 if name=='production' else r.returncode!=0 and 'OT_S81_BF_COLUMN_REQUIRES_PRODUCTION_PROFILE' in r.stdout
        records[name]=dict(returncode=r.returncode,ok=ok)
        if not ok:print(r.stdout);raise SystemExit('ERROR: actual synthesis-profile guard failed')
    (w/'terminal.json').write_text(json.dumps(dict(synthesis_defined=True,actual_column=True,cases=records,pass_=True),indent=2)+'\n')
    print('PASS actual BF production elaborates and BXST0 is refused with SYNTHESIS defined')


if __name__=='__main__':main()
