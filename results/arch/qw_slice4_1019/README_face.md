# QW-SLICE4 10-19: slice<->slice landings inside the receiving dv_slice2 face

Generator: `tools/qwen_dv/slice_face_landings.py --relay-stages <GEN p2/relay_stages.json>` (landing list read from
origin/claude/qw-gen3-1019 results/arch/qw_dieclk2_1019/landing_list.json; relay_stages = dv2f19g3r p2, sha256 e047322d...;
master facts from the CLOSED views on origin/main). Output: `slice_face_landings.json`.

- 182 links / 50,267 bits (rows with src AND dst master qfd_dv_slice2_*), 20 face port groups (one per (src, dst) instance
  pair = one new ck_s input each). Receiving face from the receiver port suffix: 91 on the W face (_wi), 91 on the E face (_ei).
- Masters: 81 links <= 32 b -> LAND8 D8 hop-0 `qfd_landh0d8_{1,3,10,32}_EW_*` (ICG main, `qfd_landh0d8n_*` no-ICG
  fallback; die-chosen L, nominal 3); 101 links > 32 b -> 250 narrow pairs `qfd_c_land_w258/r258_narrow`
  (514 b -> 257 pair), E = K = 2, +3 edges.
- Totals (all 12 instances): ~377k flops, 4.23 mm2 (list estimate 374k / 4.21 mm2).
- Per MASTER (union over its instances, bus names without the instance index): qfd_dv_slice2_e 24 landings, 54.1k ff,
  0.608 mm2; qfd_dv_slice2_w 22 landings, 49.7k ff, 0.557 mm2. Each gets 2 new clock inputs ck_s_wi / ck_s_ei
  (+ en_s released-reset pin per face group); data pins unchanged.
- Price: the dv chain is a line of 10 landed slice edges (E1..E5, E0<->W0, W0..W5; E0<->E1 share root pll_r95, not
  landed): one pass +30 cycles/layer, x36 = +1,080 cycles/token = 0.9 us/token at 1.2 GHz. The list's worst case (11 hops,
  +33/layer) is already inside its 45 cycles/layer; not additional.
- Where they get built: in the slice2 face parent of the structural redesign. The slice2_e / slice2_wh --cts gates of
  record (MU-DQ-SLICEKC, ref_gate/*-20261019-042253) FAILED: a flat 174k-flop core on one root; CTS / GRT rc 137.
  Until that parent exists, the 182 rows stay owed.
