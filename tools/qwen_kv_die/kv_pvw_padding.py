#!/usr/bin/env python3
"""Recover only generated PV replica padding, qualified by the original static frame.

PV trunk generation fills unused replica positions with high zero literals.
Exact hashed source rows, frame identities, output slices and actual zero inputs
must agree. Dynamic unconsumed command/data/flags are never declared padding.
"""
import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
import kv_output_pads as O
P=O.P
ROOT=O.ROOT
SOURCES={
 'rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv':'4601aa6d6ccb8b201d2f991a028a972d77f505506bc1ea87d5495738f0a7064d',
 'tools/qwen_kv_die/pv_trunk_gen.py':'85e6bb225c010e1758b0dbcf8e24ebb20e1ab562b304c3f159ade8c787ba9458',
 O.RTL:O.RTL_SHA,
}
BOOTAGE_SOURCES={
# KV-BIND3 10-19: re-pinned after e4eb15c83 (one line: attn_cal STATUS_DELAY default 0 in boot_ages_join; the attention
# calendar tile, not a PV trunk/replica row -- previous pin bc8a613d...).
 'tools/qwen_kv_die/kv_bootage.py':'9e5721ba45a8521a1dcb92e8fa756b2ac60f84f1dbc7e54d97f378ade6d5ebfe',
 'rtl/qwen_sys/split_20261014/qkd_pvw_die_t_ba.sv':'b15daa62c06da889ee7e0db600b08079e45862397208329b9d2e886b26ba5dad',
}


def qualify_frame(module, root):
    if module=='qkd_pvw_die_t':return {}
    if module!='qkd_pvw_die_tb':raise ValueError('PV frame is not pinned generated trunk')
    # This exact boot-age successor changes only the control cfg interface/age;
    # its standard-replica station rows are identical to the original trunk.
    for name,sha in BOOTAGE_SOURCES.items():
        p=root/name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=sha:
            raise ValueError('PV boot-age source changed; re-prove '+name)
    return dict(BOOTAGE_SOURCES)


PARENTS={'qkd_pvw_s','qkd_pvw_n'}
BAD_LITERAL=re.compile(r"(?<![A-Za-z0-9_])'[01xXzZ]|\d+'[sS]?[bBhHdDoO][0-9a-fA-F_]*[xXzZ?]")


def ranges(bits):
    out=[]
    for bit in sorted(bits):
        if out and bit==out[-1][1]+1:out[-1][1]=bit
        else:out.append([bit,bit])
    return out


def source_rows(source):
    nets,_,_,_=P.parse_die(str(source),top='qkd_pvw_die_t')
    source_text=source.read_text()
    # The generated RTL also uses legal wire[W:0] declarations; the flat die reader expects wire followed by whitespace.
    for decl in re.finditer(r'\bwire\s*\[\s*(\d+)\s*:\s*(\d+)\s*\]\s*([^;]+);',source_text):
        hi,lo=int(decl.group(1)),int(decl.group(2))
        for name in P._split_commas(decl.group(3)):
            name=name.strip()
            if re.fullmatch(r'\w+',name):nets[name]=(abs(hi-lo)+1,min(hi,lo))
    module=next(m for m in P.parse_modules(source_text,str(source)) if m.name=='qkd_pvw_die_t')
    env=module.env({})
    for port in module.ports:
        width=module.width(port,env)
        if width is None:raise ValueError('unresolved PV source port width '+port)
        nets.setdefault(port,(width,0))
    rows=[]
    # Exact source is generated with one flat standard-replica row per line, including the admitted g_ok mutant branch.
    for line in source.read_text().splitlines():
        match=re.fullmatch(r'\s*(qkd_rlys_(1|36|296|528))\s+(\w+)\s*\((.*)\);\s*',line)
        if not match:continue
        master,width,inst,body=match.groups();width=int(width);cm=dict(P._named_conns(body))
        if BAD_LITERAL.search(cm['a']):raise ValueError('ambiguous literal in pinned source')
        aa,bb=P.expr_bits(cm['a'],nets),P.expr_bits(cm['b'],nets)
        if aa is None or bb is None or len(aa)!=width or len(bb)!=width:raise ValueError('unresolved source replica '+inst)
        pad=set();prefix=True
        for msb,bit in enumerate(aa):
            if bit==('CONST',0):
                if not prefix:raise ValueError('source literal is not a high replica pad '+inst)
                pad.add(width-1-msb)
            else:prefix=False
        if pad:
            if any(not bit[0].startswith('w_') for bit in bb):raise ValueError('source pad output not private frame wire')
            rows.append(dict(master=master,instance=inst,width=width,pad=pad,output=bb))
    if not rows:raise ValueError('no generated source padding roles')
    return rows


def apply_roles(die,rows,parents,existing):
    nets,tin,tout,ins=P.parse_die(str(die));cells={i:(m,p,c)for m,i,p,c in ins}
    if len(cells)!=len(ins):raise ValueError('duplicate actual instance')
    # Physical pin repair inserts additional closed, same-bit standard stations before a source row.
    # Trace only these hashed bit-independent registers to a sized literal zero; never arbitrary logic.
    drivers={}
    for master,inst,prm,cm in ins:
        if master not in O.STANDARDS:continue
        if prm:raise ValueError('unqualified transparent repair '+inst)
        if BAD_LITERAL.search(cm.get('a','')):raise ValueError('ambiguous transparent repair literal '+inst)
        aa,bb=P.expr_bits(cm.get('a',''),nets),P.expr_bits(cm.get('b',''),nets)
        if aa is None or bb is None or len(aa)!=O.STANDARDS[master] or len(bb)!=len(aa):raise ValueError('repair width changed '+inst)
        for a,b in zip(aa,bb):
            if b[0] in ('CONST','UNDECL','Z') or b in drivers:raise ValueError('nonunique repair output')
            drivers[b]=a
    cache={}
    def zero(bit):
        path=[];active=set()
        while bit in drivers and bit not in cache:
            if bit in active:raise ValueError('cycle in same-bit padding provenance')
            active.add(bit);path.append(bit);bit=drivers[bit]
        value=cache.get(bit,bit==('CONST',0))
        for b in path:cache[b]=value
        return value
    targets={};output_counts=Counter()
    for parent in parents:
        for row in rows:
            candidates=[parent+'__'+row['instance'],parent+'__g_ok_'+row['instance']]
            found=[i for i in candidates if i in cells]
            if len(found)!=1:raise ValueError('PV source replica absent/ambiguous '+candidates[0])
            inst=found[0];master,prm,cm=cells[inst]
            aa,bb=P.expr_bits(cm.get('a',''),nets),P.expr_bits(cm.get('b',''),nets)
            expected=[('n_'+parent+'__'+n,b)for n,b in row['output']]
            if (master!=row['master'] or prm or bb is None or len(bb)!=row['width']
                    or any(bb[row['width']-1-b]!=expected[row['width']-1-b] for b in row['pad'])
                    or aa is None or len(aa)!=row['width']):
                raise ValueError('PV source role/output slice changed '+inst)
            if BAD_LITERAL.search(cm['a']):raise ValueError('ambiguous actual PV literal')
            zeros={row['width']-1-k for k,b in enumerate(aa) if zero(b)}
            if zeros!=row['pad']:raise ValueError('actual zero input differs from exact source replica padding '+inst)
            targets[inst]=(master,row,bb);output_counts.update(bb)
    reads=set();uncertain=set()
    for master,inst,prm,cm in ins:
        if master=='__assign__':uncertain.update(re.findall(r'[A-Za-z_][A-Za-z_0-9$]*',inst))
        for port,expr in cm.items():
            if inst in targets and port=='b':continue
            bits=P.expr_bits(expr,nets)
            if bits is None:uncertain.update(re.findall(r'[A-Za-z_][A-Za-z_0-9$]*',expr))
            else:reads.update(b for b in bits if b[0] not in ('CONST','UNDECL','Z'))
    doc=json.loads(json.dumps(existing));sha=hashlib.sha256(die.read_bytes()).hexdigest()
    if any('b' in doc.get('pads',{}).get(m,{}) for m in O.STANDARDS):
        raise ValueError('global relay output allowance must be removed by exact instance recovery')
    previous=doc.get('source_contract',{}).get('die_sha256')
    if previous and previous!=sha:raise ValueError('existing pads belong to a different die')
    added=0;total_source_pads=0;affected=0
    for inst,(master,row,bb) in targets.items():
        selected={b for b in row['pad'] if bb[row['width']-1-b] not in reads
                  and bb[row['width']-1-b][0] not in uncertain|tin|tout}
        if any(output_counts[b]!=1 for b in bb):raise ValueError('duplicate PV payload driver')
        ent=doc.setdefault('instances',{}).setdefault(inst,dict(master=master,ports={}))
        if ent.get('master')!=master:raise ValueError('existing instance master changed')
        ports=ent.setdefault('ports',{})
        ports['a']=ranges(row['pad']) # narrow inherited global-minimum input scope to this generated replica
        old=P.pad_bits(ports.get('b',[]),row['width'])
        if old-row['pad']:raise ValueError('existing PV output pad covers a live field')
        ports['b']=ranges(selected)
        ent['reason']='Hashed PV generator fills only out-of-logical-width high replica positions with zero; exact source/actual row and output slices match; unused output bits have no other consumer'
        total_source_pads+=len(row['pad']);added+=len(selected-old);affected+=bool(selected)
    return doc,dict(die_sha256=sha,source_pad_input_bits=total_source_pads,new_unused_output_bits=added,affected_replicas=affected)


def derive(run,die,root=ROOT,existing=None):
    for name,sha in SOURCES.items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=sha:raise ValueError('PV padding source changed; re-prove '+name)
    frames=json.loads((run/'expand.json').read_text())['frames'];_,_,_,pre=P.parse_die(str(run/'case_kv/die.v.preexp'))
    params=json.loads((run/'case_kv/die.v.params.json').read_text()) if (run/'case_kv/die.v.params.json').exists() else {}
    parents={};counts=Counter();variant_sources={}
    for master,inst,prm,cm in pre:
        if master not in PARENTS:continue
        variant_sources.update(qualify_frame(frames.get(master,{}).get('module'),root))
        merged=dict(params.get(inst,{}),**prm)
        for key in ('MUT','TRUNK_MUT','FLAG_D_ADJ','RS_MUT'):
            if key in merged and P.ev(str(merged[key]),{})!=0:raise ValueError('PV mutant cannot receive padding contract')
        parents[inst]=master;counts[master]+=1
    if not parents:raise ValueError('no source-qualified PV parents')
    if any(frames[m]['instances']!=n for m,n in counts.items()):raise ValueError('PV parent count mismatch')
    doc,contract=apply_roles(die,source_rows(root/'rtl/qwen_sys/split_20261014/qkd_pvw_die_t.sv'),parents,existing or dict(pads={},instances={}))
    contract.update(source_sha256=dict(SOURCES,**variant_sources),parents=parents,expand_sha256=hashlib.sha256((run/'expand.json').read_bytes()).hexdigest(),
                    preexpand_sha256=hashlib.sha256((run/'case_kv/die.v.preexp').read_bytes()).hexdigest())
    doc['pvw_padding_contract']=contract;return doc


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--run',type=Path,required=True);ap.add_argument('--die',type=Path,required=True);ap.add_argument('--root',type=Path,default=ROOT);ap.add_argument('--existing',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();doc=derive(a.run,a.die,a.root,json.loads(a.existing.read_text()));a.out.write_text(json.dumps(doc,indent=1)+'\n');print(json.dumps(doc['pvw_padding_contract']))
if __name__=='__main__':main()
