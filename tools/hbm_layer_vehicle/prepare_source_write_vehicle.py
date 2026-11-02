#!/usr/bin/env python3
"""Prepare real native write/refill wiring and vectors; never launch a simulator."""
import argparse
import hashlib
import json
import runpy
import subprocess
import sys
from pathlib import Path


def prepare(repo,out,image=None,isa_repo=None):
    if out.exists():raise ValueError('Fresh output required')
    out.mkdir(parents=True);src=out/'sources';src.mkdir();pins={};files=[]
    def read(ref,path):return subprocess.check_output(['git','-C',str(repo),'show',ref+':'+path])
    seed=out/'seed_stack0_body_probe.py'
    seed.write_bytes(read('1e7abd8ff','tools/hbm_layer_vehicle/stack0_body_probe.py'))
    ns=runpy.run_path(str(seed))
    old=json.loads(read('79d539a81','results/tok_hbm_provider_1030/timing833_source_dependencies.json'))
    paths=list(dict.fromkeys(ns['FILES']+list(old['shared_repo_files'])))
    for path in paths:
        # The only PHY response definition is the qualified external memory model.
        if Path(path).name.startswith('ot_hbm3e_phy_rc_'):continue
        raw=read('24de429cd',path);p=src/Path(path).name
        if p.exists() and p.read_bytes()!=raw:raise ValueError('basename source collision: '+path)
        p.write_bytes(raw);pins[path]=dict(commit='24de429cd',sha256=hashlib.sha256(raw).hexdigest())
        if p not in files:files.append(p)
    service=(src/'ot_hbm_static_load_stack0_service.sv').read_text()
    service=service.replace('module ot_hbm_static_load_stack0_service','module ot_hbm_static_service_write_fixture',1)
    marker=' // Provider ordering is leafb*2+g: physicalPC=half*16+b+8*g.'
    assert marker in service
    service=service.replace(marker,''' input wire lo_wbw_v,hi_wbw_v,input wire[29:0]lo_wbw_base,hi_wbw_base,
 input wire[11:0]lo_wbw_total,hi_wbw_total,input wire[31:0]write_v,
 input wire[959:0]write_addr,input wire[8191:0]write_data,
 output wire[31:0]write_ready,write_done,
'''+marker)
    before=".wbw_v(1'b0),.wbw_base(30'b0),.wbw_total(12'b0),.w_k_v(4'b0),.w_k_rdy(),.w_k_addr(120'b0),.w_k_wdata(1024'b0),.w_k_wr_done(),"
    after='.wbw_v(g<4?lo_wbw_v:hi_wbw_v),.wbw_base(g<4?lo_wbw_base:hi_wbw_base),.wbw_total(g<4?lo_wbw_total:hi_wbw_total),.w_k_v(write_v[g*4+:4]),.w_k_rdy(write_ready[g*4+:4]),.w_k_addr(write_addr[g*120+:120]),.w_k_wdata(write_data[g*1024+:1024]),.w_k_wr_done(write_done[g*4+:4]),'
    assert service.count(before)==1
    service=service.replace(before,after)
    p=src/'ot_hbm_static_service_write_fixture.sv';p.write_text(service);files.append(p)
    model='rtl/test/hbm_layer/ot_hbm3e_phy_rc_e8p5_dram_model.sv'
    raw=read('8f448a371',model);p=src/Path(model).name;p.write_bytes(raw);files.append(p)
    pins[model]=dict(commit='8f448a371',sha256=hashlib.sha256(raw).hexdigest())
    vehicle=Path(__file__).resolve().parents[2]/'rtl/test/hbm_layer/source_write_vehicle_1101.sv'
    p=src/vehicle.name;p.write_bytes(vehicle.read_bytes());files.append(p)
    (out/'files.f').write_text(''.join(str(p.resolve())+'\n'for p in files))
    (out/'source_pins.json').write_text(json.dumps(pins,indent=2)+'\n')
    # Stage actual fixed833 refresh rows, with both real half-PID cohorts.
    profile=out/'hbm_timing_833_profile.py';profile.write_bytes(read('24de429cd','tools/hbm_timing_833_profile.py'))
    for q in (0,1):
        subprocess.run([sys.executable,str(profile),'--first-pc',str(q*16),'--npc','16','--boot-row-out',str(out/f'boot_{q}.mem')],check=True,stdout=subprocess.DEVNULL)
    staging=dict(status='SIMULATION_ONLY_PREP_NOT_ELABORATED_OR_RUN',clock_ps=833,global_precision_fs=1,
        clock_drive='416500fs half edges, same833ps controller/stream clock',source_aliases=False,
        model='Persistent external DRAM8f448: real row/column/strobe writes, strict images, READ29/resetflush',
        actual_current_selected_COPY=False,
        scratch=dict(global_word_range=[261120,262144],slots=[[261120,261632],[261632,262144]],
            VM_SID=3,native_local_words=[64512,65024],alignment_words=64,
            status='UNITINPUT_RESERVATION_ONLY; canonical allocator currentlyscratch_reservedfalse',
            canonical_request='Reserve entire1024wordinterval acrossallphases/indirectaccesses, effectivealloccap261120, recompile/recheck; no freeexistingreservation.',
            ownership='Slot0 from actualstaging producerissue throughtrueWBACK/globalfence; Slot1 frombeforefirstoldreadback throughlastnewreadback. No overlap.',
            staged_DQ='Initialization throughactualnativeDQ/Wslot6 andnativecompletion; NOT a fabricatedCOPYproducer or canonicalstagingcost.'),
        existing_partial_proofs=dict(RAW_26b5c1288='ActualDBK→WBK→VMKS→PC24writes, but independentreadpayloadfixture, not persistentcausalreadback.',
            WBK_QH='ActualWBK→VMKS/PC→DRAM/ACK, but DMA-sideWD stimulus ratherthanDBK/nativeVMsource.'),
        mission=[
            'Initialize externalmemoryoldpattern, all selectedfillrowsectors explicitly; no uninitializedreads.',
            'Bootactualrefreshcfg. Fillownedepoch7 throughrealPC/VMKS; NPC2copyolddata toSlot1, verifythroughnativeRQ0/RR0.',
            'InitializealignedSlot0 newknownwords throughnativeDQ, verifyactualVMdone/readback. Thisisunitstimulus, notcanonicalCOPY.',
            'ProgramactualCW308collar withlegalresolvedordinal227, fixedissue/drainrelative dates. ObserveDBKmv_src separatelyfromtrueACK/mv_done.',
            'At store_done sample after NBA settlement: case-delta physical_completion_count must equal exact fragment sectors. Independently require physical_write_count delta equal sectors; accepted columns are not ACK retirement.',
            'Releaseoldcacheepoch7 afterlastconsumer. AfterACKfence begin/fillnewownedepoch8, copyfromactualupdatedDRAMthroughNPC2 toSlot1.',
            'ReadactualnativeSRAM throughRQ0/RR0 andcompareeverywrittenword toSlot0knowninputs; no modelpeek substitutes forreadback.'
        ],
        negatives=dict(premature_ACK='WB_MUT1 existing actual WBK mutant; event oracle observes independent service wk_done physical_completion_count at store_done, plus causal readback. Physical accepted-column count alone is insufficient.',
            missing_invalidation='Keepactualepoch7cache andomitrelease/newfill, repeatrealNPC2copy; actualoldBRAMdata must failnewwordoracle.'),
        costs=dict(canonical_COPY_edges=None,issue_date=None,drain_date=None,RR_RT=8,
            RR_RT_scope='ProposedlocalnativeVMunitprofile; no added72edgefabricatedtransport. Mustmeasureinfirstcomponentgate.',
            HOST_config_wire_edges=None,global_fence_date=None,physical_route_latency=None),
        holds=['No simulator/frontend/heavy job launched byprepare.',
            'Completeactualtestdriver/control-datequalification beforeclaimingcausalPASS.',
            'Selected raw COLL sector gather exists for QID2/3, but no VM0/1 source endpoint or complete bank-changing COPY programme is joined. Production COPY cost remains unpriced.',
            'No canonicaltop/RTL/plan/targetallocation/source0writeproducer installed. ActualN6/HOST/globalmapping remainsseparate.'])
    if image is not None:
        sys.path.insert(0,str((isa_repo or repo)/'tools/hbm_next'))
        from isa_loader import load_isa
        IR,IC=load_isa();records=IC.decode_all(image.read_bytes())
        candidates=[(0,18,17179919136,512)]
        for i,(_,r,rx,_)in enumerate(records):
            if(r.unit,r.op)==('DMA','STORE')and r.desc['O'].space=='HBM':
                for _,row in IR.expand(r,rx):
                    o=row.desc['O']
                    if o.n>=512:candidates.append((3,i,o.base,512))
        cases=[];case_dir=out/'cases';case_dir.mkdir();image_rows={0:set(),3:set()}
        for stk in (0,3):
            for q in (0,1):
                chosen=None
                for stack,record,base,n in candidates:
                    if stack!=stk:continue
                    groups=[]
                    for off in range(n//8):
                        sec=((base&((1<<35)-1))>>5)+off
                        qq=((sec>>6)^(sec>>11)^(sec>>16))&1;o=((sec>>7)<<6)|(sec&63)
                        if groups and groups[-1]['q']==qq and groups[-1]['o']+groups[-1]['sectors']==o:groups[-1]['sectors']+=1
                        else:groups.append(dict(q=qq,o=o,real=sec,wordoff=off*8,sectors=1))
                    chosen=next((g for g in groups if g['q']==q),None)
                    if chosen:break
                if chosen is None:raise ValueError('No actual stack/quadrant source fragment')
                n=chosen['sectors']*8;fmt=0 if stk==0 else 5;native_dst=(stk<<35)|(chosen['o']<<5)
                move=1|(fmt<<2)|(64512<<5)|(1<<77)|(fmt<<95)|(native_dst<<98)|(1<<170)|(1<<186)|(n<<206)
                read=(fmt<<2)|(((stk<<35)|(chosen['real']<<5))<<5)|(1<<77)|(1<<93)|(fmt<<95)|(261632<<98)|(1<<170)|(1<<186)|(n<<206)
                label=f'stack{stk}_q{q}';d=case_dir/label;d.mkdir()
                words=[(0x3f100000^(w*0x010101))&0xffffffff for w in range(n)]
                packets=[]
                for w in range(0,n,8):
                    data=sum(words[w+j]<<(32*j)for j in range(8))
                    packets.append((1<<280)|(((261120+w)>>3)<<264)|(data<<8)|255)
                (d/'staged_native_DQ.mem').write_text(''.join(f'{x:071x}\n'for x in packets))
                (d/'expected_new_words.mem').write_text(''.join(f'{x:08x}\n'for x in words))
                (d/'write_move227.mem').write_text(f'{move:057x}\n');(d/'read_move227.mem').write_text(f'{read:057x}\n')
                image_rows[stk].add(chosen['real']>>15)
                cases.append(dict(label=label,STK=stk,PHY_QUAD=q,VM_SID=3,
                    writer_source_SID=stk,writer_source_SID_matches_scratch=(stk==3),
                    source_SID_scope='DBK native issue_sec uses its STK strap as SID; STK0 cannot read SID3 scratch without a real COPY to VM0.',
                    record=record,representative_position=0 if stk==0 else None,
                    position_scope='Component input only, not adopted actual N6 position',record_namespace='original3916' if stk==0 else'resident37226',words=n,sectors=chosen['sectors'],
                    real_first_sector=chosen['real'],quadrant_ordinal=chosen['o'],source_word_offset=chosen['wordoff'],
                    native_source_word=64512,global_staged_word=261120,global_readback_word=261632,
                    window=dict(row=chosen['real']>>15,col=(chosen['real']>>8)&15,half=q),
                    issue_at=None,drain_at=None,COPY_cost_edges=None,CFG256_words_per_command=2,source_aliases=False))
        images=out/'images';images.mkdir()
        for stk,rs in image_rows.items():
            with(images/f'stack{stk}.hex').open('w')as f:
                for row in sorted(rs):
                    for sec in range(row<<15,(row+1)<<15):
                        value=sum(((0x3e000000^((sec*8+w)&0x00ffffff))&0xffffffff)<<(w*32)for w in range(8))
                        f.write(f'{sec:08x} {value:064x}\n')
        staging['cases']=cases
        staging['priced_staging_plan']=dict(status='BLOCKED_SELECTED_DATA_COPY_SOURCE; FINITE_ALLOCATION_REQUEST',
            reservation=[261120,262144],allocator_required_cap=261120,currently_reserved=False,
            SOURCE_COPY_selected=False,actual_COPY_cycles=None,actual_COPY_producer=None,
            native_read_chunks='ceil(fragment_words/64)',WB_sectors='fragment_words/8',
            issue_and_drain='Actual native VM/route profile + COPY completion + WB epochs needed; dates deliberatelynot0',
            dependency='Join actual VM0/1 source endpoint and selected raw COLL gather/delivery with a fixed bank-changing programme. No free generic COPY credit.')
    (out/'vehicle_plan.json').write_text(json.dumps(staging,indent=2)+'\n')
    print(json.dumps(dict(status=staging['status'],source_files=len(files),soft_write_boundary_bits=9334,heavy_launch=False)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--image',type=Path);p.add_argument('--isa-repo',type=Path)
    a=p.parse_args();prepare(a.repo,a.out,a.image,a.isa_repo)
