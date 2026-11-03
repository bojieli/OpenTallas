"""Source-active programme clock/reset entry and actual native sink inventory.

This is a disabled geometry/source map, never a built clock/reset certificate.
The separate structured internal-clock model and normal native timing remain
required before physical release.
"""
import argparse
import csv
import json
from collections import Counter
from pathlib import Path


def intersects(a,b):return a[0]<b[2]-1e-8 and b[0]<a[2]-1e-8 and a[1]<b[3]-1e-8 and b[1]<a[3]-1e-8
def plain(s):return s.replace('\\[','[').replace('\\]',']')


def main():
    p=argparse.ArgumentParser();p.add_argument('candidate',type=Path);p.add_argument('--graph',type=Path,required=True)
    a=p.parse_args();d=a.candidate;m=json.loads((d/'model.json').read_text());pins=json.loads((d/'native_pins.json').read_text())
    W,H=m['outline_um'];byname={x['name']:x for x in pins};old={k:dict(byname[k])for k in ('clk','rst_n')}
    # Nearest open vertical street to the geometric centre; M5 x tracks .024/.048.
    # Each full .048 x .48 native shape stays in the canonical macro+4.32 corridor.
    declared={'clk':(350.136,401.76),'rst_n':(350.328,401.76)}
    island=[345.816,397.44,354.456,406.08];macros=m['macros']
    body_halos=[[x-4.32,y-4.32,X+4.32,Y+4.32]for x,y,X,Y in [q['rect_um']for q in macros]]
    assert not any(intersects(island,b)for b in body_halos)
    rows={r['cell']:r for r in csv.DictReader((d/'actual_FF_rows.csv').open())}
    overlap=[]
    for r in rows.values():
        x,y=float(r['x_um']),float(r['y_um'])
        if intersects(island,[x-.54,y-.135,x+.54,y+.135]):overlap.append(r['cell'])
    assert not overlap,overlap[:10]
    pg=[]
    for k in range(200):
        for x in (2.064+4.32*k,2.064+.12+.072+4.32*k):
            if x<=W:pg.append([x-.06,0,x+.06,H])
    shape_checks={}
    for name,(x,y)in declared.items():
        assert abs((x-.024)/.048-round((x-.024)/.048))<1e-7
        shape=[x-.024,y-.24,x+.024,y+.24]
        assert 0<=shape[0]and shape[2]<=W and 0<=shape[1]and shape[3]<=H
        assert not any(intersects(shape,b)for b in body_halos)
        # Generated PDN M5 stripes: .12 width, .072 minimum signal clearance.
        assert not any(intersects([shape[0]-.072,shape[1]-.072,shape[2]+.072,shape[3]+.072],b)for b in pg)
        byname[name].update(x=x,y=y,layer='M5',face='I',w=.048,h=.48)
        shape_checks[name]=dict(rect_um=shape,macro_halo_um=4.32,pg_spacing_guard_um=.072,
             source_role='Actual scalar source clock'if name=='clk'else'Actual delivered programme reset input; no reset/START alias')
    cells={};bterms={}
    for q in csv.DictReader(a.graph.open(),delimiter='\t'):
        if q['kind']=='BTERM':bterms[q['owner']]=q;continue
        cells.setdefault(q['owner'],[]).append(q)
    sinkmap=[];counts=Counter()
    for owner,pp in sorted(cells.items()):
        for q in pp:
            if q['signal']!='CLOCK' or q['io']!='INPUT':continue
            assert q['net']==bterms['clk']['net']=='clk'
            typ='SRAM'if q['mastertype']=='BLOCK'else'FF'
            assert (typ,q['master'],q['pin'])in [('FF','DFFHQNx1_ASAP7_75t_R','CLK'),('SRAM','ot_sram_1r1w_512x256_m1_r2c2','clk')]
            counts[typ]+=1;name=plain(owner)
            sinkmap.append(dict(instance=name,pin=q['pin'],master=q['master'],kind=typ,source_clock_port='clk',actual_net=q['net']))
    assert counts=={'FF':20842,'SRAM':44}
    (d/'native_pins_clock_entry.json').write_text(json.dumps(pins,separators=(',',':'))+'\n')
    (d/'source_clock_sink_map.json').write_text(json.dumps(sinkmap,separators=(',',':'))+'\n')
    out=dict(status='DISABLED_SOURCE_ACTIVE_NATIVE_ENTRY_PREP',outline_um=[W,H],geometric_centre_um=[W/2,H/2],
       entry_island_um=island,old_declared_points=old,declared_points=declared,full_shapes=shape_checks,
       row_intersections=0,macro_halo_intersections=0,PG_M5_intersections=0,sink_counts=dict(counts),
       common_clock_contract_ps=dict(TT=250,FF=202.5,setup_uncertainty=0,hold_uncertainty=25,
                                    cross_boundary_hold_uncertainty_each=12.5),
       source_reset='Actual r10 rst_n→rs1→rs2→ra_top/ra_leaf; no SRAM reset. Source reset is distinct from collar and B113 parent identities.',
       source_proof='Exact actual0525 post-SYNTH54439 EQ, fresh official native4 conditional reset only; not physical phase66',
       held=['Separate structured internal-clock tree/model required','No CTS/PLACE/STA dispatch or parent adoption','Actual reset/START delivery and native I/O timing remain open'])
    (d/'clock_entry_gate.json').write_text(json.dumps(out,indent=2)+'\n')
    print(out['status'],dict(counts),'full-shape/row/macro/PG geometry clear',flush=True)


if __name__=='__main__':main()
