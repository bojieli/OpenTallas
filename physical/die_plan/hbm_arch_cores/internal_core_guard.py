"""Typed INTERNAL_CORE endpoint census; never a partition face-register exemption.

README R2 permits direct internal tiles only when timed in partition sign-off.
This gate inventories every reachable sequential/SRAM endpoint and rejects
unclassified leaves, missing arcs, feedthrough, constants and combinational loops.
Actual placed reach, TT/FF timing and related-pair skew remain required gates.
"""
import hashlib,json,re
from collections import defaultdict
from pathlib import Path
import face_guard as FG


def blocks(text,kind):
    for m in re.finditer(r'\b'+kind+r'\s*\(\s*"?([^\s)"{}]+)"?\s*\)\s*\{',text):
        level=1;i=m.end()
        while level and i<len(text):
            level+=(text[i]=='{')-(text[i]=='}');i+=1
        if level:raise ValueError('unbalanced Liberty '+kind)
        yield m.group(1),text[m.end():i-1]


def macro_models(kd,masters):
    result={}
    for master in masters:
        corners={};hashes={}
        for corner in ('tt','ff'):
            path=kd/'macros'/(master+'_'+corner+'.lib');raw=path.read_bytes();hashes[corner]=hashlib.sha256(raw).hexdigest()
            cells=dict(blocks(raw.decode(),'cell'));body=cells[master]
            corners[corner]={}
            for name,pin in list(blocks(body,'pin'))+list(blocks(body,'bus')):
                direction=re.search(r'\bdirection\s*:\s*(input|output)\s*;',pin)
                if not direction:continue
                arcs=[]
                for r in re.finditer(r'related_pin\s*:\s*"([^"]+)"\s*;\s*timing_type\s*:\s*(\w+)\s*;',pin):arcs.append(r.groups())
                corners[corner][name]=dict(direction=direction.group(1),arcs=arcs)
        pins={}
        for name,tt in corners['tt'].items():
            ff=corners['ff'].get(name)
            if not ff or tt['direction']!=ff['direction']:raise ValueError(master+' mismatched TT/FF '+name)
            clk=re.search(r'\bclock\s*:\s*true\s*;',dict(list(blocks(dict(blocks((kd/'macros'/(master+'_tt.lib')).read_text(),'cell'))[master],'pin'))).get(name,''))
            tta=tt['arcs'];ffa=ff['arcs'];related={a for a,t in tta+ffa}
            synchronous=(tt['direction']=='input' and any(t=='setup_rising' for _,t in tta) and any(t=='hold_rising' for _,t in ffa)) or (tt['direction']=='output' and all(any(t=='rising_edge' for _,t in a) for a in (tta,ffa)))
            pins[name]=dict(direction=tt['direction'],clock=bool(clk),synchronous=synchronous,related_clocks=sorted(related),tt_arcs=tta,ff_arcs=ffa)
        result[master]=dict(pins=pins,liberty_sha256=hashes)
    return result


def guard(text,top,kd,fz,skip):
    contract=fz['source_profile']['endpoint_contract']
    if contract.get('kind')!='INTERNAL_CORE' or fz.get('face_shell') is not None:raise ValueError('INTERNAL_CORE requires explicit no-shell native cut')
    if contract.get('partition_rule')!='R2_INTERNAL_TIMED_IN_PARTITION':raise ValueError('missing partition timing contract')
    models=macro_models(kd,fz['macros']);mods=FG.parse(text)
    for master in models:mods.pop(master,None) # retain opaque timed memory leaves
    T=mods[top];F=FG.Flat(mods,top);roots={b:F.find(b) for p in T.ports for b in FG._bits_of(T,p)}
    clock_roots={roots[b] for b in roots if b in fz['clocks'] or b.split('[')[0] in fz['clocks']}
    loads=defaultdict(list);drivers=defaultdict(list);endpoints=[];edges=[defaultdict(set),defaultdict(set)];ends=[defaultdict(set),defaultdict(set)];bad=[defaultdict(set),defaultdict(set)]
    for master,path,pins in F.cells:
        if master in models:
            model=models[master]['pins'];new={}
            for pin,(_,bits) in pins.items():
                if pin not in model:raise ValueError('unmodelled SRAM pin '+master+'.'+pin)
                new[pin]=('out' if model[pin]['direction']=='output' else 'in',bits)
            pins=new
        ins=[F.find(b) for pin,(d,bits) in pins.items() if d=='in' for b in bits];outs=[F.find(b) for pin,(d,bits) in pins.items() if d=='out' for b in bits]
        for pin,(direction,bits) in pins.items():
            for bi,b in enumerate(bits):
                root=F.find(b);(loads if direction=='in' else drivers)[root].append((master,path,pin))
                if master in models:
                    pm=models[master]['pins'][pin]
                    if pm['clock']:continue
                    clocks={F.find(c) for cp in pm['related_clocks'] for c in pins.get(cp,('',[]))[1]}
                    sequential=pm['synchronous'] and bool(clocks) and clocks<=clock_roots
                    kind='SRAM_'+('INPUT' if direction=='in' else 'OUTPUT')
                elif FG.is_ff(master):
                    if pin in ('CLK','CK','C'):continue
                    clocks={F.find(c) for cp in ('CLK','CK','C') for c in pins.get(cp,('',[]))[1]}
                    sequential=(pin=='D' if direction=='in' else pin in ('Q','QN')) and bool(clocks) and clocks<=clock_roots
                    kind='REGISTER_'+('D' if direction=='in' else 'Q')
                else:continue
                sense=0 if direction=='in' else 1
                if sequential:
                    item=dict(kind=kind,master=master,instance=path,pin=pin,pin_bit=len(bits)-1-bi,net=root,clock_nets=sorted(clocks));ei=len(endpoints);endpoints.append(item);ends[sense][root].add(ei)
                else:bad[sense][root].add(path+'.'+pin+' lacks qualified same-domain sequential arc')
        if not FG.is_ff(master) and master not in models:
            if not ins or not outs:
                for r in ins:bad[0][r].add(path+' unclassified leaf '+master)
                for r in outs:bad[1][r].add(path+' unclassified source '+master)
            for a in ins:
                for b in outs:edges[0][a].add(b);edges[1][b].add(a)
    boundary=[set(),set()]
    for p in T.ports:
        if not re.match(skip,p):
            for b in FG._bits_of(T,p):boundary[0 if T.dirs[p]=='output' else 1].add(roots[b])
    unused_internal_outputs=[dict(classification='UNUSED_INTERNAL_STDCELL_OUTPUT',master=m,instance=path,pin=pin,net=root,top_port_consumers=[]) for root,ds in drivers.items() if not loads[root] and root not in set(roots.values()) for m,path,pin in ds if m not in models and not FG.is_ff(m)]
    cache=[{},{}];visiting=[set(),set()]
    def walk(root,sense):
        if root in cache[sense]:return cache[sense][root]
        if root in visiting[sense]:return frozenset(),frozenset({'COMBINATIONAL_LOOP '+root})
        if root.startswith('CONST_'):return frozenset(),frozenset()
        visiting[sense].add(root);found=set(ends[sense][root]);fail=set(bad[sense][root])
        if len(drivers[root])>1:fail.add('MULTIPLE_DRIVERS '+root)
        if root in boundary[sense]:fail.add('COMBINATIONAL_FEEDTHROUGH '+root)
        for nxt in edges[sense][root]:
            a,b=walk(nxt,sense);found.update(a);fail.update(b)
        visiting[sense].remove(root);ans=frozenset(found),frozenset(fail);cache[sense][root]=ans;return ans
    ports={};fails={}
    for port in T.ports:
        if re.match(skip,port):continue
        direction=T.dirs[port]
        if direction not in ('input','output'):raise ValueError('inout '+port)
        for bit in FG._bits_of(T,port):
            root=roots[bit];sense=0 if direction=='input' else 1;found,fail=walk(root,sense)
            opposite=[b for b,r in roots.items() if r==root and T.dirs[re.sub(r'\[.*','',b)]!=direction and not re.match(skip,b.split('[')[0])]
            if opposite:fail=fail|{'FEEDTHROUGH '+','.join(opposite)}
            ports[bit]=dict(direction=direction,endpoints=sorted(found),direct_loads=len(loads[root]),direct_drivers=len(drivers[root]))
            if fail or not found:fails[bit]=sorted(fail or {'NO_ENDPOINT'})
    return dict(top=top,contract=contract,verdict='PASS' if not fails else 'FAIL',checked=len(ports),ok=len(ports)-len(fails),fails=fails,ports=ports,endpoints=endpoints,unused_internal_outputs=unused_internal_outputs,macro_models=models,netlist_sha256=hashlib.sha256(text.encode()).hexdigest(),required_next=['ALL_PLACED_ENDPOINT_REACH','TT_SETUP_833PS_U60','FF_HOLD_U25','RELATED_PAIR_CPPR_LE80PS','PARTITION_COMPOSED_SIGNOFF'])


if __name__ == '__main__':
    import argparse,sys
    ap=argparse.ArgumentParser();ap.add_argument('netlist',type=Path);ap.add_argument('kit',type=Path);ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    fz=json.loads((a.kit/'freeze.json').read_text());skip='^('+ '|'.join(re.escape(re.sub(r'\[\d+\]$','',n)) for n in fz['clocks']+fz['resets'])+')$'
    result=guard(a.netlist.read_text(),fz['design'],a.kit,fz,skip);a.out.parent.mkdir(parents=True,exist_ok=True)
    if a.out.exists():raise SystemExit('refusing to replace existing endpoint verdict')
    a.out.write_text(json.dumps(result,indent=1)+'\n');print('INTERNAL_CORE',result['verdict'],result['ok'],'/',result['checked'],'signal bits;',len(result['unused_internal_outputs']),'unused internal stdcell outputs')
    sys.exit(0 if result['verdict']=='PASS' else 1)
