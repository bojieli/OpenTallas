#!/usr/bin/env python3
"""Source-owned fresh CPsouth MTP pin facade sizing before engine binding.

A direct wiring facade adds no sequential latency. The checked command join
and provider state must be priced from their source before elaboration/P&R.
"""
import argparse,json
from pathlib import Path

def model(am=False,mx1=False):
    w,h=1399.656,701.976
    result=dict(schema='opentallas.hbm.cp-mtp-native-south.v1',default_enabled=False,adopted=False,
        source_contract='f49a3d30f',MTP_facade_source='f90d728da',master='hfd_cmdproc_s_mtp_native',
        replaced_master='hfd_cmdproc_s',north_master_unchanged='hfd_cmdproc_n',
        macs_per_cycle=0,compute_intensity=0,communication_intensity='control/command/emitted-token traffic',
        memory_ports=[],replicas=1,mux_demux_fanout='direct grouped field wiring; no broadcast or mux added by facade',
        boundary_bits_per_cycle=dict(f_mtp=517,t_mtp=179,f_host=224,t_host=5,f_provider=179,f_backend=81,t_backend=279,t_emit=38,t_provider=43,f_emit_host=2,t_emit_host=108,t_abort=1),
        routing=dict(face='S',layer='M5',pin_pitch_um=.192,interface_tracks=696,
            interface_span_um=696*.192,extra_transaction_endpoint_tracks=960,
            total_new_interface_span_um=(696+960)*.192,face_capacity_tracks=int(w/.192),
            channel_capacity_qualified=False,pin_offsets='must reserve disjoint exact runs alongside other real ports'),
        area=dict(slot_um=[w,h],facade_extra_standard_cells=0,facade_extra_state_bits=0,
            checked_join_register_bits_upper=600,checked_join_cell_area_bound_um2=600*.2916+800,
            emit_queue_source='ea4117432',emit_queue_depth=8,emit_queue_storage_bits=648,emit_queue_other_state_bits_upper=160,
            emit_queue_cell_area_bound_um2=808*.2916+800,
            checked_join_source='442da48ad',existing_command_memory='actual CP NCMD256×64 native SRAM provider',
            slot_fit_qualified=False),
        latency=dict(facade_added_cycles=0,native_command_accept_cycles=0,tagged_completion_to_native_done_cycles=1,serial_token_latency='one acknowledgement cycle per real native command; command count measured separately'),
        model_ready_for_build=True,
        missing_before_adoption=['actual operation descriptor translator','mutable join state protection','real finite provider and tagged completion bindings','source-owned collar/pin context closure'],
        precision=dict(MTP_token_bits=17,Qwen18_supported=False,policy='native DS MTP contract only; no implicit narrowing'),
        physical_qualification=False,headline_rate=None)
    if am or mx1:
        result['master']='hfd_cmdproc_s_mtp_native_am'
        result['MTP_facade_source']='native CP STOP197 grouped facade must bind source08e4b1bf7; separate from frozen179'
        result['native_controller_source']='08e4b1bf7'
        result['native_controller_master']='hfd_mtp_x_cp_stop'
        result['boundary_bits_per_cycle'].update(t_mtp=197,f_am=18)
        result['routing'].update(interface_tracks=714,extra_transaction_endpoint_tracks=978,total_new_interface_span_um=1692*.192)
        result['area']['checked_join_source']='a9f866a26'
        result['latency']['native_MTP_AM_pin_capture_cycles']=1
        result['AM_identity']='actual backend captured job/gen/sequence/epoch remains stable through CPRESULT winners and final completion'
        result['AM_order']='up to six ordered VHEAD winners precede final completion; no delayed/fabricated LG stream'
    if mx1:
        result['master']='hfd_cmdproc_s_mtp_native_mx1'
        result['boundary_bits_per_cycle'].update(f_host=216,f_backend=73,t_backend=271,t_emit_host=100,t_drained=1)
        result['routing'].update(interface_span_um=714*.192,extra_transaction_endpoint_tracks=947,total_new_interface_span_um=1661*.192)
        result['area'].update(checked_join_source='f7498a6b1',emit_queue_source='f7498a6b1',emit_queue_storage_bits=584,emit_queue_other_state_bits_upper=152,emit_queue_cell_area_bound_um2=736*.2916+800)
        result['AM_identity']='actual captured job/generation/sequence remains stable through winners and completion; no reset epoch'
        result['reset']='MX1 drained only; no persistent epoch; original job/generation/sequence stale-completion checks retained'
        result['control_protection']='plain flops; no SECDED, mirrors, authentication or lease machinery'
        result['area']['checked_join_cell_area_bound_um2']=592*.2916+800
        result['area']['checked_join_register_bits_upper']=592
        result['missing_before_adoption']=['actual operation descriptor translator and provider binding','actual physical context and shared drained-reset wiring']
        result['drain']='guard+queue drained_ready; backend bit71 is backend drained_ready AND no outstanding SM/service result; native done held high, emit/cmd low; job_ready remains low until coordinated reset'
        result['peer_composition_evidence']='bf972bc00: two actual native drained-reset jobs and wrong-job completion negative'
        result['acceptance']=dict(TT_setup_ps=0,FF_hold_ps=0,DRC=0,SS='sensitivity; no SS headline claim')
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);p.add_argument('--am',action='store_true');p.add_argument('--mx1',action='store_true');a=p.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(model(a.am,a.mx1),indent=2)+'\n')
if __name__=='__main__':main()
