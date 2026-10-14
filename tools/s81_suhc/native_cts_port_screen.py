#!/usr/bin/env python3
"""Read-only provisional CTS face-arc extraction, never a closed tile view.

Uses the existing ck_insertion corner/clock/parasitic setup verbatim. All output
stays in a diagnostic directory outside published views. Final routed ETMs,
three-corner checks and the actual die pin screen remain mandatory.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/closure_loop'))
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import ck_insertion as CK
import pinreg_audit as A


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--clock',default='ck')
    p.add_argument('--cell',required=True)
    a=p.parse_args();base=a.base.resolve();out=a.out.resolve()
    assert re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',a.cell)
    assert 'views' not in out.parts, 'Diagnostics must not populate published view directories'
    assert out!=base and base not in out.parents, 'Read-only ORFS input; output must be outside its base'
    db=base/'4_1_cts.odb'
    sdc=next((x for x in ('4_cts.sdc','3_place.sdc') if (base/x).exists()),None)
    assert db.exists() and sdc, 'Completed CTS checkpoint and SDC required'
    out.mkdir(parents=True,exist_ok=True)
    rec=dict(schema='opentallas.s81.hc.provisional_cts_port_screen.v1',
             status='PROVISIONAL CTS ONLY; not routed, not qualified, not release evidence',
             base=str(base),db='4_1_cts.odb',sdc=sdc,clock=a.clock,
             parasitics='placement-estimated',cell=a.cell,
             input_sha256={x:hashlib.sha256((base/x).read_bytes()).hexdigest() for x in ('4_1_cts.odb',sdc)})
    for corner in ('tt','ff'):
        src,mlibs=CK.macro_libs(base,corner)
        deck=CK.tcl(corner,'4_1_cts.odb',sdc,False,a.clock,mlibs)
        assert deck.endswith('exit\n')
        deck=deck[:-5]+f'write_timing_model -library_name provisional_cts_{a.cell}_{corner} /diag/{a.cell}_{corner}.lib\nexit\n'
        (out/(corner+'.tcl')).write_text(deck)
        cmd=['docker','run','--rm','-v',f'{base}:/base:ro','-v',f'{out}:/diag']
        if src:cmd+=['-v',f'{src}:/src:ro']
        cmd+=['openroad/orfs:latest','bash','-lc',f'/OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /diag/{corner}.tcl']
        run=subprocess.run(cmd,capture_output=True,text=True)
        (out/(corner+'.log')).write_text(run.stdout+run.stderr)
        assert run.returncode==0 and (out/f'{a.cell}_{corner}.lib').exists(), f'{corner}: export failed'
        rows=[(int(x),float(y)) for x,y in re.findall(r'^OT_CK (\d) (\S+)',run.stdout,re.M)]
        assert rows, 'Missing actual clock arrivals'
        rec[corner]={'boundary':CK.stats([y for x,y in rows if x]),'all':CK.stats([y for x,y in rows])}
    # Apply the same insertion reference to each diagnostic pin arc.
    metrics=A.pin_metrics(A.parse_lib(out/f'{a.cell}_tt.lib'),
                          A.clock_refs(A.parse_lib(out/f'{a.cell}_tt.lib'),rec,'tt'))
    ports={}
    for name,m in metrics.items():
        if m['inp'] is None:continue
        ports.setdefault(A.bus_of(name),{})[name]=m['inp']
    rec['capture_ports']={bus:{'bits':len(v),'min_ps':min(v.values()),'max_ps':max(v.values()),
                              'worst_bits':sorted(v,key=v.get,reverse=True)[:8]} for bus,v in ports.items()}
    (out/'provisional_insertion.json').write_text(json.dumps(rec,indent=2)+'\n')
    print(json.dumps(rec['capture_ports'],indent=2))


if __name__=='__main__':main()
