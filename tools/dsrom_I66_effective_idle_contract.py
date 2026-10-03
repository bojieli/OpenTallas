#!/usr/bin/env python3
"""Default-off effective-idle candidate and native source edge-name contract.

Pure Python model/source plan: no original RTL edits, hierarchy overrides,
compiler, runtime, new hardware ports or implementation/adoption claim.
"""
import argparse
import hashlib
import json
from pathlib import Path
import dsrom_I66_existing_ready_fences as F
import dsrom_I66_source_interlock as I
import dsrom_I66_consumer_deadline as D

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/dsrom_I66_effective_idle_contract_20261003'


def effective_idle(native_idle,phase_active,qualified_retired,*,enabled=False):
    if type(enabled) is not bool:raise ValueError('exact opt-in boolean required')
    for value in [native_idle,phase_active,qualified_retired]:I.uint(value,1)
    if not enabled:return native_idle
    return native_idle & ((1-phase_active)|qualified_retired)


def minima(edge):
    """F is actual WAIT exit sample, not any idle observation or wall clock.
    Earliest edge relations, never latest/completion times.
    """
    I.uint(edge)
    return dict(previous_WAIT_exit_sample=edge,
                next_QE_core_S_ISSUE_min=edge+1,
                next_registered_ROM_adapter_accept_min=edge+2,
                adjacent_SU_core_S_ISSUE_min=edge+7,
                adjacent_SU_adapter_front_latch_min=edge+8,
                adjacent_SU_vector_accept_min_if_ready=edge+9,
                publication_latest_postNBA_edge=edge-1 if edge else None,
                service_upper_bound=None)


def validate_wait_exit(sample):
    """Normalized proposed callback assertion; does not qualify a journal."""
    for k in ['native_idle','phase_active','qualified_retired','s_go','effective_idle','healthy_reset_epoch']:
        I.uint(sample[k],1)
    if I.uint(sample['adapter_st'],3)!=5 or sample['s_go']!=0 or sample['healthy_reset_epoch']!=1:
        raise ValueError('F requires healthy actual adapter WAIT exit with s_go0')
    if (sample['effective_idle']!=effective_idle(sample['native_idle'],sample['phase_active'],
                                                sample['qualified_retired'],enabled=True) or
            sample['effective_idle']!=1):
        raise ValueError('not a qualified effective-idle exit')
    I.uint(sample['edge'])
    return minima(sample['edge'])


def guard_lifecycle(adapter_st,phase_active,qualified_retired):
    I.uint(adapter_st,3);I.uint(phase_active,1);I.uint(qualified_retired,1)
    if adapter_st==0 and phase_active and not qualified_retired:
        raise ValueError('IDLE with active unretired old phase bypasses idle-only hook')
    return True


def stepped_minimum(issue_stalls=0,decode_stalls=0,vector_stalls=0):
    """Independent old-state/new-state trace of the relevant source registers.

    Starts at F=0 with adapter WAIT and !s_go; all source gates otherwise ready.
    This is a synthetic source-control witness, not an actual simulation run.
    """
    for v in [issue_stalls,decode_stalls,vector_stalls]:I.uint(v)
    core='ISSUE_QE';adapter=5;pc='later_QE';qe_go=su_go=pend=False
    result={};trace=[]
    for edge in range(12+issue_stalls+decode_stalls+vector_stalls):
        ready=(adapter==0)
        trace.append(dict(edge=edge,core=core,adapter_st=adapter,qe_go=int(qe_go),su_go=int(su_go),pend=int(pend)))
        new_adapter=adapter
        if adapter==5 and edge==0:new_adapter=0
        elif adapter==0 and qe_go:
            result.setdefault('registered_ROM_accept',edge);new_adapter=1
        elif adapter in [1,2,3]:new_adapter=adapter+1
        elif adapter==4:new_adapter=5
        new_pend=pend
        if su_go and not pend:
            result.setdefault('SU_front_latch',edge);new_pend=True
        elif pend:
            if vector_stalls:vector_stalls-=1
            else:
                result.setdefault('SU_vector_accept',edge);new_pend=False
        new_qe_go=new_su_go=False;new_core=core
        if core=='ISSUE_QE' and ready:
            if issue_stalls:issue_stalls-=1
            else:
                result.setdefault('QE_core_issue',edge);new_qe_go=True;new_core='GO'
        elif core=='GO':new_core='FETCH';pc='adjacent_SU'
        elif core=='FETCH':new_core='WAIT'
        elif core=='WAIT':new_core='CAP'
        elif core=='CAP':new_core='DEC'
        elif core=='DEC':
            if decode_stalls:decode_stalls-=1
            else:new_core='ISSUE_SU'
        elif core=='ISSUE_SU':
            result.setdefault('SU_core_issue',edge);new_su_go=True;new_core='DONE'
        core,adapter,qe_go,su_go,pend=new_core,new_adapter,new_qe_go,new_su_go,new_pend
        if 'SU_vector_accept' in result:break
    return dict(events=result,source_model_trace=trace,actual_runtime=False)


def model():
    pins=json.loads((OUT/'source_pins.json').read_text())
    for path,expected in pins.items():
        if hashlib.sha256((ROOT/path).read_bytes()).hexdigest()!=expected:raise ValueError('source pin changed: '+path)
    peer=json.loads((OUT/'inputs/composition_model.json').read_text())
    authority=json.loads((OUT/'inputs/authority.json').read_text())
    if hashlib.sha256((OUT/'inputs/composition_model.json').read_bytes()).hexdigest()!=authority['sha256']:
        raise ValueError('peer committed model identity')
    if peer['selected_clock_commit']!=authority['selected_clock_commit']:
        raise ValueError('selected c9 clock mismatch')
    desc={d['pc']:d for d in F.descriptors()};chains=[]
    rom=[pc for pc,d in sorted(desc.items()) if d['unit']==3 and d['decoded_fields']['qe_mode']==0]
    for p in peer['constructive_deadline']['fences']:
        producer,consumer,adjacent=p['producer'],p['consumer'],p['later_GU0']
        if adjacent!=consumer-1 or adjacent not in rom:
            raise ValueError('adjacent QE/SU source range differs')
        if desc[adjacent]['template_word_sha256']!=p['later_template_sha256']:
            raise ValueError('peer later-phase template source differs')
        previous=rom[rom.index(adjacent)-1]
        if not producer<=previous:
            raise ValueError('captured publication not before adjacent ready chain')
        chains.append(dict(producer_pc=producer,consumer_pc=consumer,operand=p['operand'],
                           adjacent_QE_pc=adjacent,F_is_WAIT_exit_of_pc=previous,
                           relative_core_consumer_min='F+7',registered_SU_front_min='F+8',
                           vector_accept_min_if_ready='F+9',owned_visibility='V < F',
                           source_word_evidence='intended source words; actual current enrollment unavailable'))
    if len(chains)!=12 or not F.proof(ready_holds_visibility_credit=True,idle_holds_visibility_credit=True)['all_twelve_visibility_before_read']:
        raise ValueError('all12 constructive source order required')
    floor=peer['constructive_deadline']['hook_allowedcell_floor']
    return dict(scope='MODEL_ONLY_DEFAULT_OFF_EFFECTIVE_IDLE_CONTROL_AND_CALLBACK_PLAN',
        authority=authority,source_pins=pins,chains=chains,
        hook=dict(default=0,expression='native_spine_idle && (!phase_active || qualified_VM_visible_credit_packet_retired)',
                  adapter_sink='dut.u_tile.u_core.g_rom.u_radapt.s_idle',
                  native_source='dut.u_tile.u_core.g_rom.u_spine.idle -> g_rom.s_idle',
                  source_connection_pinned='current core connects .s_idle(s_idle); no change implemented',
                  unchanged_native_s_ready=True,
                  affects=['adapter S_WAIT exit', 'adapter idle combinational output; consequently core qe_idle'],
                  ready_consequence='ready is not directly hooked: adapter remains WAIT until effective idle; next preedge IDLE allows original ready=IDLE&&s_ready.',
                  phase_lifecycle='Latch full old169/user32 owner and active before old WAIT retirement; reset starts inactive only with no old debt. Never clear active/retirement state before previous phase debt is qualified. IDLE with active unretired previous phase is forbidden.',
                  phase_active_scope='Capture W1/W3 only; uncaptured W2 follows native idle. Old published VM ownership records survive rearm and intervening W2 phases.',
                  destination_version_lease='Separate full owner/address lease until actual SU reads and observed R+2 Xtags; does not hold phase_active/bank ready until consumer.'),
        edge_names=dict(F='preedge effective idle1, adapter WAIT, s_go0: old phase can retire',
                        Fplus1='earliest later QE core issue',Fplus2='earliest registered ROM adapter acceptance',
                        Fplus7='earliest adjacent SU core admission; user front bound is conservative for registered latch',
                        Fplus8='earliest SU adapter go&&!pend front latch',
                        Fplus9='earliest v_acc when vector-ready; SU ready alone does not imply vector pipeline idle'),
        relative_relation_only='V < F < later QE admission < actual adjacent SU admission/read; no source service upper bound, no absolute clock/c9 CDC conversion.',
        hardware_reference_floor=floor,
        floor_charge_policy='Reuse peer gross two control bits/cell floor as ONE proposal; no extra addition to c9 or claim existing active bit credit. Full169 comparison/credits/packet/context/control state not included in this floor.',
        physical_routes_required=[
            dict(source='native spine idle',sink='effective-idle combine -> u_radapt.s_idle',physical_pins_route=None),
            dict(source='gather/VM postNBA visibility witness -> owner ledger',sink='qualified retirement register',physical_pins_route=None),
            dict(source='shard0/shard1 positive captured credit return and packet ACKs',sink='same old169/user32 retirement predicate',physical_pins_route=None),
            dict(source='c9 parent streaming clock and qualified reset release',sink='proposed active/retirement control flops',physical_pins_route=None)],
        callbacks_required=[
            'old full169 context + separate shard1; reset epoch; phase_active and qualified retirement pre/post',
            'raw native spine idle, adapter effective s_idle, adapter.st/s_go/s_ready, fault',
            'core.pc/st/d_unit/qe_mode/waited/unit_ready/q_gate/kv_gate/m0_gate/d_skip at source issue and next registered ROM_go',
            'all576 owned VM address/data postNBA; all12 writer families/root suppression; actual credits/packet/source rearm ledger',
            'SU core admission, go&&!pend front latch, v_acc/seq/cp, resolved VM read and observed R+2 context tag',
            'all17 QE admissions including uncaptured W2 and all old VM address/version lease releases'],
        observer_only=dict(new_hardware_ports=0,new_engine_edits=0,compiled_callback=False,
                           implementation='none; passive packet/schema plan only',simulation_cost_measured=False),
        price_and_build_blockers=['named hook/retirement forward and typed hold routes',
            'c9 root phase/reset-release control sink allocation + clock/reset/PG load',
            'full identity/control state reconciliation and retained VM leases (four-frame floor, exact peak unobserved)',
            'positive actual CDC/credit+packet service and qualified retirement provider',
            'source/binary/program/field/17phase callback enrollment with actual service origin/first-last reads'],
        minimum_C=None,stations=None,absolute_deadline=None,current_journal=None,live_job=None,
        build_admitted=False,hardware_admitted=False,additional_SU_guard=False,
        native_wrong_data_or_deadlock_claim=False)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path);p.add_argument('--verify',action='store_true')
    a=p.parse_args();text=json.dumps(model(),indent=2,sort_keys=True)+'\n'
    if a.verify:
        if (OUT/'model.json').read_text()!=text:raise SystemExit('model mismatch')
        print('source-relative hook/edge contract PASS; physical/runtime bounds unqualified')
    elif a.out:a.out.write_text(text)
    else:print(text,end='')
