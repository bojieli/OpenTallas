#!/usr/bin/env python3
"""Draft existing measured-target boundary model; no RTL or physical admission.

python3 tools/hbm_accel_current_target_portmap.py --out DIR
Sources are read from immutable git objects, including sparse checkouts.
"""
from __future__ import annotations
import argparse, ast, hashlib, json, math, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = "7f4648052d5855ff078f3b1011ba80f01b3e97bd"
LOADER_SOURCE = "67916251b"

def source(path, rev=SOURCE):
    return subprocess.check_output(["git", "show", f"{rev}:{path}"], cwd=ROOT)

def build():
    uarch = source("tools/uarch_model.py")
    dff = next(ast.literal_eval(n.value) for n in ast.parse(uarch).body
               if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "DFF_UM2" for t in n.targets))
    names = ["tools/uarch_model.py", "tools/dshbm_1m_allmeasured.py", "tools/dshbm_baseline_measure.py",
             "tools/dshbm_1m_hbm.py", "tools/dshbm_1m_coll.py", "tools/qwen_hbmacc_rt_token_w12.py",
             "rtl/test/qwen_rom_runtime/qwen_hbmacc_rt_w12.cpp", "rtl/test/qwen_rom_runtime/ot_qwen_hbmacc_rt_die_w12.sv",
             "rtl/hdc/ot_qwen_me_array_w12.sv", "rtl/hbm_accel/qwen/ot_hbmacc_qwen_wstream.sv",
             "rtl/hbm_accel/sm/ot_hbm_accel_sm_v.sv", "rtl/hbm_accel/tu/ot_hbm_accel_tu_endpoint.sv",
             "rtl/hbm_accel/service/ot_hbm_accel_expert_fetch.sv", "rtl/hbm_accel/service/ot_hbm_accel_expert_service.sv",
             "rtl/model_ready_hbm_r14/ot_hbm_r14_pkg.sv", "tools/hbm_accel_service_context_model.py"]
    pins = {p: dict(commit=SOURCE, sha256=hashlib.sha256(source(p)).hexdigest()) for p in names}
    for module in ["hbm_system_loader", "loader_host", "loader", "store", "dma64"]:
        p = f"rtl/hbm_accel/loader/ot_hbm_accel_{module}.sv"
        pins[p] = dict(commit=LOADER_SOURCE, sha256=hashlib.sha256(source(p, LOADER_SOURCE)).hexdigest())
    ds = dict(target="DS_CURRENT_MEASURED_TP96", ranks=96, rank_bits=7, position_bits=20,
        SM_per_die=32, SM_local_bits=5, stacks_per_die=4, stack_bits=2, SM_per_stack=8,
        stack_local_SM_bits=3, PCs_per_stack=32, PC_local_bits=5, PCs_per_die=128,
        selected_SM="ot_hbm_accel_sm_v", SM_parameters=dict(ENABLE=1,SUB=4,LBS=2,LSB=16,NC=8,RMAX=4096,XD=128,MAX_OUT=512),
        final_pipeline_selection="Use Popper actual frozen sm_r2 source/DS,DW,DG,PIO,STK parameters; source defaults are not routed selection authority.",
        parent_hooks={
          "DS_ISSUE": "existing static fullprogram op -> selected SM start/op_rows13/op_c16/op_g8/op_gs1/op_fmt2; do not use SIMT cmdproc instruction reinterpretation",
          "DS_X": "actual acquired operand -> xw_en/xw_addr7/xw_grp7/xw_data2048; shared publication/broadcast admission must precede start",
          "DS_FETCH": "four stack groups, ot_hbm_accel_expert_fetch NSM8/NPC32 -> eight1024bit streams each; descriptor->SM bulkcopy LINE1088/tag10 binding requires existing owner/format adapter, not zero padding or tag truncation",
          "DS_RESULTS": "32 SM rv/rrow12/rdata256 -> actual shared/DU owner publication before arrive/release_in/released; no done=publication shortcut",
          "DS_DU": "existing N1024 SU il+dr+ov, index/attention/mHC/quantise/select service hooks consume actual published operands in static order; exact per-die replica census beyond measured components not fixed by a fullparent",
          "DS_HBM": "four32PC stack groups with actual read/write arbitration, owned identity/beat returns and positive ACK; expert_service is read-only, causal provider owns write lifecycle, do not instantiate duplicate unarbitrated controllers",
          "DS_TU": "hub actual ordered fragments -> inj_rd/inj_idx16/inj_data512; del_valid/del_flit545 -> checked published consumer slots; preserve rank8/flit-index16 and return credits",
          "DS_HOST": "globalrank7, localSM5 and position20 source context; enclosing existing host hierarchy must retain these through launch/completion, not inherited4/4/16",
          "DS_LOAD": "per-die existing load/store port -> selected actual stack-service client; full byte aperture and client allocation must precede corridor sizing"},
        port_prices=dict(SM_ingest_payload_bits_per_edge=32*1088,SM_results_payload_bits_per_edge=32*256,
          SM_ingest_byte_upper_bound_per_fast_edge=32*128, per_stack_SM_ingest_byte_upper_bound=8*128,
          stack_column_payload_B_per_service_edge=32*32,die_column_payload_B_per_service_edge=4*32*32,
          clock_target_fast_Hz=1.2e9,measured_service_period_ps=1024,
          die_column_peak_Bps=4*32*32/(1024e-12),
          joint_ingest_vs_service="32SM peak4915.2GB/s > fourstack4000GB/s; actual measured schedule must stall/prices HBM stretch, no free compute/HBM overlap"),
        TU=dict(NPT=8,LANES=16,FW=512,PWT=545,PFMAX=384,INJ=2,DEL=4,HUBW=35,WSTG=14,
          all_reduce=dict(NC=8,NOG=8,BF16=1,contributors=64),all_gather=dict(NC=1,NOG=96,BF16=0,contributors=96),
          external_TX_wires=8*(545+1),external_RX_wires=8*(545+1),credit_wires_each_direction=8,
          payload_peak_Bps=8*800e9*.9/8,
          fixed_external_budget_ns_per_crossing=100+250+27.6,
          conservative_tail_us_per_collective=.15,
          topology="existing switched TU tier, no proposed direct-link/NVLS/in-switch reduction",
          owner_decision="Measured AR/gather are two separately elaborated NC/NOG/BF16 configurations. Select existing dual-configuration parent with priced shared eight-port arbitration, or provide existing compatible mode-capable source. Cannot silently share one parameter-fixed endpoint or allocate16 free ports.",
          hardware_endpoint_instance_count=None,PHY_switch_realization="vendor budget; physical PHY/FEC/switch binding absent"))
    q = dict(target="QWEN_CURRENT_HA8_TP4",ranks=4,rank_bits=2,position_extent=8192,
        source_position_bits=18,minimum_required_position_bits=13,SM32_not_selected=True,
        die_top="ot_qwen_hbmacc_rt_die_w12",die_parameters=dict(G=6144,NW=18,SNW=18,D=4,SW=64,LV=7,SMIN=7,SMAX=11,TCUT=6,BD=31,XVM=1,NWS=4,TWS=30,ORD=4),
        tile_parameters=dict(GT=6144,SMIN=7,CODE_BANKS=5,KV_LOCAL=0),
        die_parameter_note="CODE_BANKS belongs to tile model; final fmax arithmetic/core/spine successor selection must match owner terminal records, not historical defaults",
        component_census_per_die=dict(die_core_and_spine=1,tiles=6144//4,stream=1,PC_stream_controllers=4*32),
        system_collective=dict(module="ot_rom_oneshot_allreduce",N=4,LANES=16,TAGW=32,DEPTH=16,LAT=11,BPC_NUM=3600),
        parent_array_source="rtl/hdc/ot_qwen_me_array_w12.sv preserves TG4 tile mapping/tree/order; runtime C++ replicates identical fabric, not a different algorithm",
        stream_parameters=dict(ENABLE=1,NSTK=4,REF_MODE=1,CRED=32,WINW=160,SPW=24,CW=32,RL=23,MINLAT=2),
        storage=dict(stream_word_bytes=98304,window_words=160,window_payload_bytes=160*98304,
          model_resident_bytes=int(421.5*2**20),resident_and_window_overlap_binding=None,
          note="Do not sum window+resident until actual shared-bank/capacity mapping states containment; no memory abstract implied."),
        parent_hooks={
          "Q_ARRAY": "spine tgo/tb379/xl_d65536 ->1536tiles, tile-to-tile staged split tree ->t_lvl49152; preserve BD31,NWS4,TWS30 and existing array source",
          "Q_VM": "actual SW64 source VM: three64x32bit read payloads and64x32bit SU writes; ME48 ports x512bit result plus addresses/masks, existing source conflict/publication rules",
          "Q_COLLECTIVE": "four die c_valid/c_ready/c_data512/c_last/c_mode/c_tag32 into selected collective; r_valid/r_data512/r_last/r_rank2/r_err returns; preserve actual shared-edge tags/order",
          "Q_STREAM_STATUS": "w_c_gray32 -> existing two-flop ctl synchroniser; a_gray32 -> existing two-flop core synchroniser; no extra clock or free latency",
          "Q_STREAM_PAYLOAD": "MANDATORY hook: real controller sector returns -> checked code/KV window storage + positive published complete-word count. Existing wstream carries NO DATA and host preloads code/KV. Its timing count alone is not physical payload delivery.",
          "Q_LOAD": "existing ND4 loader can addressfourdie BARs; load/store1+1 per die -> real resident/window/code/KV writers through owned sector path. W12 has no MREQ/loader client port: bridge aperture+port/calendar binding remains required, not host memcpy",
          "Q_PROGRAM": "prog_addr12/prog_q1024; desc_addr6/desc_q64; staged seg_base24/seg_len24/seg_sidx32/seg_kind2 xNSEG8; actual loader/programmem writers not implicit host values"},
        port_prices=dict(core_period_ps=833.333,service_period_ps=1024,PC_sector_B=32,
          peak_service_Bps=4*32*32/(1024e-12),VM_three_read_payload_bits_per_edge=3*64*32,
          VM_SU_write_payload_bits_per_edge=64*32,ME_result_payload_bits_per_edge=(6144>>7)*512,
          tile_instruction_fanout=1536,tree_to_spine_payload_bits=(6144>>6)*512,
          collective_payload_B_per_fast_edge=64))
    loader = dict(source="ot_hbm_accel_loader_host",enabled=True,
        per_die=dict(ot_hbm_accel_loader=1,ot_hbm_accel_store=1,shared_service_clients=1),
        existing_host_group_limit=8,DS96_host_group_selection=None,Qwen4_single_existing_host_group_legal=True,
        ports=dict(request_payload_bits=256,address_bits=32,strobe_bits=32,tag_bits=16,physical_host_DMA_bits=64),
        load_parameters=dict(BURST=16,MAXOUT=8,OUTW=96,VOUT=16,TW=16,CDC_AW=5),
        store_parameters=dict(BURST=16,MAXOUT=32,VOUT=16,TW=16,CDC_AW=5),
        address_check=dict(existing_DADDR_is_byte_address=True,existing_byte_aperture=2**32,
          pkg_sectors_per_stack=703125000,bytes_per_stack=703125000*32,
          minimum_full_stack_byte_bits=math.ceil(math.log2(703125000*32)),
          minimum_four_stack_flat_byte_bits=math.ceil(math.log2(4*703125000*32)),
          source_sector_field_bits=34,source_stack_bits=2,
          owner_hook="Bind existing checked fullsector+stack translator to loader page/aperture or supply selected widened loader source.32bitDADDR is not wholefourstack address. No unchecked narrowing."),
        service_client_check="identity_t.client6 cannot encode64SMclients+loader+DU globally. Existing8SM/stack partition has16 SM clients/stack; actual DU+loader enrollment must fit<=64, source census required.",
        identity_check="identity_t.die1 is local namespace. Across die boundaries preserve immutable rank7 DS/rank2 Qwen context; no casts of rank96 to1bit. Decide contained per-die namespace vs width-selected successor explicitly.",
        corridor=dict(host64_payload=True,service256_payload=True,positive_completion="RLAST/B + actual writeACK/readback order",clock_crossings="existing load/store forward/reverse CDC retained",slot_rectangle=None,track_capacity=None,CTS_PG_allowance=None,protected_control_source_qualification=False))
    model = dict(schema="opentallas.hbm.current_target_portmap.draft.v1",default_enabled=False,RTL_admitted=False,physical_admitted=False,
      source_pins=pins,DS=ds,Qwen=q,loader=loader,
      minimum_price=dict(unified_constant_DFF_um2=dff,
        DS_fullrank_vs_local_die_extra_bits_per_identity=6,
        conditional_extra_raw_context_bits_if_fullrank_expansion=6*64*4,
        conditional_extra_raw_context_FF_floor_um2=6*64*4*dff,
        context_protection_note="current301raw->307 fits320raw/360coded context envelope; owned465->471 fits512raw/576coded; wire/codec/decode/clock not free. This is a bound for width-selected variant, not an authored or admitted change.",
        composition="Preserve current measured DS/HA8 calendars; any added copy, CDC or port arbitration contributes its actual exposed cycles. No saving, added0 or headline claim while mandatory hooks unresolved.",
        unpriced_terms=["parent issue/DU/publication mux", "TU AR/gather mode arbitration and installed endpoint count", "actual loader page translator and request merge", "Qwen real sector/window/code/KV publication", "native staged capture and VM write arbitration", "loaded physical route/CDC/mux/codec/CTS/PG in exact slots"],
        full_composed_latency=None,full_area=None,slot_fit=None),
      decisions=["DS: existing per-die static-SM+DU owner parent binding; not SIMT substitution",
                 "DS: existing eight-port TU AR/gather configuration-sharing source selection",
                 "DS: actual per-die host or supported host-group selection for96rank system",
                 "Both: loader fulladdress translation, exact client census and physical corridor",
                 "Qwen: real payload-to-window/program/VM hardware writer enrollment plus final fmax successor source selection"])
    assert ds["SM_per_stack"]*ds["stacks_per_die"]==ds["SM_per_die"]
    assert q["component_census_per_die"]["tiles"]==1536 and q["storage"]["window_payload_bytes"]==15*2**20
    assert loader["address_check"]["minimum_full_stack_byte_bits"]==35
    assert loader["address_check"]["minimum_four_stack_flat_byte_bits"]==37
    return model

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("--out",type=Path,required=True);args=ap.parse_args()
    data=build();args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"model_portmap.json").write_text(json.dumps(data,indent=2)+"\n")
    print("DS32SM/four8SMgroups;QwenTP4/1536tiles/fourstacks;BLOCKED_NAMED_HOOKS; noRTLadmission")
if __name__=="__main__":main()
