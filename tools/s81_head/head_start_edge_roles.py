#!/usr/bin/env python3
"""Resolve actual START launch/capture FF roles before routed per-edge STA.

Use the original mapped netlist to identify sequential roles. Added ordinary
wire drivers may change connections and names but may not change those FFs.
The actual overlay mapping supplies the routed instance names at extraction.
"""
import argparse,collections,json,re
from pathlib import Path


def is_ff(c):return c['type'].startswith(('DFF','SDFF'))


def census(mapped,physical,stages,top='ot_die_start_stages'):
    m=mapped['modules'][top];cells=m['cells'];nets=m['netnames'];byregion={s['region']:s for s in stages['stages']};byid={s['id']:s for s in stages['stages']}
    drivers=collections.defaultdict(list);loads=collections.defaultdict(list)
    for name,c in cells.items():
        for pin,bits in c['connections'].items():
            for bit in bits:
                (drivers if c['port_directions'][pin]=='output' else loads)[bit].append((name,pin))
    def stageof(name):return physical['cells'][name]['stage']
    def launch(sid):
        k='u_st_'+sid+'.start'
        if k not in nets or len(nets[k]['bits'])!=1:raise ValueError('missing logical stage output '+k)
        todo=[(nets[k]['bits'][0],[])];found=[];seen=set()
        while todo:
            bit,path=todo.pop()
            if bit in seen:continue
            seen.add(bit)
            for name,pin in drivers[bit]:
                c=cells[name]
                if stageof(name)!=sid:raise ValueError('logical stage output has an outside driver')
                if is_ff(c):found.append((name,pin,path));continue
                if not c['type'].startswith(('INV','BUF')):raise ValueError('START output needs reviewed non-buffer combinational polarity '+c['type'])
                ins=[b for p,bs in c['connections'].items() if c['port_directions'][p]=='input' for b in bs]
                if len(ins)!=1:raise ValueError('not a one-input output restoration path')
                todo.append((ins[0],path+[dict(cell=name,master=c['type'])]))
        if len(found)!=1:raise ValueError(f'{sid}: logical START has {len(found)} launch FFs')
        n,p,path=found[0];inv=sum(x['master'].startswith('INV') for x in path)
        return dict(cell=n,pin=p,master=cells[n]['type'],clock_pin='CLK',clock_edge='fall' if cells[n]['type'].startswith('DFFL') else 'rise',
            launch_signal_edge='fall' if inv%2 else 'rise',restoration_path=path)
    def capture(sid):
        k='u_st_'+sid+'.p_start'
        if k not in nets or len(nets[k]['bits'])!=1:raise ValueError('missing logical stage input '+k)
        todo=[(nets[k]['bits'][0],[])];found=[];seen=set()
        while todo:
            bit,path=todo.pop()
            if bit in seen:continue
            seen.add(bit)
            for name,pin in loads[bit]:
                c=cells[name]
                if stageof(name)!=sid or pin=='CLK':continue
                if is_ff(c):
                    if pin!='D':raise ValueError('START enters unsupported FF pin '+pin)
                    found.append((name,pin,path));continue
                for p,bits in c['connections'].items():
                    if c['port_directions'][p]=='output':
                        for b in bits:todo.append((b,path+[dict(cell=name,master=c['type'],input_pin=pin,output_pin=p)]))
        if len(found)!=1:raise ValueError(f'{sid}: START reaches {len(found)} first FFs')
        n,p,path=found[0];c=cells[n];edge='fall' if c['type'].startswith('DFFL') else 'rise'
        if edge!=('fall' if byid[sid]['edge_fall'] else 'rise'):raise ValueError('mapped first-sync clock edge differs from source parameter')
        return dict(cell=n,pin=p,master=c['type'],clock_pin='CLK',clock_edge=edge,capture_signal_edge='rise',input_path=path)
    launched={sid:launch(sid) for sid in byid};edges=[]
    for s in stages['stages']:
        if s['root']:continue
        parent=byregion[s['parent']]
        edges.append(dict(port=s['start_port_in'],src_stage=parent['id'],dst_stage=s['id'],kind='actual_FF_to_first_sync_D',
            launch=launched[parent['id']],capture=capture(s['id'])))
    for e in stages['die_outputs']:
        edges.append(dict(port=e['port'],src_stage=e['stage'],dst_part=e['dst_part'],kind='actual_FF_to_partition_boundary',
            launch=launched[e['stage']],capture=dict(port='start_'+e['net'],clock_edge='UNMEASURED partition view',capture_signal_edge='rise')))
    if len(edges)!=len(stages['stages'])-1+len(stages['die_outputs']):raise ValueError('incomplete START edge census')
    return dict(schema='ot_head_start_edge_roles/1',edges=edges,summary=dict(stages=len(byid),edges=len(edges),
        virtual_FF_edges=sum(e['kind']=='actual_FF_to_first_sync_D' for e in edges),boundary_edges=len(stages['die_outputs']),
        falling_first_sync=sum(e['capture'].get('clock_edge')=='fall' for e in edges),
        inverted_Q_launch=sum(e['launch']['launch_signal_edge']=='fall' for e in edges)),
        scope='role/polarity census only; routed min/max q-to-D and phase audit NOT RUN')


def main():
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('mapped');a.add_argument('physical');a.add_argument('stages');a.add_argument('--out',required=True);a=a.parse_args()
    o=census(json.load(open(a.mapped)),json.load(open(a.physical)),json.load(open(a.stages)));Path(a.out).write_text(json.dumps(o,indent=1)+'\n');print(json.dumps(o['summary']))
if __name__=='__main__':main()
