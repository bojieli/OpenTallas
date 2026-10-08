#!/usr/bin/env python3
"""Compare requested VM8 pins with legacy range and exact rectangle generation."""
import argparse
import hashlib
import json
from pathlib import Path
import hbm_accel_die_fp as H


def audit(contract_path):
    p=Path(contract_path);contract=json.loads(p.read_text());variants={}
    for mode,variant in [('historical_range',dict(H.R24SM3,vm_split8=True)),('candidate_exact',H.R24SM3V)]:
        m=H.build(variant,network_probe=True);masters=H.masters(m);widths=H.port_widths(m,1);records={}
        for name,c in contract['masters'].items():
            master=masters[name]
            rects=H.S.pin_rects(master,1,{port:widths.get((name,port),0) for port in master.order})
            actual={pn:(ly,(r[0]+r[2])/2,(r[1]+r[3])/2,r[2]-r[0],r[3]-r[1]) for pn,ly,r in rects}
            failures=[]
            for pin,want in c['pins'].items():
                got=actual.get(pin)
                if got is None or want[0]!=got[0] or any(abs(a-b)>1e-6 for a,b in zip(want[1:],got[1:])):
                    failures.append(dict(pin=pin,requested=want,generated=got))
            extra=sorted(set(actual)-set(c['pins']))
            records[name]=dict(requested=len(c['pins']),generated=len(actual),mismatches=len(failures),extra_pins=extra,examples=failures[:5])
        variants[mode]=records
    sources=[Path(__file__),Path(H.__file__),Path(H.S.__file__),p]
    sources += sorted((H.ROOT/H.VM8_DIR).glob('*/io_place.tcl'))
    return dict(scope='requested io_place pin rectangles vs emitted abstract; actual routed BPin readback remains required',
        selected=False,variants=variants,source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--contract',required=True);ap.add_argument('--out',required=True)
    a=ap.parse_args();r=audit(a.contract);p=Path(a.out);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:sum(v['mismatches'] for v in rows.values()) for k,rows in r['variants'].items()}))
