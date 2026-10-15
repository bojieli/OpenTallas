#!/usr/bin/env python3
"""Fixed-edge G96 group-reduce calendar primitives, native V2 and 613/487.

A route graph is mandatory for production lowering. No all-to-all or ideal
core-cycle link may silently stand in for the nine actual rails per die.
"""
from __future__ import annotations
import argparse,collections,hashlib,json,pathlib
G=96;SUB=8;N=1024;QUADS=4;LANES=16;TAGS=16;F=613;W=487;PRICE=1325.9

class CalendarError(ValueError):pass

class Resources:
    def __init__(self,defer_replay=False):self.defer_replay=defer_replay;self.events={};self.tags={};self.replay={};self.edges=[];self.qroutes=[];self.loads=[];self.pubs=[];self.txlog=None
    def reserve(self,unit,cycle,identity):
        k=(str(unit),int(cycle))
        if k in self.events and self.events[k]==identity:return
        if k in self.events:raise CalendarError(f'resource collision {k}: {self.events[k]} / {identity}')
        self.events[k]=identity
        if self.txlog is not None:self.txlog.append(("event",k))
    def tag_load(self,owner,tag,cycle,identity):
        if not 0<=tag<TAGS:raise CalendarError('tag outside native16')
        k=(owner,tag)
        if k in self.tags:raise CalendarError(f'occupied tag {k}')
        self.tags[k]={'ready':cycle+1,'identity':identity,'pending':False}
        self.reserve(f'{owner}.reduce.input',cycle,('load',tag,identity))
        self.loads.append({'owner':owner,'tag':tag,'cycle':cycle,'rank':identity})
    def tag_add(self,owner,tag,cycle,left,right):
        k=(owner,tag);s=self.tags.get(k)
        if s is None or s['ready']>cycle or s['pending'] or s['identity']!=left:raise CalendarError(f'bad exact left operand {k} at{cycle}')
        self.reserve(f'{owner}.reduce.input',cycle,('add_read',tag,right))
        self.reserve(f'{owner}.reduce.issue',cycle+1,('add_issue',tag))
        self.reserve(f'{owner}.reduce.writeback',cycle+9,tag)
        # LAT8 result write at issue+8; readable only at issue+9.
        s.update(ready=cycle+10,identity=(left,right),pending=False)
        return s['ready']
    def publish(self,owner,a,b,cycle,bf16,identity,release=True):
        tags=[a,b] if bf16 else [a]
        if len(set(tags))!=len(tags):raise CalendarError('BF16 publication requires two distinct tags')
        for t in tags:
            s=self.tags.get((owner,t))
            if s is None or s['ready']>cycle:raise CalendarError(f'publication before native write visible {(owner,t)}')
        self.reserve(f'{owner}.reduce.pubread',cycle,(tags,bf16,identity))
        self.reserve(f'{owner}.reduce.pubissue',cycle+1,(tags,bf16,identity))
        if release:
            for t in tags:del self.tags[(owner,t)]
        self.pubs.append({'owner':owner,'tags':tags,'read':cycle,'issue':cycle+1,'bf16':bf16,'identity':identity,'release':release})
        return cycle+1
    def qroute(self,owner,source,sink,capture,identity):
        self.reserve(f'{owner}.qsrc{source}',capture,identity)
        self.reserve(f'{owner}.qsink{sink}',capture+1,identity)
        self.qroutes.append({'owner':owner,'source':source,'sink':sink,'capture':capture,'identity':identity})
        return capture+3 # registered output capture+2, child samples+3
    def replay_use(self,link,sequence,write,read):
        if not 0<=sequence<65536:raise CalendarError('logical sequence wrap')
        if read<write+1:raise CalendarError('read before native publication')
        k=(link,sequence%64);old=self.replay.get(k)
        # Native ownership includes v2/v3/v4 plus captured write metadata.
        # Reuse after old read+4, independent of physical flight.
        if not self.defer_replay and old and write<old['read']+4:raise CalendarError(f'replay64 lifetime conflict {k}')
        if self.txlog is not None:self.txlog.append(('replay',k,old))
        self.replay[k]={'sequence':sequence,'write':write,'read':read}
        self.reserve(f'{link}.wr',write,sequence);self.reserve(f'{link}.rd',read,sequence)
        self.reserve(f'{link}.wr_seq',write-1,sequence);self.reserve(f'{link}.rd_seq',read-1,sequence)
    def ring(self,owner,direction,send,receive,identity):
        if direction not in (0,1) or receive<send+2:raise CalendarError('invalid real ring hop')
        self.reserve(f'{owner}.ring.tx{direction}',send,identity)
        self.reserve(f'{owner}.ring.rx{direction}',receive,identity)

class Gearbox:
    """Unconditional 613/487 slots including idles. Input valid never schedules."""
    def __init__(self,start=17,tx_edges=3,word_flight=3,insert_holes=False):
        self.insert_holes=insert_holes;self.start=start;self.tx_edges=tx_edges;self.word_flight=word_flight;self.used={};self.next_seq=0
    def accept(self,j):return self.start+(F*j)//W
    def recover_index(self,j):return (F*(j+1)+W-1)//W-1
    def reserve_after(self,earliest,identity,write=None):
        j=max(0,((earliest-self.start)*W)//F-1)
        ceiling=None
        if self.used:
            if not self.insert_holes:j=max(j,max(self.used)+1)
            else:
                # Both native write and read counters must see the same order.
                before=[k for k,v in self.used.items() if v[2]<=write]
                after=[k for k,v in self.used.items() if v[2]>write]
                if before:j=max(j,max(before)+1)
                if after:ceiling=min(after)
        while self.accept(j)<earliest or j in self.used:j+=1
        if ceiling is not None and j>=ceiling:raise CalendarError('no chronological gearbox hole')
        self.used[j]=(self.next_seq,identity,write);self.next_seq+=1
        if self.next_seq>65536:raise CalendarError('endpoint sequence overflow')
        return j,self.accept(j),self.start+7+self.recover_index(j),self.next_seq-1
    def trace(self):
        if not self.used:return []
        return [{'slot_ordinal':j,'accept':self.accept(j),'endpoint_read':self.accept(j)-1-self.tx_edges,
                 'endpoint_rx_expect':self.start+6+self.recover_index(j),
                 'endpoint_rx_publish':self.start+7+self.recover_index(j),
                 'valid':j in self.used,'sequence':self.used[j][0] if j in self.used else None}
                for j in range(max(self.used)+1)]

def exact_tree(leaves):
    if len(leaves)!=8:raise CalendarError('subgroup must have8')
    x=list(leaves)
    while len(x)>1:x=[(x[j],x[j+1]) for j in range(0,len(x),2)]
    return x[0]

def operation():
    return {'kind':'GROUP_REDUCE_MCAST','G':G,'subgroup':SUB,'n_FP32_per_rank':N,
            'n_BF16_per_rank_output':N*(G//SUB),'quadrants':4,'FP32_flits_per_quadrant':16,
            'BF16_flits_per_subgroup_per_quadrant':8,'BF16_flits_output_per_quadrant':96,
            'exact_tree':{'subgroup0':exact_tree(list(range(8))),'rounding':'FP32 native RNE after each pair; BF16 RNE exactly once at final root, two native16lane tags per publication'},
            'immutable_price_cycles':PRICE,'immutable_price_110percent':PRICE*1.1}

def verify_routes(v):
    links=v.get('links',[]);by={};ports=set()
    for x in links:
        a,b=x['src'],x['dst'];rail=x['rail'];q=x['quadrant']
        if not 0<=a<G or not 0<=b<G or a==b or not 0<=q<4:raise CalendarError('invalid physical link endpoint')
        if not 0<=rail<(3 if q==0 else 2):raise CalendarError('rail outside actualq3/q2')
        key=(a,q,rail)
        if key in ports:raise CalendarError('physical rail has multiple destinations')
        ports.add(key);by[(a,b,q)]=x
    if not v.get('source_binding'):raise CalendarError('route graph requires authoritative source binding')
    return by

def compile_candidate(routes,tx_edges,bidirectional=False,insert_holes=False):
    by=verify_routes(routes);r=Resources(defer_replay=insert_holes);gb={};links_by_source=collections.defaultdict(list)
    for (a,b,q),x in by.items():links_by_source[(a,q)].append((b,x))
    def route(src,dst,q):
        todo=collections.deque([(src,[]) ]);seen={src}
        while todo:
            node,path=todo.popleft()
            if node==dst:return path
            for nxt,x in links_by_source[(node,q)]:
                if nxt not in seen:seen.add(nxt);todo.append((nxt,path+[x]))
        raise CalendarError(f'no physical route {src}->{dst} quadrant{q}')
    def transmit(path,earliest,identity,final_sink=None,deliver_each=False,deliver_local=False):
        # Planning is transactional. Re-plan the source start if a future
        # resource is occupied; this is compiler search, never runtime delay.
        nonlocal r,gb
        for delay in range(200000):
            r.txlog=[];oldedges=len(r.edges);oldroutes=len(r.qroutes);gbundo=[];capture=earliest+delay;first=capture
            try:
                if deliver_local:
                    x=path[0];q=x['quadrant'];npt=3 if q==0 else 2
                    r.qroute(f'd{x["src"]}q{q}',npt+6,npt,capture,identity['id'])
                for h,x in enumerate(path):
                    a,b,q,rail=x['src'],x['dst'],x['quadrant'],x['rail'];owner=f'd{a}q{q}';key=f'd{a}q{q}r{rail}'
                    source=identity['source'] if h==0 else 2+path[h-1].get('dst_rail',path[h-1]['rail'])
                    if h==0 and source=='reduce':source=9 if q==0 else 8
                    write=r.qroute(owner,source,rail,capture,identity['id'])
                    box=gb.setdefault(key,Gearbox(tx_edges=tx_edges,insert_holes=insert_holes))
                    j,accept,receive,sequence=box.reserve_after(write+5+tx_edges,identity['id'],write)
                    gbundo.append((box,j))
                    read=accept-1-tx_edges
                    r.replay_use(key,sequence,write,read)
                    r.reserve(f'd{b}q{q}.rxrail{x.get("dst_rail",rail)}',receive-1,(sequence,identity['id']))
                    r.reserve(f'd{b}q{q}.rxseq{x.get("dst_rail",rail)}',receive-2,sequence)
                    r.edges.append({'id':identity['id'],'src':a,'dst':b,'q':q,'rail':rail,'dst_rail':x.get('dst_rail',rail),
                                    'capture':capture,'write':write,'read':read,'slot':sequence%64,'seq':sequence,
                                    'gearbox_ordinal':j,'accept':accept,'receive':receive})
                    capture=receive+1
                    if deliver_each:
                        npt=3 if q==0 else 2
                        r.qroute(f'd{b}q{q}',2+x.get('dst_rail',rail),npt,capture,identity['id'])
                if final_sink is not None:
                    x=path[-1];q=x['quadrant'];b=x['dst']
                    arrival=r.qroute(f'd{b}q{q}',2+x.get('dst_rail',x['rail']),final_sink,capture,identity['id'])
                else:arrival=capture
                r.txlog=None
                return first,arrival
            except CalendarError:
                for entry in reversed(r.txlog):
                    if entry[0]=='event':del r.events[entry[1]]
                    elif entry[2] is None:r.replay.pop(entry[1],None)
                    else:r.replay[entry[1]]=entry[2]
                for box,j in reversed(gbundo):del box.used[j];box.next_seq-=1
                del r.edges[oldedges:];del r.qroutes[oldroutes:];r.txlog=None
                continue
        raise CalendarError('candidate compiler search exhausted; no resource-safe fixed schedule')
    # All96*4 quarter reducers load exactly16 native FP32 tags. Declared SU
    # boundary input only: no internal results injected or native SU claim.
    for d in range(G):
        for q in range(4):
            for t in range(16):
                r.qroute(f'd{d}q{q}',0,(3 if q==0 else 2)+12,12+t,(d,q,t,'input'))
                r.tag_load(f'd{d}q{q}',t,15+t,d)
    arithmetic=[]
    for level in range(3):
        step=1<<level
        for group in range(12):
            for base in range(group*8,(group+1)*8,2*step):
                left,right=base,base+step
                for q in range(4):
                    left_o=f'd{left}q{q}';right_o=f'd{right}q{q}'
                    for t in range(16):
                        l=r.tags[(left_o,t)];rr=r.tags[(right_o,t)];ready=max(l['ready'],rr['ready'])
                        ident={'id':f'red.l{level}.g{group}.p{base}.q{q}.t{t}','source':'reduce'}
                        first,arrival=transmit(route(right,left,q),ready+2,ident,(3 if q==0 else 2)+12)
                        r.publish(right_o,t,t,first-2,False,ident['id'])
                        before=l['identity'];other=rr['identity']
                        r.tag_add(left_o,t,arrival,before,other)
                        arithmetic.append({'group':group,'level':level,'rank':left,'q':q,'tag':t,'read':arrival,'issue':arrival+1,'writeback':arrival+9,'tree':r.tags[(left_o,t)]['identity']})
    # A multicast walk must be an actual directed Hamiltonian cycle within each
    # quadrant, explicitly supplied in the candidate graph. No ideal switch.
    last_delivery=0;broadcasts=[]
    for group in range(12):
        source=group*8
        for q in range(4):
            owner=f'd{source}q{q}';walk=routes.get('multicast_walks',{}).get(str(q))
            if walk is None or len(walk)!=96 or set(walk)!=set(range(96)):raise CalendarError('missing actual96rank multicast walk')
            start=walk.index(source);ordered=walk[start:]+walk[:start]
            branches=[ordered]
            if bidirectional:
                branches=[ordered[:49],[source]+list(reversed(ordered[49:]))]
            for pair in range(8):
                ta,tb=pair*2,pair*2+1;ready=max(r.tags[(owner,ta)]['ready'],r.tags[(owner,tb)]['ready'])
                for branch,walk in enumerate(branches):
                    path=[]
                    for src,dst in zip(walk,walk[1:]):
                        if (src,dst,q) not in by:raise CalendarError('multicast requires missing physical edge')
                        path.append(by[(src,dst,q)])
                    ident={'id':f'bf16.g{group}.q{q}.pair{pair}.branch{branch}','source':'reduce'}
                    first,finish=transmit(path,ready+2,ident,deliver_each=True,deliver_local=branch==0)
                    r.publish(owner,ta,tb,first-2,True,ident['id'],release=branch==len(branches)-1)
                    ready=first # second copy publication read cannot sharefirstcopy port
                    last_delivery=max(last_delivery,finish+2)
                    broadcasts.append({'group':group,'q':q,'pair':pair,'branch':branch,'pub_read':first-2,'pub_issue':first-1,'local_capture':first,'last_delivery':finish+2,'rank_order':walk})
    if r.tags:raise CalendarError('live accumulator tags after final publication')
    # Native tree identity must exactly match the normative rank-order pairwise tree.
    for a in arithmetic:
        if a['level']==2 and a['tree']!=exact_tree(list(range(a['group']*8,a['group']*8+8))):raise CalendarError('reassociated reduction tree')
    if insert_holes:
        by_endpoint=collections.defaultdict(list)
        for e in r.edges:by_endpoint[f'd{e["src"]}q{e["q"]}r{e["rail"]}'].append(e)
        for key,edges in by_endpoint.items():
            ordered=sorted(edges,key=lambda e:e['read'])
            if [e['write'] for e in ordered]!=sorted(e['write'] for e in edges):raise CalendarError('native write/read sequence order differs')
            ownership={}
            for seq,e in enumerate(ordered):
                if seq>=65536:raise CalendarError('native sequence overflow')
                slot=seq%64
                if slot in ownership and e['write']<ownership[slot]+4:raise CalendarError('post-lowering replay64 lifetime conflict')
                ownership[slot]=e['read'];e['seq']=seq;e['slot']=slot
                old=gb[key].used[e['gearbox_ordinal']]
                gb[key].used[e['gearbox_ordinal']]=(seq,old[1],old[2])
    trace={k:v.trace() for k,v in gb.items()}
    return {'status':'CANDIDATE_STATIC_CALENDAR_RESOURCE_PASS; not actual RTL/physical qualification',
            'cycles':last_delivery,'immutable_price_cycles':PRICE,'ratio':last_delivery/PRICE,
            'within_110percent':last_delivery<=PRICE*1.1,'arithmetic':arithmetic,'broadcasts':broadcasts,
            'transport_hops':r.edges,'endpoint_slots':trace,'qroutes':r.qroutes,'loads':r.loads,'publications':r.pubs,'reserved_resources':len(r.events),
            'tag_lifetimes':'all16tags perquarter loaded once; each rightsubtree publication releasesits tag; leftsubtree exactorder retained through nativeLAT8; final BF16 releasealltags',
            'program_fit':'Expanded1536 microop lowering and64row counted-loop compression pending; endpointperiod613 may exceed primitive64rowmemory without additional sequencer encoding',
            'ring':'no wide vector on256bit peer ring; routing stays within perquadrant physical vector rails. Ring/read/tag primitives independently checked, no ring operations silently substituted',
            'native_SU':'not claimed; declared input boundary at fixed12edge only'}

def lower_expanded(full,layout):
    import re
    fields=layout['fields'];arfields=layout['ar_fields'];words=collections.defaultdict(dict)
    def emit(owner,cycle,name,value,shift=0,width=None):
        if cycle<0:raise CalendarError('negative instruction edge')
        f=fields[name];lsb=f['lsb']+shift;w=width or f['width']
        if not 0<=value<1<<w:raise CalendarError(f'field overflow {name}')
        mask=((1<<w)-1)<<lsb;old=words[owner].get(cycle,0)
        # Multiple disjoint fields compose the actual lowered V2 word.
        have=old&mask
        if have and have!=(value<<lsb):raise CalendarError(f'instruction conflict {owner} {cycle} {name}')
        words[owner][cycle]=(old&~mask)|(value<<lsb)
    def orfield(owner,cycle,name,value):
        f=fields[name]
        if not 0<=value<1<<f['width']:raise CalendarError('OR field overflow')
        words[owner][cycle]=words[owner].get(cycle,0)|(value<<f['lsb'])
    def ar(owner,cycle,values):
        bits=sum(v<<arfields[k]['lsb'] for k,v in values.items())
        orfield(owner,cycle,'ar_low',bits&((1<<31)-1));orfield(owner,cycle,'ar_high',bits>>31)
    for x in full['qroutes']:
        owner,c,source,sink=x['owner'],x['capture'],x['source'],x['sink']
        if source<10:orfield(owner,c,'capture_slot',1<<source)
        else:raise CalendarError('unexpected ARG source in group reduce')
        orfield(owner,c+1,'sink_slot',1<<sink)
        emit(owner,c+1,'sink_select',source,sink*4,4)
    for x in full['loads']:
        owner,c,t=x['owner'],x['cycle'],x['tag'];q=int(owner.split('q')[1]);rank=x['rank']
        ar(owner,c,{'load_v':1,'load_tag':t})
        req=c-15;orfield(owner,req,'inj_rd',1)
        emit(owner,req,'inj_idx',q*16+t,0,16)
        emit(owner,req,'inj_meta',(1<<32)|(255<<24)|(rank<<16)|(q*16+t),0,33)
    for x in full['arithmetic']:
        owner=f'd{x["rank"]}q{x["q"]}'
        ar(owner,x['read'],{'add_read':1,'read_tag':x['tag']});ar(owner,x['issue'],{'add_issue':1})
    for x in full['publications']:
        tags=x['tags'];ident=x['identity'];match=re.search(r'g(\d+).*q(\d+).*pair(\d+)',ident)
        group,q,pair=map(int,match.groups()) if match else (0,0,0)
        source=group if x['bf16'] else int(x['owner'].split('q')[0][1:])
        index=group*32+q*8+pair if x['bf16'] else tags[0]
        ar(x['owner'],x['read'],{'pub_read':1,'pub_tag_a':tags[0],'pub_tag_b':tags[-1],
             'pub_bf16':int(x['bf16']),'pub_release':int(x['release']),'pub_src':source,'pub_index':index})
        ar(x['owner'],x['issue'],{'pub_issue':1})
    for x in full['transport_hops']:
        owner=f'd{x["src"]}q{x["q"]}';dst=f'd{x["dst"]}q{x["q"]}';rail=x['rail'];dr=x['dst_rail'];seq=x['seq']
        for key,cycle in [('wr',x['write']),('rd',x['read'])]:
            orfield(owner,cycle,'lk_'+key+'_v',1<<rail)
            emit(owner,cycle-1,'lk_'+key+'_slot',seq&63,rail*6,6)
            emit(owner,cycle-1,'lk_'+key+'_seq_high',seq>>6,rail*10,10)
        orfield(dst,x['receive']-1,'lk_rx_expect',1<<dr)
        emit(dst,x['receive']-2,'lk_rx_slot',seq&63,dr*6,6)
        emit(dst,x['receive']-2,'lk_rx_seq_high',seq>>6,dr*10,10)
    summary={}
    for owner,code in words.items():
        q=int(owner.split('q')[1]);emit(owner,0,'lk_epoch_begin',3);emit(owner,0,'lk_epoch',0x35)
        unique=len(set(code.values())|{0})
        summary[owner]={'active_words':len(code),'distinct_expanded_words':unique,'fits64rows_as_direct_words':len(code)<=64,'counted_affine_compression':'UNVERIFIED'}
    return words,summary

def candidate_rings():
    links=[]
    for rank in range(96):
        for q in range(4):
            for rail,delta,dst_rail in [(0,1,1),(1,-1,0)]:
                dst=(rank+delta)%96
                local=rank//4==dst//4
                links.append({'src':rank,'dst':dst,'quadrant':q,'rail':rail,'dst_rail':dst_rail,
                              'scope':'same_package' if local else 'cross_package',
                              'physical_binding':'UNBOUND_CANDIDATE','source_port':[['lk_S0','lk_S1'],['lk_S3','lk_S4'],['lk_N0','lk_N1'],['lk_N2','lk_N3']][q][rail],
                              'destination_port':[['lk_S0','lk_S1'],['lk_S3','lk_S4'],['lk_N0','lk_N1'],['lk_N2','lk_N3']][q][dst_rail],
                              'word_bits_per_coreedge':487,
                              'full_FEC':'required for cross-package; unimplemented in present transport'})
    return {'schema':'hcoll.g96.candidate.routegraph.v1',
            'source_binding':'Owner/root authorized candidate allocation; actual96rank rail types and4die local map are absent. This is not an existing physical map.',
            'placement':'24 candidate packages of4 contiguous ranks',
            'links':links,'multicast_walks':{str(q):list(range(96)) for q in range(4)},
            'unused_actual_rails':[{'rank':d,'quadrant':0,'rail':2,'port':'lk_S2'} for d in range(96)],
            'unbound_resources':{'directed_endpoint_bindings':768,'same_package_directed_edges':576,'cross_package_directed_edges':192,
                                 'cross_package_full_duplex_links':96,'cross_package_links_per_boundary_die':4,
                                 'cross_package_boundary_dies':48,'full_FEC_required_cross_package_links':96,
                                 'clock_domain_and_physical_age':'unbound; candidate wordflight3 only, FEC latency not guessed'},
            'actual_port_inventory_source':'359252cc2:tools/hbm_accel_die_fp.py lines4043-4080; 5 S-edge +4 N-edge SerDes; lk_host separate',
            'status':'CANDIDATE_ALLOCATION_ONLY; package/local-vs-board types and fullFEC physical ports unbound'}

def selftest():
    # Independent mathematical period, wrap, idle and physical reservation checks.
    gb=Gearbox();assert gb.accept(487)-gb.accept(0)==613
    assert gb.recover_index(486)==612
    for j in range(2000):assert gb.accept(j+1)-gb.accept(j) in (1,2)
    r=Resources();r.tag_load('q',0,0,0);r.tag_add('q',0,1,0,1)
    failures=[]
    def reject(label,fn):
        try:fn()
        except CalendarError:failures.append(label)
        else:raise AssertionError('mutant escaped '+label)
    reject('early publication',lambda:r.publish('q',0,0,10,False,'x'))
    reject('wrong exact operand',lambda:r.tag_add('q',0,11,1,0))
    reject('occupied tag',lambda:r.tag_load('q',0,20,0))
    r.publish('q',0,0,11,False,'x');r.tag_load('q',0,13,0)
    r.replay_use('x',0,0,8)
    reject('replay64 overwrite',lambda:r.replay_use('x',64,11,20))
    r.replay_use('x',64,12,20)
    reject('sequence wrap',lambda:r.replay_use('x',65536,50,60))
    r.qroute('q',0,1,0,'a')
    reject('qslot conflict',lambda:r.qroute('q',0,2,0,'b'))
    r.ring('q',0,100,102,'a')
    reject('ring conflict',lambda:r.ring('q',0,100,103,'b'))
    reject('unbound route',lambda:verify_routes({'links':[]}))
    gb.reserve_after(17,'a');gb.reserve_after(30,'b')
    assert any(not s['valid'] for s in gb.trace())
    return failures

def main():
    p=argparse.ArgumentParser();p.add_argument('out',type=pathlib.Path);p.add_argument('--routes',type=pathlib.Path);p.add_argument('--candidate-rings',action='store_true');p.add_argument('--layout',type=pathlib.Path);p.add_argument('--bidirectional',action='store_true');p.add_argument('--insert-holes',action='store_true');p.add_argument('--tx-edges',type=int,choices=(3,5),default=5);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=True);checks=selftest()
    m={'schema':'hcoll.g96.native.calendar.v1','operation':operation(),'primitive_mutants_rejected':checks,
       'sources':{'V2_parent':'cc6d946ad (originala84885466)','transport':'359252cc2','reducer':'bd81c1706','golden':'tools/hgi_sim/machine.py:u_coll_group_reduce_mcast; tools/hgi_sim/lib.py:pairwise'},
       'native_edges':{'qslot_capture_to_reducer_input':3,'reduce_read_to_add_issue':1,'add_latency':8,'earliest_pub_read_after_add_issue':9,'pub_read_to_issue':1,'publication_to_qslot_capture':1,'sequence_metadata_lead':1},
       'endpoint':{'frame_reservation_bits':613,'word_bits_per_coreedge':487,'period_edges':613,'reserved_frames_per_period':487,'idle_slots_real':True,'accept':'17+floor(613*j/487)','TX_edges':a.tx_edges,'endpoint_read':f'A-{1+a.tx_edges}','endpoint_write':f'A-{5+a.tx_edges}','endpoint_receive_publication':'24+ceil(613*(j+1)/487)-1'},
       'status':'INCOMPLETE: authoritative physical route graph required; no fake direct edges or machine uops emitted','price_ratio':None}
    if a.routes or a.candidate_rings:
        routes=candidate_rings() if a.candidate_rings else json.loads(a.routes.read_text())
        (a.out/'candidate_routes.json').write_text(json.dumps(routes,indent=2)+'\n')
        by=verify_routes(routes);m['verified_physical_directed_links']=len(by)
        full=compile_candidate(routes,a.tx_edges,a.bidirectional,a.insert_holes)
        full['multicast_policy']='two native publications to two disjoint48/47hop branches' if a.bidirectional else 'one native publication to95hop branch'
        if a.layout:
            words,summary=lower_expanded(full,json.loads(a.layout.read_text()))
            with (a.out/'expanded_uops.jsonl').open('w') as f:
                for owner,code in sorted(words.items()):
                    for c,w in sorted(code.items()):f.write(json.dumps({'owner':owner,'cycle':c,'word':f'{w:0384x}'})+'\n')
            full['expanded_program_summary']=summary
        (a.out/'calendar.json').write_text(json.dumps(full,indent=2)+'\n')
        m['status']=full['status'];m['price_ratio']=full['ratio'];m['cycles']=full['cycles']
    (a.out/'model.json').write_text(json.dumps(m,indent=2)+'\n')
    print('G96_CALENDAR_PRIMITIVES PASS mutants='+str(len(checks)))
if __name__=='__main__':main()
