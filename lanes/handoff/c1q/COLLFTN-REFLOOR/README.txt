QC-COLLFTN-REFLOOR row v3 for C1q (coll_ftn re-floor), base C1p R6 plan de1cef5cf59d (sealed E10 kw45/snap_qwen_compute/qwen_compute_c1p_r6_1125).
Result plan sha256 155f0ffc9c8c9ee9cab4fa33435ddd369b3f6cc8c18a486f0efd5353225b27e5 (E10 /srv/opentallas-scratch2/claude/QC-COLLFTN-REFLOOR/tree/physical/die_plan/qwen_compute/plan_of_record/zz_c1q_collftn_refloor_1125.json).
row_patch_v3.json = exact key ops base -> result (self-check APPLY_EQUAL True). Keys: partition_types.coll_ftn, die.channels (+1 rect), reset.in_sites.coll_ftn, clock.tap_offset.per_port_ps.coll_ftn.
New tree file: physical/die_plan/qwen_compute/plan_of_record/sink_bins/hf1c/coll_ftn_c1q_refloor.json (= coll_ftn_c1q_refloor.json here).
Recipe: collftn_row.py (v2: outline 786.24->432, channel, root 129.6) -> collftn_v3.py (E-face reset/monitor block -354.24, bins) -> retap.py BASE V3PRE OUT --types coll_ftn --republish-reset (v3.sh). Guard: compose_drop_guard --drop-list drops_v3.txt PASS 0 silent (23 intended).
