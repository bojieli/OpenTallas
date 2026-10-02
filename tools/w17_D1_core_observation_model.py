"""Source-only next real-core admission probe model. No compiler/runtime entry."""
import hashlib,json
from pathlib import Path
import hdc_isa_v41 as isa
ROOT=Path(__file__).resolve().parents[1]
REC=ROOT/'results/uarch/w17_D1_core_observation_model_20261002'
PIN='4e38326d6f361bc85e660f48c59c355e2bb95274'
ASSUMPTIONS={'same_reset_origin','start_12300','exclusive_backend','credit1','primed128','no_writes_or_competitors','NPC32_REFPB3_CLK1000','same_memory_and_source_binding'}
class BoundMissing(ValueError):pass

def service_reference(assumptions):
    if set(assumptions)!=ASSUMPTIONS or any(type(v) is not bool or not v for v in assumptions.values()):
        raise BoundMissing('BOUND_MISSING: cold isolated calendar assumptions not established')
    r=json.loads((ROOT/'results/uarch/w17_D1_PC24_inputs_20261002/record.json').read_text())
    c=r['calendar']['metrics'];lat=r['request_to_reply_cycles']
    return dict(descriptor_accept=12300,first_request=12302,first_reply=12355,last_reply=r['calendar']['last_scale_response'],staged=c['staged'],stream_done=c['done'],refill=c['refill'],requests=c['reads'],replies=c['replies'],request_reply_min=lat['min'],request_reply_max=lat['max'],descriptor_to_stage=c['staged']-c['start'],descriptor_to_stream_done=c['done']-c['start'],universal_deadline=False,actual_core_issue_deadline=None,actual_original_run=False)

def validate_admission_edge(pre,post):
    keys={'me_ready','kv_ok','kvd_v','win_idle','waited','q_gate','m0_gate','fault'}
    if set(pre)!=keys|{'state','unit','class'} or set(post)!={'me_go'}:raise ValueError('paired edge schema')
    if any(type(pre[k]) is not bool for k in keys) or type(post['me_go']) is not bool:raise ValueError('strict bit types')
    if any(type(pre[k]) is not int for k in ('state','unit','class')):raise ValueError('context type')
    if (pre['state'],pre['unit'],pre['class'])!=(6,1,1):raise ValueError('not target S_ISSUE attention ME')
    # Fault is a validation failure before any alleged completion/progress credit.
    if pre['fault']:raise ValueError('faulted edge, no admission qualification')
    expected=pre['waited'] and pre['q_gate'] and pre['m0_gate'] and pre['me_ready'] and pre['kv_ok'] and not pre['kvd_v'] and pre['win_idle']
    if post['me_go']!=expected:raise ValueError('registered issue does not match pre-NBA predicates')
    return dict(qualified_admission=expected,provider_completion=False,service_progress=False)

def strict_encode(fields):
    for key,value in fields.items():
        if key not in isa.FULL_LAYOUT:raise ValueError('unknown instruction field')
        width=isa.FULL_LAYOUT[key][1]
        if type(value) is not int or not 0<=value<1<<width:raise ValueError('instruction envelope')
    return isa.encode(full_shape=True,**fields)

def build():
    model=json.loads((ROOT/'results/uarch/w17_D1_portable_successor_20261002/prerequisite_manifest.json').read_text())
    authority=model['test_git_authority'];sources={}
    for origin in ['rtl/hdc/v41x/ot_hdc_core_v41x.sv','rtl/chip/ot_chip_v41x_die.sv','rtl/test/v41_runtime/ot_v41_rt_die.sv']:
        p=ROOT/authority[PIN+':'+origin];data=p.read_bytes();row=model['files'][str(p.relative_to(ROOT))]
        if hashlib.sha256(data).hexdigest()!=row['sha256']:raise ValueError('original source authority drift')
        sources[origin]=dict(path=str(p.relative_to(ROOT)),sha256=row['sha256'])
    core=(ROOT/sources['rtl/hdc/v41x/ot_hdc_core_v41x.sv']['path']).read_text()
    for text in ['(kv_ok && !kvd_v)','(!FULL_SHAPE || win_idle)','assign me_ready = e_ready[me_eng]','S_DEC: if (!FULL_SHAPE || win_idle','else if (waited && unit_ready && q_gate && kv_gate && m0_gate']:
        if text not in core:raise ValueError('source predicate changed')
    for p in [ROOT/'tools/hdc_isa_v41.py',ROOT/'results/uarch/w17_D1_PC24_inputs_20261002/record.json',ROOT/'results/uarch/w17_owner_progress_resource_r2_20261002/model.json']:
        sources[str(p.relative_to(ROOT))]=dict(path=str(p.relative_to(ROOT)),sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    fields=dict(unit=1,wait=2,pred=0,me_nout=128,me_tiles=4,me_k=512,me_wsrc=1,me_wbase=0,me_ts=512,me_ks=1,me_js=0,me_xbase=0,me_xks=1,me_xjs=512,me_xcs=4096,me_hg=1,me_round=1,me_mmode=1,me_oen=1,me_obase=1024,me_ots=16,me_ojs=128,me_ogs=1024)
    # A controlled single attention instruction, followed by drained END; not original program/payload.
    words=[strict_encode(fields),strict_encode(dict(unit=0,wait=31,ctl=0))]
    reference=service_reference({k:True for k in ASSUMPTIONS})
    return dict(status='SOURCE_MODEL_PROGRAM_PREPARED_NO_BUILD_NO_GO',source_pin=PIN,source_pins=sources,parent_owned_current_callback_job='w17-D1-callback-fixture-parent-20261002-r1; terminalFAIL: compile413.632s PASS, firstHEALTHY20s cap with empty event log; no restart and no qualification transfer',program=dict(words_hex=[format(w,'0512x') for w in words],fields=[fields,dict(unit=0,wait=31,ctl=0)],original_program=False,entry=0,token=0,pos=127,user=0,cfg_ik_base=268435456,first_ME_class='MC_A=1; wsrc1 and wbase0<cfg_ik_base',no_instruction_force=True,no_original_PC24_relabel=True,operand_source='Explicit finite synthetic VM/source diagnostic data only; no golden/checkpoint payload',scope='Stop diagnostic after first qualified real-core ME issue; END is future engine drain only, no completion bound claimed'),
      real_binding=dict(core='original ot_hdc_core_v41x, no cancellation derivative',FULL_SHAPE=1,KV_HBM=1,X_SU=1,SUN=256,SUM=64,NSLOT=1,X_ROM=1,X_ME=0,X_ATT=1,X_IDX=0,X_SEL=0,X_EG=0,W_HBM=0,AW=30,NW=21,INSTR_BITS=2048,descriptor='original ot_chip_v41x_attn_desc_lifecycle L0_ONLY1',source='original WINDOW_HBM_ATTENTION service128rows credit1 banked stage; real mux/KARB/timed backend',geometry_shrink=False,ready_fabrication=False,port_ready_idle_owner='real attention adapter state and real engine-slot idle vectors; no forced e_ready/e_idle',selected_attention_engine='V41_ATT_CUT runtime adapter plus exact actual native attention endpoint OR full actual engine; choice/closure/price must be frozen before GO, no stub',unavailable_ckv=True),
      sample_protocol=dict(pre_NBA=['state','unit','me_cls','waited','q_gate','m0_gate','me_ready','kv_ok','kvd_v','win_idle','fault','descriptor_accept','descriptor_gen','source grant identity','read return tag/beat/poison','selected writer_ACK pending identity'],post_NBA=['registered me_go','st','pc','source publication','sticky fault'],decode_gate='win_idle can block S_DEC before kvd_v is announced; decode gate must be sampled as well as S_ISSUE',progress='Only actual owned descriptor accept, selected request/qualified callback/publication; never PC/busy/static ready or predicted time'),
      reference=reference,calendar_alignment=dict(proposed_core_start_pre_NBA=12294,NSLOT=1,source_schedule=['12294 START accepted -> S_DYN','12295 DYN -> FETCH','12296 FETCH -> WAIT','12297 WAIT -> CAP','12298 CAP -> DEC','12299 DEC and idle writer -> ISSUE; kvd_v registers high','12300 real descriptor/source accept if actual owner prerequisites hold'],not_measured=True,core_start_to_source_accept_bound=None,warning='Source phase expectation only; assert descriptor/source accepts at12300 before enabling cold-calendar envelope. No epoch/reset/timestamp force.'),
      cases=[dict(name='COLD_REAL_CORE',expected='kv_ok blocks issue until real staged descriptor; kvd_v pulse cannot grant stale readiness'),dict(name='WRITER_PENDING',expected='real producer capture/drain holds win_idle; observe S_DEC and fourbits; preserve32actualACKs, warm backend calendar BOUND_MISSING'),dict(name='HOLD_REQUEST',expected='real source offer has no accepted read; no progress credit'),dict(name='HOLD_RETURN',expected='one accepted read with no qualified return; outstanding remains pending'),dict(name='ENGINE_NOT_READY',expected='real adapter busy transaction, me_ready false; no forced ready, exact earlier engine owner program still required')],
      resources=dict(inherit_12GiB_GO=False,fixture_reference_only='128source leaf and old full-SUN profile5,686,992,896-byte aggregate frontend; old selected cone not proof of actual X_ATT1 closure',full_parent_reference_only='Prior full L0 lint31.88GiB peak is full-parent context, not this core-only measurement',price_status='SOURCE_CLOSURE_AND_REAL_ATTENTION_ENDPOINT_BINDING_REQUIRED_BEFORE_COMPILER_GO',cost='No ROM field models/whole-L0 images/payloads; actual full-SUN core and original primitives retained; no stubs/pruned ancestors',new_jobs=0),
      missing_bounds=['Actual owner descriptor accept to first read under runtime reset/start and arbitration','Warm WRITER->read bank/refresh/queue calendar with other requesters','Attention adapter loading/engine-ready/service/retirement bound for accepted ME','Real provider/PHY completion/cancel ownership; callback alone insufficient'],service_status='BOUND_MISSING',actual_original_cause='UNOBSERVED',hardware_qualification=False,compiler_invocations=0,simulations=0,fresh_GO_required=True)
if __name__=='__main__':print(json.dumps(build(),indent=2))
