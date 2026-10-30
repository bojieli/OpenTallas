"""Current publication inputs from raw bind descriptions; refuse glue guesses."""
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from bound_die import object_items,file_sha

bound=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
groups=defaultdict(dict);sidbits=defaultdict(dict);kbits=defaultdict(dict);rb=defaultdict(dict)
source_hash=file_sha(bound/'bind_sinks.json')
if len(sys.argv)>3:
    cache=json.loads(Path(sys.argv[3]).read_text())
    if cache['bind_sinks_sha256']!=source_hash:raise ValueError('raw cache source changed')
    ints=lambda d:{int(k):v for k,v in d.items()}
    groups.update({(r['unit'],r['port']):ints(r['bits'])for r in cache['groups']})
    rb.update({(r['unit'],r['port']):ints(r['bits'])for r in cache['rb']})
    sidbits.update({u:ints(b)for u,b in cache['sidbits'].items()})
    kbits.update({u:ints(b)for u,b in cache['kbits'].items()})
else:
    for key,value in object_items(bound/'bind_sinks.json'):
        if not key.startswith('u_s_'):continue
        m=re.fullmatch(r'(.+\.u_xg)\.(ri_w|ri_e|vi|sid|xf_v|xf_s|xf)\[(\d+)\]',key)
        if m:
            unit,port,bit=m[1],m[2],int(m[3])
            (sidbits[unit] if port=='sid' else groups[unit,port])[bit]=value
            continue
        m=re.fullmatch(r'(.+\.u_vq)\.k\[(\d+)\]',key)
        if m:kbits[m[1]][int(m[2])]=value;continue
        m=re.fullmatch(r'(.+\.u_vn\.u_b)\.(rb_v|rb_d)\[(\d+)\]',key)
        if m:rb[m[1],m[2]][int(m[3])]=value
    cache={'bind_sinks_sha256':source_hash,'groups':[{'unit':u,'port':p,'bits':b}for(u,p),b in groups.items()],
           'rb':[{'unit':u,'port':p,'bits':b}for(u,p),b in rb.items()],'sidbits':sidbits,'kbits':kbits}
    (out/'raw_selected.json').write_text(json.dumps(cache))

def literal(bits,width):
    if set(bits)!=set(range(width)):raise ValueError('missing literal strap bits')
    val=0
    for i,d in bits.items():
        if d not in (['const','0'],['const','1'],['strap','0'],['strap','1']):raise ValueError('nonliteral strap '+str(d))
        val|=int(d[1])<<i
    return val
ids={u:literal(b,4)for u,b in sidbits.items()}
if sorted(ids.values())!=list(range(16)):raise ValueError('need exact16unique sourceSIDstraps')

def word(bits,width,source_lsb=0):
    if set(bits)!=set(range(width)):return {'status':'BLOCKED','reason':'incomplete word','seen':len(bits),'wanted':width}
    sources=set();ages=set();bad=[]
    for bit,d in sorted(bits.items()):
        if not isinstance(d,list)or len(d)!=4 or d[0]!='pin' or d[3] is not False:
            bad.append((bit,d));continue
        m=re.fullmatch(r'(.+)\.(\w+)\[(\d+)\]',d[1])
        if not m or int(m[3])!=bit+source_lsb or type(d[2])is not int or d[2]<0:
            bad.append((bit,d));continue
        sources.add(m[1]+'.'+m[2]);ages.add(d[2])
    if bad or len(sources)!=1 or len(ages)!=1:
        return {'status':'BLOCKED','sources':sorted(sources),'ages':sorted(ages),'bad':bad[:3]}
    return {'status':'PASS_RAW_WORD','source':next(iter(sources)),'age_edges':next(iter(ages)),'bits':width}

rings=[];xf=[];broadcast=[]
for u,sid in sorted(ids.items(),key=lambda p:p[1]):
    for p in ('ri_w','ri_e','vi'):
        width=276 if p=='vi' else 1104
        rings.append({'sid':sid,'xg':u,'port':p,**word(groups[u,p],width)})
    for k in range(5):
        vf=groups[u,'xf_v'].get(k);sf=groups[u,'xf_s'].get(k)
        payload={i:groups[u,'xf'].get(276*k+i)for i in range(276)}
        w=word(payload,276);r={'sid':sid,'xg':u,'leaf_input':k,**w}
        if w['status']=='PASS_RAW_WORD':
            vq=w['source'].rsplit('.',1)[0]
            expected_v=['pin',vq+'.xf_v[0]',w['age_edges'],False]
            expected_s=['pin',vq+'.xf_s[0]',w['age_edges'],False]
            if vf!=expected_v or sf!=expected_s:r.update(status='BLOCKED',reason='xf valid/side incoherent',valid=vf,side=sf)
            else:
                try:r.update(vq=vq,k_strap=literal(kbits[vq],3),bits=278)
                except ValueError as e:r.update(status='BLOCKED',reason=str(e))
        xf.append(r)
for (u,p),bits in sorted(rb.items()):
    broadcast.append({'vn_b':u,'port':p,**word(bits,1 if p=='rb_v' else 32)})
record={'schema':'opentallas.s81.current_publication_raw_inputs.v1',
        'source_asbuilt_sha256':file_sha(bound/'asbuilt.json'),
        'die_sha256':file_sha(bound/'rtl/s81_bound_top.sv'),
        'sid_straps':ids,'ring_links':rings,'xf_forward':xf,'rstd_broadcast':broadcast,
        'glue_aliases_inferred':False,'full_bind_verification':'PENDING dieowner',
        'full_token':False,'physical_START_qualified':False}
(out/'publication_inputs.json').write_text(json.dumps(record,indent=2)+'\n')
for key in ('ring_links','xf_forward','rstd_broadcast'):
    rows=record[key];print(key,len(rows),'PASS',sum(r['status']=='PASS_RAW_WORD'for r in rows))
