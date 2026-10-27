# HEAD-CORE-R13: elemA / elemB R12b route + signoff collect (2026-10-27)

Kits: elemA `intel1:/srv/opentallas-scratch2/claude/head-core-r10/elemA_hold2`, elemB `epyc2:.../elemB_hold2`
(R10 hold2 GRT repair -> R12 LEC on the repaired export -> R12b route/finish/signoff).
Verdict: **neither core is signed off.** `signoff.py` returned NOT SIGNED on both. Under `set -e` the R12/R12b chains then
stopped before the post-route LEC. That LEC was relaunched at 02:55 (`r12b_route_lec.sh KIT skip-route`).

Sign-off logs are newer than the runs (CHECKED: elemA 6_final.v 02:04:40 < signoff_actual.log 02:20:11; elemB 01:52:10 < 02:06:02).

## Numbers
CHECKED means recomputed with my own OpenSTA census (`nc_tail.tcl`: golden SDC, routed SPEF, propagated clock, all_registers
-clock_pins arrival_max_rise), or read from the raw report files. UNCHECKED means the value is as signoff.py reported it.

| item | elemA | elemB | band / need | label |
|---|---|---|---|---|
| TT setup WNS (reg->reg, clk) | +122.12 / 0 viol | +115.88 / 0 viol | >= 0 | CHECKED |
| FF hold WNS reg->reg (clk) | **-3.38** (6 endpoints, TNS -9.63) | +2.98 / 0 | >= 0 | WNS CHECKED; count UNCHECKED |
| FF hold incl IO, bound-ff vclk 202.5 overlay (verdict) | -3.38 | +2.98 | >= 0 | UNCHECKED (my check had no overlay; with the ideal vclk, IO = A -42.46 / B -27.32, INFO) |
| DRC / antenna | 0 / 0 | 0 / 0 | 0 | CHECKED (5_route_drc.rpt empty; 5_2_route.json) |
| DRV max slew (320 ps) | **TT 8**, FF 0 | **TT 9, FF 1** | 0 | UNCHECKED count; nets probed |
| face_guard | PASS 456/456 | **FAIL: 50 dropped** (row0[16:0], b_v, b_d[31:0]) | PASS | UNCHECKED |
| RCX insertion TT, ft_mstrap_i -> all sinks: mean (min..max) | **228.52** (211.09..242.09), n 28723 | 232.73 (223.79..245.17), n 25983 | 230..270 | CHECKED |
| RCX insertion FF: mean (min..max) | 184.77 (169.38..200.70) | 190.95 (182.05..204.82) | 182.5..222.5 | CHECKED |
| pin-flop insertion TT / FF mean | 229.02 / 184.85 | 234.19 / 192.34 | info | UNCHECKED |
| related-pair skew TT / FF (CPPR) | 29.6 / 26.9 | 25.4 / 24.1 | 80 target | UNCHECKED |
| routed LEC (6_final.v vs r11 RTL) | RUNNING | RUNNING | EQUIVALENT | -- |
| pre-route LEC (repaired export) | EQUIVALENT 30203/30203 | EQUIVALENT 27498/27498 | -- | from R12/HEAD-KITS-1 |

Band verdict (COORD ruling INFRA-FIRST-HEAD-2 ASK2, 12.3a). The core latency is the mean over all sinks.
- elemB: the mean is in band at both TT and FF. The edge W pin is accepted.
- elemA: FF is in band. TT is 1.48 ps under 230, so it is out of band and goes back for a centre re-pin (ASK).

## Root causes
1. **Slew, both cores, same RTL cone.** In each case an INVx1 drives fanout 2: an AND2 next to it, plus an OA21x2 .A1 pin 121-146 um away on one horizontal row (elemA y~237, elemB y~200-206).
   - Routed RCX gives 321-395 ps against the 320 ps limit.
   - The GRT-stage repair_design ran on `rc_cal` estimates scaled down to R 0.8 / C 0.9, so it missed these nets.
   - Fix: the flow must repair slew on unscaled RC, or with a SLEW_MARGIN. In addition, a post-route repair_design + ECO route pass is needed for the residual. These are data nets only.
   - Probe: `slew_probe_tail.tcl`.
2. **elemA FF hold -3.38.** The failing path is a zero-logic pair (1 INV): `u_m.g_m[11].u_m.y[31]` -> `u_m.g_ch[1].g_s[3].u_a.u_c0.g_r.r[38]`.
   - Launch is on the N1 top branch (clock 169.79); capture is on the N0 top branch (190.78). The only common point is `u_isl_root`, so CPPR = 0.18.
   - The edge entry makes the first trunk leg 53-57 ps to every N* node. The N0_2 sub-branch is a further 40 ps leg, while the other branches take 21-27 ps.
   - As a result, the routed all-sink spread is 31 ps on elemA versus 21 ps on elemB.
   - GRT estimated +10.6 for this pair; routed RC moved it by ~14 ps.
   - Structural fix: a centre entry with a symmetric trunk (12.8a/b), which is also needed for the TT band. Also add a post-route data-path hold repair (12.4a a1, HB4 only), which covers the 6 endpoints.
3. **elemB face_guard.** row0/b_v/b_d are PROVEN-DEAD inputs (RTL header; proof results/head_core_lat_r6_1026/elemB/dead_inputs.json).
   - The refreshed face_guard/signoff (main 4983d8e2d) now checks them: 341 bits, where the 10-26 kit guard checked 291.
   - signoff.py refuses data_pin_exemptions, so no declaration path exists.
   - This needs a ruling: remove the ports from the macro (RTL + LEC), or let face_guard accept a declared proven-dead input with its proof (tool change).
4. **Chain stop.** signoff.py exits non-zero on NOT SIGNED, and with `set -e` the post-route LEC never ran. The next chain must run the LEC independently of the verdict.

## Collect (live)
Two jobs are live:
- elemB: epyc2 unit oth-ubuntu-3494190-1793095017.
- elemA: intel1 unit oth-ubuntu-1585112-1793095018.

Logs are at `intel2:/srv/opentallas-scratch2/claude/head-core-r13-elem{A,B}-plec.otrun.log`. To collect, run `grep R12B_ KIT/r12b_chain.log`, then read `KIT.lec_final/lec/lec.json`. The ETA is about 03:45 for B and 04:30 for A.
