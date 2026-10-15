#!/usr/bin/env python3
"""Lower the declared G2/PF384 ALL_GATHER calendar to actual native issuer SRAM.
This is a mechanism compiler at the parent boundary, not the normative HGI join.
"""
import argparse,json,pathlib
ROOT=pathlib.Path(__file__).resolve().parents[2]
LAYOUT=ROOT/'rtl/hbm_accel/generic/collective/p2p/static_uop_layout.json'

def compile_program(die,qid):
    fields=json.loads(LAYOUT.read_text())['fields'];npt=3 if qid==0 else 2
    def pack(d):
        out=0
        for k,v in d.items():
            f=fields[k]
            if not 0<=v<(1<<f['width']):raise ValueError((k,v))
            out|=v<<f['lsb']
        return out
    def row(c,step=False):
        d={};cap=0;sinks=0;sel=0
        d['del_obase']=sum((0x10000+qid*0x4000+lane*0x1000)<<(40*lane) for lane in range(4))
        if c==0:d.update(lk_epoch_begin=3,lk_epoch=0x35)
        if 0<=c<48:
            idx=[qid*96+2*c+j for j in range(2)]
            d.update(inj_rd=3,inj_idx=idx[0]|(idx[1]<<16),
                     inj_meta=sum(((1<<32)|(255<<24)|(die<<16)|idx[j])<<(33*j) for j in range(2)),
                     inj_addr=sum((idx[j]*16+8*h)<<(80*j+40*h) for j in range(2) for h in range(2)))
        if 12<=c<60:cap|=3
        if 29<=c<77:cap|=12
        if 13<=c<61:
            for dst,src in [(0,0),(1,1),(npt,0),(npt+1,1)]:sinks|=1<<dst;sel|=src<<(4*dst)
        if 30<=c<78:
            for dst,src in [(npt+2,2),(npt+3,3)]:sinks|=1<<dst;sel|=src<<(4*dst)
        for key,start in [('lk_wr',15),('lk_rd',18),('lk_rx',27)]:
            if start<=c<start+48:
                slot=c-start
                if slot>=64:raise ValueError('link slot overflow')
                d[key+'_v' if key!='lk_rx' else 'lk_rx_expect']=3
                d[key+'_slot']=slot|(slot<<6)
        d.update(capture_slot=cap,sink_slot=sinks,sink_select=sel)
        # Epoch is immutable outside explicit begin; parent keeps its register.
        if step:d.update(iter_inj_idx_step=2,iter_inj_addr_step=32,iter_link_slot_step=1)
        return d
    schedule=[*range(30),30,*range(48,80)]
    words=[];meta=[]
    for pc,c in enumerate(schedule):
        m=(pc+1)&63
        if c==30:m|=(30<<6)|(18<<12)|(30<<45)
        if c==79:m|=1<<44
        d=row(c,c==30);words.append(pack(d));meta.append(m)
    if len(words)!=63:raise AssertionError('program capacity')
    # Independently unroll the actual metadata/counter ISA, and compare every
    # active numeric/bit field to a fresh logical-cycle schedule. No modulo slots.
    pc=0;counters=[0]*64;trace=[]
    for c in range(80):
        m=meta[pc];it=counters[(m>>45)&63];d=row(schedule[pc],schedule[pc]==30)
        applied=dict(d)
        if it:
            for key in ('lk_wr_slot','lk_rd_slot','lk_rx_slot'):
                if key in d:
                    slots=[(d[key]>>(6*j))&63 for j in range(3)]
                    active=d.get(key.replace('_slot','_v'),d.get('lk_rx_expect',0))
                    for j in range(3):
                        if active>>j&1:
                            slots[j]+=it
                            if slots[j]>=64:raise AssertionError('compiled link wrap')
                    applied[key]=sum(v<<(6*j) for j,v in enumerate(slots))
            for key,width,num,increment in [('inj_idx',16,2,2),('inj_meta',33,2,2),('inj_addr',40,4,32)]:
                if key in d:applied[key]=sum((((d[key]>>(width*j))&((1<<width)-1))+it*increment)<<(width*j) for j in range(num))
        expected=row(c)
        for key in set(applied)|set(expected):
            if key.startswith('iter_'):continue
            if applied.get(key,0)!=expected.get(key,0):raise AssertionError((c,pc,it,key,applied.get(key),expected.get(key)))
        trace.append({'cycle':c,'pc':pc,'iteration':it})
        if m>>44&1:
            if c!=79:raise AssertionError('early halt')
            break
        count=(m>>12)&0xffffffff;lid=(m>>45)&63
        if count and counters[lid]<count-1:counters[lid]+=1;pc=(m>>6)&63
        else:
            if count:counters[lid]=0
            pc=m&63
    cfg=[]
    for pc,(w,m) in enumerate(zip(words,meta)):
        for bank in range(3):
            cfg.append((1<<36)|(pc|(bank<<6)))
            cfg.extend((1<<36)|(1<<32)|((w>>(512*bank+32*j))&0xffffffff) for j in range(16))
        cfg.extend([(1<<36)|pc,(1<<36)|(2<<32)|(m&0xffffffff),(1<<36)|(3<<32)|(m>>32)])
    return words,meta,cfg,trace

def main():
    p=argparse.ArgumentParser();p.add_argument('out',type=pathlib.Path);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True)
    allcfg=[]
    for die in range(2):
        for q in range(4):
            words,meta,cfg,trace=compile_program(die,q);name=f'd{die}q{q}';allcfg.extend(cfg)
            for suffix,vals,width in [('uop',words,384),('meta',meta,16),('cfg',cfg,10)]:
                (a.out/f'{name}.{suffix}.hex').write_text(''.join(f'{v:0{width}x}\n' for v in vals))
    (a.out/'all.cfg.hex').write_text(''.join(f'{v:010x}\n' for v in allcfg))
    model={'scope':'native G2 full8parent ALL_GATHER mechanism; not normative HGI compiler/nativeSU/productionG96 qualification',
           'dies':2,'quadrants_each':4,'actual_q3_K2048_instances':2,'actual_q2_instances':6,
           'PF_per_die':384,'flits_per_quadrant':96,'rails_active_per_stop':2,'SW_rails_instantiated':3,
           'rows':63,'config_words_per_parent':len(cfg),'unrolled_cycles':80,'trace':trace,
           'calendar':{'SU_requests':[0,47],'SU_capture':[12,59],'local_and_rail_sink_instruction':[13,60],
                       'local_delivery_output':[14,61],'link_write':[15,62],'link_read':[18,65],
                       'TX_output':[21,68],'RX_expect':[27,74],'remote_capture':[29,76],
                       'remote_sink_instruction':[30,77],'remote_delivery_output':[31,78],'halt':79},
           'timing':'logical instruction consumption P0 = start+4; native linkTX3/RX1 and five registered package wires',
           'budget':{'SU_flits_per_cycle':2,'per_active_rail_flits_per_cycle':1,'quarter_flits':96,'all_payload_and_metadata_bits':545},
           'qualification':'UNQUALIFIED until actualnativebench matches declared timing; TTFF, producerjoin, G96n1024 remain pending'}
    (a.out/'model.json').write_text(json.dumps(model,indent=2)+'\n')
    print(f'ALLGATHER_COMPILE PASS parents=8 rows=63 expanded=80 cfg_words={len(cfg)}')
if __name__=='__main__':main()
