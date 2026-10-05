#!/usr/bin/env python3
"""One read-only snapshot and pinned static PC24 diagnosis. No build/process attach."""
import argparse,hashlib,json,re,subprocess,types
from datetime import datetime,timezone
from pathlib import Path
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
ROOT=Path(__file__).resolve().parents[1]
PATHS=['tools/hdc_isa_v41.py','rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp','rtl/test/v41_runtime/ot_v41_rt_die.sv','rtl/w17_runtime/chip/ot_chip_v41x_die.sv','rtl/w17_runtime/chip/ot_chip_v41x_tile.sv','rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv','rtl/hdc/v41x/ot_hdc_v41x_su_adapt.sv','rtl/hdc/v41x/ot_hdc_v41x_vec.sv','rtl/hdc/v41x/ot_hdc_v41x_window_kv_blocks.sv','rtl/chip/ot_chip_v41x_attn_desc_lifecycle.sv','rtl/chip/ot_chip_v41x_window_attn_source.sv','rtl/chip/ot_chip_v41x_window_refill_schedule.sv','rtl/chip/ot_chip_v41x_window_kv_prefetch.sv','rtl/chip/ot_chip_v41x_kv_reqmux.sv','rtl/chip/ot_chip_v41x_kv_rope_reqmux.sv','rtl/chip/ot_chip_v41x_hbm_karb.sv','rtl/chip/ot_chip_v41x_hbm3e_phy.sv','rtl/hdc/v41x/ot_hdc_v41x_idx_hbm.sv']
def sha(b):return hashlib.sha256(b).hexdigest()
def pinned(p):return subprocess.check_output(['git','show',PIN+':'+p],cwd=ROOT)
def decode_terminal(value):
    fields=[('fault_sticky',32),('core_st',4),('d_unit',3),('idles',5),('coll_busy',1),('waited',1),('cdma_busy',1),('cdma_mode',1),('cdma_fault',1),('e_valid',1),('e_ready',1),('o_valid',1),('o_ready',1),('padding',7)]
    out={};shift=0
    for name,width in reversed(fields):out[name]=(value>>shift)&((1<<width)-1);shift+=width
    out['SU_idle']=bool(out['idles']&2)
    return out

def collect(work,images,baseline,out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    sources={p:pinned(p) for p in PATHS};texts={p:b.decode() for p,b in sources.items()}
    launch_bytes=(work/'launch.json').read_bytes();launch=json.loads(launch_bytes)
    assert launch['source_commit']==PIN
    mismatches={p:sha(b) for p,b in sources.items() if p in launch['source_sha256'] and sha(b)!=launch['source_sha256'][p]}
    assert not mismatches,mismatches
    isa=types.ModuleType('pinned_isa');isa.__file__=str(ROOT/'tools/hdc_isa_v41.py');exec(compile(texts['tools/hdc_isa_v41.py'],isa.__file__,'exec'),isa.__dict__)
    decoded={};images_sha={};cfgs={}
    for rank in range(4):
        pp=images/('r'+str(rank))/'prog.hex';data=pp.read_bytes();words=[int(w,16) for w in data.decode().splitlines() if w.strip()]
        decoded[str(rank)]={str(n):isa.decode(words[n],full_shape=True) for n in (21,22,23,24)}
        images_sha[str(pp)]=sha(data)
        cp=pp.with_name('cfg.txt');cb=cp.read_bytes();images_sha[str(cp)]=sha(cb)
        cfgs[str(rank)]={k:int(v,0) for k,v in (line.split() for line in cb.decode().splitlines() if line.strip())}
    assert images_sha[str(images/'r0/prog.hex')]=='e3d93b7bd9b74773c109761c41fbe5fcd72503a2513ac420abc5ddfffae9dd4a'
    for d in decoded.values():
        assert d['24']['unit']==1 and d['24']['wait']==2 and d['24']['me_k']==512
        assert d['24']['me_d_nout']==33 and d['24']['me_d_tiles']==46
        assert d['23']['su_nout']==16 and d['23']['su_nin']==64 and d['23']['su_chase']==0 and d['23']['sfu']==0 and d['23']['red']==0
    progress=(work/'L0_output/progress.log').read_bytes();(out/'progress_snapshot.log').write_bytes(progress)
    rows=[]
    for line in progress.decode().splitlines():
        m=re.fullmatch(r'CYC (\d+) wall ([\d.]+) s pc (\d+) (\d+) (\d+) (\d+)',line)
        if m:rows.append(dict(cycle=int(m[1]),wall_seconds=float(m[2]),pc=list(map(int,m.groups()[2:]))))
    first=next(i for i,r in enumerate(rows) if r['pc']==[24]*4);before=rows[first-1];after=rows[first];last=rows[-1]
    assert all(r['pc']==[24]*4 for r in rows[first:])
    record_bytes=(baseline/'record.json').read_bytes();br=json.loads(record_bytes);log=(baseline/'runtime.log').read_bytes()
    assert br['status']=='PASS_BOUNDED_CONNECTED_BASELINE' and br['simulation']['log_sha256']==sha(log)
    assert br['metrics']==dict(start=12300,staged=136669,done=136800,refill=124368,reads=2176,replies=2176,beats=32,max_inflight=1)
    assert all(sha(pinned(p))==h for p,h in br['source_sha256'].items())
    (out/'baseline_attempt9_record.json').write_bytes(record_bytes);(out/'baseline_attempt9_runtime.log').write_bytes(log)
    refs={}
    anchors={'rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv':['wire waited =','S_DEC: if (win_admit)','wire kv_gate =','S_GO: begin pc <='], 'rtl/chip/ot_chip_v41x_window_attn_source.sv':['assign staged_v=','assign issue_ready='], 'rtl/chip/ot_chip_v41x_window_kv_prefetch.sv':['assign s_rdy =','m_tag[WIN_STACK*TAGW +: TAGW] = TAGW\'(sec);','FR: if (grant)','FR_DONE: if (response)'], 'rtl/chip/ot_chip_v41x_hbm3e_phy.sv':['ot_hdc_v41x_idx_hbm #'], 'rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp':['long WD =','if (cyc - last_move > WD)'], 'rtl/hdc/v41x/ot_hdc_v41x_vec.sv':['wire ch_ok =','wire idle_c =']}
    for p,aa in anchors.items():refs[p]={a:next(i for i,l in enumerate(texts[p].splitlines(),1) if a in l) for a in aa}
    r=dict(schema='opentallas.pc24_connected_static_diagnosis.v1',utc=datetime.now(timezone.utc).isoformat(),source_commit=PIN,source_sha256={p:sha(b) for p,b in sources.items()},launch_sha256=sha(launch_bytes),launch_pin_mismatches=mismatches,image_instruction_config_sha256=images_sha,decoded_instructions=decoded,configuration=cfgs,source_line_references=refs,
       trace=dict(path=str(work/'L0_output/progress.log'),snapshot_bytes=len(progress),snapshot_sha256=sha(progress),previous=before,first_all_PC24=after,last=last,all_ranks_PC24_through_snapshot=True,elapsed_since_transition_interval=[last['cycle']-after['cycle'],last['cycle']-(before['cycle']+1)],no_periodic_handshake_or_SU_state=True),
       PC24=dict(operation='ME attention QK',wait_mask=2,wait_interpretation='SU idle AND no registered su_go; no ME wait bit',effective_k=512,effective_nout=128,effective_tiles=4,raw_dynamic_selectors={'33':'FDYN_T0','46':'FDYN_CEIL_T0_32'},issue='waited && unit_ready && q_gate && kv_gate && m0_gate; kv_gate includes kv_ok && !kvd_v and win_admit; S_GO increments PC after issue',prefetch_can_overlap_SU23=True),
       SU23=dict(elements=1024,lanes=256,slot_elements=64,rows_per_vector=4,vectors=4,chase=0,SFU=0,reduction=0,external_credit_chain=False,flatten=False,flatten_reason='A and output outer stride512 differ from extent64',control_path_depth='1 broadcast +3 F +1 PRE +3 M1 +3 M2 +3 AD +0 SFU +6 epilogue +1 retirement =21, plus setup/status edges; no memory-ready handshake on raw reads/stores',scope='Prior SU pipeline occupancy can delay first emit; no exact live accepted-edge/deadline or SU runtime arithmetic credit inferred'),
       dependency_chain=[
         'PC21 producer handoff: core blocks drains16 blocks; source writes code WC then masked scale WS per block; core EMPTY is final block acceptance, distinct from final source write ack. PC24 decode waits win_idle before descriptor.',
         'kvd_v is formed in S_DEC with win_idle; lifecycle accepts descriptor, starts WINDOW schedule without waited/SUidle or MEgo dependency.',
         'Schedule SEND waits prefetch_ready (source writer IDLE, no block/prime); WAIT waits stage valid with exact absolute row/user.128rows ordered,17sectors each, scale last.',
         'Credit1 FR presents len1/tagsec; grant -> FR_DONE; exact tagsec/beat0 and nonpoison response increments counters. No next sector before prior response. Final sec16 publishes stage and IDLE.',
         'WINDOW/CKV priority mux, KV/RoPE alternating mux, per-PC KARB round robin, timed idx_hbm, then owner demux and WINDOW always-ready return.',
         'After all128rows, schedule ISSUE produces staged_v independently of stream_go; lifecycle STAGE->READY makes kv_ok. Core also needs SUidle and attention unit_ready; MEgo then PC25. stream_go unlocks row merge only afterward.'
       ],transport=dict(WIN_STACK_live=0,WIN_STACK_baseline=2,stack_scope='Baseline routes source STACK2, live default STACK0. Backend per-stack timing parameters identical; start/state differences remain unqualified.',credits=1,retain=0,stream_II1=0,NPC=32,QD=64,RQD=32,REFPB=3,CLK_PS=1000,LENW=4,BEATW=4,source_TAGW=16,backend_TAGW=17,source_tags=list(range(17)),backend_tags='0x10000|sector, WINDOW inner owner00; no epoch field in credit1',epoch512_collision_affects_current=False,sectors=2176,bytes=69632,reads_per_PC=68,addresses=[262144,264319],pc_map='((s>>2)^(s>>7)^(s>>12))&31',row=8,return_deadline_ps='READcolumn+12500CL+1024burst+10000response=23524',timing_origin='Backend own cyc increments each rising edge; now=cyc*1000ps. C++ global CYC includes reset/setup/prime ticks, so origins are distinct. No physicalclock assertion.',competitors='CKV tied0, X_IDX0. RoPE may have prior bank/refresh effects; outstanding queues and actual WINDOW start are unobserved. Four ranks have separate backend instances; do not multiply single-rank latency by4.',queue_credit_reason='WINDOW own traffic at most1 outstanding, cannot fill QD64/RQD32. Other traffic/return gating must be measured before attributing queue stalls.'),
       conditional_expectation=dict(baseline=br['metrics'],baseline_status=br['status'],same_source_pins_verified=True,baseline_scope=br['limits'],sensitivity_elapsed=[123964,125727],sensitivity_live_bound=False,measured_replay_live_deadline=False,hypothetical_same_start12300_ready=136669,no_sector_completion_inferred_from_PC=True),
       watchdog=dict(environment_authority='Parent supplied RT_WATCHDOG=100000, maxcycles400000; no process env attached',condition='cyc-last_move>100000, last_move reset by ANY rank PC change only',last_move_interval=[before['cycle']+1,after['cycle']],trigger_interval=[before['cycle']+100002,after['cycle']+100001],baseline_refill_minus_watchdog=24368,classification='A healthy bounded cold refill exceeds PC-only watchdog; a timeout is FAIL/incomplete, not DUT deadlock proof.'),
       cause_candidates=[dict(name='Expected one-credit serialized cold refill, with premature PC-only watchdog',status='SUPPORTED_SOURCE_AND_SAME_SOURCE_BOUNDED_REPLAY; actual live progress not observed'),dict(name='Prior SU23 nonretirement',status='POSSIBLE_LIVE_BLOCKER; four-vector no-chase fixed-depth op does not itself explain80k healthy execution, needs terminal SUidle/waited'),dict(name='Descriptor/writer/transport fault or blocked response',status='NOT_ESTABLISHED; no causal counter snapshot. Epoch512 alias and omitted LENW fixture defect do not apply to currentcredit1 production wiring.')],
       verdict='SOURCE_BOUND_CAUSE_CANDIDATE_NOT_OBSERVED_LIVE_ROOT_CAUSE',next_evidence='Hubble owner existing progress/terminal only. Terminal unit_busy bit1 +dbg_state waited/SUidle/core_st separates SU wait from admission. st6,unit1,waited1,SUidle1 is admission candidate, not enough to separate kv_ok/windowidle/unit_ready. Existing periodic interface cannot reveal2176event progress; no live attach/overlay/restart/new watcher.',terminal_decoder_layout='dbg_state bits27:24 st,23:21 unit,20:16 idles,14 waited,59:28 fault sticky; unit_busy bit1=SU busy',limits=['No unconditional live deadline','No payload checkpoint reads','No live process access or change','No compile/run','No pve2/pve3 jobs','No fulltoken/hardware/physical visibility qualification'])
    (out/'record.json').write_text(json.dumps(r,indent=2)+'\n');return r
if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--work',type=Path,required=True);ap.add_argument('--images',type=Path,required=True);ap.add_argument('--baseline',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();print(collect(a.work,a.images,a.baseline,a.out)['verdict'])
