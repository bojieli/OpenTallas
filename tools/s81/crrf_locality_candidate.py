#!/usr/bin/env python3
"""Generate an UNADOPTED C0 Y-output pin-order candidate, no RTL changes.

N pins remain fixed to the actual y-slice homes. S Y-data pins retain exactly
all existing coordinates/tracks while their logical names follow N x order.
The downstream chain peer MUST be rebound before adoption; it is not supplied
by this local model. No clock, epoch, width, register or arithmetic is changed.
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import sys
R=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(R/'tools/s81_suhc'))
sys.path.insert(0,str(R/'tools/hier_contract'))
import crr_pinplan as P
import pin_align as PA


def remap(pins):
    top={int(n[4:-1]):x for face,n,layer,x in pins if face=='N' and n.startswith('p_y[')}
    targets=[(face,n,layer,x) for face,n,layer,x in pins if face=='S' and n.startswith('ch_fd[') and int(n[6:-1])>=P.O_D]
    assert len(top)==len(targets)==P.YS==2816
    bitorder=sorted(top,key=lambda i:top[i])
    sites=sorted(targets,key=lambda q:q[3])
    replacement={old[1]:(old[0],f'ch_fd[{P.O_D+i}]',old[2],old[3]) for i,old in zip(bitorder,sites)}
    out=[replacement.get(q[1],q) if q[0]=='S' else q for q in pins]
    assert len(set(q[1] for q in out))==len(out)
    assert {(q[0],q[2],q[3]) for q in pins}=={(q[0],q[2],q[3]) for q in out}
    assert [q for q in pins if q[0]!='S' or q[1] not in replacement]==[q for q in out if q[0]!='S' or q[1] not in replacement]
    return out


def measure(pins):
    pp={n:(face,L,x) for face,n,L,x in pins}
    aa=[pp[f'p_y[{i}]'][2] for i in range(P.YS)]
    bb=[pp[f'ch_fd[{P.O_D+i}]'][2] for i in range(P.YS)]
    order=sorted(range(P.YS),key=lambda i:aa[i])
    inv=PA.inversions([bb[i] for i in order])
    return dict(bits=P.YS,opposite_order_bit_pairs=inv,
                max_horizontal_offset_um=max(abs(a-b) for a,b in zip(aa,bb)),
                sum_horizontal_bit_um=sum(abs(a-b) for a,b in zip(aa,bb)),
                total_direct_manhattan_bit_um=P.YS*P.HF+sum(abs(a-b) for a,b in zip(aa,bb)))


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    before,h=P.plans(True)['crrf'];after=remap(before);east,_=P.plans(False)['crrf']
    checks=P.check(after,h,'C0 locality candidate');b=measure(before);n=measure(after)
    a.out.mkdir(parents=True,exist_ok=True)
    candidate=a.out/'crrf_w_y_order_candidate.tcl'
    candidate.write_text(P.emit(after,h,'UNADOPTED C0 Y-order locality candidate; downstream peer-rebind REQUIRED'))
    oldmap={q[1]:q for q in before};newmap={q[1]:q for q in after}
    with (a.out/'y_peer_rebind.csv').open('w') as f:
        w=csv.writer(f);w.writerow(['logical_y_bit','output_port','old_layer','old_x_um','old_y_um','new_layer','new_x_um','new_y_um','input_port','input_layer','input_x_um','input_y_um'])
        for i in range(P.YS):
            port=f'ch_fd[{P.O_D+i}]';old=oldmap[port];new=newmap[port];inp=oldmap[f'p_y[{i}]']
            w.writerow([i,port,old[2],old[3],0.,new[2],new[3],0.,inp[1],inp[2],inp[3],h])
    sources=[R/'tools/s81_suhc/crr_pinplan.py',R/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_crootr.sv',R/'physical/s81_hc_pinplan/crrf_w.tcl',Path(__file__)]
    report=dict(scope='LOCAL_PLANNED_PIN_GEOMETRY_ONLY_NOT_ROUTED',variant='C0 LC11 RF7 v6 276.48x345.6',
                source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
                rtl_mapping='POST p_y[i] -> ydq/yr[i] -> dsel[i] -> ch_fd[104+i]; RF7 unchanged',
                before=b,after=n,closed_east_pin_reference=measure(east),pin_track_checks=checks,
                moved_y_pin_names=sum(x!=y for x,y in zip(before,after)),
                horizontal_bit_um_saved=b['sum_horizontal_bit_um']-n['sum_horizontal_bit_um'],
                unchanged=['all N input pins and actual y-slice home assignment','S metadata/control pins','W/E pins including clocks/reset','exact set of S physical tracks and dimensions','RTL and static latency'],
                required_before_adoption=['Identify actual downstream chain peer and per-bit rebind to these S Y-data pins',
                                         'Check all incident fb/FWD and downstream wire paths, aggregate cuts and native pin reach',
                                         'CTS/placement/routing TT setup FF hold DRC0 on exact source+pin candidate'],
                unknown=['Actual canonical expanded HC downstream peer pins are absent from partial global graph',
                         'Internal register positions are not modeled: opposite-order pairs are geometric pressure, not routed crossing counts'])
    (a.out/'report.json').write_text(json.dumps(report,indent=1)+'\n')
    print(json.dumps(dict(before=b,after=n,horizontal_bit_um_saved=report['horizontal_bit_um_saved'],moved=report['moved_y_pin_names'])))
if __name__=='__main__':main()
