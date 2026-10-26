#!/usr/bin/env python3
"""Resolve only source-determined native boot fields; retain missing bookings.

This provider does not choose a launch phase, MU calendar, KIT or END. It consumes
current selected-source timing plus an optional actual execution booking.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/die_plan'))
import bind_elab as E

OUTER='physical/die_plan/s81/bind/source_modules/portfix178/dsdv_hostb_seqhost_mux.sv'
MUWIN='rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hwin.sv'
MUSLOT='rtl/dsrom_sys/s81_dv/unit/dsdv_mu_hslot.sv'
SEQ='rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host.sv'
WALK='rtl/dsrom_sys/s81_dv/unit/ot_dsdv_walk_issue.sv'


def resolve(program, timing, source_root, execution=None):
    root=Path(source_root)
    if timing.get('schema')!='opentallas.s81.bound_control_local.v1' or timing.get('verdict')!='PASS':
        raise ValueError('selected source-qualified local timing required')
    if timing['masters']['dsdv_hostb_seqhost_mux']['source_path']!=OUTER:
        raise ValueError('different selected outer master needs a new stage-chain proof')
    hashes={}
    for path in (OUTER,MUWIN,MUSLOT,SEQ,WALK):
        hashes[path]=hashlib.sha256((root/path).read_bytes()).hexdigest()
        if hashes[path]!=timing['source_sha256'].get(path):
            raise ValueError('selected native header-chain source differs: '+path)
    def require(path,master,fragment):
        body=re.sub(r'\s+','',E.module_body(root/path,master))
        if fragment not in body:
            raise ValueError('actual stage/phase chain changed: '+master+' '+fragment)
    require(OUTER,'dsdv_hostb_seqhost_mux','dsdv_seq_host_muxu_seqhost(')
    require(MUWIN,'dsdv_seq_host_mux','dsdv_seq_host_mu#(.NSLOT(47),.SELR(SELR))u(')
    require(MUSLOT,'dsdv_seq_host_mu','parameterintegerSTAGE=0')
    require(MUSLOT,'dsdv_seq_host_mu','dsdv_seq_host#(.V(V),.STAGE(STAGE),.MUT(MUT),.SELR(SELR))u_u(')
    require(SEQ,'dsdv_seq_host','dsdv_sh_sq#(.V(V),.STAGE(STAGE),.MUT(MUT))u_l1(')
    require(SEQ,'dsdv_sh_sq',"ot_dsdv_walk_issue#(.NOPS(128),.NENG(NE),.STAGE(STAGE),.ENG_PRESENT(5'b10111))u_iss(")
    require(WALK,'ot_dsdv_walk_issue',"pw_d[6:0]!=7'(STAGE)")
    require(WALK,'ot_dsdv_walk_issue',"((phase_q+2'd1)!=start_phase_q)")
    result=dict(schema='opentallas.s81.bound_boot_contract.v1',status='PARTIAL',
        die_sha256=program['die_sha256'],stage=0,start_phase=None,source_sha256=hashes,
        stage_basis='selected mux omits STAGE override; exact mu wrapper declaration STAGE0 propagates through seq_host/sh_sq into walker',
        begin_permitted=False,seal_permitted=False,
        phase=dict(header_field='PWheader[8:7]',accept_equation='(issuer phase_q + 1) modulo4 == header start_phase',
            ks_descriptor='start,user10,token21,position21; no phase field',
            measured=timing.get('seqhost_input_clock'),
            holds=['actual KS pin events and actual reset release in the same local clock required',
                   'only start_phase0 has the supplied local injection proof; no arbitrary alternate phase adopted']),
        mu=dict(slot_count_limit=47,event_count=8,endpoint_order=['7n','7s','0n','0s'],
            gap_rule='actual consecutive KS pin-event differences; table cycles, never calendar command count',
            slot_count_rule='one gap word uses47slots; two or more gap words use exactly table length slots',
            rl_rule='KIT issue + measured f_ks_pin_event_plus_kit_issue_to_t_kd - 1',
            constraints=['min gap > used slots+1','RL > used slots','RL <= sum(expanded slot gaps)',
                'each event delay is in [used slots+2, RL-2]',
                'all8event rows have explicit kind/endpoint/delay and all used slots have explicit land/ab',
                'endpoint events must not collide over the periodic actual start calendar',
                'actual KS user must not be duplicated while its prior start remains outstanding',
                'configuration occurs while tracker unarmed with no outstanding starts'],
            missing=['actual KS start calendar','actual KIT issue and static END/retirement contract',
                     'matching actual KS user/token/position descriptors',
                     'actual eight tag/replay event allocations, delays and per-slot copy/replay attributes',
                     'current target5 commit/HLOAD/GAIN and NORM/GO/NX readiness records']),
        readiness_provider_api=dict(
            required_identity=['die_sha256','source_asbuilt_sha256','source_sha256','clock_reset_id'],
            required_entry=['target5_command_pin_edges','store_commit_edges','hload_command_pin_edges',
                            'last_hload_word_edges','gain_command_pin_edges','last_gain_word_edges'],
            required_norm=['normr_command_pin_edges','pre_resident_before_normr','go_command_pin_edges',
                           'nx_partial_ready_edges','rstd_completion_edges','xq_tx_tag_and_replay_event_edges'],
            required_retirement=['actual_kit_issue','fixed_end_issue','all_row_last_use_edges'],
            rule='consume exact static records in explicit local pin-event clocks; never infer completion from issue+5 ACK'),
        full_token=False)
    if execution is not None:
        if execution.get('die_sha256')!=program['die_sha256']:
            raise ValueError('execution booking belongs to a different actual bound die')
        ks=execution.get('ks_pin_edges');reset=execution.get('reset_release_pin_edge')
        if type(reset) is int and isinstance(ks,list) and ks and all(type(k) is int and k>reset for k in ks):
            proof=timing.get('seqhost_input_clock') or {}
            offset=proof.get('accepted_ks_pin_event_offset_from_reset_release_pin_event_mod4')
            if type(offset) is int and all((k-reset)%4==offset for k in ks):
                result['start_phase']=0
                result['phase']['binding']='explicit actual booking matches measured start_phase0 injection class'
            else:result['phase']['holds'].append('actual KS booking is outside measured start_phase0 class')
            result['mu']['observed_consecutive_gaps']=[b-a for a,b in zip(ks,ks[1:])]
        rows=program.get('rows',[])
        kits=[r for r in rows if r['eng']==14]
        if len(kits)==1:
            offset=timing['masters']['dsdv_hostb_seqhost_mux']['edges']['f_ks_pin_event_plus_kit_issue_to_t_kd']
            result['mu']['actual_calendar_kit_issue']=kits[0]['issue']
            result['mu']['required_return_latency']=kits[0]['issue']+offset-1
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('program','timing','source-root','out'):p.add_argument('--'+arg,type=Path,required=True)
    p.add_argument('--execution',type=Path)
    a=p.parse_args();read=lambda path:json.loads(path.read_text()) if path else None
    result=resolve(read(a.program),read(a.timing),a.source_root,read(a.execution))
    if a.out.exists():raise ValueError('preserve previous contract result')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=1)+'\n')
    print('BOUND_BOOT_CONTRACT stage',result['stage'],'start_phase',result['start_phase'],'PARTIAL; BEGIN/SEAL held')


if __name__=='__main__':main()
