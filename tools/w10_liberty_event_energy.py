#!/usr/bin/env python3
"""Compatible Liberty when-state energy envelopes, split by triggering pin."""
import ast
from decimal import Decimal as D
import itertools
import re
from tools.w10_q_power_envelope import blocks, NUM

def parse_when(text):
    expression=text.strip('"').replace('!',' not ').replace('*',' and ').replace('+',' or ').strip()
    tree=ast.parse(expression,mode='eval')
    allowed=(ast.Expression,ast.Name,ast.Load,ast.BoolOp,ast.And,ast.Or,ast.UnaryOp,ast.Not,ast.Constant)
    if any(not isinstance(n,allowed) for n in ast.walk(tree)):raise ValueError('unsupported Liberty when')
    return tree

def truth(tree,state):
    n=tree.body if isinstance(tree,ast.Expression) else tree
    if isinstance(n,ast.Name):return state[n.id]
    if isinstance(n,ast.Constant) and n.value in (0,1):return bool(n.value)
    if isinstance(n,ast.UnaryOp):return not truth(n.operand,state)
    if isinstance(n,ast.BoolOp):
        values=[truth(x,state) for x in n.values]
        return all(values) if isinstance(n.op,ast.And) else any(values)
    raise ValueError('unsupported condition')

def events(text,name,fixed=None):
    fixed=fixed or {}; cs=list(blocks(text,r'cell\s*\('+re.escape(name)+r'\)'))
    if len(cs)!=1:raise ValueError('missing/duplicate cell')
    groups={}
    for pin in blocks(cs[0],r'\bpin\s*\([^)]*\)'):
        owner=re.search(r'pin\s*\(([^)]*)\)',pin)[1]
        for power in blocks(pin,r'\binternal_power\s*\([^)]*\)'):
            rel=re.search(r'related_pin\s*:\s*([^;]+)',power)
            trigger=rel[1].strip().strip('"') if rel else owner
            pg=re.search(r'related_pg_pin\s*:\s*([^;]+)',power)
            rail=pg[1].strip().strip('"') if pg else 'UNSPECIFIED'
            wh=re.search(r'when\s*:\s*([^;]+)',power)
            condition=parse_when(wh[1]) if wh else ast.parse('1',mode='eval')
            edges={}
            for edge in ('rise','fall'):
                tables=list(blocks(power,r'\b'+edge+r'_power\s*\([^)]*\)'))
                if len(tables)!=1:raise ValueError('missing/duplicate edge table')
                v=re.search(r'\bvalues\s*\((.*?)\)\s*;',tables[0],re.S)
                if not v:raise ValueError('missing values')
                ns=[abs(D(n)) for n in re.findall(NUM,v[1])]
                if not ns:raise ValueError('empty values')
                edges[edge]=max(ns)
            groups.setdefault((owner,trigger,rail),[]).append((condition,edges))
    if not groups:raise ValueError('no internal power')
    result={};proof=[]
    for (owner,trigger,rail),arcs in sorted(groups.items()):
        variables=sorted({n.id for condition,_ in arcs for n in ast.walk(condition) if isinstance(n,ast.Name)}-set(fixed))
        if len(variables)>10:raise ValueError('condition too large')
        maxima={'rise':D(0),'fall':D(0)}; compatible_max=0
        for bits in itertools.product((False,True),repeat=len(variables)):
            state={**fixed,**dict(zip(variables,bits))}
            active=[edges for condition,edges in arcs if truth(condition,state)]
            compatible_max=max(compatible_max,len(active))
            for edge in maxima:maxima[edge]=max(maxima[edge],sum((a[edge] for a in active),D(0)))
        energy=sum(maxima.values(),D(0));result[trigger]=result.get(trigger,D(0))+energy
        proof.append({'owner_pin':owner,'trigger_pin':trigger,'rail':rail,'conditional_arcs':len(arcs),
                      'maximum_compatible_arcs':compatible_max,'rise_max_fJ':str(maxima['rise']),
                      'fall_max_fJ':str(maxima['fall']),'cycle_max_fJ':str(energy)})
    return {'event_cycle_fJ':{k:str(v) for k,v in sorted(result.items())},'fixed_conditions':fixed,'compatible_arc_proof':proof}
