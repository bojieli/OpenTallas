# MU-S81/LINK, 2026-10-18: user tag, second h landing, and copy-A/B transmit at the S81 end-slice link

Lane MU-S81 (owner MU.DECIDE option A, HANDOFF 0is). Items MU.S81.BUF (link part) and MU.S81.L20 (RTL part).
Branch `claude/mu-s81-link-1018`. Every feature is behind a parameter that defaults to off.

## What was built

| item | where | form |
|---|---|---|
| (a) user tag on the stage h message | `ot_s81sl_lep_core` (MU_EN = 1), top `ot_s81sl_lep_mu` | The tag uses spare XB/XQ beat bits [1077:1045], so it needs 0 new ring or link wires. The layout is [1045] tag, [1046] land, [1056:1047] user, [1077:1057] pos. The compiler opens a TX window with `mu_c` = {pos 21, user 10, land, ab, v}. The next NB outbound ring beats are stamped in the frame mux, with no added cycle. On RX the tag is stripped from `ri`, so `ri` is bit-identical to single-user, and it is driven on `mu_rt` = {v, user, pos} in the same cycle as the beat. |
| (b) 2nd h landing | NEW leaf `dsdv_mu_land` (beside each end-slice lep) | Tagged beats with land = 1 fill one slot (NB beats, one {user, pos}). The compiler replays the slot with `rc` = {user, v}. Replay starts 4 edges after `rc`, then runs at one beat a cycle and merges into `ri` through lep pin flops. Faults (all sticky): a write to a full slot, a foreign tag in a partly filled slot, a replay of an empty, partial or wrong-user slot, a replay against a cut-through beat. |
| (c) copy A/B transmit | `ot_s81sl_lep_core` (AB_EN = 1) + cluster `ot_s81sl_slice_lep` (AB_EN = 1: 2 more `dsfd_coll_lane_*` tiles) | A second lane pair forms a second static circuit. A window opened with ab = 1 goes on pair B; every other frame stays on pair A. User 0 is always on A in hardware: ab = 1 with user 0, or ab = 1 at AB_EN = 0, raises a fault and the beats go to A. Pair B RX merges into `ri`; both pairs releasing in one cycle is a fault. |

**MTP wavefront landing: not reusable (0 mm² is not available).**
- The DV die has no wavefront landing.
- The stage h lands straight in the 80 `ot_s81sl_vn` h stores, and those stores are the resident residual for the whole stage.

**Physical form of A/B: a second static circuit, not a destination field.**
- The lane tile's reliable link layer (`ot_s81ph_link_ep`: seq, CRC, go-back-N, credits) runs end to end per peer pair across the switch. It is HF-3 FROZEN.
- A destination field would alternate one endpoint's frames between two peers. That mixes two sequence spaces, so it would need a per-destination link layer inside the frozen tile.
- The second circuit instead reuses the closed lane tile unchanged, on a spare switch plane. This costs 2 more PHY lanes on the endpoints that carry the hop on the 8 pre-group and 8 post-group stages (S029 S020 S011 S002 S034 S040 S046 S052).

## Benches (Verilator 5.050, ot-epyc4)

Script: `rtl/dsrom_sys/s81_dv/slice/test/run_lep_mu_bench.sh` (base / mut / regr) and `lint_lep_mu.sh`.

**Vehicle `tb_s81sl_lep_mu`:**
- Die P is the pre-group stage: AB_EN 1, with 4 lane tiles and 4 UCIe macros.
- Dies A and B are the two copies, each `ot_s81sl_lep_mu` + `dsdv_mu_land` (NB 80, SRAM macros).
- RP → RA is the single-user reference built from the pre-MU `ot_s81sl_lep_nh` tops.
- Six users run on a static calendar:
  - u0: copy A, cut-through (the latency user)
  - u1: copy B, land
  - u2: copy A, land
  - u3: copy B, cut-through
  - u4: copy B, land (reusing the slot freed by u1's replay)
  - u5: copy A, cut-through
- Background untagged ring beats also run.

| run | result |
|---|---|
| `pass_lep_mu_seed1.log`, `pass_lep_mu_seed5.log` | PASS. 280 + 240 beats bit-exact with tags. User 0 is cycle- and bit-identical to the single-user run (120 beats). No main-phase fault. F1 (full slot), F2 (empty replay) and F3 (ab for user 0) all faulted. |
| `witness_tagdrop.log` (OT_S81SL_LEP_MUT_TAGDROP) | FAIL as required: 640 mismatches, user identity lost |
| `witness_wrongcopy.log` (OT_S81SL_LEP_MUT_WRONGCOPY) | FAIL as required: B received 0/240 |
| `witness_ovr.log` (OT_DSDV_MU_LAND_MUT_OVR) | FAIL as required: the full-slot write was not faulted |
| `regr_lep_s1/s7`, `regr_nh_s1`, `regr_host_s3` | PASS: the pre-MU benches still pass on the refactored file (MU_EN 0 tops) |
| `regr_swap.log` | FAIL as required (old mutant still detected) |
| `lint/` | 0 errors on lep, lep_nh, lep_mu (two variants), land (128 / 256), MU cluster W+AB and E+host, and the 3 die masters |

## Tiles, closure, area

- **Changed RTL text:** `rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv`.
  - The logic moved into `ot_s81sl_lep_core`.
  - `ot_s81sl_lep` and `ot_s81sl_lep_nh` are now wrappers with the same ports, at MU_EN 0 and AB_EN 0, so their function is unchanged (regression benches above).
  - New in the file: the top `ot_s81sl_lep_mu`, and MU_EN/AB_EN parameters plus MU ports on the cluster `ot_s81sl_slice_lep`. The 3 die masters tie those ports to 0, and they are unread.
- **Kits touched by the source change:** s81sl_lep and s81sl_lepnh, both UNCLOSED and in gating since S81-SLICEP 10-18 18:10. Their function is identical, but the source sha changes. Merge after those gates, or re-gate.
- **No CLOSED tile changes and none needs to re-close:**
  - `dsfd_coll_lane_w/e` (HF-3) is untouched. AB adds 2 more instances of the closed kit.
  - `ot_s81sl_slice`, `vq` and `vn` are untouched.
- **New leaves without kits (owed):**
  - `dsdv_mu_land`: 5 × ot_sram_1r1w_128x256 (0.0195 mm² of macros per lep, ≤ 0.078 mm² per die). That is above the README's 0.021 mm² because it stores 1,104-b beats and the macros are coarse.
  - `ot_s81sl_lep_mu`: with AB the W face doubles to about 4.4k pins. That needs a taller outline (≥ 760 µm at 6/µm), or the B lanes go on the S face, and 10 more TX SRAM macros.
- **Die wiring owed (S81-DIE8 / MU-S81-HOST):**
  - `mu_c` (34 b) and `mu_rc` (11 b) from seq_host's calendar program to each MU end slice.
  - `mu_rt` (32 b) back to seq_host for base selection.
  - Pre- and post-group die masters with AB, plus 2 PHY lanes per AB endpoint.
