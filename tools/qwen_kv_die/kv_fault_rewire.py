#!/usr/bin/env python3
"""Emit review-only fault-plane netlist and exact pad contracts in a fresh directory.

This never edits a run. Missing generated KC pins, clock/reset loads, native lane
age proof, physical route and retirement guard remain explicit admission blocks.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import kv_fault_plane as I
import kv_output_pads as O
P=I.P


def signal(bit):
    if bit[0]=='CONST':return "1'b"+str(bit[1])
    return f'{bit[0]}[{bit[1]}]'


def rewrite(text,nets,insts,plan):
    if re.search(r'\bn_kv_fault_',text):raise ValueError('fault plane already present or naming collision')
    cells={i:(m,p,dict(c)) for m,i,p,c in insts};changed=set();wires=set();mapping={};occupied=[]
    for src in plan['sources']:
        if src['signal'] is None:
            i=src['instance'];m,p,c=cells[i]
            if src['port'] in c:raise ValueError('planned absent source port is already connected')
            net='n_kv_fault_source_'+i;wires.add(net);c[src['port']]=net;changed.add(i);mapping[src['id']]=net
        else:mapping[src['id']]=signal(src['signal'])
    for node in plan['nodes']:
        net='n_kv_fault_'+node['id'];mapping[node['id']]=net;wires.add(net)
    bit_changes={}
    for trans in plan['transports']:
        bit=trans['payload_bit'];prev=None
        for k,inst in enumerate(trans['stations']):
            m,p,c=cells[inst]
            if p or not re.fullmatch(r'qkd_(rlysh0?|landsh0?)_(1|36|296|528)',m):
                raise ValueError('unqualified transport station '+inst)
            aa=P.expr_bits(c['a'],nets);bb=P.expr_bits(c['b'],nets)
            if aa is None or bb is None or len(aa)!=len(bb) or bit>=len(aa):raise ValueError('station vector not exact')
            net=f'n_kv_fault_{trans["id"]}_s{k}';wires.add(net)
            for port,value in [('a',('REF',trans['source']) if k==0 else ('WIRE',prev)),('b',('WIRE',net))]:
                key=(inst,port)
                if bit in bit_changes.setdefault(key,{}):raise ValueError('payload bit allocated twice')
                bit_changes[key][bit]=value
                occupied.append(dict(instance=inst,master=m,port=port,bit=bit))
            prev=net;changed.add(inst)
        mapping[trans['id']]=prev
    for (inst,port),updates in bit_changes.items():
        m,p,c=cells[inst];bits=list(reversed(P.expr_bits(c[port],nets)))
        rendered=[signal(b) for b in bits]
        for bit,(kind,value) in updates.items():rendered[bit]=mapping[value] if kind=='REF' else value
        c[port]='{'+','.join(reversed(rendered))+'}'
    sink=cells['kvs_attn'][2]
    old=next(s['signal'] for s in plan['sources'] if s['id']=='existing_ufh')
    if P.expr_bits(sink['ufh'],nets)!=[tuple(old)]:raise ValueError('existing UFH consumer changed')
    sink['ufh']=mapping[plan['sink']];changed.add('kvs_attn')
    # Generated netlists have one flat named-port instance per line. Fail if any planned edit cannot be matched once.
    seen=set()
    def replace_instance(match):
        master,inst=match.group(2),match.group(3)
        if inst not in changed:return match.group(0)
        m,p,c=cells[inst]
        if inst in seen or master!=m:raise ValueError('ambiguous instance edit '+inst)
        if p:raise ValueError('no parameter rewrite supported')
        seen.add(inst)
        return '  '+m+' '+inst+' ('+', '.join('.'+p+'('+e+')' for p,e in c.items())+');'
    regex=re.compile(r'(?m)^([ \t]*)([A-Za-z_][A-Za-z_0-9$]*)[ \t]+([A-Za-z_][A-Za-z_0-9$]*)[ \t]*\([^\n]*\);[ \t]*$')
    text=regex.sub(replace_instance,text)
    if seen!=changed:raise ValueError('expected exactly one flat instance for '+str(sorted(changed-seen)))
    extra=['wire '+w+';' for w in sorted(wires)]
    placements=[]
    for n in plan['nodes']:
        if n['kind']=='pipe' and n['a']!=n['b']:raise ValueError('physical pipes require duplicated real input')
        if n['kind']=='sticky' and n['b']!=n['id']:raise ValueError('sticky feedback not explicit')
        inst='kv_'+n['id']
        extra.append('qkd_astk_fault_join '+inst+' (.ck('+n['clock']+'), .rst_n('+n['reset']+'), .a('+mapping[n['a']]+'), .b('+mapping[n['b']]+'), .q('+mapping[n['id']]+'));')
        pl=n['placement'];placements.append(f'ot_mts::place [$_blk findInst {inst}] {pl["x"]:.4f} {pl["y"]:.4f} R0')
    modules=list(re.finditer(r'\bmodule\s+\w+',P.strip_comments(text)));start=modules[-1].start();end=text.index('endmodule',start)
    text=text[:end]+'\n'+'\n'.join(extra)+'\n'+text[end:]
    return text,occupied,placements


def emit(run,source_tree,inventory,plan,out):
    if out.exists():raise ValueError('output directory already exists; use a fresh review directory')
    for name,digest in inventory['pinned_files'].items():
        if I.digest(run/name)!=digest:raise ValueError('source case changed '+name)
    if plan['sources']!=inventory['sources']:raise ValueError('plan source identities differ from exact inventory')
    lanes={l['id']:l for l in inventory['spare_transport_candidates']}
    for t in plan['transports']:
        l=lanes[t['lane_id']]
        if t['payload_bit'] not in l['free_bits'] or t['stations']!=l['stations']:
            raise ValueError('plan steals unqualified payload bit')
        if t['latency_cycles']!=l['conservative_model_cycles']:
            raise ValueError('transport latency differs from pinned inventory')
    src=run/inventory.get('input_die','port_bind_v2/die_bound.v');nets,_,_,insts=P.parse_die(str(src))
    text,occupied,placements=rewrite(src.read_text(),nets,insts,plan)
    out.mkdir(parents=True);die=out/'die_fault_candidate.v';die.write_text(text)
    # Re-derive every relay declaration after functional bits are renamed/wired; never retain old instance b permissions.
    oldfile=run/'case_kv/die.v.pads.json';old=json.loads(oldfile.read_text()) if oldfile.exists() else {}
    pads=O.derive(die,source_tree,old);loaded=P.load_pads(pads)
    for item in occupied:
        key=(item['master'],item['port'],item['instance'])
        globalkey=(item['master'],item['port'])
        width=int(item['master'].rsplit('_',1)[1])
        if any(item['bit'] in P.pad_bits(loaded[k],width) for k in (key,globalkey) if k in loaded):
            raise ValueError('stale pad allowance survives on functional bit '+str(item))
    (out/'pads.json').write_text(json.dumps(pads,indent=1)+'\n')
    (out/'placement_additions.tcl').write_text('\n'.join(placements)+'\n')
    meta=dict(status='REVIEW_ONLY_NOT_PHYSICAL_CASE',plan_sha256=I.digest(Path(plan['_path'])) if '_path' in plan else None,
              die_sha256=I.digest(die),source_bound_sha256=I.digest(src),sources=len(plan['sources']),
              occupied_payload_port_bits=len(occupied),occupied_bits=occupied,new_join_cells=len(plan['nodes']),
              padding_check='Every occupied a/b bit absent from both instance and master pad permissions',
              blocks=plan['requirements']+['Regenerate LEF/libs and native source/clock/reset bindings for all added cells and restored KC outputs'])
    (out/'rewire_manifest.json').write_text(json.dumps(meta,indent=1)+'\n');return meta


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--source-tree',type=Path,required=True);ap.add_argument('--inventory',type=Path,required=True);ap.add_argument('--plan',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();plan=json.loads(a.plan.read_text());plan['_path']=str(a.plan)
    doc=emit(a.run,a.source_tree,json.loads(a.inventory.read_text()),plan,a.out)
    print(json.dumps({k:doc[k] for k in ('status','sources','occupied_payload_port_bits','new_join_cells','die_sha256')}))
if __name__=='__main__':main()
