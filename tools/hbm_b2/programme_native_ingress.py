"""Read-only actual ODB graph: ABI input to FIRST sequential/native boundary.

Graph traversal follows the StoreA native census helper31d701040, conservatively
crossing combinational cells only. Sequential cells always stop traversal.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--graph',type=Path,required=True)
    ap.add_argument('--ff-rows',type=Path,required=True);ap.add_argument('--pins',type=Path,required=True)
    ap.add_argument('--std-lef',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    cells={};bterms={};loads=defaultdict(list)
    for x in csv.DictReader(a.graph.open(),delimiter='\t'):
        if x['kind']=='BTERM':bterms[x['owner']]=x;continue
        c=cells.setdefault(x['owner'],dict(master=x['master'],mastertype=x['mastertype'],pins=[]))
        c['pins'].append((x['pin'],x['io'],x['signal'],x['net']))
    for name,c in cells.items():
        c['kind']='macro' if c['mastertype']=='BLOCK' else 'ff' if any(s=='CLOCK' and io=='INPUT' for p,io,s,n in c['pins']) else 'comb'
        for pin,io,sig,net in c['pins']:
            if net and io=='INPUT':loads[net].append((name,pin,sig))
    clock_nets={n for c in cells.values() for p,io,s,n in c['pins'] if io=='INPUT' and s=='CLOCK'}
    clock_ports={n for n,b in bterms.items() if b['io']=='INPUT' and b['net'] in clock_nets}
    assert clock_ports=={'clk'},clock_ports
    def frontier(net):
        todo=[net];seen=set();combs=set();ends=set()
        while todo:
            n=todo.pop()
            if n in seen:continue
            seen.add(n)
            for owner,pin,sig in loads.get(n,[]):
                c=cells[owner]
                if c['kind']=='comb':
                    if owner in combs:continue
                    combs.add(owner)
                    todo.extend(z for p,io,s,z in c['pins'] if z and io=='OUTPUT' and s!='CLOCK')
                elif sig!='CLOCK':
                    # Include D and asynchronous/enable control pins, but never
                    # traverse any FF, even one not accepted as a data sink.
                    ends.add((c['kind'],owner,pin))
        return sorted(ends),len(combs)
    ffrows={x['cell']:x for x in csv.DictReader(a.ff_rows.open())}
    assert len(ffrows)==21930
    # OpenDB escapes literal bus brackets inside instance names. Decode only
    # that textual spelling and require a total bijection, never a name alias.
    row_names={n:n.replace('\\[','[').replace('\\]',']') for n,c in cells.items() if c['kind']=='ff'}
    assert len(row_names)==len(set(row_names.values()))==20842
    assert set(row_names.values())<=set(ffrows),'ODB/mapped FF names differ beyond literal bracket escaping'
    assert all(cells[n]['master']==ffrows[v]['master'] for n,v in row_names.items())
    absent_rows=sorted(set(ffrows)-set(row_names.values()))
    assert len(absent_rows)==1088
    pins={p['name']:p for p in json.loads(a.pins.read_text())}
    std=a.std_lef.read_text();masters={}
    for master in {c['master'] for c in cells.values() if c['kind']=='ff'}:
        mm=re.search(r'\bMACRO\s+'+re.escape(master)+r'\s*\n(.*?)\nEND\s+'+re.escape(master)+r'\s*\n',std,re.S);assert mm,master
        w,h=map(float,re.search(r'SIZE\s+([\d.]+)\s+BY\s+([\d.]+)',mm[1]).groups())
        pinblocks={}
        for pp in re.finditer(r'\bPIN\s+(\S+)\s*\n(.*?)\n\s*END\s+\1\s*\n',mm[1],re.S):
            rects=[list(map(float,z)) for z in re.findall(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s*;',pp[2])]
            if rects:pinblocks[pp[1]]=rects
        masters[master]=dict(w=w,h=h,pins=pinblocks)
    def boxes(owner,pin):
        rr=ffrows[row_names[owner]];c=cells[owner];m=masters[c['master']]
        x,y=float(rr['x_um'])-m['w']/2,float(rr['y_um'])-m['h']/2
        # Row candidate centres are conservative footprints, not an actual
        # orientated native view. R0/MX union is optimistic; FAIL stays real.
        rects=m['pins'][pin]
        return [[x+u,y+v,x+U,y+V] for u,v,U,V in rects]+[[x+u,y+m['h']-V,x+U,y+m['h']-v] for u,v,U,V in rects]
    def distance(point,rect):
        x,y=point;u,v,U,V=rect
        return max(u-x,0,x-U)+max(v-y,0,y-V)
    rows=[];fields=defaultdict(list)
    for name,b in sorted(bterms.items()):
        if b['io']!='INPUT' or name in clock_ports:continue
        assert name in pins,name
        pp=pins[name];point=[pp['x'],pp['y']];ends,count=frontier(b['net']);details=[]
        for kind,owner,pin in ends:
            q=dict(kind=kind,owner=owner,pin=pin)
            if kind=='ff':
                assert owner in row_names,owner
                q['mapped_row_cell_name']=row_names[owner]
                q['native_pin_rects_R0_MX_um']=boxes(owner,pin)
                q['optimistic_native_pin_distance_um']=min(distance(point,z) for z in q['native_pin_rects_R0_MX_um'])
                q['candidate_FF_centre_um']=[float(ffrows[row_names[owner]]['x_um']),float(ffrows[row_names[owner]]['y_um'])]
            details.append(q)
        worst=max((d.get('optimistic_native_pin_distance_um',0) for d in details),default=0)
        q=dict(port=name,actual_net=b['net'],planned_GEN_input_pin_um=point,first_sequential_sinks=details,
               combinational_cells_visited=count,max_optimistic_input_to_first_FF_pin_um=worst,
               exceeds405=worst>405+1e-8,has_direct_native_macro=any(d['kind']=='macro' for d in details))
        rows.append(q);fields[name.split('[')[0]].append(q)
    assert len(rows)==621,len(rows)
    summary={n:dict(bits=len(rr),bits_exceed405=sum(q['exceeds405'] for q in rr),
        max_optimistic_first_FF_pin_um=max(q['max_optimistic_input_to_first_FF_pin_um'] for q in rr),
        unique_first_FF=len({d['owner'] for q in rr for d in q['first_sequential_sinks'] if d['kind']=='ff'}),
        direct_macro_bits=sum(q['has_direct_native_macro'] for q in rr)) for n,rr in fields.items()}
    out=dict(status='FAIL_PROPOSED_INPUT_FIRST_CAPTURE_LOCALITY' if any(q['exceeds405'] for q in rows) else 'NECESSARY_FIRST_CAPTURE_GEOMETRY_ONLY',
        source='Actual0525 saved1_synth.odb graph; no CAD mutation',clock_ports=sorted(clock_ports),
        actual_inventory=dict(std_cells=sum(c['kind']!='macro' for c in cells.values()),
        FF=sum(c['kind']=='ff' for c in cells.values()),SRAM=sum(c['kind']=='macro' for c in cells.values()),ABI=len(bterms)),
        raw_nonclock_input_bits=len(rows),bits_exceed405=sum(q['exceeds405'] for q in rows),
        FF_name_encoding_join=dict(actual_ODB_to_row_subset_bijective=20842,unknown=0,collisions=0,
                                   rule='Only literal OpenDB bracket escaping removed; exact master/name match required'),
        reserved_row_FF_absent_from_post_SYNTH_ODB=dict(count=1088,names=absent_rows,
              source_EQ_scope='Normal1_2_yosys proof only; post-SYNTH/physical equivalence not inferred'),
        fields=summary,rows=rows,FF_native_pin_masters=masters,
        scope='First sequential sinks only; no transitive FF traversal. Structural combinational reach is conservative, not Boolean sensitization or STA.',
        optimism=['R0/MX native FF pin rectangles may choose either orientation independently','Planned GEN input pins and disabled FF-row sites are not an actual native physical view'],
        holds=['No PLACE/CTS/route/STA or currentparent/source adoption','Direct macro terminals need separate real LEF geometry if present','Actual collar/transport producer placement and clock/reset/START delivery remain unqualified'])
    (a.out/'ingress_first_capture.json').write_text(json.dumps(out,indent=2)+'\n')
    print(out['status'],out['actual_inventory'],'bad',out['bits_exceed405'],'of',len(rows),flush=True)
    for name,q in summary.items():print(name,q,flush=True)


if __name__=='__main__':main()
