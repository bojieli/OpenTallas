#!/usr/bin/env python3
"""Expose existing mapped bank headers without adding cells or clock edges.

This is a physical source cut of the exact native32-qualified endpoint. The
original external ports remain on a wrapper; only already-kept bank headers
move out of the core. All original module definitions and cell connections
are retained. Local placement and routed ages are not inferred from this cut.
"""
import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import re

TOP='ot_hbm_su_indexed_scalar_f20'
CORE='ot_hbm_gather_f20_native_core_0c55'


def cut(source):
    result=copy.deepcopy(source);m=source['modules'][TOP]
    heads={n:c for n,c in m['cells'].items() if re.fullmatch(r'g_banked\.engine\.bank\[\d+\]\.head',n)}
    assert len(heads)==32
    bank_ports=('rq','rr','wq')
    bank_bits={b for p in bank_ports for b in m['ports'][p]['bits'] if isinstance(b,int)}
    core=copy.deepcopy(m);core['cells']={n:c for n,c in core['cells'].items() if n not in heads}
    assert len(core['cells'])==3065
    assert not any(bank_bits.intersection(bits) for c in core['cells'].values() for bits in c['connections'].values())
    core['ports']={p:v for p,v in core['ports'].items() if p not in bank_ports}
    core['attributes']=dict(core.get('attributes',{}));core['attributes'].pop('top',None)
    wrapper=copy.deepcopy(m);wrapper['cells']=copy.deepcopy(heads)
    banks=[]
    for n,c in sorted(heads.items(),key=lambda x:int(re.search(r'bank\[(\d+)\]',x[0])[1])):
        index=int(re.search(r'bank\[(\d+)\]',n)[1]);body=source['modules'][c['type']]
        assert int(c['type'].rsplit("'",1)[1],2)==index
        row=dict(bank=index,VM_bank='vmb_'+('SW','SE','NW','NE')[index//8]+str(index%8),
            cell=n,master=c['type'],core_links=[],native_bank_links=[],clock_links=[])
        for p,bits in c['connections'].items():
            if p in bank_ports:
                row['native_bank_links'].append(dict(port=p,bits=bits));continue
            if p=='clk' and bits==m['ports']['clk']['bits']:
                row['clock_links'].append(dict(port=p,source='original clk port',bits=bits));continue
            direction=body['ports'][p]['direction'];assert direction in ('input','output')
            port=f'bank{index}_{p}'
            core['ports'][port]=dict(direction='output' if direction=='input' else 'input',bits=bits)
            row['core_links'].append(dict(port=p,core_port=port,direction=direction,bits=bits))
        row['core_link_bits']=sum(len(p['bits']) for p in row['core_links'])
        assert row['core_link_bits']==116
        banks.append(row)
    # Every new boundary refers to the same original native net IDs. Flattening
    # this one wrapper level restores each original cell/port/net connection.
    links={p:v['bits'] for p,v in core['ports'].items()}
    wrapper['cells']['u_core']=dict(hide_name=0,type=CORE,parameters={},attributes={},connections=links,
        port_directions={p:v['direction'] for p,v in core['ports'].items()})
    for n,c in core['cells'].items():assert c==m['cells'][n]
    for n,c in heads.items():assert c==wrapper['cells'][n]
    for bank in banks:
        for p in bank['core_links']:
            assert wrapper['cells'][bank['cell']]['connections'][p['port']]==links[p['core_port']]
    global_bits={b for p in wrapper['ports'].values() for b in p['bits'] if isinstance(b,int)}
    global_bits.update(b for h in heads.values() for bs in h['connections'].values() for b in bs if isinstance(b,int))
    port_map={}
    for p,v in core['ports'].items():
        for local,global_bit in zip(v['bits'],links[p]):
            if isinstance(local,int):
                assert local not in port_map or port_map[local]==global_bit
                port_map[local]=global_bit
    rejoined=copy.deepcopy(heads)
    for n,cell in core['cells'].items():
        cell=copy.deepcopy(cell)
        for p,bs in cell['connections'].items():
            for bit in bs:
                assert not isinstance(bit,int) or bit in port_map or bit not in global_bits,('uncut shared wire',n,p,bit)
            cell['connections'][p]=[port_map.get(bit,bit) for bit in bs]
        rejoined[n]=cell
    def graph_hash(cells):
        payload={n:{k:cell.get(k,{}) for k in ('type','parameters','connections')} for n,cell in cells.items()}
        return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    original_hash=graph_hash(m['cells']);rejoined_hash=graph_hash(rejoined)
    assert original_hash==rejoined_hash
    assert set(rejoined)==set(m['cells']) and wrapper['ports']==m['ports']
    result['modules'][TOP]=wrapper;result['modules'][CORE]=core
    core_bits=sum(len(v['bits']) for v in core['ports'].values())
    assert core_bits==4182,core_bits
    quadrant_bits={q:sum(b['core_link_bits'] for b in banks if b['VM_bank'][4:6]==q)
                   for q in ('SW','SE','NW','NE')}
    host_inputs=sum(len(v['bits']) for p,v in m['ports'].items()
                    if p not in bank_ports+('clk',) and v['direction']=='input')
    status_outputs=sum(len(v['bits']) for p,v in m['ports'].items()
                       if p not in bank_ports and v['direction']=='output')
    faces=dict(W=quadrant_bits['SW']+host_inputs,E=quadrant_bits['NE'],
               N=quadrant_bits['NW'],S=quadrant_bits['SE']+status_outputs)
    assert sum(faces.values())+1==core_bits
    assert all(bits <= (367.2 if face in 'EW' else 345.6)*6*.60 for face,bits in faces.items())
    return result,dict(status='EXACT_NATIVE_PHYSICAL_CUT',source='0c55c33fc',
        original_top_cells=len(m['cells']),core_cells=len(core['cells']),bank_headers=len(heads),
        native_bank_bits=17760,original_endpoint_port_bits=18230,core_port_bits=core_bits,
        added_cells=0,removed_cells=0,added_register_edges=0,
        original_connectivity_sha256=original_hash,rejoined_connectivity_sha256=rejoined_hash,
        physical_cell_aliases={n:'u_core.'+n if n in core['cells'] else n for n in m['cells']},
        equivalence='Every original core and header cell/type/port/net is identical after flattening the added wrapper level',
        banks=banks,clock='Original endpoint clock remains literal on each kept header',
        pin_policy=dict(max_pins_per_um_per_face=6,face_utilization_cap=0.60,
            face_layers=dict(W='M4',E='M4',N='M5',S='M5'),
            basis='die_case_v16 coordinator6-pin standard and grants.py owner0.60face cap'),
        grant_requests=dict(core=dict(master=CORE,outline_MAIN_um=[345.6,367.2],outline_FB_um=[388.8,388.8],
            face_data_bits=faces,separate_clock_terminals=1,
            nature='pin-access request, not a placed or qualified view'),
            bank_local=dict(count=32,header_plus_selector=True,outline_MAIN_um=[64.8,216],
                face_data_bits=dict(W=556,E=556,N=119,S=0),separate_clock_terminals=2,
                outline_FB_um=[86.4,237.6],nature='actual bank W client face, native headers and selectors both explicit')),
        physical_placement='OPEN',boundary_pin_registration='NOT_EVALUATED',
        routed_read_write_launch_ages='OPEN; local source component remains R10/W5 and launch4')


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__)
    for n in ('input','output','report'):a.add_argument(n,type=Path)
    p=a.parse_args();raw=p.input.read_bytes();source=json.loads(gzip.decompress(raw) if p.input.suffix=='.gz' else raw)
    c,r=cut(source);r['input_sha256']=hashlib.sha256(raw).hexdigest()
    for path,obj in ((p.output,c),(p.report,r)):
        path.parent.mkdir(parents=True,exist_ok=True);data=json.dumps(obj,indent=1).encode()
        path.write_bytes(gzip.compress(data,mtime=0) if path.suffix=='.gz' else data+b'\n')
    print('GATHER_NATIVE_CUT core4182bits +32actualheaders; no added cells or register edges; physical paths OPEN')
