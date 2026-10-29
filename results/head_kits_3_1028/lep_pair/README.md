# HEAD-KITS-3: ot_s81hd_lep_pair core kit (2026-10-28 22:59 PDT)

Driver: tools/s81_head/head_lep_pair_kit.py (die-local; imports the shared gen_core_kit_hbm.py unchanged).
Kit: intel2:/srv/opentallas-scratch2/claude/head-kits-3/kits/ot_s81hd_lep_pair_kit (kit_hash 8317e3737ea832b4,
2142 pins, clock clk, reset rst_n, 55 SRAM macros, outline 388.8 x 432 um).

## Status: kit built, preflight PASS; sign-off BLOCKED at face_guard (RTL item)

| check | result | label |
|---|---|---|
| kit_preflight | PASS, 0 issues (2nd floorplan; DIE-HEAD-9 packing failed macro_channels + clock_entry_clear) | CHECKED |
| rtl_lint | PASS with defines OT_COLL_NATIVE32 + OT_COLL_NATIVE32_OFF (HEAD link profile); FAIL without (nxt_rw2 undeclared, ep_safe4.sv:401) | CHECKED |
| port_bind | PASS (0 missing, 0 extra) | CHECKED |
| SELRANGE | rc 0 | CHECKED |
| face_guard | FAIL: 1584/2140 ok, 556 bits class "shared" | CHECKED |
| LEC | first run UNPROVEN (slang refused TOP_PARAMS CHB=1'b1); driver now drops the override (RTL default is 1'b1); rerun running: docker hk3-lep-lec on intel2, collect diag/ot_s81hd_lep_pair_diag/lec/lec.json + lec_run2.log | UNCHECKED |
| place (diagnostic, face_guard bypassed) | 108,269 cells, 28,021 flops, fill 19% of free, max bin 0.60, 0 bins > 0.8, pin->reg p90 6.1 um | CHECKED (render viewed) |

## Clock entry for DIE-HEAD-21 (plan has no clk pin on lep_pair)
clk = interior M5 port 0.048 x 0.48 um at (194.52, 216.0), two M5 tracks east of the centre rst_n (194.424, 216.0).
The driver's SRAM site table (6 x 256x64 rows in 6 columns + 7 x 32x64 top rows + 5 x 32x64 centre column)
replaces the DIE-HEAD-9 packing estimate; the plan should adopt both.

## face_guard blocker (RTL, not hacked)
Ports k_lo_v, k_lo_d[552:0], k_li_r, k_rxv (556 bits) each load 4 cells inside
u_land.u_kn.u_w.g_chunk[*].u_local (ot_s81_mu72_lnland -> ot_pl_land_vector_reset_kw_w): the D=4 landing
bank write logic (AO21 enable muxes), not a pin register. Neither declared landing-slot form matches:
- land_slots D=4 form icg: "load AO21x1 ... is not a slot flop D pin"
- land_slots D=4 form hold_mux: "write conditions not mutually exclusive"
Proposed default: the landing RTL owner (S81 mu72 lnland) either adds one face flop per input bit ahead of the
bank (+1 cycle, needs the token budget) or recodes the kw_w write enables as one-hot per slot so the hold_mux
slot form proves; until then lep_pair cannot sign off.

Render: lep_pair_place.png (viewed: macros on the planned grid, channels open, clk entry in the clear centre column
gap; face logic clusters along the W face).
