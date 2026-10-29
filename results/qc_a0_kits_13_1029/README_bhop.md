# QC-A0-KITS-13 10-29: A0 clock-gate B-hop RTL (COORD ruling d) + NL ICG0 `-overflow 0.21` placement (ruling b)

Branch `claude/qc-a0-icg-bhop-1029`, based on origin/main a4453d4004d.
- The results-only branch is `claude/qc-a0-kits-13-1029@b95168042` (README §1-3: the estimates).

## 1. B-hop RTL (ICG = 2, opt-in; the default ICG = 0 is unchanged)
- New file `rtl/physical/a0_core/ot_a0_icg_hop.sv`, with `keep_hierarchy`.
  - It holds one ICGx8DC per clock entry.
  - Its ENA is the tile `en` relayed through K FFs on the ungated `ck`.
  - The hops are async-set to 1 in reset, so every gate is open during reset, as in the root form.
  - Simulation only: `xk` adds one extra hop, used for the bench mutants.
- `qfd_tile_n{l,k}_a0c.sv`:
  - `ICG == 1` keeps the DIE-QC-16 tile-root gate (block `g_root`).
  - `ICG == 2` (block `g_hop`) gives one gate per entry: NL has 34, NK has 36.
  - New parameters set the relay depth per entry. Each must satisfy K <= s - 1:
    - `ICG_K_CK` = 0
    - `ICG_K_RP` = 2
    - `ICG_K_RQ` = 2 (rsw/rnw/dw/de/rs/rn)
    - `ICG_K_TX` = 2
    - `ICG_K_LSL` = 2
    - `ICG_K_FA2`: NL 2, NK 0
    - NK only: `ICG_K_FA3` = 0, `ICG_K_NODE` = 0
- The tile enable logic (go_f/go_h/me_idle/nv/rst/dr) is untouched. Turn-off is delayed by K, which only adds clock edges.
- Bench: `tools/qwen_romleaf/a0core/icg/` gains `TB_ICG` (`ICG=2 build.sh ...`).
  - `build.sh` adds the hop file.
  - Default `TB_ICG = 1`, so the Codex bench is unchanged.
  - Kits that build ICG = 2 must add `rtl/physical/a0_core/ot_a0_icg_hop.sv` to SRCS.

### Bound s (bhop/entry_depth.py, bhop/*_entry_depth.json, CHECKED)
- Method:
  - yosys flatten of the body, kit RTL, REGROOT 3.
  - For each body clock entry: the minimum number of gated register stages from the ungated domain (ck_fa4, NK also ck_fa0/ck_fa1, plus body inputs except rst_n/tile_id).
  - Register submodules and hard children are counted as registers on their entry.

| entry | NL s | NK s | K chosen |
|---|---|---|---|
| ck (body main) | 1 | 1 | 0 |
| ck_rp0..9 (romleaf) | 3 | 3 | 2 |
| ck_rsw/rnw/dw/de/rqr0/1 | 4 | 4 | 2 |
| ck_tx0..7 | 5 | 5 | 2 |
| ck_lsl0..7 (rawleaf) | 7 | 7 | 2 |
| ck_fa2 (t_out face) | 5 | 1 | 2 / 0 |
| ck_fa3, ck_node (NK) | - | 1 | 0 |

- Consequence: the main body clock and the NK node/output faces must take the enable with zero relay (K = 0).
  - Their gate copies must sit near the enable sources: E face for go/rst, W face for nv in V1.
  - Only the ROM/RQR/TX/LSL clusters can take the relayed (far) form.
  - Whether the K = 0 gates meet the ~590-ps enable budget is UNCHECKED until a placed build with ICG = 2.

## 2. Proof (bhop/bench/*, verilator 5.050, 12,000 cycles, valid-qualified operational miter ICG=0 vs ICG=2)

| case | NL | NK |
|---|---|---|
| 0 design | **PASS 0** (gated 6647 = 55%, wakeups 10) | **PASS 0** (gated 6073 = 50%, wakeups 11) |
| 9 control (en = 1) | strict 0 | strict 0 |
| **7 every hop +1 (ck K 0 -> 1 > s-1)** | **CAUGHT 4156** | **CAUGHT 4157** |
| 8 ROM-pair hops +1 (K 2 -> 3 = s) | PASS (not caught) | PASS (not caught) |
| 1 no lead | CAUGHT 4156 | CAUGHT 4156 |
| 2 ~me_idle dropped | CAUGHT 10460 | CAUGHT 9847 |
| 3 drain dropped | **PASS (was CAUGHT 6054 at ICG=1)** | CAUGHT 5285 |
| 4 nv dropped | n/a | CAUGHT 733 |
| 5 reset term dropped | CAUGHT 996 | CAUGHT 5000 |
| 6 go hold dropped | PASS (equivalent, as ICG=1) | PASS (equivalent) |

- LEC (yosys, `bhop/lec_main.sh`):
  - main vs branch ICG = 0: EQUIVALENT. NL 517 and NK 1031 $equiv cells proven.
  - The .tile_id mutant is NOT EQUIVALENT (16).
  - `lec.sh` on main no longer applies: its me_idle gold hook is stale since QC-PG-5. `lec_main.sh` is the same recipe without the hook.
- ICG = 2 elaborates under -DSYNTHESIS:
  - NL: 1 K0 hop + 33 K2 hops = 34 ICG, 66 relay FFs.
  - NK: 4 K0 + 32 K2 = 36 ICG, 64 relay FFs.
- Notes:
  - Mutant 8 survives: the static s = 3 bound of the romleaf entries is conservative under this stimulus (the first ROM read comes later than the 3-stage path). K = 2 rests on the structural bound, not on the bench.
  - The NL mutant 3 (drain) is no longer caught. The relayed clusters (fa2/tx/lsl, K = 2) now cover the NL tail without dr, so the bench does not prove ICG_DRAIN in NL under B-hop. NK still catches it.

## 3. NL ICG0 one run with `GLOBAL_PLACEMENT_ARGS=-overflow 0.21` (ruling b; exact kit copy, CHECKED)
- GPL converged at overflow 0.2070, iteration 4824, HPWL 1.81e6. There was no GPL-0323/0998/0999 divergence revert, which the 0.20 target had hit twice.
  - Routability final weighted congestion 1.0842. Runtime 1556 s, 8 threads.
- Detailed placement: legal, HPWL 2,428,282 um.
- AUTO-GEOM on 3_place (`nl_ov21/auto_geom.json`), compared with the reset6 reference 3_place of the same tile (`r6_auto_geom.json`):

| metric | ov21 ICG0 | reset6 ref |
|---|---|---|
| r2r max (count >405) | 405.38 (1) | 404.35 (0) |
| channel_h / channel_v / col_v | 1.171 / 2.53 / 2.368 | 1.128 / 2.866 / 2.401 |
| pin_reg_max / pin_unreg | 145.16 / 0 | 143.52 / 0 |
| clock_reach (pre-CTS) | 762 | 763 |

- The single r2r is `u_me.s2_x[105] -> g_sl[5] u_tx q[105]`, +0.38 um over 405.
- The other FAILs (aspect, partial_face, channel/col estimates, pre-CTS clock_reach) are the same classes as the reference.
- Not visually reviewed.
- ODB: intel2 `/srv/opentallas-scratch2/claude/qc-a0-kits-13-1029/nl_icg0_r6/run/results/asap7/kq_qfd_tile_nl_a0c_a0nl12icg0typed/base/3_place.odb`.
