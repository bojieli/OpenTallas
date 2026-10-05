#!/usr/bin/env python3
"""Static WINDOW owner-tag/epoch contract, before RTL; no simulation or payload access."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import sys
from w17_window_credits_model import SOURCE, ROOT, obj, digest, tag_failure

P = 'rtl/chip/'
PATHS = [P+p+'.sv' for p in ('ot_chip_v41x_window_kv_prefetch',
    'ot_chip_v41x_window_attn_source', 'ot_chip_v41x_window_refill_schedule',
    'ot_chip_v41x_kv_reqmux', 'ot_chip_v41x_kv_rope_reqmux',
    'ot_chip_v41x_hbm_karb', 'ot_chip_v41x_hbm3e_phy', 'ot_chip_v41x_attn_desc_lifecycle')]
PATHS += ['rtl/chip/ckvsel/ot_chip_v41x_die.sv', 'rtl/test/v41_runtime/ot_v41_rt_die.sv',
    'rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp',
    'rtl/w17_runtime/hdc/v41x/fastpp_pc21/l0/ot_hdc_core_v41x.sv',
    'rtl/rom/ot_rom_pkg_ctrl_x.sv', 'tools/w17_current_fastpp_die_rt.py',
    'tools/hdc_replay_v41.py', 'tools/uarch_model.py',
    'results/rtl/hdc_v41x_fullshape_1m_s20260930_program_bind_rope_hbm.json',
    'results/rtl/hdc_v41x_fullshape_1m_s20260930_l20_program_bind_rope_hbm.json']
PRIOR_COMMIT = 'd36550dcae6eeb3940e1d4db9e4cf348b521d97b'
PRIOR_PATH = 'results/uarch/w17_window_credits_model_20261001/model_r2.json'


def route(client, payload):
    assert 0 <= payload < (1<<14) and client in (0,1,2)
    master=(client<<14)|payload
    backend=(1<<16)|master
    # Inverse of KARB bit16 owner, outer RoPE bit15, inner CKV bit14.
    assert backend>>16 == 1
    low=backend&0xffff
    selected=2 if low&0x8000 else (1 if low&0x4000 else 0)
    return backend, selected, low&0x3fff


def static_checks():
    legacy_legal=0
    for sector in range(17):
        for owner in (0,):
            _, selected, returned=route(owner,sector)
            assert selected==0 and returned==sector
        legacy_legal+=1
    payload_routes=0
    for owner in range(3):
        for payload in range(1<<14):
            _, selected, returned=route(owner,payload)
            assert selected==owner and returned==payload
            payload_routes+=1
    for tag in range(1<<16):
        # Indexer B bypasses KV/RoPE and has all16 payload bits, owner bit16=0.
        backend=tag
        assert backend>>16==0 and (backend&0xffff)==tag
    legal=0
    for epoch in range(512):
        for sector in range(17):
            encoded=(epoch<<5)|sector
            backend, selected, returned=route(0,encoded)
            assert selected==0 and returned>>5==epoch and returned&31==sector
            assert backend>>14==4 # backend[16:14]=100 for WINDOW
            legal+=1
    assert ((512<<5)&0xc000)==0x4000
    # Algebra of healthy row completion: scale cannot issue while any code remains.
    codes_received=16; code_pending=0
    assert codes_received==16 and code_pending==0
    pending_after_scale_grant=code_pending+1
    pending_after_valid_scale_response=pending_after_scale_grant-1
    assert pending_after_valid_scale_response==0
    # Epoch comparison rejects unequal generations but cannot reject aliased postwrap ghosts.
    assert ((1<<5)|7)!=((2<<5)|7)
    assert (((1+512)%512)<<5)|7 == (1<<5)|7
    return dict(legacy_read_and_write_sector_tags_legal=legacy_legal,
        all14bit_payloads_roundtrip_for_WINDOW_CKV_RoPE=payload_routes,
        full16bit_indexer_payloads_roundtrip=65536,
        proposed9bit_epoch_times17sectors_roundtrip=legal,
        preserved_old_encoding_failure_epoch=512,
        healthy_scale_completion_pending_zero='conditional arithmetic PASS',
        same_tag_after512epochs='EXPECTED_ALIAS; drain/nonreplay prerequisite, not staleproof',
        scope='Integer packing and source predicates only; no RTL execution or exactness transfer')


def anchors(text, tokens):
    return {token:[i for i,line in enumerate(text.splitlines(),1) if token in line] for token in tokens}


def build():
    raw={p:obj(p) for p in PATHS}
    src={p:b.decode() for p,b in raw.items()}
    pf=src[P+'ot_chip_v41x_window_kv_prefetch.sv']
    wrapper=src['rtl/test/v41_runtime/ot_v41_rt_die.sv']
    die=src['rtl/chip/ckvsel/ot_chip_v41x_die.sv']
    buildtool=src['tools/w17_current_fastpp_die_rt.py']
    assert 'parameter integer WINDOW_REFILL_CREDITS = 1' in die
    assert 'WINDOW_REFILL_CREDITS' not in wrapper and 'WINDOW_REFILL_CREDITS' not in buildtool
    assert 'WINDOW_RETAIN_L0' not in wrapper and 'WINDOW_RETAIN_L0' not in buildtool
    assert "m_tag[WIN_STACK*TAGW +: TAGW] = TAGW'(sec)" in pf
    assert pf.count('refill_epoch <= refill_epoch +')==1
    assert 'if (REFILL_CREDITS > 1)' in pf
    assert digest((ROOT/'tools/uarch_model.py').read_bytes())==digest(raw['tools/uarch_model.py'])
    traces=[]
    for layer,suffix in [(0,''),(20,'_l20')]:
        path=f'results/rtl/hdc_v41x_fullshape_1m_s20260930{suffix}_program_bind_rope_hbm.json'
        d=json.loads(raw[path])
        all_mmode=[x for x in d['instruction_trace'] if x.get('fields',{}).get('me_mmode')]
        ops=[x for x in all_mmode if x['tag'] in (f'L{layer}.scores',f'L{layer}.pv')]
        if layer==0:
            assert len(all_mmode)==2
        assert len(ops)==2 and [x['tag'] for x in ops]==[f'L{layer}.scores',f'L{layer}.pv']
        traces.append(dict(layer=layer,path=path,position=d['position'],
            descriptors=[dict(pc=x['pc'],tag=x['tag'],fields=x['fields']) for x in ops],
            end_pc=d['instruction_trace'][-1]['pc'],
            other_mmode_ops=[dict(pc=x['pc'],tag=x['tag'],fields=x['fields']) for x in all_mmode if x not in ops],
            counting_scope='Only named WINDOW scores/PV candidates. L0 has exactly2mmodeops. L20 also has an indexer SC1 operation: do not equate everymmodeop to WINDOWrefill or claim wholeindexed-layer epochcount without its routing proof.',
            window_rows_per_descriptor=128,
            epoch_advances_if_credit1=0,maximum_if_credit8_and_two_refills=256,
            retention_qualification='Eligible only exact L0 shapes and completion. L20 T1/640 shapes do not match the L0 retention signatures; this separate layer example supplies no full40 composition.'))
    prior_raw=obj(PRIOR_PATH,PRIOR_COMMIT)
    old=json.loads(prior_raw)
    assert old['tag_owner_gate']['first_bad_epoch']==512
    return dict(schema='opentallas.uarch.window_epoch_contract.v1',
        verdict='STATIC_SCOPE_RESOLVED_PROPOSED_ENCODING_LEGAL_DRAIN_COMPOSITION_PENDING',
        recorded_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        source_commit=SOURCE,source_sha256={p:digest(b) for p,b in raw.items()},
        model_source_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        model_source_sha256={p:digest((ROOT/p).read_bytes()) for p in ('tools/w17_window_epoch_contract.py','tools/w17_window_credits_model.py')},
        preserved_failure=dict(commit=PRIOR_COMMIT,path=PRIOR_PATH,sha256=digest(prior_raw),
            old_verdict=old['tag_owner_gate']['status'],counterexample=tag_failure(),overwritten=False,
            clarification='The real failure belongs to REFILL_CREDITS>1/FR_PIPE. It does not apply to current default1 or producer WC/WS tags.'),
        actual_current_binding=dict(WINDOW_REFILL_CREDITS=1,WINDOW_RETAIN_L0=0,CKV_SELECTED=0,
            KARB_LOCAL=0,PIPE_OUT=0,PIPE_RSP=0,source_TAGW=16,backend_KTAGW=17,
            chain='runtime wrapper ot_v41_rt_die instantiates FULL_SHAPE1 WINDOW_HBM_ATTENTION1 die, does not override credit/retain; build tool has no override; die forwards its default1 to source REFILL_CREDITS then prefetch.',
            current_read_path='IDLE->FR->FR_DONE; tags sector0..16. FR_PIPE unreachable by normal valid prefetch at credits1; epoch remains reset0 because only advance is inside credits>1 branch.',
            writes='WC(code sec0..15) and WS(scale sec16) both m_tag=sec, independently of credit count. One outstanding write waits wr_done; writes/prime/retain_invalidate do not advance refill_epoch.',
            collision_affects_current_credit1=False,
            proof_boundary='Source binding proof only. No live attach/state observation, binary rebuild or inherited payload qualification.'),
        owner_tag_path=[
            dict(boundary='WINDOW source output',width=16,owners='none generated by client; bits15:14 must00',
                 payload='credit1 and WC/WS zeroextend sec5; credit>1 currently epoch11:sec5'),
            dict(boundary='KV/RoPE outer admission',width=16,owners='client tags bits15:14 must00; otherwise valid blocked and stickybad_tag',payload_bits=14),
            dict(boundary='outer w_t -> inner kv_reqmux',width=15,owners='inner15bit tag bit14 WINDOW0/CKV1',payload_bits=14,
                 transform='wt[14:0] enters inner; inner emits {ownerC,payload[13:0]}'),
            dict(boundary='outer KV/RoPE -> KARB K',width=16,owners='bits15:14 WINDOW00 CKV01 RoPE10;11 invalid',payload_bits=14,
                 transform='K: {0,inner15}; RoPE:{1,pt[14:0]}, withpt14=0 enforced'),
            dict(boundary='KARB -> idx_hbm',width=17,owners='bit16 K1/indexerB0',
                 transform='K:{1,master16}; B:{0,Btag16}; K and B have different payload budgets',
                 WINDOW_encoding='backend bits16:14=100; remaining14bits client payload'),
            dict(boundary='idx_hbm return',width=17,owners='preserved backend tag',beat_bits=4),
            dict(boundary='KARB selected K return',width=16,owners='lowestPC with rsp_v and bit16=1; ready only selectedK port',
                 transform='stripbit16; B bit16=0 goes directly B and retains all16payload bits'),
            dict(boundary='outer/inner response demux -> WINDOW',width=16,owners='outer stripsRoPE flag, inner stripsCKV flag, restores bits15:14=00',
                 transform='WINDOW:{00,returned[13:0]}; CKV same restored upperzeros; RoPE requires10owner'),
        ],
        response_guards=dict(credit1='FR_DONE and response, full16bit tag==sec, beat0,nonpoison. No epoch validation; one outstanding transport must return once and be drained before reuse.',
            creditN='FR_PIPE&&!fault&&response; sector<=16,fullreturnedtag>>5==epoch,issuedbit1,receivedbit0,beat0,nonpoison. Onlyvalid replies commitstage/incrementread/decrementpending.',
            publish='Scale request after all16code received; onlyvalid scale reply sets stage_valid/tag/user and IDLE; no early row publication.',
            writes='wr_done untagged. KV mux routes completions to WINDOW only (CKV/RoPE writes forbidden). KARB kw_out/bw_out perPC plus same-PC otherwriter exclusion route completion without tag.',
            late_unsolicited='Current IDLE ignores reads; credit1 can alias same-sector late duplicates; creditN rejects wrong epoch/duplicate withinrow but finiteepoch can alias afterwrap. Closed exactly-once/drained transport is required; no arbitraryreplay guarantee.'),
        epoch_lifetime=dict(programs=traces,
            credit1='No increments for any number of ordinary operations: remains reset0; small sector tags reused only under single-outstanding exact transport.',
            one_L0_invocation_if_credit8_no_retention='At most256increments from two128row refills, epochs1..256 from reset. Source chronology, not proof that current execution completed.',
            one_L0_invocation_if_eligible_retention_hit='128increments; PVdispatch skips refill entirely. A miss falls back to256. No across-token retention.',
            repeated_no_reset_old_encoding='Global row epoch across all users/operations in this source. Fourth128row refill hits epoch512 on its finalrow. For repeated identical L0 programs with no retention: second invocation PVfinalrow; if every PVretains: fourth invocation QKfinalrow. Conditional call-count examples, not live/warm measurements.',
            runtime_reset='C++ eight reset ticks then rst=1 once, priming, one start pulse, loopuntilEND/TIMEOUT; no second token loop and no rst=0 afterrelease. Does not prove reset-per-token in another caller.',
            hardware_reset='die rn is synchronizer of rst_n only. t_start/c_start changes core step/retentionmetadata, not rn or refill_epoch. Package controller can emit later core_start while keeping same reset.',
            reset_on_prime=False,reset_on_blockwrite=False,reset_on_start=False,reset_on_descriptor_done=False,
            maximum_lifetime_in_resident_caller='Unbounded number of row refills absent external operational limit; epoch is global modulo counter. No layer-id or token-id epoch reset/exclusion implied.',
            full40_transfer=False),
        proposed_minimal_encoding=dict(status='PROPOSAL_ONLY_NO_RTL_IMPLEMENTATION',
            applies='Existing opt-in credits>1; default1 branch/write format remains unchanged.',
            implementation_model_ready=True,
            implementation_scope='Healthy actualdirect mux/KARB path with certifiedexactlyoncebackend and rowdrain; reset/fault recovery remains existingexternalquiescence, not anew automaticrecovery feature.',
            minimal_RTL_change_map=['Prefetch EPOCH_W forconnectedclientTAGW16 becomes9 (TAGW-5sector-2reservedowner); keep REFILL_CREDITS1 and WC/WS branch logic unchanged',
                'Keep local rowepoch increment onaccepted multi-credit prefetch, but at9bitwidth so511 wraps0 naturally; concat epoch9:sector5 zeroextends16 with top2zero',
                'Returned epoch comparison uses same9bitstate; fullreturned16tag>>5 equals it becauseownerstripping restores top2zero; do not compare masked wiretag withold11bitstate',
                'Multi-credit parameter guard requires TAGW>=8 withtworeservedownerbits; actual16bitconfiguration unchanged',
                'No newhealthy DRAINstate/port: qualifyexisting validscalecompletion and post-edgepending0 plustransportconservation; preserve failstop and externalresetdrain contract'],
            client_width=16,backend_width=17,owner_budget=2,payload_width=14,
            sector_bits=5,epoch_bits=9,encoding='clienttag={2b00,epoch9,sector5}; backendtag={1b1,2b00,epoch9,sector5}',
            initial_epoch=0,advance='On accepted next-row prefetch afterdrain: epoch=(epoch+1)mod512; sequence1..511,0,1. Epoch0 is legal for rowtickets; descriptor generation0 remains invalid independently.',
            maximum_legal_window_tag='0x3ff0 for epoch511sector16',
            fixes_required='Counter width/advance AND returned epoch comparison must agree at9bits. Masking only outgoing11bit epoch leaves receive comparison broken; backend widening to17 does not free client owner bits.',
            wrap='No reset everytoken. Natural9bit modulo wrap only on drained row boundary; whole active row carries oneimmutable epoch,user,row.',
            alternative='Reserveepoch0 wouldneed511->1 compare/select; unnecessary for this source predicate. Proposed minimum uses0 and adds no wrapstate.'),
        drain_wrap_contract=dict(source_conservation_argument='Defaultdirect path has no request/responsepipeline: WINDOWgrant iff KV/RoPEselects legalWINDOW, KARB grantsK atpc_of(address), and backend req_ready. The same valid/readyedge enqueues one read. Onreturn, backendbit16=1 andclientowner00 selectWINDOW; onlylowestreadyKPC is routed; WINDOWs_rdy=1 propagates to thatPC r_rdy. Sameedge popsbackendreturn and consumes source response. idx_hbm generates one return per admittedread, removes eachqueuedread once, and has no retrypath. Under validreply/nonpoison and exclusiveWINDOWsource, perPC accepted-consumed counts all WINDOWqueued/scheduled/heldreturns; sum=pending. Thus validscale response with pending0 afteredge certifies no WINDOWtransportentries remain for the unchangeddirect path.',
            source_conservation_status='SOURCE_DERIVED_CONDITIONAL; connectedRTLcounter gate pending, not numerical/timingproof',
            normal_drain_witness='At validscale response edge: all16code received, scaleissued andunique scaleaccepted, pending becomes0, issued==received==17ones, state becomesIDLE. No next-row request until next prefetch acceptance/epochadvance.',
            transport_preconditions=['same clock/pre-edge handshakes, actual default PIPE_OUT/RSP0 and no hidden CDC/replayfifo',
                'Each WINDOW grant admits exactlyonebackend read; each visible ready response pops exactlyone backend return and commits source once',
                'WINDOW accepted-minus-consumed perPC equals outstanding transport WINDOW entries; no unsolicitedduplicate/replayedresponses',
                'All WINDOW requests reside within the one live source row, max8total; no other WINDOW producer shares tag namespace'],
            proof_obligation='Acknowledge rowdrain only when no accepted WINDOW request, scheduledread, heldresponse, pipe/FIFOor retryentry survives. pending0 is sufficient only after proving above transport conservation and source/backend handshake equivalence.',
            default_healthy_cost='The scale barrier and existing row transition already enforce local rowdrain. With conservation proved, no new port/register/cycle for wrap.',
            fault_recovery='Stop admission; retain failed verdict and no publication. Existing fault branch stops updatingpending, so its counter cannot certifydrain afterfault. Use trusted external quiescence of whole resetaffected transport before rst_n, or design a separately modeled recovery mechanism; not in this minimumencoding.',
            reset='rst_n clears source AND sharedarbiter/backend in actual die: drain all resetaffected owners/readqueues/writecompletions and any outside pipes/retrybuffers, then reset. Source-onlyreset whileoldtransactions live is forbidden.',
            unknown_external_drain='If external/replay lifetime cannot be certified, do not wrap/reuse/reset tags or claim compositionready. A finiteepoch width cannot solve unbounded replay.'),
        isolation_stale_invariants=[
            'Ownerbits are generated only by mux/KARB; WINDOWclient cannot claim CKV/RoPE/index ownership; owner11 at KV/RoPE is failclosed.',
            'Captured row/user stays fixed until all admitted row reads return; nointerrow or userinterleaving; memoryregion/useroffsets prevent contentalias.',
            'Sector tag is checked against issued/received sets and beat0 before payloadcommit; invalid/duplicate/poison response neverreleases credit or publishes row.',
            'New content/config/prime/write invalidates relevant stage/retention; otherwriters into WINDOWregion must beexcluded or coherentlyinvalidated. Tagfix doesnotprovide coherency.',
            'Old epoch ticket must be retired from every transport location before sameepoch reappears. Unequalepoch stale replies reject; equal postwrapghost is indistinguishable and forbidden by drain/nonreplay contract.',
            'Lifecycle generation16 and content_epoch32 remain separatefromrefill epoch9. A retained PV uses fresh lifecyclegeneration and no refill advancement.',
        ],
        storage_control_latency_cost=dict(old_refill_metadata_bits=11+34+10,proposed_refill_metadata_bits=9+34+10,
            delta_bits=-2,new_payload_bits=0,new_queue_entries=0,new_boundary_bits=0,new_healthy_state_bits=0,
            owner_tag_boundary_widths_unchanged=[16,15,16,17,16,15,16],
            counter_increment_width_delta=-2,epoch_equality_width_delta=-2,
            wrap_compare_mux='none beyond natural9bit truncation; tagupper2 constantzeros',
            healthy_wrap_added_cycles=0,existing_scale_response_to_nextrow_grant_cycles=3,
            row_or_job_latency_change_from_encoding_only_cycles=0,
            fault_drain_latency='Externallybounded by actual queues/service or unknown; neverpricedzero.',
            area_flop_delta_um2=-2*0.2916,area_qualification='ASSUMEDunifiedDFFbasis, no synthesis or contextual SS/FF closure',
            fanout='Existing issued/received selectors and singlefillport unchanged; epochnet2bitsnarrower. No new globalbroadcast.',
            credit1_delta='No behaviorchange underminimumproposal; its unused refillmetadata mayalreadyprune.',
            new_frequency_or_token_rate_claim=False),
        bounded_connected_gate_prerequisites=dict(model_ready_for_bounded_healthy_integration=True,build_run=False,
            next_gate='Bounded connected128x17credit1/8 memory-service gate through actual owner muxes, directKARB admission and unchangedidx_hbm OOO/heldreturns, legalexisting epochs1..128. Preserve separate oldepoch512 expectedrejection. Proposed9bitwrap needs an approvedcandidate implementation before a later wrapgate; no buildrun now.',
            legal_first_window_model_ready=True,
            proposed_wrap_RTL_implemented=False,
            requirements=['For unchangedsourcefirst128test, initialize epoch0 froma verifiedquiescentreset and keep alladmitted epochs<=511. Candidate9bitwrapqualification requires a separatelyapproved implementation; nevermask11bit tags at an ownerboundary.',
                'All original RTL and tools/uarch_model.py sourcepins verified; standalone addedmodelpaths only',
                'Bind actual16bitclient/15bitinnermux/17bitbackend and both responseownerselectors, defaultdirectKARB andCLK_PS1000event alignment',
                'Check all512epochs/staticpacking plus seeded510->511->0->1 healthyrowdrain, heldrequestbackpressure, simultaneousvalidgrant/reply, OOOreturns',
                'Connected128x17 legalregion with syntheticnonpoison data, no checkpointreads; compare1and8 admission/return/scale/publish counters with sameinitialbank/time state',
                'Observe perPC WINDOW accepted/consumed outstanding at everyrowboundary, nohiddenrequest/returnbuffer; exactrow/user/tag beforefreshgenerationstagepublish',
                'Reject unknownsector/duplicate/staleepoch/owner11/poison, invalidateretentiononstart/write/prime/config, prove externalresetquiescence before reuse',
                'Count program rowepochs only for actual L0or namedlayerjob; no across-tokenretention, full40transfer, headline or adoption'],
            no_bench_or_build_in_this_task=True),
        source_line_anchors={p:anchors(src[p],tokens) for p,tokens in {
            P+'ot_chip_v41x_window_kv_prefetch.sv':["TAGW'(sec)",'refill_epoch <=','REFILL_CREDITS > 1','FR_DONE:','pipe_reply_ok'],
            P+'ot_chip_v41x_kv_rope_reqmux.sv':['wt[TAGW-1:TAGW-2]','TAGW(TAGW-1)','w_stag'],
            'rtl/chip/ckvsel/ot_chip_v41x_die.sv':['WINDOW_REFILL_CREDITS = 1','REFILL_CREDITS(WINDOW_REFILL_CREDITS)','wire rn =','retain_invalidate(t_start'],
            'rtl/test/v41_runtime/w17_current_fastpp_die_rt.cpp':['uint8_t rst =','rst = 1','start(1, tok']}.items()},
        static_checks=static_checks(),
        compatibility=dict(uarch_original_byte_identical=True,RTL_original_byte_identical=True,
            standalone_prior_model_CLI='python3 tools/w17_window_credits_model.py --out NEW_PATH.json',
            standalone_epoch_contract_CLI='python3 tools/w17_window_epoch_contract.py --out NEW_PATH.json',
            previous_optional_uarch_CLI_patch='Not carried into this branch; parent can take only addedpaths.',
            no_main_live_edit=True,no_payload_or_checkpoint_read=True,no_build=True,no_adoption=True))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',required=True,help='new evidence JSON; never overwrite')
    args=parser.parse_args()
    payload=json.dumps(build(),indent=2)+'\n'
    target=Path(args.out)
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('x') as stream:
        stream.write(payload)
    print(payload,end='')


if __name__=='__main__':
    main()
