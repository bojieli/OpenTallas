"""Bind exact emitted native output fragments, not retained-history substitutes.
A finite per-rank native AW27 service-plane extent; no GPU physical translation,
macro/PHY, shared-memory, area or rate qualification follows.
"""
import argparse,gzip,hashlib,json,math
BASE=33554432;CAP=33554432
FLOAT={'I2F','FADD','FMUL','DIV','SQRT','LDEXP','BITCAST_F'}
INTEGER={'SHR','SHL','AND','OR','XOR','IADD','ISUB','IMUL','IMOD'}
def output_spec(p,name):
    widths={};types={};nodes={}
    for i in p['code']:
        op=i['op'];a=[types[x] for x in i['src']]
        if op in ('LOAD','CONST'):dtype=i['attrs']['dtype']
        elif op in FLOAT:dtype='F32'
        elif op=='BITCAST_U' or op.startswith('FCMP'):dtype='U32'
        elif op in ('F2I','IOTA'):dtype='I64'
        elif op in INTEGER:dtype='I64' if 'I64' in a else 'U32'
        elif op=='SELECT':
            if a[1]!=a[2]:raise ValueError('mixed SELECT output type requires source promotion proof')
            dtype=a[1]
        elif a:dtype=a[0]
        else:raise ValueError('source dtype unbound '+op)
        types[i['dst']]=dtype;nodes[i['dst']]=i
    node=p['outputs'][name];return dict(shape=nodes[node]['shape'],dtype=types[node],bytes=max(1,math.prod(nodes[node]['shape']))*({'F32':4,'U32':4,'I64':8}[types[node]]))
def compile_directory(native,source_hash):
    cursor={};rows=[];cache={}
    for op in native['instructions']:
        for w in op['writes']:
            if w['home_indices']:continue
            for owned in op['rank_bindings']:
                if owned.get('empty_owned_extent'):continue
                if owned.get('buffer_programs'):raise ValueError('unbound collective output home cannot use a single template')
                rank=owned['rank'];key=owned['template'];name=w['native_result_binding']['result'];spec=cache.setdefault((key,name),output_spec(native['templates'][key],name))
                if 'flat_slice' in w['native_result_binding']:raise ValueError('persistent flat slice requires exact shape binding')
                off=cursor.get(rank,0);length=(spec['bytes']+511)//512*512
                if off+length>CAP:raise BufferError('finite state extent exhausted; no modulo or unpriced growth')
                rows.append(dict(PC=op['pc'],version=w['version'],rank=rank,base=BASE+off,bytes=spec['bytes'],reservation_bytes=length,shape=spec['shape'],dtype=spec['dtype'],source_template=key,source_result=name,home_class='HBM_NATIVE_STATE',semantic_scope='exact produced output fragment only; full-history append/aux consumption remains source-bound separately'))
                cursor[rank]=off+length
    return dict(source_native_sha256=source_hash,rows=rows,per_rank_reserved_bytes=cursor,extent=dict(AW=27,base=BASE,bytes=CAP,address_class='native software service plane; GPU physical AW34 translation NOT supplied'),capacity_charged_bytes_all96_ranks=CAP*96,source_operator_or_rounding_changes=0,actual_initial_context_supplied=False,hardware_qualified=False)
def patch_homes(native,homes,directory):
    by={}
    for r in directory['rows']:
        index=len(homes);homes.append(dict(version=r['version'],rank_group=[r['rank']],home=dict(class_=r['home_class'],base=r['base'],bytes=r['bytes'],shape=r['shape'],dtype=r['dtype']),binding=r))
        homes[-1]['home']['class']=homes[-1]['home'].pop('class_');by.setdefault((r['PC'],r['version']),[]).append(index)
    instructions=[]
    for op in native['instructions']:
        writes=[dict(w,home_indices=by[op['pc'],w['version']]) if not w['home_indices'] else w for w in op['writes']]
        instructions.append(dict(op,writes=writes))
    return dict(native,instructions=instructions),homes
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--native',required=True);ap.add_argument('--out',required=True);a=ap.parse_args();raw=open(a.native,'rb').read();p=json.loads(gzip.decompress(raw));r=compile_directory(p,hashlib.sha256(raw).hexdigest())
    with open(a.out,'x') as f:json.dump(r,f,sort_keys=True,separators=(',',':'));f.write('\n')
