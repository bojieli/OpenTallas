#!/usr/bin/env python3
"""Candidate degree-eight calendar using source-pinned actual quarter bridge.

Expanded native V2 and separate real bridge command words are emitted. The
additional bridge issuer/catalog join and physical/FEC joins remain open.
"""
import argparse,collections,json,pathlib
from g96_calendar import Resources,Gearbox,CalendarError,exact_tree,lower_expanded,operation,PRICE
RING=[0,1,3,2]
OFFSETS=[1,4,16,24]

def quarter_path(a,b):
    i,j=RING.index(a),RING.index(b)
    cw=(j-i)%4;ccw=(i-j)%4
    step=1 if cw<=ccw else -1
    return [RING[(i+step*k)%4] for k in range(min(cw,ccw)+1)]

def topology():
    edges=[]
    for rank in range(96):
        for q,step in enumerate(OFFSETS):
            for rail,sign in enumerate((1,-1)):
                edges.append(dict(src=rank,dst=(rank+sign*step)%96,quadrant=q,rail=rail,dst_rail=1-rail))
    return edges

class Compiler:
    def __init__(self,relay_edges=0,interleave=False,local_retime=False):
        self.local_retime=local_retime;self.interleave=interleave;self.r=Resources(defer_replay=True);self.gb={};self.bridge=[];self.rx=[];self.relay_edges=relay_edges
        self.links=collections.defaultdict(list)
        for x in topology():self.links[x['src']].append(x)
        self.undo=[]
    def bridge_route(self,rank,srcq,dstq,source,output,edge,identity):
        path=quarter_path(srcq,dstq);r=self.r
        for a,b in zip(path,path[1:]):
            direction=0 if (RING.index(b)-RING.index(a))%4==1 else 1
            npt=3 if a==0 else 2;out=2*npt+direction
            self.select(rank,a,source,out,edge,identity)
            # Native bridge output C+1; next input C+2, plus real relay FFs.
            r.reserve(f'd{rank}.quarterwire.{a}.{b}',edge,identity)
            edge+=2+self.relay_edges
            source=(3 if b==0 else 2)+direction
        self.select(rank,dstq,source,output,edge,identity)
        return edge+2
    def select(self,rank,q,source,out,edge,identity):
        owner=f'd{rank}q{q}'
        self.r.reserve(f'{owner}.bridge.input{source}',edge,identity)
        key=(f'{owner}.bridge.output{out}',edge)
        old=self.r.events.get(key)
        if old is not None and old[1]==identity:
            # Real multicast copies with identical full545 identity may meet.
            # Capture/expect every input, select the already chosen copy once.
            self.bridge.append(dict(owner=owner,cycle=edge,source=source,out=None,identity=identity))
            return
        self.r.reserve(key[0],edge,(source,identity))
        self.bridge.append(dict(owner=owner,cycle=edge,source=source,out=out,identity=identity))
    def rxface(self,rank,q,port,edge,bridge,identity):
        owner=f'd{rank}q{q}'
        self.r.reserve(f'{owner}.rxface{port}',edge,(bridge,identity))
        self.rx.append(dict(owner=owner,cycle=edge,port=port,bridge=bridge,identity=identity))
        return edge+2
    def hop(self,x,lq,capture,source,identity,prepare=None):
        a,b,p,rail=x['src'],x['dst'],x['quadrant'],x['rail'];dr=x['dst_rail'];r=self.r
        owner=f'd{a}q{lq}';key=f'd{a}q{p}r{rail}'
        # Logical quarter uses the existing native rail-TX0/1 bridge inputs.
        r.qroute(owner,source,rail,capture,identity)
        write=self.bridge_route(a,lq,p,rail,rail,capture+3,identity)
        box=self.gb.setdefault(key,Gearbox(tx_edges=5,insert_holes=True))
        def attempt(extra):
            read=accept-6
            r.replay_use(key,seq,write,read)
            r.reserve(f'd{b}q{p}.rxrail{dr}',receive-1,(seq,identity))
            r.reserve(f'd{b}q{p}.rxseq{dr}',receive-2,seq)
            r.edges.append(dict(id=identity,src=a,dst=b,q=p,logical_q=lq,rail=rail,dst_rail=dr,capture=capture,write=write,read=read,slot=seq%64,seq=seq,gearbox_ordinal=j,accept=accept,receive=receive))
            # All endpoint RX first traverses the source quarter's actual RX mux.
            localcap=self.rxface(b,p,dr,receive+1,False,identity)
            if p==lq:
                if prepare:prepare(b,localcap,2+dr)
                return localcap,2+dr
            # No invented direct RX->bridge path. Native qslots forwards it first.
            r.qroute(f'd{b}q{p}',2+dr,dr,localcap,identity)
            npt=3 if lq==0 else 2
            ejected_consume=self.bridge_route(b,p,lq,dr,npt+dr,localcap+3,identity)
            destcap=self.rxface(b,lq,dr,ejected_consume,True,identity)
            if prepare:prepare(b,destcap,2+dr)
            return destcap,2+dr
        for extra in range(512 if self.local_retime and prepare else 1):
            mark=len(r.txlog);marks=(len(r.edges),len(r.qroutes),len(self.bridge),len(self.rx));j=None
            try:
                j,accept,receive,seq=box.reserve_after(write+10+extra,identity,write)
                result=attempt(extra)
                self.undo.append((box,j))
                return result
            except CalendarError:
                for event in reversed(r.txlog[mark:]):
                    if event[0]=='event':del r.events[event[1]]
                    elif event[2] is None:r.replay.pop(event[1],None)
                    else:r.replay[event[1]]=event[2]
                del r.txlog[mark:]
                if j is not None:del box.used[j];box.next_seq-=1
                del r.edges[marks[0]:];del r.qroutes[marks[1]:];del self.bridge[marks[2]:];del self.rx[marks[3]:]
        raise CalendarError('no statically safe native replay read reservation')
    def transaction(self,earliest,fn):
        r=self.r
        for delay in range(20000):
            r.txlog=[];marks=(len(r.edges),len(r.qroutes),len(self.bridge),len(self.rx));self.undo=[]
            try:
                value=fn(earliest+delay);r.txlog=None
                return earliest+delay,value
            except CalendarError:
                for event in reversed(r.txlog):
                    if event[0]=='event':del r.events[event[1]]
                    elif event[2] is None:r.replay.pop(event[1],None)
                    else:r.replay[event[1]]=event[2]
                for box,j in reversed(self.undo):del box.used[j];box.next_seq-=1
                del r.edges[marks[0]:];del r.qroutes[marks[1]:];del self.bridge[marks[2]:];del self.rx[marks[3]:]
                r.txlog=None
        raise CalendarError('candidate bridge compile search exhausted')
    def path(self,src,dst):
        todo=collections.deque([(src,[])]);seen={src}
        while todo:
            a,path=todo.popleft()
            if a==dst:return path
            for x in self.links[a]:
                if x['dst'] not in seen:seen.add(x['dst']);todo.append((x['dst'],path+[x]))
        raise CalendarError('unreachable candidate rank')
    def multicast_tree(self,root):
        todo=collections.deque([root]);seen={root};edges=[]
        while todo:
            a=todo.popleft()
            for x in self.links[a]:
                b=x['dst']
                if b not in seen:seen.add(b);todo.append(b);edges.append(x)
        assert len(edges)==95
        return edges
    def compile(self):
        r=self.r;adds=[];broadcasts=[];last=0
        for d in range(96):
            for q in range(4):
                for t in range(16):
                    r.qroute(f'd{d}q{q}',0,(3 if q==0 else 2)+12,12+t,(d,q,t,'input'))
                    r.tag_load(f'd{d}q{q}',t,15+t,d)
        for level in range(3):
            step=1<<level
            for group in range(12):
                for base in range(group*8,(group+1)*8,2*step):
                    for q in range(4):
                        left,right=f'd{base}q{q}',f'd{base+step}q{q}';npt=3 if q==0 else 2
                        for tag in range(16):
                            ls,rs=r.tags[(left,tag)],r.tags[(right,tag)];other=rs['identity'];before=ls['identity']
                            identity=f'red.l{level}.g{group}.p{base}.q{q}.t{tag}';path=self.path(base+step,base)
                            def plan(c):
                                source=npt+6
                                for x in path:c,source=self.hop(x,q,c,source,identity)
                                return r.qroute(left,source,npt+12,c,identity)
                            first,arrival=self.transaction(max(ls['ready'],rs['ready'])+2,plan)
                            r.publish(right,tag,tag,first-2,False,identity);r.tag_add(left,tag,arrival,before,other)
                            adds.append(dict(group=group,level=level,rank=base,q=q,tag=tag,read=arrival,issue=arrival+1,writeback=arrival+9,tree=r.tags[(left,tag)]['identity']))
        tasks=([(g,q,p) for p in range(8) for g in range(12) for q in range(4)] if self.interleave else [(g,q,p) for g in range(12) for q in range(4) for p in range(8)])
        for group,q,pair in tasks:
            root=group*8;tree=self.multicast_tree(root);owner=f'd{root}q{q}';npt=3 if q==0 else 2
            ta,tb=pair*2,pair*2+1;ready=max(r.tags[(owner,ta)]['ready'],r.tags[(owner,tb)]['ready'])
            identity=f'bf16.g{group}.q{q}.pair{pair}'
            def plan(c):
                arrivals={root:(c,npt+6)};finish=c+2
                r.qroute(owner,npt+6,npt,c,identity)
                children=collections.defaultdict(list)
                for e in tree:children[e['src']].append(e)
                def prepare(rank,cap,source):
                    r.qroute(f'd{rank}q{q}',source,npt,cap,identity)
                    for e in children[rank]:
                        rail=e['rail'];portq=e['quadrant']
                        r.qroute(f'd{rank}q{q}',source,rail,cap,identity)
                        self.bridge_route(rank,q,portq,rail,rail,cap+3,identity)
                for x in tree:
                    a,b=x['src'],x['dst'];cap,source=arrivals[a]
                    dstcap,dstsource=self.hop(x,q,cap,source,identity,prepare if self.local_retime else None)
                    arrivals[b]=(dstcap,dstsource)
                    r.qroute(f'd{b}q{q}',dstsource,npt,dstcap,identity)
                    finish=max(finish,dstcap+2)
                return finish
            first,finish=self.transaction(ready+2,plan)
            r.publish(owner,ta,tb,first-2,True,identity);last=max(last,finish)
            broadcasts.append(dict(group=group,q=q,pair=pair,pub_read=first-2,pub_issue=first-1,last_delivery=finish))
        assert not r.tags
        for a in adds:
            if a['level']==2:assert a['tree']==exact_tree(list(range(a['group']*8,a['group']*8+8)))
        by=collections.defaultdict(list)
        for e in r.edges:by[f'd{e["src"]}q{e["q"]}r{e["rail"]}'].append(e)
        for key,edges in by.items():
            ordered=sorted(edges,key=lambda e:e['read']);assert [e['write'] for e in ordered]==sorted(e['write'] for e in edges)
            ownership={}
            for seq,e in enumerate(ordered):
                assert seq<65536;slot=seq%64
                if slot in ownership and e['write']<ownership[slot]+4:raise CalendarError('native replay64 lifetime')
                ownership[slot]=e['read'];e['seq']=seq;e['slot']=slot
                old=self.gb[key].used[e['gearbox_ordinal']];self.gb[key].used[e['gearbox_ordinal']]=(seq,old[1],old[2])
        return dict(status='CANDIDATE_COMPONENT_SCHEDULE_ONLY',cycles=last,ratio=last/PRICE,within_110percent=last<=PRICE*1.1,arithmetic=adds,broadcasts=broadcasts,loads=r.loads,publications=r.pubs,qroutes=r.qroutes,transport_hops=r.edges,endpoint_slots={k:v.trace() for k,v in self.gb.items()},bridge=self.bridge,rx_faces=self.rx,reserved_resources=len(r.events),relay_edges_per_quarter_link=self.relay_edges)

def bridge_words(full):
    result=collections.defaultdict(dict)
    def emit(o,c,mask,bits):
        old=result[o].get(c,0)
        if old&mask and old&mask!=bits:raise CalendarError('bridge command conflict')
        result[o][c]=(old&~mask)|bits
    for x in full['bridge']:
        o,c,s,d=x['owner'],x['cycle'],x['source'],x['out'];npt=3 if o.endswith('q0') else 2;ns=npt+2;nd=2*npt+2;sw=3 if npt==3 else 2
        emit(o,c,1<<s,1<<s)
        if d is None:continue
        emit(o,c,1<<(ns+d),1<<(ns+d))
        shift=ns+nd+sw*d;emit(o,c,((1<<sw)-1)<<shift,s<<shift)
    for x in full['rx_faces']:
        o,c,p,b=x['owner'],x['cycle'],x['port'],x['bridge'];npt=3 if o.endswith('q0') else 2;shift=(37 if npt==3 else 22)+4*p
        bits=(int(not b)|(int(b)<<1)|4|(int(b)<<3))<<shift
        emit(o,c,15<<shift,bits)
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('out',type=pathlib.Path);p.add_argument('--layout',type=pathlib.Path,required=True);p.add_argument('--relay-edges',type=int,default=0);p.add_argument('--interleave-groups',action='store_true');p.add_argument('--local-retime',action='store_true');a=p.parse_args()
    if a.relay_edges<0:raise ValueError('negative relay stages')
    a.out.mkdir(parents=True,exist_ok=True)
    full=Compiler(a.relay_edges,a.interleave_groups,a.local_retime).compile();words,summary=lower_expanded(full,json.loads(a.layout.read_text()));full['expanded_program_summary']=summary
    bw=bridge_words(full)
    for name,code in [('expanded_uops',words),('expanded_bridge',bw)]:
        with (a.out/(name+'.jsonl')).open('w') as f:
            for owner,events in sorted(code.items()):
                for c,w in sorted(events.items()):f.write(json.dumps(dict(owner=owner,cycle=c,word=hex(w)))+'\n')
    (a.out/'calendar.json').write_text(json.dumps(full)+'\n')
    receipt=dict(operation=operation(),cycles=full['cycles'],ratio=full['ratio'],within_110percent=full['within_110percent'],physical_links=len(topology()),candidate_offsets=OFFSETS,rank_diameter=4,bridge_source='d72069aec',relay_edges=a.relay_edges,interleave_groups=a.interleave_groups,local_retime=a.local_retime,physical='All port/package/FEC/clock/geometry bindings unqualified; zero relay is a lower bound only',program='Native V2 expanded1536 and separate actual49/30-bit bridge commands; actual extra catalog/issuer integration and64-row compression absent',sources=dict(parent='cc6d946ad',endpoint='cc12ab88a TX5/RX1',transport='359252cc2'),counts={k:len(full[k]) for k in ['arithmetic','publications','qroutes','transport_hops','bridge','rx_faces']})
    (a.out/'model.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt,indent=2))
if __name__=='__main__':main()
