#!/usr/bin/env python3
"""Source-bound actual compile/program/controller event accounting, no RTL run.

Reproduce using Git metadata only. The local discrete scheduler models accepted
control events after READY; it neither reads KV/weight payloads nor invents HBM
arrival times. A uniform E->R0 cut is an explicitly conditional sizing case.
"""
import argparse
import hashlib
import json
import math
import re
import subprocess
from pathlib import Path

REAL='4e38326d6f361bc85e660f48c59c355e2bb95274'
BASE='e72abea5ae169d3167dddc89543013f0e6bb3a7a'
CENSUS='9696a5b920013eaa176f8ffe9995bef54da5d50f'
LAUNCH='1895c0711'
SERVICE='38967d1b790730cfe3a22d34cf1f2e6aa8961f0c'
PRIOR='ca3f30e8cddeb538f2dfba43507352ff8d2f5fac'
PINS={}
CACHE={}
ENG='rtl/hdc/v41x/ot_hdc_v41x_attn.sv'
ADAPT='rtl/w17_runtime/hdc/v41x/ot_hdc_v41x_att_adapt.sv'
CORE='rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv'
DIE='rtl/w17_runtime/chip/ot_chip_v41x_die.sv'
LIFE='rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv'
WINDOW='rtl/chip/ot_chip_v41x_window_attn_source.sv'


def read(commit,path):
    key=commit+':'+path
    if key not in CACHE:
        raw=subprocess.check_output(['git','show',key])
        CACHE[key]=raw.decode()
        PINS[key]=dict(commit=commit,path=path,sha256=hashlib.sha256(raw).hexdigest())
    return CACHE[key]


def record(commit,path):
    return json.loads(read(commit,path))


def citation(path,text):
    lines=read(REAL,path).splitlines()
    hits=[dict(line=i,text=s.strip()) for i,s in enumerate(lines,1) if text in s]
    if not hits:
        raise ValueError('Unbound source consumer '+path+':'+text)
    return dict(pin=REAL+':'+path,matches=hits)


def scheduler(rows=128, extra_cut=0, row_II=4, first_row=1, credit_count=64):
    """Non-ILV PWORDS1 controller control recurrence, pre-edge tick convention.

    Row producer is the READY bank-stage compatibility merge (II4), whose first
    beat is already held while A_LDX runs. Q/P producers are adapter A_RUN, not
    an idealised softmax stream. Transfer durations here are valid-line counts,
    not FP32 value emulation. Credit return includes the adapter register.
    """
    if rows<1 or rows>640 or extra_cut<0:
        raise ValueError('Unsupported schedule')
    blocks=math.ceil(rows/32)
    qcnt=wptr=qrow=plblk=plword=flblk=flcnt=filled=issblk=issc=0
    phase=False
    nextbank=qbank=plbank=0
    held=[False]*3
    guards=[0]*3
    blockbank={}
    events=[]
    sc_debt=pv_debt=0
    max_sc=max_pv=0
    sc_seen=pv_seen=0
    sc_due={}; pv_due={}; sc_return={}; pv_return={}; fill_due={}
    counts=dict(Q_push=0,P_loader_pop=0,KV_accept=0,QK_issue=0,PV_issue=0,fill_issue=0)
    stalls=dict(Q_bank=0,P_bank_or_lookahead=0,QK_row=0,QK_credit=0,PV_credit=0,PV_load_or_fill=0)
    q_load=[];p_load=[];kv_load=[];qk=[];pv=[]
    row_available=first_row
    for t in range(10000):
        sc_seen+=sc_due.get(t,0);pv_seen+=pv_due.get(t,0)
        # credits sampled this edge are from the adapter's preceding sc_v/pv_v.
        sr=sc_return.get(t,0);pr=pv_return.get(t,0)
        if t in fill_due:filled=fill_due[t]
        qgo=t>=1 and qcnt<16 and (qcnt!=0 or (not held[nextbank] and guards[nextbank]==0))
        words=min(16,math.ceil((rows-plblk*32)/2)) if plblk<blocks else 0
        pbankok=not held[nextbank] and guards[nextbank]<=5
        pgo=qcnt==16 and plblk<blocks and (plword!=0 or (pbankok and plblk<issblk+3))
        plast=pgo and plword+1==words
        kvgo=t>=row_available and wptr<rows
        loaded=plblk>issblk or (plast and plblk==issblk)
        final=issblk+1==blocks
        pvgo=phase and issblk<blocks and loaded and filled>issblk and (not final or pv_debt<credit_count)
        half_free=flblk<issblk+2 or (flblk==issblk+2 and pvgo and issc+1==8)
        flgo=phase and flblk<blocks and half_free
        qrowsok=wptr>=rows or qrow+4<=wptr
        qkgo=(not phase) and qcnt==16 and qrow<rows and qrowsok and sc_debt<credit_count
        ibank=(nextbank if plword==0 else plbank) if plblk==issblk else blockbank.get(issblk,0)
        if qcnt<16 and t>=1 and not qgo:stalls['Q_bank']+=1
        if qcnt==16 and plblk<blocks and not pgo:stalls['P_bank_or_lookahead']+=1
        if not phase and qcnt==16 and qrow<rows:
            stalls['QK_row']+=int(not qrowsok)
            stalls['QK_credit']+=int(sc_debt>=credit_count)
        if phase and issblk<blocks:
            stalls['PV_load_or_fill']+=int(not loaded or filled<=issblk)
            stalls['PV_credit']+=int(final and pv_debt>=credit_count)
        guards=[max(0,g-1) for g in guards]
        if qgo:
            if qcnt==0:qbank=nextbank;held[qbank]=True;nextbank=(nextbank+1)%3
            q_load.append(dict(cycle=t,bank=qbank,group=qcnt,mode=0))
            qcnt+=1;counts['Q_push']+=1
        if pgo:
            if plword==0:
                plbank=nextbank;blockbank[plblk]=plbank;held[plbank]=True;nextbank=(nextbank+1)%3
            p_load.append(dict(cycle=t,bank=plbank,group=plword,block=plblk,mode=1))
            if plast:plblk+=1;plword=0
            else:plword+=1
            counts['P_loader_pop']+=1
        if kvgo:
            kv_load.append(t);wptr+=min(4,rows-wptr);row_available=t+row_II;counts['KV_accept']+=1
        if qkgo:
            qk.append(t);qrow+=4;guards[qbank]=21;counts['QK_issue']+=1
            if qrow>=rows:phase=True;held[qbank]=False
            due=t+49+extra_cut
            sc_due[due]=sc_due.get(due,0)+1
            sc_return[due+1]=sc_return.get(due+1,0)+1
        if flgo:
            counts['fill_issue']+=1
            if flcnt+1==8:fill_due[t+2]=flblk+1;flblk+=1;flcnt=0
            else:flcnt+=1
        if pvgo:
            pv.append(dict(cycle=t,bank=ibank,block=issblk,dim=issc,final=final))
            guards[ibank]=20;counts['PV_issue']+=1
            if final:
                due=t+50+extra_cut
                pv_due[due]=pv_due.get(due,0)+1
                pv_return[due+1]=pv_return.get(due+1,0)+1
            if issc+1==8:held[ibank]=False;issblk+=1;issc=0
            else:issc+=1
        sc_debt+=int(qkgo)-sr
        pv_debt+=int(pvgo and final)-pr
        assert 0<=sc_debt<=credit_count and 0<=pv_debt<=credit_count
        max_sc=max(max_sc,sc_debt);max_pv=max(max_pv,pv_debt)
        if sc_seen==math.ceil(rows/4) and pv_seen==8 and qcnt==16 and plblk==blocks and wptr==rows:
            break
    else:raise ValueError('Control recurrence did not drain')
    # source bad-shape gate ensures one job (nhd/H=16/16) per attention op.
    return dict(rows=rows,extra_cut_cycles=extra_cut,counts=counts,stalls=stalls,
                Q_load_events=q_load,P_load_events=p_load,KV_accept_cycles=kv_load,
                QK_issue_cycles=qk,PV_issue_events=pv,
                outputs=dict(scores=sorted(sc_due),PV=sorted(pv_due)),
                adapter_A_RUN_completion_cycle=t,
                max_credit_debt=dict(score=max_sc,PV=max_pv),
                peak_registered_probability_skid_occupancy=0,
                convention='Cycle0 is job acceptance; all firings refer to pre-edge signals. Due outputs are observed at listed pre-edge cycles. No data/arithmetic simulation.',
                scope='Analytical source transcription after READY, not RTL equivalence or a routed timing result.')


def adapter_envelope(read_elements,write_words):
    """Count actual A_LDX capture/job and A_WR/idle states without payloads."""
    st='LDX';lc=0;l1=l2=jobv=False
    for t in range(1,10000):
        old1=l1;old2=l2;l1=False;l2=old1
        if st=='LDX':
            if lc<read_elements:lc+=4;l1=True
            elif not old1 and not old2:st='JOB'
        elif st=='JOB':
            if jobv:break
            jobv=True
    else:raise ValueError('Adapter prefix did not finish')
    prefix=t
    st='WR';wc=0;owe=idle=False
    for t in range(1,10000):
        if idle:break
        oldst=st;oldowe=owe;owe=False
        idle=oldst=='IDLE' and not oldowe
        if oldst=='WR':
            owe=wc<write_words;wc+=4
            if wc>=write_words:st='IDLE'
    else:raise ValueError('Adapter suffix did not finish')
    return dict(go_to_job_acceptance_cycles=prefix,run_complete_to_published_idle_cycles=t,
                read_issue_cycles=math.ceil(read_elements/4),write_issue_cycles=math.ceil(write_words/4))


def program_dependencies(bind):
    """Build actual unit-wait/issue-order graph without giving unknown costs 0."""
    last={};nodes=[]
    for ins in bind['instruction_trace']:
        pc=ins['pc'];f=ins['fields'];u=ins['unit'];wait=f.get('wait',0)
        deps=[]
        if pc:deps.append(dict(event=f'pc{pc-1}.issue',kind='sequencer_fetch_decode_issue_order',min_runtime_ticks=6 if nodes[-1]['unit'] else 5))
        for bit in range(5):
            if wait&(1<<bit) and bit+1 in last:deps.append(dict(event=f'pc{last[bit+1]}.complete',kind='wait_mask',unit=bit+1))
        if u in last:deps.append(dict(event=f'pc{last[u]}.ready',kind='unit_acceptance',unit=u))
        if u==6:
            for unit,old in last.items():
                if unit<=5:deps.append(dict(event=f'pc{old}.complete',kind='collective_all_engine_drain',unit=unit))
        if ins['tag'].endswith(('.scores','.pv')):
            deps.append(dict(event=f'pc{pc}.descriptor_READY',kind='generation_matched_packed_descriptor'))
        nodes.append(dict(pc=pc,unit=u,tag=ins['tag'],wait_mask=wait,reads=ins['reads'],writes=ins['writes'],
                          issue_dependencies=deps,completion_cost=f'bound_cost(pc{pc}, clocks, service, credits)',
                          completion_duration_known=False))
        if u:last[u]=pc
    return nodes


def main_record():
    launchpath='results/rtl/w17_connected_token_preparation_20261001/L0_cli_recovery_launch.json'
    manifest=record(LAUNCH,launchpath)
    census=record(CENSUS,'results/rtl/w11_field_common_prefix_coverage_gap_20261001/source_pins.json')
    assert PINS[LAUNCH+':'+launchpath]['sha256']==census['manifest_sha256']
    assert manifest['source_commit']==REAL and len(manifest['source_sha256'])==145
    # Bind only relevant sources; the committed census already accounts all145.
    required=[ENG,'rtl/hdc/v41x/ot_hdc_v41x_attn_tile.sv',ADAPT,CORE,DIE,LIFE,WINDOW,
      'rtl/test/v41_runtime/ot_v41_rt_die.sv','rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp',
      'tools/w17_current_fastpp_die_rt.py','rtl/chip/ot_chip_v41x_window_stage4.sv',
      'rtl/chip/ot_chip_v41x_attn_row_merge.sv','rtl/chip/ot_chip_v41x_window_refill_schedule.sv',
      'rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv','rtl/hdc/v41x/ot_hdc_v41x_vec.sv',
      'rtl/w17_runtime/chip/ot_chip_v41x_tile.sv']
    for p in required:
        read(REAL,p)
        assert PINS[REAL+':'+p]['sha256']==manifest['source_sha256'][p]
    args=manifest['observed_actual_argv']
    params={}
    for arg in args:
        m=re.fullmatch(r'-G(\w+)=(\d+)',arg)
        if m:params[m[1]]=int(m[2])
    for p in ['ILV','REPL','NSTAGE','SC_CRED','PV_CRED']:
        m=re.search(r'parameter (?:integer|bit) '+p+r'\s*=\s*(\d+)',read(REAL,ENG))
        params[p]=int(m[1])
    assert params==dict(H=16,D=512,TD=32,NL=4,TROWS=640,PWORDS=1,ILV=0,REPL=0,NSTAGE=1,SC_CRED=64,PV_CRED=64)
    bpaths=['results/rtl/hdc_v41x_fullshape_program_bind_rope_hbm.json',
            'results/rtl/hdc_v41x_fullshape_1m_s20260930_l20_program_bind_rope_hbm.json']
    binds=[record(REAL,p) for p in bpaths]
    isa_path='tools/hdc_isa_v41.py'
    isa_env={'__name__':'source_only_ISA','__file__':str(Path(isa_path).resolve())}
    exec(compile(read(REAL,isa_path),isa_path,'exec'),isa_env)
    program_identity=[]
    for bind_path,bind,layer in zip(bpaths,binds,(0,20)):
        stem=f'results/rtl/hdc_v41x_fullshape_l{layer}_program'
        meta=record(REAL,stem+'.json');code=read(REAL,stem+'.hex')
        assert meta['program_sha256']==PINS[REAL+':'+stem+'.hex']['sha256']
        metadata_bind_hash_matches=meta['source_sha256'][bind_path]==PINS[REAL+':'+bind_path]['sha256']
        assert meta['source_sha256'][isa_path]==PINS[REAL+':'+isa_path]['sha256']
        words=[int(line,16) for line in code.splitlines()]
        assert len(words)==len(bind['instruction_trace'])==meta['instructions']
        for word,event in zip(words,bind['instruction_trace']):
            fields={k:tuple(v) if isinstance(v,list) else v for k,v in event['fields'].items()}
            assert word==isa_env['encode'](full_shape=True,**fields)
        program_identity.append(dict(layer=layer,encoded_instructions=len(words),metadata=meta,
                                     metadata_bind_hash_matches=metadata_bind_hash_matches,
                                     actual_trace_reencoded_byte_identical=True,
                                     authority='Actual pinned ISA words and independently reencoded current trace; stale metadata hash is retained, not silently repinned.',
                                     program_sha256=meta['program_sha256'],bind_sha256=PINS[REAL+':'+bind_path]['sha256']))
    # L0 launch image identity from the retained source-work receipt, not a live
    # image or checkpoint read. The instruction hex above contains ISA only.
    workpath='results/rtl/w17_connected_token_preparation_20261001/L0_PC24_source_work_admission.json'
    work=record(SERVICE,workpath)
    assert program_identity[0]['program_sha256']==work['image_sha256']['prog.hex']
    admission=record(SERVICE,'results/rtl/w17_connected_token_preparation_20261001/L0_PC24_actual_HBM_service_binding.json')
    scalarpath='tools/w17_L0_window_service_expectation.py'
    scalar=read(SERVICE,scalarpath)
    assert PINS[SERVICE+':'+scalarpath]['sha256']==admission['conditional_expectation']['tool_sha256']
    # Existing scalar calibration is a source-only Python function. No main()
    # launch, backend, image or checkpoint access. Keep its sensitivity scope.
    env={'__name__':'model_source_only'}
    exec(compile(scalar,scalarpath,'exec'),env)
    sensitivity=[]
    for edge in (1,2):
        for start in range(12200,13401,100):
            before=env['replay'](start,3,edge);after=env['replay'](start+2,3,edge)
            sensitivity.append(dict(start=start,edge_padding=edge,elapsed=before['elapsed_cycles'],
                                    shifted_start_elapsed=after['elapsed_cycles'],
                                    completion_delta=after['end_cycle']-before['end_cycle']))
    prior=record(PRIOR,'results/uarch/dsrom_attention_controller_gap_20261001/composed_model_gap.json')
    whole=record(BASE,'results/quality/w16_w17_whole_calendar_20261001/actual_program_metadata.json')
    attention=[n for n in whole['functional_ops'] if n['kind']=='attention']
    assert len(attention)==40
    producer=whole['producer_source_pin']
    read(producer['commit'],producer['path'])
    assert PINS[producer['commit']+':'+producer['path']]['sha256']==producer['sha256']
    # Structural graph depth; deliberately not a timing result.
    depth={}
    for n in whole['functional_ops']:
        depth[n['id']]=max((depth[x] for x in n['depends_on']),default=0)+int(n['kind']=='attention')
    actual=[]
    for b in binds:
        ins=b['instruction_trace'];score=next(x for x in ins if x['tag'].endswith('.scores'))
        pv=next(x for x in ins if x['tag'].endswith('.pv'))
        soft=next(x for x in ins if x['pc']>score['pc'] and x['unit']==2 and x['fields'].get('wait',0)&1)
        drain=next(x for x in ins if x['pc']>pv['pc'] and x['unit']==2 and x['fields'].get('wait',0)&1)
        rows=128 if b['layer']==0 else 640
        heads=8<<score['fields']['me_hg']
        assert heads==16 and pv['fields']['me_hg']==1
        actual.append(dict(layer=b['layer'],position=b['position'],rows=rows,heads=heads,engine_jobs_per_op=heads//16,
             score_instruction=score,PV_instruction=pv,SU_wait_for_score_completion=soft,
             SU_wait_for_PV_completion=drain,
             QK_op=dict(X_read_elements=heads*512,X_read_issue_cycles=heads*512//4,
                        result_write_words=heads*math.ceil(rows/16),result_write_issue_cycles=heads*math.ceil(rows/16)//4),
             PV_op=dict(X_read_elements=heads*rows,X_read_issue_cycles=heads*rows//4,
                        result_write_words=heads*32,result_write_issue_cycles=heads*32//4),
             source_admission='L0 descriptor admitted after matched stage/READY and SU idle; runtime completion not claimed' if rows==128 else
                 'REJECTED by current L0_ONLY lifecycle: incoming_rows640 !=128, before engine issue. L20 bind is a program prerequisite, not a current connected engine execution.',
             per_rank_controller_job_completion_dependencies=2,
             TP_group_serial_multiplier=1,
             graph=program_dependencies(b)))
    normal=scheduler();cut=scheduler(extra_cut=2)
    assert normal['counts']==dict(Q_push=16,P_loader_pop=64,KV_accept=32,QK_issue=32,PV_issue=32,fill_issue=32)
    assert cut['Q_load_events']==normal['Q_load_events'] and cut['P_load_events']==normal['P_load_events']
    assert cut['QK_issue_cycles']==normal['QK_issue_cycles'] and cut['PV_issue_events']==normal['PV_issue_events']
    assert cut['adapter_A_RUN_completion_cycle']-normal['adapter_A_RUN_completion_cycle']==2
    assert max(cut['max_credit_debt'].values())<64
    # Check the same guarantees across finite complete WINDOW row counts and
    # delayed initial row offers. This is model validation, not an RTL gate.
    checked=0
    for rows in (4,8,32,64,128):
        for first in (1,17,64,129):
            a=scheduler(rows,first_row=first);z=scheduler(rows,2,first_row=first)
            assert a['QK_issue_cycles']==z['QK_issue_cycles'] and a['PV_issue_events']==z['PV_issue_events']
            assert z['adapter_A_RUN_completion_cycle']-a['adapter_A_RUN_completion_cycle']==2
            checked+=1
    # The write word count is nhd * ceil(nout/W), not nhd*rows:
    qenv=adapter_envelope(16*512,16*math.ceil(128/16))
    penv=adapter_envelope(16*128,16*math.ceil(512/16))
    assert qenv['run_complete_to_published_idle_cycles']==35
    assert penv['run_complete_to_published_idle_cycles']==131
    qenv['go_to_idle_cycles_post_READY']=qenv['go_to_job_acceptance_cycles']+normal['adapter_A_RUN_completion_cycle']+qenv['run_complete_to_published_idle_cycles']
    penv['go_to_idle_cycles_post_READY']=penv['go_to_job_acceptance_cycles']+normal['adapter_A_RUN_completion_cycle']+penv['run_complete_to_published_idle_cycles']
    # A finite-credit negative case ensures the scheduler does not assume
    # perfect downstream service. It is an analytical mutant, never hardware.
    small=scheduler(credit_count=8);small_cut=scheduler(extra_cut=2,credit_count=8)
    assert small['QK_issue_cycles']!=small_cut['QK_issue_cycles']
    assert small_cut['adapter_A_RUN_completion_cycle']-small['adapter_A_RUN_completion_cycle']==8
    long=scheduler(extra_cut=128)
    assert long['QK_issue_cycles']==normal['QK_issue_cycles']
    assert long['max_credit_debt']==dict(score=32,PV=8)
    allrows=scheduler(640,row_II=1);allrows_cut=scheduler(640,13,row_II=1)
    assert allrows['QK_issue_cycles']==allrows_cut['QK_issue_cycles']
    assert allrows_cut['max_credit_debt']['score']==63
    # Bind completion costs on the actual instruction graph after READY; the
    # descriptor service/previous-unit waits remain separate predecessor edges.
    for prog in actual:
        if prog['layer']==0:
            for node in prog['graph']:
                if node['tag'].endswith(('.scores','.pv')):
                    env=qenv if node['tag'].endswith('.scores') else penv
                    node['completion_duration_known']=True
                    node['completion_cost']=env['go_to_idle_cycles_post_READY']
                    node['cost_scope']='Logical runtime ticks after descriptor_READY with fixed VM and source-bound WINDOW merge; upstream descriptor/SU wait remains separately bound.'
                    node['uniform_cut_extra_completion_ticks']=2
    load=512+3+2+8;issue=576+1+2;tag=35
    added=2*(64*(load+issue)+tag)
    citations={
      'load_mode_and_acceptance':citation(ENG,'e_ld_mode <= p_go'),
      'Q_loader':citation(ENG,'assign q_ready ='), 'P_loader':citation(ENG,'wire p_ready_i ='),
      'no_skid_actual':citation(ENG,'assign p_v_i = p_v'),
      'last_word_bypass':citation(ENG,'wire iss_loaded ='),
      'bank_guard':citation(ENG,'bcnt[iss_bank] <='),
      'finite_local_valid':citation(ADAPT,'if (q_go) begin qi'),
      'P_valid_until_accept':citation(ADAPT,'if (p_go) begin'),
      'registered_credit_return':citation(ADAPT,'sc_cr <= sc_v; pv_cr <= pv_v'),
      'both_halves_completion':citation(ADAPT,'nsc + sc_v == sc_need'),
      'VM_read_capture':citation(ADAPT,'l2_v <= l1_v'),
      'VM_result_writes':citation(ADAPT,'wc + p < wend'),
      'adapter_published_idle_and_write_drain':citation(ADAPT,'idle <= (st == A_IDLE)'),
      'VM_no_backpressure_read':citation('rtl/w17_runtime/chip/ot_chip_v41x_tile.sv','if (vx_re[q]) vx_q'),
      'VM_masked_write':citation('rtl/w17_runtime/chip/ot_chip_v41x_tile.sv','if (vw_me_mask[q*W + l])'),
      'generation_wrap_source_drain':citation(DIE,'!win_service_busy && window_prime_ready && !win_blk_v'),
      'matching_row_producer_drain':citation(CORE,'wire win_admit ='),
      'packed_ready':citation(ADAPT,'assign packed_kv_ready ='),
      'SU_expected_wait':citation(CORE,'wire waited ='),
      'SU_completion':citation('rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv','assign idle ='),
      'SU_actual_retirement':citation('rtl/hdc/v41x/ot_hdc_v41x_vec.sv','if (ret_p && ret_p_last)'),
      'SU_pipeline_idle':citation('rtl/hdc/v41x/ot_hdc_v41x_vec.sv','wire idle_c ='),
      'descriptor_READY':citation(LIFE,'assign issue_ok = state == READY'),
      'descriptor_DRAIN':citation(LIFE,'DRAIN: begin'),
      'descriptor_L0_only':citation(DIE,'.L0_ONLY(1)'),
      'descriptor_shape_refusal':citation(LIFE,'L0_ONLY &&'),
      'WINDOW_only_runtime':citation('rtl/test/v41_runtime/ot_v41_rt_die.sv','.WINDOW_HBM_ATTENTION(1)'),
      'stage_READY_no_issue_cycle':citation(WINDOW,'assign staged_v=issue_v && !staged_sent'),
      'stage_bank_finite_ready':citation('rtl/chip/ot_chip_v41x_window_stage4.sv',"assign req_ready = 1'b1"),
      'stage_bank_response':citation('rtl/chip/ot_chip_v41x_window_stage4.sv','rsp_v <= v1'),
      'row_merge_accept':citation('rtl/chip/ot_chip_v41x_attn_row_merge.sv','if (kv_v && kv_ready)'),
      'row_merge_wait':citation('rtl/chip/ot_chip_v41x_attn_row_merge.sv','WAIT_WB: if (wb_rsp_v)'),
      'row_merge_compat_default':citation(WINDOW,'end else begin : g_compat'),
      'refill_serial_source':citation('rtl/chip/ot_chip_v41x_window_refill_schedule.sv','WAIT: if (prefetch_ok)'),
      'engine_compile':citation('tools/w17_current_fastpp_die_rt.py','"-GH=16"'),
      'runtime_no_register_added_by_cut':citation('rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp','bool att_propagate()')}
    return dict(schema='dsrom.attention-controller-product-events.v1',verdict='LOCAL_EVENT_AND_CREDIT_MODEL_BOUND_WHOLE_PRODUCT_ADMISSION_BLOCKED',
      scope='Advance actual compile/consumer binding; no source replacements, field latency transfer, RTL/PnR or payload reads.',
      original_failure=prior['original_failure'],source_dependency_events=citations,
      manifest_binding=dict(source_commit=REAL,manifest_commit=LAUNCH,manifest_sha256=census['manifest_sha256'],
                            source_count=145,relevant_source_hashes_checked=len(required),compile_params=params,
                            census_commit=CENSUS,observed_compile_argv=args),
      characterization_vs_real=dict(characterization_source=prior['engine_source_commit'],
           characterization=dict(PWORDS=2,ILV=1,REPL=2,NSTAGE=2,PHYS=1),
           actual=dict(params,PHYS=0,stationary_banks=3,BW=2,probability_skid_entries=0),
           transfer='Acceptance logic/source comparison only; CTS stub9537 fanout/geometry and timing not transferred to the real arithmetic engine; FAST fieldLAT8 does not set attention or SU valid latency.'),
      program_identity_checks=program_identity,
      bound_programs=actual,
      adapter_control_envelopes=dict(QK=qenv,PV=penv,
          scope='Source counted fixed VM ports and state transitions; postREADY first WINDOW beat held during A_LDX. A_RUN from control scheduler, not real-engine measured timing.'),
      actual_port_and_state_budget=dict(Q_data_Bpc=1024,P_data_Bpc=64,KV_data_Bpc_peak=2120,
          KV_compat_sustained_Bpc=530,VM_X_read_Bpc=16,VM_result_write_Bpc=256,
          E_load_boundary_bits_per_cycle=64*525,E_issue_boundary_bits_per_cycle=64*579,
          runtime_att_to_bits=25690,runtime_att_from_bits=35938,
          staging_bits=640*16*265,stationary_bits=64*3*16*32*16,transposer_bits=64*2*32*8*18,
          MACs_per_cycle_peak=32768,
          note='Logical widths/rates; no measured mapped area, real macro slot capacity or field512bit route transfer.'),
      local_finite_service=dict(
         Q_and_P='Adapter A_RUN holds q_v/p_v and ordered payloads until handshake; one Q head per beat and one P word per beat. No external SU service after A_LDX completes.',
         producer_X='G4 fixed vector-memory reads, two-cycle capture, BF16 RNE. L0 QK2048 read-issue cycles; PV512. Result writes32/128 issue cycles respectively; setup/drain states additional.',
         row_stage='All128 WINDOW rows validated before READY. Four-bank req_ready=1; two registered stages. Compatibility merge consumes a four-row beat every4 cycles once engine KV-ready, holding first beat during A_LDX.',
         credits='SC/PV64 initial reserved beats, registered credit return from actual adapter. No downstream ready on output; reserved result buffers write unconditionally. Final PV uses8 credits; nonfinal blocks use none.',
         completion='A_RUN waits all32 score beats AND8 final PV beats, all input valids drained; then A_WR masked VM writes before ME idle and descriptor DRAIN->IDLE.',
         pre_READY='2176 cold HBM reads with1 outstanding refill credit; bounded own occupancy, not an unconditional arrival deadline. Existing timed provider has finite default timings, but reset/bank state and competing-request schedule not bound to observed PC24.',
         SU='PC24 waitmask2 is published SU idle, not expected vector-count alone. PC23 emits4 packed RoPE vectors at SUN256; cr_dseq and pipeline/reducer retirement determine idle. No cut-induced delay before ME issue; CROM/RoPE service guarantees remain separate.'),
      local_event_schedules=dict(baseline=normal,uniform_two_stage_diagnostic=cut),
      conditional_cut=dict(location='Uniform E->R0 load + issue + shared result-tag boundary, common delay2',
           implementation_applied=False,certified_minimum=False,
           state=dict(load_bits_per_tile=load,issue_bits_per_tile=issue,shared_tag_bits=tag,replicas=64,
                      added_register_bits=added,DFF_cell_area_um2=round(added*0.2916,4),
                      return_reset_clock_hold_buffer_placement_area='Requires contextual physical intake; not priced as zero'),
           finite_credit_effect=dict(max_score_debt=cut['max_credit_debt']['score'],max_PV_debt=cut['max_credit_debt']['PV'],
                     reserved_each=64,added_input_skid_entries_needed_for_this_cut=0,controller_issue_stall_delta=0,
                     L0_total_score_beats_per_job=32,L0_total_final_PV_beats_per_job=8,
                     L0_credit_sufficiency='All32 score and8 finalPV beats fit initially reserved64 each. For one-job-at-a-time caller, any finite uniform cut cannot exhaust initial credits; this does not qualify a physical delay or clock.',
                     general_full640_II1_conservative_delay_check=13,
                     limit_basis='Conservative score issue-to-credit roundtrip <=51+delay cycles at worst II1, so <=64 fordelay<=13. L0 actual rowII4 gives tighter observed model debt. This is not a physical-stage qualification.'),
           alignment_and_bank_invariance='Every load-write and issue-read timestamp shifts by same2 cycles, including bank/group/w2v/data/valid. Pairwise RAW/WAR margins unchanged; keep GUARD_Q20/GUARD_P16 and NBANK3. Last-P-word issue bypass remains paired. An asymmetric load-only cut does not have this property.',
           cut_mode_data_alignment=dict(load_mode_accepts='p_v && p_ready_i on actual no-skid path; coincides with loader pop',
                    Q_push='q_v && q_ready; Q and P stationary data/mode/bank/group enter same E edge',
                    controller_vs_consumer='Controller accept/issue counters unchanged; only actual R0 write/read/output visibility shifts. Mode-only or load-only cuts require a different guarded recurrence.',
                    completion_and_reuse='Caller serializes one job and observes all score/PV outputs plus final masked writes. Added pipeline drains before published idle; generation DRAIN and wrap ownership remain tied to actual source service.'),
           transfer_latency=dict(local_job_completion_delta_cycles=2,L0_QK_and_PV_complete_dependencies=2,
                      local_two_op_serial_upper_cycles=4,local_two_op_serial_upper_common3600MHz_ticks=12,
                      caveat='Bound on these controller episodes with producer schedule held fixed. Program HC overlap can hide some QK delay. New PV prefetch start can change timed HBM service; full-token bound requires that service recurrence, not addition of4 per layer.'),
           async_domain='Actual runtime models share clk; product1.2GHz streaming /0.9GHz serial timing must compose3/4 common3600MHz ticks and add measured CDC/return credit costs. No free or changed clock.',
           readiness='Local input/event/credit sizing available for review; no implementation admission while real endpoint geometry/physical context and complete service-start schedule remain unbound.'),
      actual_critical_dependency_counts=dict(
           L0_per_rank=dict(engine_jobs=2,Q_load_accepts=32,P_loader_pops=128,QK_issue_beats=64,PV_issue_beats=64,
                            score_to_SU_wait_pc=[24,30],PV_to_SU_wait_pc=[32,34],
                            visible_completion_joins=2,fanout_multiplier=1),
           L20_program=dict(engine_jobs_requested=2,Q_load_accepts_if_admitted=32,P_loader_pops_if_admitted=640,
                        completion_wait_pcs=[[55,61],[63,65]],actual_runtime_admission='FAIL_SHAPE before issue; do not count these as executed jobs.'),
           whole_functional_graph=dict(source=whole['producer_source_pin'],attention_nodes=40,
                        attention_nodes_on_longest_dependency_chain=max(depth.values()),
                        conditional_two_job_adapter_completion_joins=80,
                        conditional_uniform_cut_serial_ticks=480,
                        claim='80/480 are structural conditional counts, not an executed full40 schedule or token latency. Existing functional graph is retained; full40 runtime unavailable and L20 descriptor source unsupported.')),
      HBM_calibration_reuse=dict(provider=admission['actual_backend'],conditions=admission['conditional_expectation']['conditions'],
             sensitivity_cases=sensitivity,shifted_start_two_cycle_completion_delta_range=[min(x['completion_delta'] for x in sensitivity),max(x['completion_delta'] for x in sensitivity)],
             verdict='Sensitivity transcription retained; actual bank/start state and queue competitors unresolved. No finite actual pre_READY deadline or full-token rate claimed.'),
      four_target_applicability=dict(DeepSeek_V41_ROM='Direct source4e383 postREADY controller composition bound for L0; indexed/L20 producer rejected by current source.',
           Qwen3_ROM='No matching source4e383 attention adapter; no latency/state transfer. Parent Qwen program/model retained.',
           Qwen3_GPU_HBM='Ordinary GPU TC/RF/TMEM/shared-memory/collective consumers remain owner-bound; no dedicated DSROM controller cut transferred.',
           DeepSeek_V41_GPU_HBM='Same workload labels do not create DSROM controller wiring; ordinary SM source/finite service graph retained, no imported penalty.'),
      remaining_exact_intakes=[
        'Measured real engine/control replica macro endpoints, directional M2-M5 channel capacity, mux/fanout/clock/reset/hold and complete slot area; original b819 stub coordinates cannot supply this.',
        'Source-bound actual prefetch starts, postwrite/RoPE bank state and competing request schedule for fixed HBM recurrence; existing cold scenarios are sensitivity only.',
        'Real indexed/selected CKV source plus descriptor lifecycle supports T640 and generation READY/DRAIN; present L0_ONLY source explicitly rejects it.',
        'Full40 compiled issue/complete graph and target-domain CDC costs; the retained40 functional dependency nodes establish structural joins, not finite physical token latency.',
        'Model-priced >=1% per-user gain and measured exact real-engine gain, opt-in gate, contextual SS/FF and hub routing gate before implementation/adoption; preserve current failure.'],
      analytical_checks=dict(cases=checked,
                reduced_credit_negative_case=dict(credits=8,baseline_completion=small['adapter_A_RUN_completion_cycle'],
                    cut_completion=small_cut['adapter_A_RUN_completion_cycle'],delta_cycles=8,
                    schedules_changed=True,scope='Analytical negative only, not proposed hardware or source parameter change'),
                initial_credit_sufficiency_large_delay_check=dict(delay=128,max_debt=long['max_credit_debt'],issue_schedule_unchanged=True),
                hypothetical_T640_II1_check=dict(delay=13,score_debt=63,issue_schedule_unchanged=True,
                    scope='Analytical credit stress only; actual WINDOW-only product rejects T640'),
                encoded_trace_byte_match='PASS_113_L0_AND_144_L20',
                L0_metadata_bind_hash='STALE_RETAINED_INDEPENDENT_ISA_REENCODE_PASS',
                adapter_prefix_suffix_state_count='PASS',counts='PASS',credit_conservation='PASS',
                identical_accept_and_issue_schedules_under_uniform_cut='PASS',two_cycle_local_completion_delta='PASS',
                source_manifest_and_census_hash_binding='PASS',not_an_RTL_exact_gate=True),
      operations=dict(RTL_edits=0,original_model_edits=0,PnR_jobs=0,payload_reads=0,live_process_operations=0),pins=PINS)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path);a=p.parse_args()
    d=main_record();d['generator_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    out=json.dumps(d,sort_keys=True,indent=2)+'\n'
    if a.output:
        if a.output.exists() and a.output.read_text()!=out:raise SystemExit('Choose a new evidence path; differing records are immutable')
        a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(out)
    else:print(out,end='')

if __name__=='__main__':main()
