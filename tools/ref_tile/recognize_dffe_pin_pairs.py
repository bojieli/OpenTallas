#!/usr/bin/env python3
"""Fail-closed placement recognizer for an exact mapped AND2/AO21 DFFE.

This proves connectivity and actual Liberty Boolean functions. It changes no
netlist or timing constraints. A recognized pair is anchored at its q face.
"""
import argparse
import itertools
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dft.liberty import read_liberty, parse_function, evaluate, expr_vars
from dft.netlist import read_module, build_aliases, Module, Instance


def read_graph(path, top):
    """Native OpenDB net IDs preserve distinct bus bits/internal scalar nets."""
    m=Module(top,'');instances={}
    for line in path.read_text().splitlines():
        fields=line.split('\t');kind=fields[0]
        if kind=='PORT' and len(fields)==4:
            _,direction,name,net=fields
            m.ports.append(name);m.port_dirs[name]=direction;m.ranges[name]=None
            m.assigns.append(([name],[net],(0,0)))
        elif kind=='CELL' and len(fields)==3:
            _,name,master=fields
            if name in instances: raise Reject('repeated native instance')
            i=Instance(master,name,{}, {},(0,0));instances[name]=i;m.instances.append(i)
        elif kind=='PIN' and len(fields)==4:
            _,name,pin,net=fields
            i=instances[name]
            if pin in i.pins: raise Reject('repeated native pin')
            i.pins[pin]=[net]
        else:raise Reject('invalid native graph row')
    return m


class Reject(ValueError):
    pass


class Recognizer:
    def __init__(self, mod, cells, hops=12):
        self.mod, self.cells, self.hops = mod, cells, hops
        alias = build_aliases(mod)
        self.canon = alias.find
        self.drivers = defaultdict(list)
        self.sinks = defaultdict(list)
        self.ports = defaultdict(list)
        self.byname = {i.name:i for i in mod.instances}
        for direction in ('input','output','inout'):
            for p in mod.port_bits(direction):
                self.ports[self.canon(p)].append((direction,p))
        for i in mod.instances:
            if i.cell=='TAPCELL_ASAP7_75t_R' and not i.pins:
                continue  # Physical-only cell, proven to have no signal edges.
            if i.cell not in cells:
                raise Reject('unknown Liberty cell '+i.cell)
            for pin, bits in i.pins.items():
                if len(bits)!=1 or pin not in cells[i.cell]['pins']:
                    raise Reject('non-scalar or unknown cell pin '+i.name+'/'+pin)
                direction=cells[i.cell]['pins'][pin]['direction']
                if direction=='output': self.drivers[self.canon(bits[0])].append((i,pin))
                elif direction=='input': self.sinks[self.canon(bits[0])].append((i.name,pin))
                elif direction not in ('internal',): raise Reject('unknown pin direction')

    def wire(self,i,p):
        if p not in i.pins: raise Reject('missing pin '+i.name+'/'+p)
        return self.canon(i.pins[p][0])

    def driver(self,n):
        ds=self.drivers[n]
        if len(ds)!=1: raise Reject('ambiguous/no driver '+n)
        return ds[0]

    def exact_sinks(self,n,want):
        if sorted(self.sinks[n])!=sorted(want): raise Reject('unexpected fanout '+n)

    def function(self,i,out,inputs,want):
        c=self.cells[i.cell]
        actual=sorted(p for p,d in c['pins'].items() if d['direction']=='input')
        outputs=sorted(p for p,d in c['pins'].items() if d['direction']=='output')
        if actual!=sorted(inputs) or outputs!=[out] or c['ff'] or c['latch']:
            raise Reject('unknown combinational signature '+i.name)
        f=c['pins'][out]['function']
        if not f: raise Reject('missing function '+i.name)
        e=parse_function(f)
        for row in itertools.product((0,1),repeat=len(inputs)):
            v=dict(zip(inputs,row))
            if evaluate(e,v)!=want(v): raise Reject('wrong Boolean function '+i.name)

    def transparent(self,i,out):
        if not i.cell.startswith(('BUF','INV','HB')): raise Reject('non-transparent cell '+i.name)
        c=self.cells[i.cell]
        ip=[p for p,v in c['pins'].items() if v['direction']=='input']
        if len(ip)!=1: raise Reject('non-scalar transparent cell')
        try:
            self.function(i,out,ip,lambda v:v[ip[0]])
            parity=0
        except Reject:
            self.function(i,out,ip,lambda v:1-v[ip[0]])
            parity=1
        return ip[0],parity

    def ff(self,i,out):
        c=self.cells[i.cell]; f=c['ff']
        if not i.cell.startswith('DFF') or not f or c['latch']:
            raise Reject('not supported FF '+i.name)
        if sorted(p for p,v in c['pins'].items() if v['direction']=='output')!=[out] or not c['pins'].get('CLK',{}).get('clock'):
            raise Reject('unknown FF output/clock signature')
        state=parse_function(f.get('next_state',''))
        if expr_vars(state)!={'D'} or f.get('clocked_on')!='CLK' or any(k in f for k in ('clear','preset')):
            raise Reject('unknown FF state/clock/reset '+i.name)
        if len(f['vars'])!=2: raise Reject('unknown FF state variables')
        e=parse_function(c['pins'][out]['function'] or '')
        x,y=f['vars']; values=[]
        for d in (0,1):
            b=evaluate(state,{'D':d});values.append(evaluate(e,{x:b,y:1-b}))
        if values==[0,1]: parity=0
        elif values==[1,0]: parity=1
        else: raise Reject('unknown FF output function')
        # CTS leaf clock net names can differ; prove transparent physical root.
        cn=self.wire(i,'CLK');cp=0;seen=set()
        for _ in range(self.hops):
            if cn in seen:raise Reject('clock scalar cycle')
            seen.add(cn)
            if not self.drivers[cn]:break
            ci,co=self.driver(cn);pin,inv=self.transparent(ci,co)
            cp^=inv;cn=self.wire(ci,pin)
        else:raise Reject('clock scalar depth')
        if cp or self.ports[cn]!=[('input','clk')]:
            raise Reject('clock not noninverting actual clk root')
        return cn,parity

    def back(self,start,exclusive=False):
        n=start; parity=0; edges=[]; seen=set()
        for _ in range(self.hops):
            if n in seen: raise Reject('cycle in scalar chain')
            seen.add(n)
            if not self.drivers[n]:
                return ('port',n,parity,edges,None)
            i,p=self.driver(n)
            if self.cells[i.cell]['ff']:
                clk,fp=self.ff(i,p)
                return ('ff',i,parity^fp,edges,clk)
            ip,inv=self.transparent(i,p)
            incoming=self.wire(i,ip)
            if exclusive: self.exact_sinks(incoming,[(i.name,ip)])
            edges.append((n,i.name,p,incoming,ip))
            parity^=inv;n=incoming
        raise Reject('scalar traversal depth exceeded')

    def pair(self,q):
        qnet=self.canon(q)
        kind,ff,qp,edges,clk=self.back(qnet)
        if kind!='ff' or qp: raise Reject('output does not equal FF D state')
        ao,out=self.driver(self.wire(ff,'D'))
        if not ao.cell.startswith('AO21'): raise Reject('D driver not AO21')
        self.function(ao,out,['A1','A2','B'],lambda v:(v['A1']&v['A2'])|v['B'])
        andi,ap=self.driver(self.wire(ao,'B'))
        if not andi.cell.startswith('AND2'): raise Reject('feedback not AND2')
        self.function(andi,ap,['A','B'],lambda v:v['A']&v['B'])
        chain_nets=set([qnet]+[e[3] for e in edges])
        feedback_pins=[p for p in ('A','B') if self.wire(andi,p) in chain_nets]
        if len(feedback_pins)!=1: raise Reject('feedback not exact output state')
        feedback_pin=feedback_pins[0]; feedback_net=self.wire(andi,feedback_pin)
        fbroot=self.back(feedback_net)
        if fbroot[0]!='ff' or fbroot[1].name!=ff.name or fbroot[2]: raise Reject('feedback polarity differs')
        en_false=self.wire(andi,'B' if feedback_pin=='A' else 'A')
        false_root=self.back(en_false)
        if false_root[0]!='ff' or false_root[4]!=clk: raise Reject('enable root clock differs')
        if false_root[1].name==ff.name: raise Reject('enable is data register itself')
        me=self.back(self.wire(false_root[1],'D'))
        if me[0]!='port' or me[2] or self.ports[me[1]]!=[('input','me_e')]:
            raise Reject('enable root not previous-edge me_e register')
        options=[]
        for ep,dp in [('A1','A2'),('A2','A1')]:
            try:
                en=self.back(self.wire(ao,ep));data=self.back(self.wire(ao,dp),True)
                if en[0]!='ff' or en[1].name!=false_root[1].name or en[2]==false_root[2] or en[4]!=clk:
                    raise Reject('enables not opposite same registered root')
                if data[0]!='port' or data[2]: raise Reject('data not positive scalar input')
                ps=self.ports[data[1]]
                if len(ps)!=1 or ps[0][0]!='input': raise Reject('data input not unique port')
                self.exact_sinks(self.wire(ao,dp),[(ao.name,dp)])
                options.append(ps[0][1])
            except (Reject,KeyError,ValueError): pass
        if len(options)!=1: raise Reject('ambiguous or invalid data/enable inputs')
        self.exact_sinks(self.wire(ff,'D'),[(ff.name,'D')])
        self.exact_sinks(self.wire(andi,ap),[(ao.name,'B')])
        if self.ports[self.wire(ff,'D')] or self.ports[self.wire(andi,ap)]: raise Reject('internal cone exposed as port')
        # Every output-chain load accounted for. Only q carries the exact feedback branch.
        want=defaultdict(list);want[feedback_net].append((andi.name,feedback_pin))
        for _,name,_,incoming,ip in edges: want[incoming].append((name,ip))
        for n in set([qnet]+[e[3] for e in edges]):
            self.exact_sinks(n,want[n])
            if self.ports[n] != ([('output',q)] if n==qnet else []): raise Reject('extra output-chain port')
        return {'ff':ff.name,'d':options[0],'q':q,'clock_net':clk,'enable_ff':false_root[1].name}

    def run(self):
        pairs=[];rejects={}
        for q in self.mod.port_bits('output'):
            try:pairs.append(self.pair(q))
            except (Reject,KeyError,ValueError) as e:rejects[q]=str(e)
        for key in ('ff','d','q'):
            values=[p[key] for p in pairs]
            if len(values)!=len(set(values)): raise Reject('ambiguous shared '+key)
        return {'pairs':pairs,'rejected':rejects,'placement_priority':'q face; d/q paired; no netlist/SDC change'}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    source=p.add_mutually_exclusive_group(required=True)
    source.add_argument('--netlist',type=Path);source.add_argument('--graph',type=Path)
    p.add_argument('--top',required=True)
    p.add_argument('--libs',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();mod=read_graph(a.graph,a.top) if a.graph else read_module(a.netlist,a.top)
    r=Recognizer(mod,read_liberty(a.libs)).run()
    a.out.write_text(json.dumps(r,indent=2)+'\n')
    for x in r['pairs']:
        if any('\t' in x[k] or '\n' in x[k] for k in ('ff','d','q')):raise Reject('unsafe TSV name')
        print('\t'.join(x[k] for k in ('q','ff','d')))


if __name__=='__main__':main()
