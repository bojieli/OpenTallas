"""Interpret generated prefix/sort connections numerically; static, never HDL.

Threshold and expected IDs use IEEE comparisons, without radix/order-key code.
This audits the generated connection constants and width semantics, not clocks,
control execution, synthesis or SystemVerilog elaboration.
"""
import argparse
import ast
import operator
import json
from pathlib import Path
import re
import struct
import prepare_dsrom_full_selector_dma_fixture as V

def register_bits(source):
    """Read generated declarations rather than trust generator's price ledger."""
    values={'PF':64,'NBIN':256,'CB':14,'DIG':8}
    ops={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul}
    def number(expr):
        def walk(node):
            if isinstance(node,ast.Constant) and isinstance(node.value,int):return node.value
            if isinstance(node,ast.Name):return values[node.id]
            if isinstance(node,ast.BinOp) and type(node.op) in ops:return ops[type(node.op)](walk(node.left),walk(node.right))
            raise ValueError('unsupported register dimension')
        return walk(ast.parse(expr,mode='eval').body)
    wanted=re.compile(r'^(hist_pc_\d+|hist_valid|suffix_up_\d+|suffix_down_\d+|choose_lower_sum|choose_pred|choose_node_\d+|eq_count_\d+|eq_id_\d+|eq_gt_\d+|eq_mask_\d+|eq_v_\d+|sort_record_\d+|take_count_\d+|take_total_\d+|sort_valid|pvalid|pk)$')
    inventory={}
    for m in re.finditer(r'\breg\s+(?:\[([^:\]]+):([^\]]+)\]\s*)?([^;]+);',source):
        for entry in m[3].split(','):
            name=re.match(r'\s*([A-Za-z0-9_]+)',entry)
            if not name or not wanted.fullmatch(name[1]):continue
            bits=abs(number(m[1])-number(m[2]))+1 if m[1] else 1
            for lo,hi in re.findall(r'\[([^:\]]+):([^\]]+)\]',entry):bits*=abs(number(lo)-number(hi))+1
            if name[1] in inventory:raise ValueError('duplicate register declaration')
            inventory[name[1]]=bits
    # Removed h2_v:1 and widened original pk:2 are baseline-state debits.
    net=sum(inventory.values())-1-2
    if net!=127140:raise ValueError('generated register count differs from priced127140 bits')
    return dict(generated_register_bits=inventory,new_declarations_gross_bits=sum(inventory.values()),baseline_replaced_bits=3,net_added_bits=net)

def topology(source):
    if 'wire choose_min=(ascending==lower_lane);' not in source:raise ValueError('sort select relation changed')
    if 'here[38:32]<other[38:32]' not in source or 'here[38:32]>other[38:32]' not in source:raise ValueError('sort comparison changed')
    levels=[]
    for stage in range(1,22):
        m=re.search(r'wire ascending=\(si'+str(stage)+r'&(\d+)\)==0;',source)
        n=re.search(r'wire lower_lane=\(si'+str(stage)+r'&(\d+)\)==0;',source)
        partner=re.search(r'wire \[38:0\] here=.*?,other=.*?\(si'+str(stage)+r'\^(\d+)\)',source)
        # Stage>=2 formats other=sort_record_previous[(si^j)].
        if not m or not n or not partner:raise ValueError('missing source sort connection')
        k,j,j2=map(int,(m.group(1),n.group(1),partner.group(1)))
        if j!=j2 or j<1 or k<2 or j>=k or j&(j-1) or k&(k-1):raise ValueError('invalid source sort pair')
        levels.append((k,j))
    expected=[(k,j) for k in (2,4,8,16,32,64) for j in [1<<(h) for h in reversed(range(k.bit_length()-1))]]
    if levels!=expected:raise ValueError('source sort topology not the admitted21-level network')
    prefix=[]
    for l in range(6):
        m=re.search(r'if\(ep'+str(l)+r'>=(\d+)\).*?eq_count_'+str(l)+r'\[ep'+str(l)+r'\]<=([0-9]+)\x27',source)
        if not m:raise ValueError('missing source prefix connection')
        step,width=map(int,m.groups())
        if (step,width)!=(1<<l,l+2):raise ValueError('source prefix step/width differs from model')
        prefix.append((step,width))
    if 'CB\'(eq_count_5[l-1])<eq_left' not in source:raise ValueError('exclusive lane quota missing')
    return prefix,levels

def row(gt,eq,ids,quota,prefix,sort):
    vec=list(eq)
    for step,width in prefix:
        old=vec;mask=(1<<width)-1
        vec=[(v+(old[i-step] if i>=step else 0))&mask for i,v in enumerate(old)]
    exclusive=[0]+vec[:-1]
    take=[g or (e and p<quota) for g,e,p in zip(gt,eq,exclusive)]
    records=[(((0 if take[i] else 1)<<6)|i,ids[i]) for i in range(64)]
    for k,j in sort:
        prior=records;records=[]
        for i,here in enumerate(prior):
            other=prior[i^j];minimum=((i&k)==0)==((i&j)==0)
            records.append(here if (here[0]<other[0] if minimum else here[0]>other[0]) else other)
    values=[v for key,v in records if not key>>6]
    return values,max(0,quota-vec[-1])

def audit(source):
    prefix,sort=topology(source);records=[];totalrows=0
    for index,(n,k,pattern) in enumerate(V.cases()):
        raw=V.scores(n,pattern);f=[struct.unpack('!f',struct.pack('!I',v))[0] for v in raw]
        ids=[(i//n)*(2*n)+i%n for i in range(4*n)]
        ranked=sorted(range(len(f)),key=lambda i:(-f[i],ids[i]))
        threshold=f[ranked[k-1]];quota=k-sum(v>threshold for v in f)
        selected=[]
        for offset in range(0,len(f),64):
            values=f[offset:offset+64];chunk=ids[offset:offset+64]
            gt=[v>threshold for v in values];eq=[v==threshold for v in values]
            chosen,after=row(gt,eq,chunk,quota,prefix,sort)
            expected=[];seen=0
            for g,e,id in zip(gt,eq,chunk):
                if g or (e and seen<quota):expected.append(id)
                seen+=e
            if chosen!=expected or after!=max(0,quota-sum(eq)):raise AssertionError('SOURCE_CONNECTION_ROW_DIFF')
            selected.extend(chosen);quota=after;totalrows+=1
        target=sorted(ids[i] for i in ranked[:k])
        if selected!=target or quota!=0:raise AssertionError('SOURCE_CONNECTION_SELECTION_DIFF')
        records.append(dict(case=index,n=n,k=k,rows=4*n//64,selected=k))
    return dict(register_declaration_audit=register_bits(source),scope='STATIC_GENERATED_CONNECTION_INTERPRETATION_NOT_HDL',source_sha256=V.sha(source.encode()),cases=records,
       rows=totalrows,sort_levels=len(sort),prefix_levels=len(prefix),HDL_executed=False,clock_or_control_qualification=False)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise ValueError('fresh audit receipt required')
    V.write_json(a.out,audit(a.source.read_text()));print(json.dumps({'cases':37,'scope':'static connection interpretation only'}))
