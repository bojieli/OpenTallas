#!/usr/bin/env python3
"""Bounded identity/calendar model, not RTL or arithmetic simulation."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
SOURCES=["tools/s81_dv/layer_prog/lower_svc.py","tools/s81_dv/layer_prog/xs_bf.py","tools/s81_dv/layer_prog/lower_vs.py","tools/s81_dv/layer_prog/xs_place.py","rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_rs.sv","rtl/dsrom_sys/s81_dv/svc_rs/dsdv_svc_att.sv","rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_smq.sv","rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_sms.sv","rtl/dsrom_sys/s81_dv/su_sm/ot_s81_su_smh.sv","rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sm.sv","rtl/dsrom_sys/s81_dv/slice/ot_s81sl_xs.sv","rtl/dsrom_sys/s81_ctrl/ot_s81_svc_job.sv"]
def audit(mut=None):
    # lower_svc.pv_words wire identity: t=4ST+quarter tile, b=pv_c, wi=payload index.
    store={}; beat_count=[0]*4
    for st in range(4):
        if mut=="missing_quarter" and st==3: continue
        for tile in range(4*st,4*st+4):
            for b in range(8):
                for wi in range(1,5):
                    d=32*tile+8*(wi-1)+b
                    for h in range(16):
                        hh=h^1 if mut=="head_swap" else h
                        store[hh,d]=(h,d)
                    beat_count[st]+=1
    # Real SMJ head mask, 32 operands x 16 FP32 lanes, no receiving-side arithmetic.
    if mut=="reset_stale": store.clear()  # payload may remain but new epoch is invalid
    if len(store)!=8192 or beat_count!=[128]*4: return False
    output={}
    for h in range(16):
        for row in range(32):
            vals=[store[h,16*row+l] for l in range(16)]
            if vals!=[(h,16*row+l) for l in range(16)]: return False
            # Each 256-bit SO result occupies the actual half mask of one 512-bit write.
            mask=0xff00 if h&1 else 0x00ff
            if mut=="half_swap": mask^=0xffff
            addr=8*row+h//2
            for l in range(16):
                half=1 if mask==0xff00 else 0
                key=(addr,16*half+l)
                if key in output: return False
                output[key]=(h,16*row+l)
    for h in range(16):
        for d in range(512):
            if output[8*(d//16)+h//2,16*(h&1)+d%16]!=(h,d): return False
    # wo_a K=4096 means 8 adjacent heads/group, 64 BF gather beats/group, 8 consumers/group.
    gather={}
    for h in range(16):
        for d in range(512):
            group=h//8; k=(h%8)*512+d
            gather[group,k//64,k%64]=(h,d)
    assert len(gather)==8192
    return True
assert audit()
neg={m:not audit(m) for m in ["missing_quarter","head_swap","half_swap","reset_stale"]}
assert all(neg.values())
m={
 "verdict":"MODEL_ONLY_TARGET_ABI_ENUMERATED_FULL_PRODUCTION_CALENDAR_AND_COST_OPEN",
 "base_revision":"df32caee0", "historical_storage_model":"83c2428ca", "q_inventory_model":"d6185918c",
 "source_sha256":{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
 "scope":{"heads_rank":16,"dimensions":512,"window":128,"wo_a_K":4096,"wo_a_group_heads":8,"wo_a_groups_local":2,"output_slices_per_group":8,"shape_authority":"xs_bf.py declared production shape; selected fixture and physical slice group installation still required"},
 "se_existing":{"consumer":"dsdv_svc_rs pb_w/pbuf -> RNE BF16 -> pl_d -> score exchange -> fold PV frame -> owner P feed","old_no_se_consumer_claim":"superseded for PPATH=True; external write-face routing still open","new_hardware_for_existing_P_path":0},
 "pv_ingress":{"quarter_records":160,"quarter_data_records":128,"quarter_headers":32,"all_quarter_records":640,"all_data_records":512,"remote_records":480,"remote_payload_bits":196608,"unique_payload_bits":262144,"wire_record_bits":514,"identity_enumerated":8192,"storage_logical":"16 coherent 32x512-bit head stores, 32-bit lane write masks; simultaneous 16 head writes per PV data record, one 512-bit head-row read for serializer","conditional_native_capacity":"128 singleclock32x64 banks (8 per head) with actual 32-bit half masks; per bank writes occur only on its lane pair; no same-address read/write needed after all-quarter fence","conditional_macro_count":128,"conditional_macro_area_um2":128*552.40704,"conditional_macro_clock_pins":128,"macro_qualification":"historical b65718325 source family only; local contacts/access/PG/native timing unqualified; no physical grant"},
 "so_q_frames":{"parameter_header_words":1,"parameter_payload_words":5,"operand_frames":16,"operand_payload_words":512,"operand_header_words":16,"total_q_words":534,"q_pin_II1_first_to_last_edges":533,"conditional_upstream_NP4_first_to_last_edges":2132,"conditional_upstream_NP4_occupied_edges":2133,"parameters":"SMJ kind5/start1; row0 obase; rows1..4 token-position coslo/coshi/sinlo/sinhi. Broadcast once then per-head mask1<<h, start0, operand flag1. No new SE and no denominator overwrite.","start_bound":"all four quarters proven current epoch AND previous SE denominator arrived AND final parameter/cos row early enough for tail divide use","earliest_schedule":"symbolic only: max(Q return/gather/QR readiness, four-quarter arrivals, SE den readiness) + assembler macro read/pin ages; all ages not yet installed"},
 "so_result":{"writes_per_head":32,"all_write_events":512,"live_payload_bits_per_write":256,"wire_interface_bits_per_head":555,"full_face_capture_FF":16*555,"optional_pruned_static_half_capture_FF":16*(1+14+16+256+12),"pruned_interface":"requires private exact head-parity specialization; no grant and no omission of live bits","existing_address":"obase + 8*oc + floor(h/2)","existing_mask":"h even00FF, oddFF00; do not overwrite complementary half","unique_normalized_payload_bits":131072,"four_rows_pack_register_bits":1024,"unique_gather_beats_1024b":128,"beats_per_wo_a_group":64,"delivered_beats_all_slices":1024,"existing_XS_target":"ot_s81sl_xs g_v/g_fam=1/g_idx/g_d source0..2; one global BF beat index arrives once per slice. Must open matching parity gather window before arrivals; no direct arbitrary VM write ABI","outgoing_beat_interface_bits":1033,"group_beat_index":"idx=floor(((h mod8)*512+d)/64), lane=d mod64; phase group selected by xs_bf row partition","VM_unique_bits":131072,"VM_replica_payload_bits_16_slices":1048576,"new_VM_macro_count":None,"VM_reuse_reason":"existing XS BF capacity80beats/parity >=64, but source assignment/parity/arrival lifetime must be proven; do not charge new VM by assumption"},
 "cost_status":{"candidate_C1_min_checker_FF":166,"candidate_C1_capture_pack_output_checker_FF_lower_bound":8880+1024+1033+166+514,"logic_mux_area_um2":None,"capture_FF_area_um2":None,"total_FF":None,"macro_clock_cap_fF":None,"regional_clock_reset_FF":None,"relay_stations_and_edges":None,"floorplan_capacity_and_die_cost":None,"reason":"source graph design, target placement and original transaction calendar are missing; exact lower bounds above are not a whole-block bill"},
 "calendar_status":{"programme_installed":False,"selected_return_calendar":None,"cross_die_quarter_transport":None,"SE_to_SO_den_epoch_proof":None,"SMJ_job_qframe_count_and_END_lifetime":{"original_PPATH_frames":7,"proposed_combined_frames":24,"additional_SMJ_frames":17,"counterexample":"original attention synthetic END occurs after local P.V, before SO can consume all four quarters. Raising frame count alone cannot define SO completion or denominator lifetime; a separate SO job also lacks a matching END producer without structural change."},"SO_completion_vs_existing_jd":None,"SO_to_group_gather_to_actual_WO_A_RETIRE":None,"SU_latency_edges":None,"MU_occupancy_and_slot_reuse":None,"original_strict_token_failure":"unchanged 1324/2628; no token claim"},
 "checks":{"identity_positive":"PASS8192","causal_negative_rejected":neg,"test_class":"finite Python ABI identity enumeration, not RTL numerical simulation, source timing proof or selected programme replay"}}
(OUT/"model.json").write_text(json.dumps(m,indent=2,sort_keys=True)+"\n")
print("PASS identity8192 / four causal negatives; production calendar HOLD")
