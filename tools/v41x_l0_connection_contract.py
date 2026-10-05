#!/usr/bin/env python3
"""Source-check the remaining V4.1 full-shape L0 execution connections."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import re
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import hdc_replay_v41 as R  # noqa: E402

SOURCES=[
    "rtl/hdc/v41x/ot_hdc_core_v41x.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_att_adapt.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_xu_adapt.sv",
    "rtl/chip/ot_chip_v41x_tile.sv",
    "rtl/chip/ot_chip_v41x_die.sv",
    "rtl/chip/ot_chip_v41x_attn_row_merge.sv",
    "rtl/chip/ot_chip_v41x_ckv_selected_dma.sv",
    "rtl/chip/ot_chip_v41x_packed_attn_service.sv",
    "rtl/chip/ot_chip_v41x_hbm3e_phy.sv",
    "rtl/hdc/hbm/ot_hdc_qstream.sv",
    "tools/hdc_replay_v41.py",
    "results/rtl/hdc_v41x_fullshape_qe_stream_200k_l0_rank0.json",
    "results/rtl/v41x_attn_packed_bypass.json",
]
OUT=ROOT/"results/rtl/v41x_l0_connection_contract.json"


def digest(p:Path)->str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def at(path:str,pattern:str)->int:
    lines=(ROOT/path).read_text().splitlines()
    hits=[i for i,line in enumerate(lines,1) if re.search(pattern,line)]
    if len(hits)!=1:
        raise AssertionError(f"expected one {pattern!r} in {path}, got {hits}")
    return hits[0]


def main()->None:
    die="rtl/chip/ot_chip_v41x_die.sv"
    tile="rtl/chip/ot_chip_v41x_tile.sv"
    core="rtl/hdc/v41x/ot_hdc_core_v41x.sv"
    phy="rtl/chip/ot_chip_v41x_hbm3e_phy.sv"
    qstream="rtl/hdc/hbm/ot_hdc_qstream.sv"
    sources={p:digest(ROOT/p) for p in SOURCES+["tools/v41x_l0_connection_contract.py"]}
    if R.RATIO[0]!=0 or R.dyn_values(R.SHIPPED,199999)["T0"]!=128:
        raise AssertionError("L0 window-only geometry changed")
    layout=R.ShapeLayout(R.SHIPPED,tp_exact=True)
    sel_base=layout.vm.map["SEL"]
    l0_vm_end=layout.vm.map["SLOT2"]
    if sel_base!=365024 or l0_vm_end!=446688:
        raise AssertionError("L0 VM allocation changed; redo connection sizing")
    qe=json.loads((ROOT/SOURCES[-2]).read_text())
    sectors=qe["physical_qe_bytes_reserved"]//32
    if qe["physical_qe_bytes_reserved"]%32 or sectors!=65242240:
        raise AssertionError("QE physical image changed; redo HBM width")
    line={
        "die_desc_ok":at(die,r"else if \(att_packed_desc_ready\) packed_desc_ok <= 1'b1;"),
        "die_window_read_tied":at(die,r"\.packed_re\(1'b0\)"),
        "die_ckv_tied":at(die,r"\.c_v\(4'b0\)"),
        "die_weight_addr":at(die,r"wire \[23:0\] wq_addr"),
        "phy_weight_addr":at(phy,r"input  wire \[23:0\]          w_addr"),
        "qstream_haw":at(qstream,r"parameter integer HAW    = 24"),
        "tile_sharded_default":at(tile,r"parameter integer IDX_SHARDED = 0"),
        "tile_sharded_core":at(tile,r"\.PIKH_HAW\(PIKH_HAW\), \.IDX_SHARDED\(IDX_SHARDED\)"),
        "die_vm_default":at(die,r"parameter integer VM_AW   = FULL_SHAPE \? 19 : 16"),
        "tile_vm_default":at(tile,r"parameter integer VM_AW   = FULL_SHAPE \? 19 : 16"),
        "die_sharded_parameter":at(die,r"parameter integer IDX_SHARDED = 0"),
        "die_sharded_tile":at(die,r"\.IDX_SHARDED\(IDX_SHARDED\)"),
        "die_weight_parameter":at(die,r"parameter integer W_HBM   = 1"),
        "die_weight_tile":at(die,r"\.W_HBM\(W_HBM\)"),
        "core_kvd_repeat":at(core,r"else kvd_v <= \(KV_HBM != 0\) && \(st == S_DEC\)"),
        "row_selected_id":at("rtl/chip/ot_chip_v41x_attn_row_merge.sv",r"input  wire \[POS_W-1:0\]     selected_source_id"),
        "ckv_owner":at("rtl/chip/ot_chip_v41x_ckv_selected_dma.sv",r"wire \[1:0\] source_die = source_id\[5:4\]"),
        "selector_local_index":at("rtl/hdc/v41x/ot_hdc_v41x_xu_adapt.sv",r"pc = q \* xs_R \+ \(xs_b << LSW\) \+ l;"),
        "emitter_final_select_estimated":at("tools/hdc_replay_v41.py",r'_estimated="cross-die final select over tp x topk on the XU select"'),
    }
    die_text=(ROOT/die).read_text()
    if "ot_chip_v41x_ckv_selected_dma u_" in die_text or \
       "ot_chip_v41x_attn_row_merge u_" in die_text:
        raise AssertionError("a listed missing die connection has landed; update contract")
    if "ot_chip_v41x_ckv_selected_dma" not in (ROOT/"rtl/chip/ot_chip_v41x_ckv_selected_dma.sv").read_text():
        raise AssertionError("CKV DMA source missing")
    observations={
        "l0": {"ratio":0,"position":199999,"window_rows":128,"selected_rows":0,
               "attention_rows":128,"selected_id_stream_needed_for_l0":False},
        "vm": {"sel_element_base":sel_base,"l0_first_later_layer_slot":l0_vm_end,
               "minimum_l0_address_bits":math.ceil(math.log2(l0_vm_end)),
               "die_reduced_default_bits":16,"die_full_default_bits":19,
               "full_40_layer_layout_elements":layout.vm.top,
               "full_40_layer_monolithic_fits_30_bits":layout.vm.top <= 1<<30},
        "weight_hbm": {"selected_image_reserved_bytes":qe["physical_qe_bytes_reserved"],
                       "selected_image_reserved_sectors":sectors,
                       "minimum_sector_address_bits":math.ceil(math.log2(sectors)),
                       "current_qstream_and_phy_bits":24},
        "current_missing_connections":{
            "die_window_packed_read":True,
            "die_selected_ckv_client":True,
            "die_row_merger":True,
            "die_selected_id_vm_stream":True,
            "local_index_to_global_ckv_id_and_tp_final_select":True,
            "die_remote_ckv_fabric":True,
            "descriptor_outstanding_generation":True,
        },
        "line_evidence":line,
        "connected_options":{"full_mode_vm_aw19":True,"die_w_hbm_parameter":True,
                             "die_idx_sharded_parameter":True,"idx_sharded_default_enabled":False},
    }
    if observations["vm"]["minimum_l0_address_bits"]!=19 or \
       observations["weight_hbm"]["minimum_sector_address_bits"]!=26:
        raise AssertionError("unexpected full-shape widths")
    record={
        "schema":"opentallas.rtl.v41x_l0_connection_contract.v1",
        "status":"blocked_pending_integration",
        "claim_boundary":"Read-only, source-pinned connection inventory. No full-shape token, HBM attention serving, sustained rate or P&R verdict.",
        "observations":observations,
        "required_transitions":[
            "IDLE: accept one new KVD generation and latch pos/user/rows/SEL base; repeated S_DEC assertions must not create duplicate jobs",
            "STAGE: derive W=min(pos+1,128), selected=T-W; transform RTL local scan indices into global CKV IDs after real TP final selection, then read SEL VM in order and validate source_count/owner",
            "READY: assert kv_ok only for the matching descriptor after initial packed rows are serviceable; never accept an unqualified late ready",
            "STREAM: send ceil(T/4) ordered 4-row beats; final mask is a prefix; count only valid&&ready and hold payload under backpressure",
            "DRAIN: wait for row merger completion and attention engine idle; clear generation and readiness before the next descriptor",
            "FAULT: hold fail-closed on stale generation, address/region violation, bad source ID, remote mismatch or wrong beat count",
        ],
        "required_ports":{
            "descriptor":"kvd_v,pos,user,T,selected_count,sel_vm_base,published_source_count,mode,generation; ready and done/fault responses",
            "selected_vm":"arbitrated 32-bit VM read request/response with SEL_base+i address; TP final select and local-index-to-global-ID transform precede one ID per row; no golden ID injection",
            "packed_attention":"4x16x265 bit beat, 4-bit prefix mask, valid/ready, fault and completion; window/CKV row merger is the source",
            "remote_ckv":"source ID, owner die, local row, user/layer/generation, valid/ready and tagged packed 288-byte response through real fabric",
            "weight_hbm":"W_HAW>=26 from qstream through die/PHY/model; capacity/placement covers at least 65,242,240 selected-image sectors",
            "index":"one die IDX_SHARDED parameter passed to both pooled reader and key writer; index image uses matching layout",
        },
        "ownership_proposal":{
            "root_architecture":"approve VM port arbitration, per-die HBM region layout, remote CKV transport and production memory capacity",
            "attention_owner":"descriptor lifecycle and packed adapter ready/beat completion contract",
            "die_packed_kv_owner":"window/CKV DMA plus row merger hookup and selected/remote source tags",
            "fullshape_emitter_owner":"emit SEL base/source count and exact dependency before attention; L0 T0 has no selected rows",
            "fullshape_core_owner":"source-check connection manifest and L0 arithmetic harness once interfaces freeze",
            "qe_hbm_owner":"propagate W_HAW and source-mode capacity through qstream/die/PHY comparator path",
            "index_owner":"paired IDX_SHARDED propagation and exact image gate",
        },
        "source_sha256":sources,
    }
    OUT.write_text(json.dumps(record,indent=2,sort_keys=True)+"\n")
    print("PASS: source-pinned L0 connection inventory; execution remains blocked")


if __name__=="__main__": main()
