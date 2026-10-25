#!/usr/bin/env python3
"""Adopt owner decision16a on a B2 wiring delta, without altering arithmetic.
Clocks of core logic alias to the die stream clock; only the actual HBM PHY keeps
its internal external-memory clock.  SU requests must not cross a ratio clock.
SU ALAT4 must compile with ot_hdc_fastfp_lat_c12.sv (the f12_l4 standard), never
with the legacy ot_hdc_fastfp_lat.sv (whose LAT4 is lat4i).
"""
import argparse,json,re
from pathlib import Path

def apply(delta):
    delta['source_alias']={
        'hb_ckgen__pll_serial':['hb_ckgen','pll_stream'],
        'hb_ckgen__pll_hbm':['hb_ckgen','pll_stream'],
        'hb_ckgen__por_serial':['hb_ckgen','por_stream'],
        'hb_ckgen__por_hbm':['hb_ckgen','por_stream'],
    }
    delta['source_alias_exempt']=['PHY_.*','phy_.*','hbm_phy_.*']
    # Retire the serial/stream bridge-release FSMs and their now-irrelevant
    # fault inputs. Removing a source also compacts the fault leaf SYNC_MASK;
    # no zero is substituted for a monitored fault bit.
    retired=[]
    for q in ('NW','NE'):
        bridge='subr_'+q;leaf='fr_'+q
        dsrc=delta['rebuild'][leaf]['in'];p=delta['remaster'][leaf]['params']
        mm=re.search(r"\.SYNC_MASK\((\d+)'h([0-9a-fA-F]+)\)",p)
        assert mm,(leaf,p)
        mw,mask=int(mm[1]),int(mm[2],16);new=[];oldpos=0;newpos=0;nmask=0;removed=0
        for e in dsrc:
            w=e[1] if e[0]=='const' else e[3]-e[2]+1
            if e[0]==bridge:
                assert e[1]=='fault' and w==1,e
                removed+=w;oldpos+=w;continue
            nmask|=((mask>>oldpos)&((1<<w)-1))<<newpos
            new.append(e);oldpos+=w;newpos+=w
        assert removed==1,(leaf,dsrc)
        delta['rebuild'][leaf]['in']=new
        p=re.sub(r'\.N\(\d+\)',f'.N({newpos})',p)
        p=re.sub(r"\.SYNC_MASK\(\d+'h[0-9a-fA-F]+\)",f".SYNC_MASK({mw}'h{nmask:x})",p)
        delta['remaster'][leaf]['params']=p
        delta['keep'].setdefault('drop_instances',[]).append(bridge)
        delta['source_alias'][bridge+'__bridge_rst_n']=['hb_ckgen','por_stream']
        retired.append(bridge)
    changed=[]
    for n,r in delta['remaster'].items():
        if re.fullmatch(r'su_N[WE][0-3]',n):
            p=r['params']
            for k,v in [('MULTIRATE',0),('ALAT',4),('MLAT',4),('RSYNC',0)]:
                if re.search(r'\.'+k+r'\(',p):p=re.sub(r'\.'+k+r'\([^()]*\)',f'.{k}({v})',p)
                else:p+=f', .{k}({v})'
            r['params']=p;changed.append(n)
    delta['items'].append(dict(id='R-ONECLOCK',status='bound; physical/token requalification required',
        what='Core serial/HBM clock consumers use the die clock; PHY clocks exempt; SU MULTIRATE0 ALAT4 MLAT4 RSYNC0',
        changed=changed,retired=retired,source_override='rtl/hdc/ot_hdc_fastfp_lat_c12.sv (f12_l4)',
        cycles='ALAT3->4: +1 dependent add cycle at 1.2GHz; FP32 lane model prices operation-specific chains'))
    return delta

def main():
    p=argparse.ArgumentParser();p.add_argument('delta');p.add_argument('--out',required=True);a=p.parse_args()
    d=apply(json.loads(Path(a.delta).read_text()));Path(a.out).write_text(json.dumps(d,indent=1))
    print('NATIVE_CLOCK_BIND',len(d['items'][-1]['changed']),'SU slices')
if __name__=='__main__':main()
