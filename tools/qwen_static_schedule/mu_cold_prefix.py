"""Source-bound once-per-epoch context/prefetch/INIT startup contract.

The steady admission image remains unchanged. Missing physical/consumer evidence
produces an explicit blocked manifest, never a guessed production FIRST value.
"""
from __future__ import annotations
import argparse,copy,gzip,hashlib,json,re,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'qwen_split'))
import d2d_link_calendar as L
import sys_face_image as S
CALS=('C_tx','C_rx','K_tx','K_rx')
class ContractError(ValueError): pass

def decode(words):
    t=0;out=[]
    for word in words:
        t+=word>>18
        for i in range((word&31)+1):
            out.append(dict(time=t+i,port=(word>>14)&7,kind=(word>>10)&15,beat=((word>>5)&31)+i))
        t+=word&31
    return out

def admission_image(text,c):
    v=int(re.search(r'OVL_'+c.upper()+r'_IMG = 1024\'h([0-9a-f]+)',text)[1],16)
    words=[]
    for a in range(16,32):
        w=(v>>(32*a))&0xffffffff;words.append(w)
        if w&(1<<17):return words
    raise ContractError('unterminated admission source')

def dense_digest(image):
    d=0x51484f5354505247;mask=(1<<64)-1
    for desc,name in enumerate(('pw','dw')):
        for addr,w in enumerate(image[name]):
            d=(((d<<7)&mask)|(d>>57))^w^(desc<<10)^addr
    return d

def context_record(*,token,position,context_epoch,image_epoch,digest,cap,generation):
    if not 0<=token<151936 or not 0<=position<8192 or context_epoch&3:
        raise ContractError('cold record requires legal user0 token/position/epoch')
    if not 0<=image_epoch<65536 or not 0<=context_epoch<65536 or not 0<=generation<4 or cap not in (0,1):
        raise ContractError('context identity width')
    tag=(context_epoch<<43)|(token<<19)|(position<<6)
    return (12<<539)|(63<<533)|(context_epoch<<517)|(digest<<78)|(image_epoch<<62)|(cap<<61)|(generation<<59)|tag

def validate(m):
    if m['steady_period']!=m['admission_period'] or m['steady_runtime_delta_edges']!=0:
        raise ContractError('cold prefix changed steady period')
    p=m['plan'];r=m['context'];sel=m['init_selector']
    if not r.get('present') or r['wire_beat']!=0 or r['logical_beat']!=0 or r['user']!=0:
        raise ContractError('missing/noncanonical cold user0 context')
    actual=int(r['wire548'],16)
    expected=context_record(token=r['token'],position=r['position'],context_epoch=r['context_epoch'],
                            image_epoch=m['image_identity']['epoch'],digest=int(m['image_identity']['digest64'],16),
                            cap=m['image_identity']['cap'],generation=r['generation'])
    if actual!=expected:raise ContractError('cold context image/user/token/epoch identity mismatch')
    if not sel['enabled'] or sel['stage']!=0 or sel['user']!=0 or sel['first']%4 or not 0<sel['cnt']<=1023:
        raise ContractError('missing/invalid explicit INIT selector')
    if not p['auth_checked']<p['context_checked']<p['head_reference']<p['INIT_external_pin']:
        raise ContractError('context/prefetch/INIT order')
    if p['provider_core_sample']<p['provider_first_safe_sample']:
        raise ContractError('row not resident before actual provider core_start')
    if p['first_L0_external_pin']-p['INIT_external_pin']!=m['raw_GI_INIT_to_L0']:
        raise ContractError('INIT-to-L0 contract changed')
    if (sel['first'],sel['cnt']) != (m['init_range_source']['first'],m['init_range_source']['cnt']):
        raise ContractError('INIT selector range differs from immutable programme source')
    if (sel['T_entry'],sel['T_word'])!=(m['T_prefix']['init_entry_absolute'],m['T_prefix']['init_entry_word']):
        raise ContractError('INIT selector T entry differs from immutable cold prefix')
    if sel['external_pin_edge']!=p['INIT_external_pin']:
        raise ContractError('INIT selector not aligned to DH')
    if any(x['time']>=p['provider_core_sample'] for x in m['embedding_expected_decoder_events']):
        raise ContractError('embedding preload reaches consumer too late')
    return True

def build(admission,frame,source_text,*,token,position,context_epoch,image_epoch,generation,
          d2d_rx_age=3,d2d_rx_measured=False,kv_rx_age=2,lp_input_age=3,lp_measured=False):
    old={c:admission_image(source_text,c) for c in CALS}
    txdp={end:[(int(re.search(r'OVL_TXDP_'+end+r' = 32\'h([0-9a-f]+)',source_text)[1],16)>>(8*i))&255 for i in range(4)] for end in ('C','K')}
    messages=[dict(src=c[0],cyc=e['time'],tx_port=e['port'],rx_port=e['port'],kind=e['kind'],beat=e['beat'])
              for c in ('C_tx','K_tx') for e in decode(old[c])]
    exact,tab=L.compile_seg(messages,6,7,0,txdp)
    if exact!=old:raise ContractError('source SEG2 decode/recompile mismatch')
    # Preserve the source AUTH→WITNESS replay interval when the actual checked
    # receive boundary changes; never update the row phase alone.
    old_auth=max(e['rx_out'] for e in tab if e['kind']==13)
    witness=next(e for e in messages if e['src']=='C' and e['kind']==14)
    replay_gap=witness['cyc']-old_auth
    new_auth=max(e['arrive']+d2d_rx_age for e in tab if e['kind']==13)
    witness['cyc']=new_auth+replay_gap
    _,retimed=L.compile_seg(messages,6,7,0,txdp)
    def checked(e):return e['arrive']+(d2d_rx_age if e['src']=='K' else kv_rx_age)
    send=max(max(checked(e),e['cyc']) for e in retimed)+4
    messages.append(dict(src='K',cyc=send,tx_port=1,rx_port=1,kind=12,beat=0))
    adm_images,tab=L.compile_seg(messages,6,7,0,txdp)
    tab=[dict(e,checked_pin=checked(e)) for e in tab]
    if any(len(v)>16 for v in adm_images.values()):raise ContractError('SEG2 capacity')
    adm_ofs=72;adm_len=max(max(e['checked_pin'],e['cyc']) for e in tab)+4
    # All plan edges below share the LINK calendar reference. They remain model
    # values until final D2D/control/clock ledger and consumer certificate join.
    head_ref=adm_ofs+adm_len+4
    im=frame['im'];head={c:im['tok_rx'][c] for c in ('K_tx','C_rx')}
    crows=[dict(e,time=head_ref+head['C_rx']['start']+e['time']) for e in decode(head['C_rx']['img']) if e['kind'] in (6,7,8)]
    last_rx=crows[-1]['time']+d2d_rx_age
    # Measured real FACE/provider rule c11632a5b: sample >= final RX pin+3.
    safe=last_rx+3
    raw_gi_emb=63;provider_sample_age=lp_input_age+raw_gi_emb+1
    init=safe-provider_sample_age
    if init<=head_ref:raise ContractError('prefetch has no initialisation separation')
    prefix=admission['user0_prefix'];firstL0=init+prefix['span']
    auth=max(e['checked_pin'] for e in tab if e['kind']==13)
    ctx=next(e for e in tab if e['kind']==12)
    digest=dense_digest(admission['image'])
    cap=int(bool(admission['image']['pw'][1023]&(1<<12)))
    record=context_record(token=token,position=position,context_epoch=context_epoch,image_epoch=image_epoch,digest=digest,cap=cap,generation=generation)
    # Decoder events must coincide with real emb_rx_v samples. FACE registers
    # expected slots and actual words together; FILL precedes first header.
    ecal=[dict(time=crows[0]['time']+d2d_rx_age-1,kind='FILL',port=7,arg=0)]
    for e in crows:
        scale=e['kind']==8;idx=0 if scale else (e['kind']-6)*32+e['beat']
        ecal.append(dict(time=e['time']+d2d_rx_age,kind='EMBW',port=6,arg=64 if scale else idx))
    e_pin_events=[(e['time']+1-head_ref,e['port'],e['arg']) for e in ecal]
    e_image=S.compile_cal('E',e_pin_events)
    steady_e_image=S.compile_cal('E',[(c+frame['head_ref'],k,a) for c,k,a in e_pin_events])
    e_seg1=len(steady_e_image)
    if e_seg1+len(e_image)>S.NE['E']:raise ContractError('cold/steady E tables exceed16 entries')
    cold_t_start=head_ref-S.GO_OFS
    t_pin_events=[(head_ref-cold_t_start,5,128),(init-cold_t_start,0,0),(init+1-cold_t_start,1,4)]
    t_image=S.compile_cal('T',t_pin_events)
    T=admission['T']
    stage_units=[(name,t,b) for name,t,b in frame['cal']['schedule']['0'] if 0<=t<T]
    steady_t_events=[(t+S.GO_OFS,0,b['stage']|(64 if 1<=b['stage']<=36 else 128 if b['stage']==0 else 0)) for name,t,b in stage_units]
    steady_t_events.append((T,1,4))
    steady_t_image=S.compile_cal('T',steady_t_events)
    t_seg1=len(steady_t_image)
    if t_seg1+len(t_image)>S.NE['T']:raise ContractError('canonical stage-control T and cold prefix exceed64 entries')
    full_images={};seg1={}
    for c in CALS:
        s0=im['req'].get(c,im['rsp'].get(c));s1=im['tok_tx'].get(c,im['tok_rx'].get(c))
        words=list(s0['img']);seg1[c]=len(words);words+=s1['img']
        if len(words)>16:raise ContractError('request/head segments cross SEG2')
        words += [0]*(16-len(words));words+=adm_images[c];words += [0]*(32-len(words));full_images[c]=words
    m=dict(schema='opentallas.mu.cold-start.v1',production_bound=False,verdict='BLOCKED',
           blockers=['final SAFE KV witness checked age / compute die receive-lane phase unqualified','landed control/clock and absolute forwarded epoch join unqualified','actual production embedding consumer/token-epoch witness pending','full production programme identity not selected','Ecalendar/T MARK launch-to-decoder binding pending','canonical T stage-control image lacks production LEVEL/ordinary token-epoch closure'],
           steady_period=admission['H'],admission_period=admission['H'],steady_runtime_delta_edges=0,
           raw_GI_INIT_to_L0=prefix['span'],calendar_reference='shared link calendar epoch; absolute forwarded-epoch offset unbound',
           admission=dict(offset=adm_ofs,length=adm_len,seg2_base=16,images=adm_images,events=tab,source_AUTH_to_WITNESS_gap=replay_gap,KV_checked_age=kv_rx_age,KV_checked_age_measured=False),
           image_identity=dict(epoch=image_epoch,digest64=f'{digest:016x}',cap=cap,artifact_sha256=admission['artifact_sha256'],profile='public command-class fixture; full arithmetic image separate'),
           context=dict(present=True,user=0,logical_kind=12,logical_beat=0,wire_beat=0,token=token,position=position,context_epoch=context_epoch,generation=generation,wire548=f'{record:0137x}',calendar_send=adm_ofs+send),
           init_range_source=dict(first=prefix['init_first'],cnt=prefix['init_cnt'],PW_sha256=admission['artifact_sha256']['pw.hex'],serialized_entries=admission['image']['initial_range']['entries']),
           init_selector=dict(enabled=True,user=0,stage=0,first=prefix['init_first'],cnt=prefix['init_cnt'],external_pin_edge=init,source='explicit registered init_u0 aligned DH stage0; no inference or reserved bit'),
           plan=dict(auth_checked=adm_ofs+auth,context_checked=adm_ofs+ctx['checked_pin'],head_reference=head_ref,INIT_external_pin=init,INIT_raw_GI_pin=init+lp_input_age,
                     emb_start_pin=init+lp_input_age+63,provider_core_sample=init+provider_sample_age,last_row_rx_pin=last_rx,provider_first_safe_sample=safe,first_L0_external_pin=firstL0,first_L0_raw_GI_pin=firstL0+lp_input_age),
           edge_ledger=dict(raw_GI_INIT_to_cal_accept=dict(edges=1,measured=True,source='0877475d8'),raw_GI_INIT_to_emb_pin=dict(edges=63,measured=True,source='0877475d8'),
                            LP_external_DH_to_raw_GI=dict(edges=lp_input_age,measured=lp_measured),FACE_DH_to_external_CTLMPin=dict(edges=None,measured=False),D2D_RX_to_FACEPin=dict(edges=None,measured=False),FACE_word_to_providerPin=dict(edges=None,measured=False),CTLM_emb_to_providerPin=dict(edges=None,measured=False),GI_emb_pin_to_provider_sample=dict(edges=1,measured=False),
                            D2D_calendar_to_emb_rx_pin=dict(edges=d2d_rx_age,measured=d2d_rx_measured),emb_rx_pin_to_first_safe_core_sample=dict(edges=3,measured=True,source='c11632a5b'),
                            external_context_offer_to_landed_filler_bank=dict(edges=3+lp_input_age,measured=False,raw_GI_measured_edges=3)),
           player_prefix={c:dict(segment=1,user=0,start=head_ref+d['start'],calendar_image=d['img'],wrap_skips_prefix=True) for c,d in head.items()},
           embedding_expected_decoder_events=ecal,
           T_prefix=dict(start=cold_t_start,pin_events_relative_start=t_pin_events,image=t_image,append_base=t_seg1,init_entry_relative=1,init_entry_absolute=t_seg1+1,init_entry_word=t_image[1],steady_total_entries=len(steady_t_image),total_entries=t_seg1+len(t_image),capacity=64,cold_END_must_not_loop=True),
           T_stage_control=dict(scope='canonical user0 stage starts only; production LEVEL/identity unbound',source_units=[dict(name=n,time=t,stage=b["stage"]) for n,t,b in stage_units],pin_events=steady_t_events,image=steady_t_image,combined_image=steady_t_image+t_image,first_steady_start=firstL0-S.GO_OFS,steady_period=T),
           Ecalendar=dict(cold_start=head_ref,cold_seg=1,cold_seg1_base=e_seg1,cold_pin_events_relative_start=e_pin_events,cold_image=e_image,steady_seg=0,steady_image=steady_e_image,combined_image=steady_e_image+e_image,total_entries=e_seg1+len(e_image),go_to_decoded_age=None,initial_MARK_required=True,INIT_must_not_restart_Ecalendar=True,selector='explicit COLD_PREFIX && cold_active; optionB agreed SYSFACE owner'),
           full_calendar_images=full_images,seg1_base=seg1,
           absolute_startup=dict(forwarded_epoch_to_calendar_reference=None,FIRST_OFS=None,qualified=False),
           ordinary_identity_contract=dict(status='unresolved',rule='trace resident token/epoch at core_start and next preload; do not assume lookahead or change steady schedule'))
    m['init_selector'].update(T_entry=t_seg1+1,T_word=t_image[1],T_prefix_base=t_seg1)
    m['face_prefix_cfg_writes']=[dict(target=3,addr=i,data=w) for i,w in enumerate(steady_t_image+t_image)]
    m['face_prefix_cfg_writes'] += [dict(target=3,addr=128,data=t_seg1)]
    m['face_prefix_cfg_writes'] += [dict(target=5,addr=i,data=w) for i,w in enumerate(steady_e_image+e_image)]
    m['face_prefix_cfg_writes'] += [dict(target=5,addr=128,data=e_seg1)]
    validate(m);return m

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--admission',type=Path,required=True);p.add_argument('--frame',type=Path,required=True);p.add_argument('--source-ovl',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--d2d-age-receipt',type=Path,required=True);p.add_argument('--provider-age-receipt',type=Path,required=True)
    p.add_argument('--token',type=int,required=True);p.add_argument('--position',type=int,required=True);p.add_argument('--context-epoch',type=lambda x:int(x,0),required=True);p.add_argument('--image-epoch',type=lambda x:int(x,0),required=True);p.add_argument('--generation',type=int,required=True)
    a=p.parse_args();fb=a.frame.read_bytes();fb=gzip.decompress(fb) if fb[:2]==b'\x1f\x8b' else fb
    d2d=json.loads(a.d2d_age_receipt.read_text());provider=json.loads(a.provider_age_receipt.read_text())
    if d2d.get('schema')!='opentallas.qwen.safe3-embedding-age.v1' or d2d.get('calendar_to_pin_age')!=3:
        raise ContractError('source-pinned SAFE3 compute RX age receipt required')
    pe=provider.get('edges',{})
    if provider.get('schema')!='opentallas.qwen.face-provider-age.v1' or pe.get('first_complete_safe_sample',0)-pe.get('last_emb_rx_pin',0)!=3:
        raise ContractError('source-pinned actual FACE/provider safe-consume receipt required')
    m=build(json.loads(a.admission.read_text()),json.loads(fb),a.source_ovl.read_text(),token=a.token,position=a.position,context_epoch=a.context_epoch,image_epoch=a.image_epoch,generation=a.generation,d2d_rx_age=d2d['calendar_to_pin_age'],d2d_rx_measured=True)
    m['source_sha256']={name:hashlib.sha256(x.read_bytes()).hexdigest() for name,x in dict(admission=a.admission,frame=a.frame,ovl_source=a.source_ovl,compiler=Path(__file__),link_calendar=Path(L.__file__),face_calendar=Path(S.__file__),d2d_receipt=a.d2d_age_receipt,provider_receipt=a.provider_age_receipt).items()}
    m['boundary_receipts']=dict(compute_d2d=d2d,face_provider=provider)
    a.out.mkdir(parents=True,exist_ok=True);(a.out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
    for c,words in m['full_calendar_images'].items():(a.out/(c+'.memh')).write_text(''.join(f'{w:08x}\n' for w in words))
    print('COLD_PREFIX_MODEL',m['verdict'],json.dumps(m['plan'],sort_keys=True))
if __name__=='__main__':main()
