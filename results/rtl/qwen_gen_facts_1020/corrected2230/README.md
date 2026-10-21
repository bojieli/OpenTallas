Corrected production GEN safety diagnosis, 2026-10-20.

Actual immutable GEN: ep6 /srv/opentallas-scratch/claude/codex-qw-reset-inputs2230,
base production g5r2b geometry plus reset-input repair ed5b5c214 and exporter
6926a4cc8. Source/input/netlist SHA256 values are in diagnosis.json. This GEN
completed with RESET_SYNC_AUDIT PASS, 13,761 repeaters, five endpoints, zero
untreated foreign-domain resets. This repairs the earlier two specific
forwarded-clock reset hops; it does not establish regional reset safety.

The original GEN safety failure is preserved: C1=550, C2=8, W1=0, W2=0.
The derived audit uses the actual emitted netlist to correct seven clock-alias
lookups and to describe the existing qfd_rstsync.arst_n package synchronizer.
It also stitches actual qfd_rst_rep q0..q7 branches through the full reset trees,
rather than assuming a nonexistent q output. These exporter fixes are source
commit 3fe1d74c8, validated by 19 small Python tests. No new GEN was launched.

Derived result remains FAIL: C1=543/1,562 crossings, C2=0, W1=0, W2=0,
3,103 complete data/reset chains, maximum hop 385.6 um. Every input segment has
actual corresponding generated-bit geometry: centroid_only_segments=0. All
14,841 actual relay/reset frame footprints lie completely within the 608
hard-block/keepout-free channel rectangles (uncovered_frames=0). Thus no channel
or 405-um hop defect was found on this plan. This does not qualify detailed
cell/via occupancy, routed pin timing, or the die.

Remaining C1 targets are real source/clock connections, retained without a waiver:

* 521 regional reset connections: 384 distinct source leaf repeaters and 95
  destinations; 470 connections target c16 clusters. Example: rstt_rst_field_20
  clock root188 feeds c16_W5_3/rst_c0r2 and rst_c1r2, both clocked on root3.
  rstt_rst_field_3 root1118 feeds rly_dvw_ss_wo_0/en clocked on root143. The
  complete source/root/destination/actual-port list is diagnosis.json.
* 20 direct E0/E1 data connections: actual dvs_E0 root95 and dvs_E1 root121,
  including dvs_E1/l9_eo -> dvs_E0/l9_wi. No emitted lane landing ring exists.
* ucie_up is driven on clk_ucie and sampled by face0 codec root clk_coll. RTL
  tracing reaches raw p_tx_up in new_fault at
  rtl/qwen_sys/split_20261014/ot_qwen_static_slot_link.sv:60. No input
  synchronizer was found along that wrapper path. It remains a source fix target.
* lnk_fwd_lrst is a forwarded-reset lane with a final rlyrl capture, not a
  landing ring. Its actual source-feed contract is explicitly physically
  unqualified. D2D fwd_link_rst_n has a single q input register in the pinned
  ot_qwen_d2d_dies.sv:405-408. Qualification/synchronization remains owed.

Affected reset-root multiplicity counts only currently failing destinations:
324 leaves have one affected target root, 59 have two, one has five. A leaf may
also feed currently same-root sinks; inspect all outgoing sinks before rehoming.
The parent Qwen lead owns reset source repair; this work changes only the
exporter and preserves actual evidence.

Reproduce the post-GEN audit, with output to a new directory:
  PYTHONPATH=tools/qwen_split:tools/die_safety python3 results/rtl/qwen_gen_facts_1020/corrected2230/audit_existing_gen.py --gen GEN_DIR --out NEW_DIR

Full derived facts remain on the fleet at
/srv/opentallas-scratch/claude/codex-qw-facts-audit2240/out/derived_facts.json;
SHA256SUMS pins them and all audit tool/output files. Only compact reports and
source-level target records are committed here. No original failure was replaced.
