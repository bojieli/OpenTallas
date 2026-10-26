Q-ATTN r3 (Claude, 2026-10-15): root cause and fix of the static native attention service FIRST_FAULT age 99.

Two composition defects, both in the native QK engine binding (ECTL3 static + nativehead_r4), found with observers:
1. ROW_RETURN_LAT. ECTL observer (build_dbg_ectl.sh: qkd_ectl3_epoch_direct_s_d from real source with QATTN_ECTL_DBG
   fault-term/age displays, everything else the pinned b4 libraries) shows in every engine of all 4 stacks a ring
   fault at engine age 23: write_valid=1 with write_slot=0. rq_valid at age 1, row at the control copy at age 22:
   the true round trip is K_EXT + 2 request relays (RQD) + 3 response pin stages = K_EXT+5 = 21, the service had
   K_EXT+6 = 22 (tools/qwen_kv_die/static_qk_calendar.py already derives row_latency+5). With 21 the fault is gone.
2. HXK. With the fault gone the output was wrong in all 512 words. Service observer (QATTN_SVC_DBG in
   ot_qwen_tp8_attention_native_service.sv here) + Python reference (ref_intermediates.py, zblock_compare.py):
   lmax exact, but every Z block labelled round k equals the reference block of round k-1 (round 0 junk, round 15
   lost): each score reached the EP tagged with the position 8 issues (one KV round) earlier. The ECTL K-pass tag
   delay SCD assumes a flat head (HXK=0); the hierarchical native head ot_qkh_head_native_r4 adds
   NRS1+NRI2+NRK2+3 = 8 edges. Fix: HXK parameter through qkd_ectl3_epoch_direct_s and its A/B/C leaves into
   ot_qkd_ectl_part, bound to 8 (HEAD_SCORE_HXK) in ot_qwen_tp8_attention_native_stack (source branch
   codex/q-native-attention-1014). Leaf C physical master grows by the deeper tag delay (13 b x 8 flops).

build_fix.sh: production composition (no debug defines): ECTL3 library rebuilt from the b4 file list at
ROW_RETURN_LAT=21/HXK=8, stack_cp from Codex cp_minimal with the REAL b4 ctl library, b4 EP/ER/EX/ZN/head libraries,
Codex min-parent with the stack library swapped. run_fix.sh runs the unchanged bench. Calendar for T=8192:
124e124e124e05aa07bc076c06af032705aa03200352 (P0=P1=R=4686 = measured pair output age; others = Codex generous
discovery ages). Results: see receipt.json.
