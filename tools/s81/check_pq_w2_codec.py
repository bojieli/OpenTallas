#!/usr/bin/env python3
"""Minimum full-width W2 codec proof and validity/fault negative controls."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RTL='rtl/dsrom_sys/s81_pq_parent/ot_s81_pq_union_lane.sv'
TB='tests/rtl/s81_pq_parent/union_lane_tb.sv'
MODEL='results/uarch/dsrom_s81_pq_w2_codec_20261007/model.json'


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    cases=[('positive',None,None,'PASS W2 6000 packets'),
           ('wrong_q_bit','rtl',('lane_rx[290:35]','lane_rx[289:34]'),'Q payload mismatch'),
           ('no_tx_family_guard','rtl',('(qv && bv) ||',"1'b0 ||"),'both-valid input was not rejected'),
           ('consumer_ignores_valid','tb',('if(qv &&',"if(1'b1 &&"),'Q payload mismatch'),
           ('not_default_off','rtl',('parameter integer ENABLE = 0','parameter integer ENABLE = 1'),'default bypass changed native data')]
    results=[]
    for name,target,change,marker in cases:
        rtl=(ROOT/RTL).read_text();tb=(ROOT/TB).read_text()
        if target=='rtl':
            assert change[0]in rtl;rtl=rtl.replace(*change)
        if target=='tb':
            assert change[0]in tb;tb=tb.replace(*change)
        rpath=a.out/(name+'.sv');tpath=a.out/(name+'_tb.sv')
        rpath.write_text(rtl);tpath.write_text(tb);exe=a.out/(name+'.vvp')
        c=subprocess.run(['iverilog','-g2012','-s','union_lane_tb','-o',str(exe),str(rpath),str(tpath)],capture_output=True,text=True)
        (a.out/(name+'.compile.log')).write_text(c.stdout+c.stderr)
        if c.returncode:raise RuntimeError('Compilation failure is not a negative proof')
        r=subprocess.run(['vvp',str(exe)],capture_output=True,text=True)
        (a.out/(name+'.log')).write_text(r.stdout+r.stderr)
        good=(r.returncode==0 if name=='positive'else r.returncode!=0)and marker in r.stdout
        results.append(dict(case=name,exit_code=r.returncode,PASS=good,
            scope='intentional invalid-payload consumer'if target=='tb'else 'codec'))
    record=dict(schema='opentallas.s81.pq-w2-codec-proof.v1',results=results,
        source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest()for p in [RTL,TB,MODEL,'tools/s81/check_pq_w2_codec.py']},
        positive_packets=6000,Q_packets=2000,BF_packets=2000,idle_packets=2000,
        exact_scope='All fixed fields and active family payload; source-native duplicate b/pos preserved. Inactive payload intentionally unspecified.',
        real_element_inactive_payload_proof=False,full_field_exactness=False,physical_adopted=False)
    (a.out/'record.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(results));return 0 if all(r['PASS']for r in results)else 1


if __name__=='__main__':raise SystemExit(main())
