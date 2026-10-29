#!/usr/bin/env python3
"""Compile explicit one-stack key allocations into static relative SVG programmes.

Every physical row/slot, epoch, GO edge and cache-ready deadline comes from the
input allocation. No production addresses or HBM completion bounds are guessed.
Outputs are source candidates until native service, transport and plan qualify.
"""
import argparse
import json
from pathlib import Path


def field(word, low, width, value):
    if type(value) is not int or not 0 <= value < 1 << width:
        raise ValueError(f'field{low}+{width} out of range: {value}')
    return word | value << low


def programme(rows, slots, base):
    # Native PREL's lstep relocates row/tag by iteration. One4word body
    # serves all64/43row blocks: no424word unrolled store is required.
    words=[0]*slots
    words[0]=(1<<83)|(1<<29)
    words[-1]=1<<117 #feed retires only on the last loop iteration
    return [(0xc7a1<<240)|((base+i)<<224)|w for i,w in enumerate(words)]


def compile_allocation(a):
    if a.get('schema')!='opentallas.hbm_idx.key_cohort_allocation.v1':
        raise ValueError('unsupported explicit key allocation schema')
    if a.get('physical_stack')!=2 or a.get('slots')!=4:
        raise ValueError('current native source requires physicalstack2 and two local4slot pipes')
    packet_delay=a['packet_from_go_edges'];relay=a['relay_cycles'];query=a['query_start_at'];phase=a.get('pipe_phase',0)
    if type(phase) is not int or not 0<=phase<4:raise ValueError('explicit pipe phase0..3 required')
    programme_base=a['programme_base'];descriptor_base=a['descriptor_base']
    if not isinstance(programme_base,int) or programme_base<0 or not isinstance(descriptor_base,int) or not 0<=descriptor_base<=250:
        raise ValueError('explicit available programme/descriptor base required')
    if any(type(x) is not int or x<0 for x in (packet_delay,relay,query)):
        raise ValueError('explicit nonnegative packet/relay/query edges required')
    cohorts=a['cohorts']
    if sorted(c['id'] for c in cohorts)!=[0,1]:raise ValueError('both distinct logical cohorts0/1 required')
    sizes=[64,64,43]
    pwords=programme(64,4,programme_base)
    shapes={r:(programme_base,programme_base+len(pwords)) for r in set(sizes)}
    if programme_base+len(pwords)>2048:raise ValueError('source programme capacity exceeded')
    for low,high in a['occupied_programme_ranges']:
        if programme_base<high and low<programme_base+len(pwords):raise ValueError('new programme overlaps selected existing source programme')
    for low,high in a['occupied_descriptor_ranges']:
        if descriptor_base<high and low<descriptor_base+6:raise ValueError('new descriptors overlap selected existing source descriptors')
    groups={};used=set();timeline=[]
    for c in sorted(cohorts,key=lambda c:c['id']):
        if sorted(g['lane'] for g in c['groups'])!=list(range(8)):raise ValueError('each cohort needs all8 physical source groups')
        for g in sorted(c['groups'],key=lambda g:g['lane']):
            lane=g['lane'];blocks=g['blocks'];key=f'svg_NW{lane}'
            path=g.get('path',[])
            if any(type(n.get('cycles')) is not int or n['cycles']<1 or not n.get('node') for n in path):raise ValueError('named positive-cycle path segments required')
            source_relay=sum(n['cycles'] for n in path) if path else relay
            if len(blocks)!=3:raise ValueError('171rows require64,64,43 blocks')
            rows_done=0
            for b,x in enumerate(blocks):
                rb=x['row_base'];slot=x['slot'];epoch=x['epoch'];go=x['go_at'];ready=x['cache_ready_by']
                if type(rb) is not int or not 0<=rb<32768 or type(slot) is not int or not 0<=slot<8:raise ValueError('physical row/slot out of range')
                if type(epoch) is not int or not 1<=epoch<65536:raise ValueError('explicit nonzero finite epoch required')
                ident=(lane,rb,slot)
                if ident in used:raise ValueError('physical key allocations alias across blocks/cohorts')
                used.add(ident)
                if ready>=go or ready<0:raise ValueError('cache not resident strictly before fixed GO')
                if (go+packet_delay+source_relay-phase)%4!=lane%4:raise ValueError('source packet edge misses its static local lane slot')
                # A group cannot run two programmes or issue both cohorts at once.
                prev=groups.setdefault(key,[])
                if prev and go<prev[-1]['go_at']+prev[-1]['programme_runtime_edges']+a['go_done_tail_edges']:
                    raise ValueError('service programme GO intervals overlap')
                rows=sizes[b];pb,pl=shapes[rows];di=descriptor_base+c['id']*3+b
                tagbase=(128*lane+rows_done)%1024
                d=0
                for lo,w,v in [(0,32,(2<<30)|(slot<<7)),(32,15,rb),(47,2,b%4),(49,16,epoch),(65,7,rows),(72,10,tagbase),(82,10,pb&1023),(92,11,pl&2047),(103,16,rows),(119,24,go),(189,1,pb>>10),(191,4,1),(190,1,pl>>11),(232,8,di),(240,16,0x5d15)]:d=field(d,lo,w,v)
                rec=dict(cohort=c['id'],descriptor=di,descriptor_word=f'{d:064x}',row_base=rb,slot=slot,epoch=epoch,go_at=go,cache_ready_by=ready,first_row=rows_done,rows=rows,programme_base=pb,programme_limit=pl,programme_words=pl-pb,programme_runtime_edges=rows*4,programme_loops=rows,tag_base=tagbase,arithmetic_issue=False)
                prev.append(rec)
                for r in range(rows):
                    edge=go+packet_delay+r*4
                    timeline.append(dict(edge=edge,arrival_edge=edge+source_relay,path=path,source=key,lane=lane%4,physical_lane=lane,cohort=c['id'],row=rows_done+r,tag=(128*lane+rows_done+r)%1024,consumer=('hb_idx__s_SW' if lane<4 else 'hb_idx__s_SE') if c['id']==0 else ('hb_idx__s_NW' if lane<4 else 'hb_idx__s_NE')))
                rows_done+=rows
    # One1112b pipe per hub; every reserved edge is unique, including cross-block/cohort boundaries.
    taken=set()
    for t in timeline:
        k=(t['physical_lane']//4,t['arrival_edge'])
        if k in taken:raise ValueError('two source packets collide in one local pipe slot')
        taken.add(k)
    node_events=set()
    for t in timeline:
        edge=t['edge']
        for segment in t['path']:
            edge+=segment['cycles']
            identity=(segment['node'],edge)
            if identity in node_events:raise ValueError('source packets collide at named distributed path node')
            node_events.add(identity)
    last=max(t['arrival_edge'] for t in timeline)
    if query<=last+1:raise ValueError('query begins before all distinct role SRAM writes commit')
    return dict(schema='opentallas.hbm_idx.key_cohort_programme.v1',verdict='SOURCE_CANDIDATE',installable=False,programme_words=[f'{w:064x}' for w in pwords],programme_word_count=len(pwords),programme_base=programme_base,descriptor_base=descriptor_base,pipe_phase=phase,source_groups=groups,ingest_timeline=sorted(timeline,key=lambda x:(x['edge'],x['physical_lane'])),last_arrival_edge=last,query_start_at=query,unused_prefill_slack=query-last-1,HBM_deadlines='caller supplied, not measured by compiler',claim=dict(native=False,physical=False,token=False))


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('allocation',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
    d=compile_allocation(json.loads(a.allocation.read_text()));a.out.write_text(json.dumps(d,indent=2)+'\n')
    print('KEY_COHORT_SOURCE_CANDIDATE',len(d['ingest_timeline']),'packets',d['programme_word_count'],'programme words; not installable')

if __name__=='__main__':main()
