# S81-TYPEMERGE-IMPL handoff (2026-11-15 ~08:0x PST)
Branch hub:OpenTallas claude/s81-typemerge-impl-1115 @410761b21b (tools/fleet/col_typemerge.py, test_col_typemerge.py, col_inherit.py --merge-classes). Work dir epyc7 /srv/opentallas-scratch2/claude/s81-typemerge (wt = clone).
## Done
- R1: col_inherit.groups(merge_classes=True): key = (family, clock key without cl/pv labels); col_typemerge.py groups = sibling groups (13) and layout hashes.
- R2: col_typemerge.py depth: ring DEPTH (hence strap_ca_k_* width = log2(DEPTH)+4) = max over sibling group per bus, edit of count_aligned.ports[*].depth only (K, sched_lat, regions unchanged). 89 ports raised on 40 col r0 types. FINDING: the 6 vs 7 bit strap width is NOT only a port width; it follows ring DEPTH 4 vs 8 (strap_kw = bit_length(depth)-1+4), so unifying means the depth-4 pv siblings get a DEPTH-8 ring (count window wider, more slot flops; ring band footprint formula ca_ring_flops is width-only).
- R4: col_typemerge.py taps: core taps of a sibling group take the group modal xy: 132 taps on 24 types, max move 15.66 um.
- Chain: TYM1 = B6gsl + R4 taps + R2 table + CA compose (chain_ca_92.sh, ot-run --priority plan on epyc7). Compose OK, cycles unchanged (clock_landing sum 2992, cycles sum 14021 = B6gslcf), G0 same 7 schema errors as B6gslcf.
## Counts (col layout hashes)
B6gsl 29, B6gslcf 79, TYM1 76 (r0 families 1-8 each, h9_r1 9, h9_r2 17, h10_r1 3, h10_r2 5). Remaining spread = reset collector tree + monitor entry sites + plain/collector form (R3a/R3b).
## Open
- R3a NOT implemented: the entry sites are the reset-tree outputs to neighbour partitions (RT.wf_plan outs, rst_n_t<consumer_count+k>), so a union means a reset-tree change, not a monitor band option. Needs a design call.
- bind result of TYM1 pending (log s81-b3-clk/log/TYM1.log); B6gslcf and B6gshcf both fail bind on bk_sel__t2 EMIT fclk_out_tl_o0 source_clock_port clk_t2 (DIE-S81-92 owns).
- signed col types: no col type in RMINIMAL-SIGNED/PROFILE-1-SIGNED; only core LOCAL_PASS_NEEDS_PARENT rows for col_h9_r0_p1/p4/p5. ROM image to GDS: tools/mem_compiler/rom_gen.py emits no GDS (LEF, Liberty, model only); per-instance via map <INSTANCE>.viamap.hex must be applied at die assembly, no tool for it yet.
