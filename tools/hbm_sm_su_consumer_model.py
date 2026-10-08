#!/usr/bin/env python3
"""Actual SM-result/SU binding alternatives. Model only; no endpoint adoption."""
import hashlib
import json
from pathlib import Path
from hbm_sm_result_provider_model import model as store_model
ROOT=Path(__file__).resolve().parents[1]

def translate_result_word(logical_word, logical_base, rows, result_base, result_limit):
    """Checked byte address for a proposed installed result-span read binding.

    Called only after owner/publication qualification; no narrowing of37-bit
    provider addresses to the old fixed32-bit virtual HCpost provider.
    """
    if not (1 <= rows <= 4096 and result_base >= 0 and result_base % 32 == 0
            and result_base + rows*32 <= result_limit <= (1 << 37)):
        raise ValueError('invalid installed result span')
    offset=logical_word-logical_base
    if not 0 <= offset < rows*8:
        raise ValueError('logical SU read outside published result span')
    address=result_base+offset*4
    return dict(byte_address=address,sector_address=address & ~31,word_in_sector=(address >> 2) & 7)

def model():
    store=store_model()
    files=['tools/hbm_accel_die_fp.py','tools/hbm_die_station_gen.py','tools/hbm_hub_quarter_gen.py',
           'rtl/hbm_accel/control_20261007/result_provider/ot_hbm_sm_result_provider.sv',
           'rtl/hbm_accel/su/ot_hbm_accel_su_parent_exec.sv',
           'rtl/hdc/v41x/ot_hdc_v41x_vec_c12.sv','tools/hbm_sm_native_install.py']
    return dict(schema='opentallas.hbm.sm_su_consumer.alternatives.v1',selected=False,adopted=False,
      decision='Develop existing source-owned result provider to shared memory to checked SU reads; no second result store.',
      existing_path_finding={'physical_tree':'SM rv,row12,data256,fault -> concatenating gather -> hfd_su.r',
        'endpoint':'physical exercise envelope, not functional SU consumer; keep historical only',
        'unrelated_bridge':'integrated_gather_bridge is512bit score/ID borrower, not270bit native result input',
        'real_SU_inputs':'vi_q[32] and four rd_q[32] perlane with source/address; outputfault aggregate',
        'existing_executor_limit':'fixed4-op HCpost virtual-edge executor; its32bit byte addressing/1MiB VM range is not a general37bit installed result reader'},
      alternatives={
       'source_owned_shared_service':dict(preferred=True,new_capture_store_count=0,
         existing_store_rows=4096,existing_store_payload_bits=256,existing_macro_count_per_SM=40,
         existing_macro_area_per_SM_um2=store['macro_area_um2'],
         retained_contract='Reserve complete row count before no-ready native start; capture unique row; sticky nativefault inhibits publication; actual write ACK+bit-exact readback before publication; hold result allocation until all SU reads retire.',
         capture_boundary_bits=270,protected_capture_frame_candidate_bits=318,
         source_identity='fixedSM wire plus installed record/owner context; current318frame lacks explicitrecord and requires separately priced binding',
         service_request_bits=344,service_response_bits=276,
         logical_read_translation='base +4*(logical_word-logical_base); boundscheck entire installed span; preserve37bit address until actualproviderdecode',
         admission_barrier='SU program cannot issue dependent read until exact installed record and generation publication accepted; do not infer publication from native_done',
         latency=dict(reservation_setup_cycles=64,capture_cycles='>= rows',
           publish_cycles='rows*(4 + WrReqStall + WrRspLatency + RdReqStall + RdRspLatency)',
           SU_read_cycles='actualsharedservice+protectedrequest/response path+lane capture; no assumed fixedmemorylatency',
           candidate_capture_codec_cycles=7,
           total='setup + capture + publication + SUread barrier/returns; price concurrentrecords only after measuredscheduler'),
         boundary_bandwidth=dict(capture_bytes_per_cycle=32,read_or_write_payload_bytes_per_accepted_service=32,macro_bytes_per_cycle=40),
         SU_adapter='Reuse virtual-edge freeze until required reads return, rather than pretending arbitrarylatency provider meetsfixedlane port latency; generalinstalledprogram adapter isnotyetimplemented',
         outstanding_hardware='native_fault/sourceidentity capture; memoryrow+record integrity binding; actual sharedservice owner adapter; installedSUprogram/operand mapping; protected publication/release coupling',
         floorplan_fit=False,routing_capacity_qualified=False),
       'global_protected_gather':dict(preferred=False,frame_bits=318,slices_per_SM=6,hard_slice_bits=64,
         transport_cycles_baseline=72,transport_cycles_combined_geometry_candidate=91,
         encoder_cycles=3,checker_cycles=4,combined_candidate_cycles=98,
         existing_store_reuse_required=True,
         requirement='318bits survive every gather/storagestage until actualresultprovidercapture checker; fixedperSM grouping andidle/valid sequence checked; protectednativefault controlsstickyquarantine',
         rejects='No CRCstrip atlegacy270gather, no claimfromXORexerciseSU, no extraunpricedglobalsink',
         new_global_sink_area=None,routing_capacity_qualified=False,floorplan_fit=False)},
      shared_open_requirements=['nativefaultinput presentlyabsentresultprovider','storedpayloadECC notsufficientrow/recordassociation','exactallocatorlogicalSUoperand mapping','actualproviderlatency/credit inventory','reset andallocationlifetime/replay bound','allsource andreturnedmemorydata remainsprotected through finalSUcapture'],
      source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in files})
if __name__=='__main__':print(json.dumps(model(),indent=2))
