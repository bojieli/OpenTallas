"""Exact intra/crossing timing views for compiler consumers; legacy depth() is unchanged."""
from collections import defaultdict


def timing_depths(b,path,port):
    ci=b.cell_index()[path]
    def describe(d,old):
        kind=d[0]
        if kind=='int':
            if old[0]!='int' or old[1:4]!=d[1:4]:raise ValueError('INNER original endpoint changed')
            return dict(kind='intra',source=b.F.cells[d[1]].path,source_port=d[2],source_bit=d[3],asbuilt_stages=old[4],landed_stages=d[4])
        if kind=='x':
            depth=b.bitcyc[(d[1],d[6],d[2],d[3],d[4])]+(d[7] if len(d)>7 else 0)
            return dict(kind='crossing',source=b.F.cells[d[2]].path,source_port=d[3],source_bit=d[4],asbuilt_stages=d[5],landed_stages=depth)
        if kind in ('or','and'):
            if old[0]!=kind or len(d[1])!=len(old[1]):raise ValueError('INNER original logic changed')
            return dict(kind=kind,inputs=[describe(x,y) for x,y in zip(d[1],old[1])])
        return dict(kind=kind)
    return {i:describe(b.sinks[(ci,port,i)],getattr(b,'_inner_original',{}).get((ci,port,i),b.sinks[(ci,port,i)])) for i in range(len(b.F.cells[ci].ports[port]))}


def changed_inner_groups(b):
    groups=defaultdict(list)
    views={}
    def walk(d):
        if d['kind'] in ('or','and'):
            for x in d['inputs']:yield from walk(x)
        else:yield d
    for ci,pn,i in getattr(b,'_inner_original',{}):
        path=b.F.cells[ci].path
        if (ci,pn) not in views:views[(ci,pn)]=timing_depths(b,path,pn)
        for d in walk(views[(ci,pn)][i]):
            if d['kind']!='intra' or d['asbuilt_stages']==d['landed_stages']:continue
            key=(path,b.cpart[ci],pn,d['source'],d['source_port'],d['asbuilt_stages'],d['landed_stages'])
            groups[key].append((i,d['source_bit']))
    def ranges(vals):
        out=[]
        for x in sorted(set(vals)):
            if out and out[-1][1]+1==x:out[-1][1]=x
            else:out.append([x,x])
        return out
    return [dict(id=f'INNER:{part}:{sink}.{pn}<-{src}.{sp}@{a}',kind='intra',sink=sink,sink_part=part,src_part=part,sink_port=pn,source=f'{src}.{sp}',asbuilt_stages=a,landed_stages=z,lane=f'INNER:{part}',sink_bits=ranges(x for x,_ in bits),source_bits=ranges(y for _,y in bits)) for (sink,part,pn,src,sp,a,z),bits in sorted(groups.items())]
