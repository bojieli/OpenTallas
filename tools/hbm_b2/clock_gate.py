#!/usr/bin/env python3
"""Reject fixed-age core paths on mixed ratio clocks. The PHY owns its clock exception."""
import argparse,json,re
from pathlib import Path
import b2_top as T

def check(path):
    die=T.Die(path,[]);bad=[];checked=0
    for n,i in die.insts.items():
        if i['master']=='ot_hbm_su_bridge_release_s':
            bad.append(dict(inst=n,rule='retired serial bridge-release FSM still bound'))
        if n=='hb_ckgen' or i['master'].startswith('ot_hbm3e_phy_'):continue
        for p,e in i['conns'].items():
            if not re.search(r'(^|_)(clk|clock)(_|$)',p):continue
            segs=die.resolve(T.parse_expr(e,die.widths));checked+=1
            if not segs or any(s[0]!='n' or s[1]!='hb_ckgen__pll_stream' or s[2]!=0 or s[3]!=0 for s,_ in segs):
                bad.append(dict(inst=n,port=p,source=e))
        if re.fullmatch(r'su_N[WE][0-3]',n):
            if not re.search(r'\.MULTIRATE\(0\)',i['params']):bad.append(dict(inst=n,rule='MULTIRATE must be 0'))
            if not re.search(r'\.ALAT\(4\)',i['params']):bad.append(dict(inst=n,rule='ALAT must be 4'))
    return dict(verdict='PASS' if not bad else 'FAIL',clock_ports=checked,failures=bad)

def main():
    p=argparse.ArgumentParser();p.add_argument('die');p.add_argument('--out',required=True);a=p.parse_args()
    r=check(a.die);Path(a.out).write_text(json.dumps(r,indent=1));print('B2_CLOCK_GATE',r['verdict'],'ports',r['clock_ports'],'fail',len(r['failures']))
    return int(r['verdict']!='PASS')
if __name__=='__main__':raise SystemExit(main())
