#!/usr/bin/env python3
"""Prepare exact opaque-leaf native HC elaboration from real interface signatures.

The fragment does not invent a whole-field assembly, external producer, timing
arc, register or pin. It preserves the fourteen real leaf names and source wires.
"""
import argparse
import collections
import hashlib
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/hier_contract'))
import pinreg_audit as A


def prepare(plan_path, out):
    plan=json.loads(plan_path.read_text());out.mkdir(parents=True,exist_ok=True)
    records={};texts=[]
    for leaf in plan['instances']:
        cell=leaf['cell']
        if cell in records:continue
        if cell=='ot_s81_hc_ccf':view=ROOT/'results/rtl/s81_suhc_20261013/ccf_pinwindows_e0cae3a4a/ccf_v10_provisional'
        elif cell=='ot_s81_hc_pad_fv4fd5r2':view=ROOT/'results/rtl/s81_suhc_20261013/ccf_pinwindows_e0cae3a4a/r2_sized_driver_v7_provisional'
        else:view=ROOT/leaf['view']
        lib=view/(cell+'_tt.lib');parsed=A.parse_lib(lib)
        assert parsed['cell']==cell
        buses=collections.OrderedDict()
        for name,pin in parsed['pins'].items():
            if pin['dir'] not in ('input','output','inout'):continue
            bus=A.bus_of(name);m=re.search(r'\[(\d+)\]$',name)
            b=buses.setdefault(bus,dict(direction=pin['dir'],indices=[],scalar=m is None))
            assert b['direction']==pin['dir'] and b['scalar']==(m is None)
            if m:b['indices'].append(int(m.group(1)))
        lines=[f'(* blackbox *) module {cell} ({", ".join(buses)});']
        if cell=='ot_s81_hc_cseq':lines+=['parameter integer PIPE=0, PD=40;']
        for bus,b in buses.items():
            if b['scalar']:width='';bits=1
            else:
                idx=sorted(b['indices']);assert idx==list(range(len(idx))), (cell,bus,idx)
                bits=len(idx);width=f'[{bits-1}:0] '
            lines.append(f'{b["direction"]} wire {width}{bus};')
            b['bits']=bits
        lines.append('endmodule');texts.append('\n'.join(lines))
        records[cell]={'actual_interface_lib':str(lib.relative_to(ROOT)),'lib_sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'ports':buses,'scope':'opaque exact physical interface, not new RTL qualification'}
    (out/'leaf_interfaces.sv').write_text('\n\n'.join(texts)+'\n')
    src=ROOT/'rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_pad_split.sv';text=src.read_text();wrappers=[]
    for name in ['ot_s81_hc_cpad_split','ot_s81_hc_ccr_align']:
        matches=re.findall(r'\bmodule\s+'+name+r'\b.*?\bendmodule\b',text,re.S);assert len(matches)==1
        wrappers.append(matches[0])
    (out/'wrappers.sv').write_text('\n\n'.join(wrappers)+'\n')
    parent=ROOT/'rtl/dsrom_sys/s81_suhc/hier/dsfd_sp_hc_comb_native.sv'
    (out/'parent.sv').write_bytes(parent.read_bytes())
    manifest={'schema':'opentallas.s81.native_hc_interface_graph.v1','status':'SOURCE FRAGMENT ONLY; external whole-field producers/clock/reset relations not bound','parent':'dsfd_sp_hc_comb_native','parent_source_sha256':hashlib.sha256(parent.read_bytes()).hexdigest(),'wrapper_source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'tuple':plan['production_params'],'expected_instances':[l['instance'] for l in plan['instances']],'leaf_interfaces':records,'source_plan':str(plan_path),'route_admission':False}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (out/'elaborate.ys').write_text('read_verilog -sv -D SYNTHESIS -D OT_S81_HC_COMB_HARD -D OT_S81_HC_PAD_HARD /diag/leaf_interfaces.sv /diag/wrappers.sv /diag/parent.sv\nhierarchy -check -top dsfd_sp_hc_comb_native\nproc\nflatten\nopt_expr\nopt_clean\nwrite_json /diag/source_graph.json\n')
    print(len(records),'real master interfaces;',len(plan['instances']),'named leaf instances')

# Analysis is deliberately separate from preparation: the file must be emitted
# by a real HDL elaborator under the recorded physical binding macros.
def summarize(graph_path, manifest_path, out):
    graph=json.loads(graph_path.read_text());manifest=json.loads(manifest_path.read_text())
    module=graph['modules'][manifest['parent']]
    cells={n:c for n,c in module['cells'].items() if c['type']!='$scopeinfo'}
    assert set(cells)==set(manifest['expected_instances']), 'actual fourteen leaf names required'
    assert all(c['type'] in manifest['leaf_interfaces'] for c in cells.values()), 'unqualified logic or master'
    sources=collections.defaultdict(list);loads=collections.defaultdict(list);constants=[]
    for port,p in module['ports'].items():
        for index,bit in enumerate(p['bits']):
            assert isinstance(bit,int)
            (sources if p['direction']=='input' else loads)[bit].append(['PARENT',port,index])
    for name,cell in cells.items():
        for port,bits in cell['connections'].items():
            direction=cell['port_directions'][port]
            for index,bit in enumerate(bits):
                if isinstance(bit,int):
                    (sources if direction=='output' else loads)[bit].append([name,port,index])
                else:constants.append({'instance':name,'port':port,'index':index,'value':bit})
    groups=collections.defaultdict(list);issues=[]
    for bit,ends in loads.items():
        drivers=sources.get(bit,[])
        if len(drivers)!=1:
            issues.append({'bit':bit,'drivers':drivers,'loads':ends});continue
        a=drivers[0]
        for b in ends:groups[(a[0],a[1],b[0],b[1])].append([a[2],b[2],bit])
    assert not issues, 'floating or multiple actual data drivers'
    clock_map=[]
    for name,cell in cells.items():
        order=manifest['expected_instances'].index(name)
        assert cell['connections']['sk']==[module['ports']['sk_leaf']['bits'][order]]
        clock_map.append({'instance':name,'child_port':'sk','parent_port':'sk_leaf','parent_index':order})
    assert cells['u_seq']['connections']['cck']==module['ports']['cck']['bits']
    clock_map.append({'instance':'u_seq','child_port':'cck','parent_port':'cck','parent_index':0})
    rows=[{'a':[a,ap],'b':[b,bp],'bits':sorted(v),'scope':'external producer/consumer missing' if 'PARENT' in (a,b) else 'internal actual source join'} for (a,ap,b,bp),v in sorted(groups.items())]
    rec={'schema':'opentallas.s81.native_hc_actual_source_join_graph.v1','status':'OPAQUE ACTUAL SOURCE FRAGMENT; full-field clock/reset/producer binding and routed qualification remain',
         'source_graph_sha256':hashlib.sha256(graph_path.read_bytes()).hexdigest(),
         'parent_source_sha256':manifest['parent_source_sha256'],
         'actual_leaf_instances':len(cells),'parent_ports':len(module['ports']),
         'parent_functional_bits':sum(len(p['bits']) for p in module['ports'].values()),
         'clock_map':clock_map,'constants':constants,'source_driver_issues':issues,
         'joins':rows,'internal_joins':sum(r['scope'].startswith('internal') for r in rows),
         'internal_bits':sum(len(r['bits']) for r in rows if r['scope'].startswith('internal')),
         'external_joins':sum(r['scope'].startswith('external') for r in rows),
         'external_bits':sum(len(r['bits']) for r in rows if r['scope'].startswith('external')),
         'legacy_parent_sk_unused':not loads.get(module['ports']['sk']['bits'][0]),
         'route_admission':False}
    out.write_text(json.dumps(rec,indent=2)+'\n')
    return rec

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path)
    p.add_argument('--graph',type=Path)
    p.add_argument('--manifest',type=Path)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.graph:
        assert a.manifest and not a.plan
        r=summarize(a.graph,a.manifest,a.out)
        print(r['actual_leaf_instances'],'actual leaves;',r['internal_joins'],'internal joins;',r['external_joins'],'external joins')
    else:
        assert a.plan and not a.manifest
        prepare(a.plan,a.out)
