DIE-KV-14 (c) KV LOCAL CLOCK FORM = FISHBONE (2026-10-28 17:26 PDT); METHODOLOGY 12.13b / 12.16b(i) / 12.16e.
Cause (DIE-KV-13 width plan on main 013a): 13 FAIL = hgi_ES_k <-> pv_S_k, 6.6-10.0 ns unshared. The KV region graph is a ladder:
each row k is a chain phy_W - hg_W - hgi_W - pv - hgi_E - hg_E - phy_E, with vertical links on the pv columns (4.8-7.5k bits),
hg columns (2.4k) and phy columns (1.4k+0.7k). The DIE-KV-11 re-tree hung the pv_S column from hub_C and the hg_ES column from
root phy_ES_0, so every row rung hgi_ES_k->pv_S_k closed a loop through the root.  Moving only hgi_ES_k under pv_S_k (the
literal ask) breaks the heavier hg_ES_k<->hgi_ES_k link (2.7k bits) the same way.  Clock-follows-data form: SPINE = the pv_S/pv_N
columns from hub_C, each ROW a RIB pv_k -> hgi_k -> hg_k -> phy_k on both sides (ovr_all.json; retree2.py = DIE-KV-11 retree.py
+ parent overrides + hard-cap key, run with NOSEARCH=1; the edge-swap search only made the worst link longer, fb2_all_0.log).
ESTIMATE (locality.score + cap_reading, clock_variation table; estimate_fishbone.log) DIE-KV-11 re-tree -> fishbone:
  worst unshared (score) 9.61 -> 2.51 ns; max a+b over ALL crossings 4.51 ns (phy column verticals; was 10.3);
  hgi_ES<->pv_S now tree edges (a+b <= 430 ps, margin >= 727); D4/D8/FAIL 3551/44/0 -> 3595/0/0; min margin 111.3 -> 126.0;
  chain 23 hops/13.36 ns -> 12 hops/6.59 ns; tracks worst 0.718 unchanged; bit-cycles 1.316M -> 1.383M (+5 %, ring flops).
BUILD (DIE-KV-12 recipe, kit2/chain2/grt/ca.sh here; die_trial qc11 archive, inv, rep 150, tap pads pad_it2; tools = wt/die-kv-14):
  1920 taps, 5949 repeaters, feed 195.3 mm (KV-11 201.9); render clock_tree_fishbone.png VIEWED (two central spines, one rib per
  row out to the phy edge columns, no stray wire); combo GRT0 incl clock TT/FF overflow 0, usage 2.37 %;
  duty TT 47.2-52.6 % / FF 47.7-51.3 %, 0 outside 45-55.
GATE (main count_align_bind + die_sta_related, clock_variation table, spice, cppr-lca, shared droop, inv, FF 202.5, HB4):
  start-clean width: CA TT/FF fail 0 (min 106.5 / 108.4 ps), D4/D8 2710/885, sim min 105.2, 0 window violations  [was 13 FAIL]
  start-clean phase: CA TT/FF fail 0 (min 106.5 / 108.4), D4/D8 3379/216, sim min 105.2/110.6
  START-SKEW: width 38/127 (TT,FF) = the 32 rib-end hg->phy start edges (d width 300-450 ps, long edge spurs) + 6;
              phase 12/167 TT, 7/167 FF (KV-12 0/189): hroot_WN/WS, sys_SE/SW, phy_ES_*, phy_EN_*, pv_S_7 start stages; plan and gate
              intervals agree (same d), so the start-stage placement on the shorter tree needs a re-plan: OPEN.
  intra FF kit-contract hold -62.8 (KV-13 -76.5); landed class = plan-defined forwarded form (as baseline).
Run data: intel1:/srv/opentallas-scratch2/claude/die-kv-14-1028 (kit_fb_inv_r150, out_fb_inv_r150_*, proof_*, ca_*, sta_*).
START-TREE FIX (17:32 PDT): the 12/7 phase start-skew fails were rise-only samples (FLOW-ONEMODEL-1 fail-closed: a proof without
measured fall loses fall-edge start samples).  tap_fall_merge.py (main, tap deltas from the duty readout, TT then FF) -> proofF_fb;
st2.sh fall (phase, same options): 27 fall tree edges, CA TT/FF fail 0 (min 106.5/108.4), START-SKEW 0/156 TT and FF -> COUNT-ALIGN
PASS both corners (sta_start_fall_ca_lines.txt).  retime-up / start-skew-clean on the rise proof did not help (ru 12/7, rusk 18/18).
Gate of record for the KV clock = phase start, proofF_fb (both edges at taps; tree-node falls not in the readout, stay rise-only).
