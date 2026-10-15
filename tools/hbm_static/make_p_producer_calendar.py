#!/usr/bin/env python3
"""Compile one bounded actual P-producer head; no numerical result input.

The diagnostic VM map is explicit and distinct for all16heads. Auxiliary
commands are stored in the real182-bit paged issuer alongside the SFU IO issuer.
Physical/global production admission remains open.
"""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from su_reduce_compile import Program

AUX=[('command_v',1),('source_operand',1),('source_word',10),('command_op',3),('a',10),('b',10),('d',10),('x',32),('tag',32),('publish_slot',1),('expected_tag',32),('publish_sector',16),('publish_word',3),('reduce_fetch_v',1),('reduce_fetch_sector',16),('reduce_fill_burst',4)]
IO=[('prefetch_v',8),('prefetch_scalar',8),('prefetch_sector',128),('prefetch_group',16),('prefetch_local_addr',120),('prefetch_word',24),('scalar_addr',96),('scalar_enable',4),('drain_v',2),('drain_addr',30),('drain_vm_sector',32),('drain_round_bf16',2),('arith_start',1)]


def packed(fields,layout):
    word=shift=0
    for k,w in layout:
        v=fields.get(k,0)
        if not 0<=v<1<<w:raise ValueError((k,v,w))
        word|=v<<shift;shift+=w
    return word


def compile_head(rows,head,sfu_tools,out,normalize=False,scaled_in_e=False,wrong_lease_sc=False):
    sys.path.insert(0,str(sfu_tools))
    from sfu_control_image import encode
    from sfu_vector_calendar import compile_vector
    beats=rows//16;bursts=rows//64
    sc=head*(rows//8);eraw=4096;scaled=sc if wrong_lease_sc else (eraw if scaled_in_e else 2048);eb=6000+head*(rows//8)
    mb=7800+head//8;se=7808+head//8;scalar_word=head%8;mb_local=12672
    io={};aux={};events={}
    def put(table,t,**fields):
        old=table.setdefault(t,{})
        if old.keys()&fields.keys():raise ValueError(('slot collision',t,old,fields))
        old.update(fields)
    def source_fetch(start,base):
        for b in range(bursts):put(aux,start+b,reduce_fetch_v=1,reduce_fetch_sector=base+8*b,reduce_fill_burst=b)
        return start+bursts-1+18
    def drain(start,base,rounding):
        for b in range(beats):put(io,start+b,drain_v=3,drain_addr=(16*b)|((16*b+8)<<15),drain_vm_sector=(base+2*b)|((base+2*b+1)<<16),drain_round_bf16=3 if rounding else 0)
        return start+beats-1
    def cmds(program):
        for t,op,a,b,d,x,tag in program.commands:
            put(aux,t,command_v=1,source_operand=int(op in (1,3)),source_word=x if op in (1,3) else 0,
                command_op=op,a=a,b=b,d=d,x=0 if op in (1,3) else x,tag=tag)
    def scalar(cycle,tag,sector):
        put(aux,cycle+9,publish_slot=1,expected_tag=tag,publish_sector=sector,publish_word=scalar_word)
        return cycle+8
    # Real VM rawSC -> actual A SRAM. Unused operands are not oracle-fed.
    for beat in range(beats):
        fields=dict(prefetch_v=0,prefetch_sector=0,prefetch_group=0,prefetch_local_addr=0)
        for part in range(2):
            sector=sc+beat*2+part;b=sector%8
            fields['prefetch_v']|=1<<b
            fields['prefetch_sector']|=sector<<(16*b)
            fields['prefetch_local_addr']|=(16*beat+8*part)<<(15*b)
        put(io,beat,**fields)
    arith_start=beats+20;put(io,arith_start,arith_start=1)
    scale_program=compile_vector(words=rows,bases=(0,0,0,0,0),m1=3,imm1=0x3d3504f3,rnd=0)
    scaled_end=drain(arith_start+scale_program['cycles']+16,scaled,False)
    max_start=source_fetch(scaled_end+16,scaled)
    p=Program();p.c=max_start
    for k in range(8):p.emit(0,d=k,x=0xff7fffff)
    for k in range(rows):p.emit(3,a=k%8,d=k%8,x=k)
    stride=1
    while stride<8:
        for k in range(0,8,2*stride):p.emit(5,a=k,b=k+stride,d=k)
        stride*=2
    p.emit(4,a=0,tag=2*head);max_issue=p.commands[-1][0];cmds(p)
    max_scalar=scalar(max_issue,2*head,mb)
    mb_fetch=max_scalar+15
    b=mb%8
    put(io,mb_fetch,prefetch_v=1<<b,prefetch_scalar=1<<b,prefetch_sector=mb<<(16*b),
        prefetch_group=1<<(2*b),prefetch_word=scalar_word<<(3*b))
    exp_start=mb_fetch+20
    exp_program=compile_vector(words=rows,bases=(0,mb_local,0,0,0),strides=(1,0,1,1,1),m1=3,imm1=0x3d3504f3,ad=3,sfu=1,rnd=0)
    raw_end=drain(exp_start+exp_program['cycles']+16,eraw,False)
    eb_end=drain(raw_end+2,eb,True)
    sum_start=source_fetch(raw_end+16,eraw)
    q=Program();q.c=sum_start;nc=rows//8;npad=1<<(nc-1).bit_length()
    for k in range(npad):q.emit(0,d=k)
    for offset in range(8):
        for chunk in range(nc):q.emit(1,a=chunk,d=chunk,x=chunk*8+offset)
    stride=1
    while stride<npad:
        for k in range(0,npad,2*stride):q.emit(2,a=k,b=k+stride,d=k)
        stride*=2
    q.emit(4,a=0,tag=2*head+1);sum_issue=q.commands[-1][0];cmds(q)
    sum_scalar=scalar(sum_issue,2*head+1,se)
    end=max(sum_scalar+32,eb_end+32)
    # Programme/control stages remain stable over each exact arithmetic drain.
    exp_offset=exp_start-arith_start
    arithmetic={'cycles':exp_offset+exp_program['cycles'],'rows':scale_program['rows']+
                [dict(cycle=r['cycle']+exp_offset,fields=r['fields']) for r in exp_program['rows']]}
    if normalize:
        # Actual MB/SE published by the producer; only SINK and PV are external.
        def scalar_fetch(t,sector,group):
            bank=sector%8
            put(io,t,prefetch_v=1<<bank,prefetch_scalar=1<<bank,
                prefetch_sector=sector<<(16*bank),prefetch_group=group<<(2*bank))
        se_fetch=sum_scalar+16
        scalar_fetch(se_fetch,7808,2)
        scalar_fetch(se_fetch+1,7840,0)
        den_start=se_fetch+22
        den_program=compile_vector(words=1,bases=(12720,mb_local,12688,0,0),
             strides=(0,0,0,1,1),ad=3,sfu=1,e1=2,rnd=0)
        den_drain=den_start+den_program['cycles']+16
        put(io,den_drain,drain_v=1,drain_addr=0,drain_vm_sector=7904,drain_round_bf16=0)
        pv_fetch=den_drain+16
        for beat in range(32):
            fields=dict(prefetch_v=0,prefetch_sector=0,prefetch_group=0,prefetch_local_addr=0)
            for part in range(2):
                sector=2304+2*beat+part;bank=sector%8
                fields['prefetch_v']|=1<<bank
                fields['prefetch_sector']|=sector<<(16*bank)
                fields['prefetch_local_addr']|=(16*beat+8*part)<<(15*bank)
            put(io,pv_fetch+beat,**fields)
        den_fetch=pv_fetch+32
        scalar_fetch(den_fetch,7904,1)
        norm_start=den_fetch+20
        norm_program=compile_vector(words=512,bases=(0,12704,0,0,0),
             strides=(1,0,1,1,1),m1=4,rnd=1)
        norm_drain=norm_start+norm_program['cycles']+16
        for beat in range(32):
            put(io,norm_drain+beat,drain_v=3,drain_addr=(16*beat)|((16*beat+8)<<15),
                drain_vm_sector=(4608+2*beat)|((4609+2*beat)<<16),drain_round_bf16=0)
        end=norm_drain+64
        for start,program in [(den_start,den_program),(norm_start,norm_program)]:
            offset=start-arith_start
            arithmetic['rows'] += [dict(cycle=r['cycle']+offset,fields=r['fields']) for r in program['rows']]
            arithmetic['cycles']=offset+program['cycles']
        events.update(se_prefetch=se_fetch,sink_prefetch=se_fetch+1,den_start=den_start,
            den_drain=den_drain,pv_prefetch=pv_fetch,den_prefetch=den_fetch,
            norm_start=norm_start,norm_drain=norm_drain)
    image=encode(arithmetic)
    if end>4096 or len(image)>4096:raise ValueError('PAGE_AW2 hardware capacity exceeded')
    # Address-tagged B scalar enabled only after real MB prefetch has landed.
    for t in range(end):
        fields=io.setdefault(t,{})
        fields['scalar_addr']=mb_local<<24
        fields['scalar_enable']=2 if t>=exp_start-2 else 0
        if normalize and se_fetch<=t<den_fetch:
            fields['scalar_addr']=12720|(mb_local<<24)|(12688<<48)
            fields['scalar_enable']=7
        if normalize and t>=den_fetch:
            fields['scalar_addr']=12704<<24
            fields['scalar_enable']=2
    out.mkdir(parents=True,exist_ok=True)
    (out/'arithmetic.hex').write_text(''.join(f'{w:0436x}\n' for w in image))
    (out/'io.hex').write_text(''.join(f'{packed(io[t],IO):0118x}\n' for t in range(end)))
    (out/'aux.hex').write_text(''.join(f'{packed(aux.get(t,{}),AUX):046x}\n' for t in range(end)))
    model={'rows':rows,'head':head,'scale_bits':'3d3504f3','arithmetic_rows':len(image),'io_aux_rows':end,
           'events':{'arithmetic_start':arith_start,'scaled_last_drain':scaled_end,'max_start':max_start,'max_scalar':max_scalar,
                     'mb_prefetch':mb_fetch,'exp_start':exp_start,'raw_e_last_drain':raw_end,'eb_last_drain':eb_end,'sum_start':sum_start,'sum_scalar':sum_scalar,**events},
           'diagnostic_VM_sectors':{'SC':sc,'scaled_SC':scaled,'E':eraw,'EB':eb,'MB':mb,'SE':se,'scalar_word':scalar_word,**({'PV':2304,'SINK':7840,'DEN':7904,'OUT':4608} if normalize else {})},
           'macro_inventory':{'operand':80,'arithmetic_programme':32,'io_programme':12,'aux_programme':4,'source_scratch':10,'VM':24},
           'extra_scalar_configuration_bits':4*(24+32+1),'head_reconfiguration_setup_not_priced':True,
           'scaled_SC_lease':('invalid_live_SC' if wrong_lease_sc else ('future_E_until_MAX_source_captured' if scaled_in_e else 'private_diagnostic')),
           'production_qualified':False,'physical_qualified':False,'native_whole_kernel_qualified':False}
    (out/'calendar.json').write_text(json.dumps(model,indent=2)+'\n')
    (out/'config.txt').write_text(' '.join(map(str,[rows,head,len(image),end,sc,scaled,eraw,eb,mb,se,scalar_word]))+'\n')
    return model


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('out',type=Path);p.add_argument('--sfu-tools',type=Path,required=True)
    p.add_argument('--rows',type=int,choices=(128,640),required=True);p.add_argument('--head',type=int,choices=range(16),default=0)
    p.add_argument('--normalize',action='store_true')
    a=p.parse_args();print(json.dumps(compile_head(a.rows,a.head,a.sfu_tools,a.out,a.normalize),indent=2))
