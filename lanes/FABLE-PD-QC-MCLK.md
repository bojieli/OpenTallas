# FABLE-PD-QC-MCLK: QC cbn_q01 hold class (21,431 pairs) and the S4q9m clock chain

2026-11-16 20:2x PST. Technical PD review, read only. MEASURED = my own FF STA read of the failed kit's post-CTS DB
(epyc2 `/srv/opentallas-scratch3/claude/fable-pd-qc-mclk`: `sta.tcl`, `sta.log`, `rows.tsv` = all 21,467 violating paths;
kit `kw43-wave-1109n/.../s29q103S4Q6D/items/cbn_q01__clab6e67f2`, job cee3540cfd65; same frame as the kit hold gate:
4_cts.odb, 4_cts.sdc + core_taps_ff.sdc, FF libs, placement RC). My read reproduces the kit: wns -211.66, 21,467 endpoints.
PROJECTED = recomputed from those rows with other tap tolerances; not a new build.

## 0. Verdict

**It is not a half-cycle class.** It is a same-edge (rise -> rise) cross-tap hold class made by the width of the
per-port tap windows in the kit SDC. The S4q9m clock rows (one tree per type + SPEF readout) remove about 92 % of it.
The S4q9l2 rows do not remove it. One kit-tool rule (lockup latch on its launch tap) and ordinary hold repair take the rest.

## 1. What creates it (MEASURED)

| item | number |
|---|---|
| violating paths | 21,467 = cross-tap 21,431, same-tap 34, input port 2 |
| launch / capture edge | all 21,465 register paths: clk rise -> clk rise. 0 falling-edge flops, 0 inverted taps, 0 fclk paths |
| endpoint cells | flops 20,244; lockup latches (DLL, `u_lk_nk_*`) 1,187 |
| tap-port pairs involved | 316 (135 taps in the type) |
| per-port window in the kit FF SDC (late - early) | 63 .. 248 ps, median 135 |
| window term on a pair = late(capture port) - early(launch port) | 66.7 .. 243.7 ps, median 144.2 |
| mid-offset difference between the two ports | -22.1 .. +26.5 ps |

Worst path (-211.66): `u_pc_nk_u_t_0_2_tap.q[337]` on clk_t35 (source latency early -124.1) ->
`u_lk_nk_u_t_0_2_tap/q[337]` (DLLx1) on clk_t31 (late +98.6). Window term 222.7 ps + 25 ps hold uncertainty.
The two local trees are equal (125.7 vs 127.9 ps); data path 42 ps; CRPR 0 because the two ports share nothing.
With the window term removed the same path has +11 ps.

So: no negedge landing, no inverted tap, no opposite-edge seam, no CA / K choice. The negative-level latch is only the
endpoint cell. Its D check is the ordinary same-edge check and it crosses a tap port because the latch is not hung on the tap
of the register that drives it: `clock_taps.tcl` re-hangs hop latches `u_fl_*` / `u_fx_*` on their launch tap, the NK
core-input lockup latches `u_lk_nk_*` are not in that rule.

Cause of the wide windows: plan `clock.tap_offset.per_port_ps` tol = same-type instance half range. For this type that is
65.7 ps on the GRT readout and <= 0.3 ps on the exact SPEF readout of the templated trees (s4q9m_r `reg/tol.log`).
The window is the GRT gcell-phase artefact FABLE-DIE-QC-R already measured, carried into every cb kit SDC.

Why repair did not fix it: the pre-GRT pass did work (endpoints 21,467 -> 2,707, TNS -1.26 us -> -78 ns, 36,093 buffers),
but the worst latch endpoint stayed at -211.66 and the WNS-only accept test discarded all of it. The in-flow GRT repair then
added about 2 buffers per iteration (890 at iteration 450, 23,019 endpoints open) until the 12 h cap. Its cross-tap guard
was off ("no tap window lines in the kit SDC": it does not read the per-port offset lines).

## 2. What removes it (PROJECTED on the 21,431 measured pairs)

| clock rows for cbn_q01__clab6e67f2 | tol per port | pairs left | worst |
|---|---|---|---|
| kit as built (S4q6d rows) | 31 .. 124 | 21,431 | -211.7 |
| S4q9l2 rows (tol = GRT half range + 10) | 41.6 .. 134.1, median 77.6 | about 20,037 (at 76) | -211.6 |
| S4q9m rows (template=2 + SPEF, tol = 0.3 + 10) | 11 | **1,707** | -81.6 |
| S4q9m rows + `u_lk_nk_*` on the launch tap | 11 | **707** (flops only) | -63.8 |
| floor, zero window | 0 | 456 (73 flops) | -59.6 (-41.8 flops) |

Limit of the projection: it keeps the old mid offsets; S4q9m trees give new ones (same order, +-26 ps here).
Scope: the same rows apply to all 18 cb types / 192 partitions; in S4q9l2 their tol is median 48.4, p90 96.6, max 139.1.

## 3. Is the S4q9m / l2d chain on the right path

Yes for the dominant term: s4q9m_r is at TOL with 198 copied / 0 refused / 42 embedded, SPEF half range max 36.2
(slw_sc_v2, H-tree), p90 1.4, every cb type <= 0.3. It misses three things:
1. It is a die proof. Nothing in it reads a kit cross-tap hold, so the class is not gated by it.
2. The `u_lk_nk_*` launch-tap rule (1,000 of the 1,707 pairs left).
3. S4q9l2 as an intermediate event keeps the class on every cb type; a cb kit built on L2 rows fails the same way.
l2d only moves coll_ftc / coll_ftn / slw_fw_v3; cb rows do not need to wait for it.

## 4. Ranked fixes

| # | fix | lane | clears |
|---|---|---|---|
| 1 | Finish s4q9m_r, hand cb rows with tol = SPEF half range + 10. Add one row check before hand-off: per type, max over ports of 2 x tol <= 40 ps on templated types | QC-CLK-R2 | 21,431 -> 1,707 on this type; 18 cb types |
| 2 | `clock_taps.tcl` hop-latch rule also matches `u_lk_nk_*` (latch rides the tap of its `u_pc_nk_*` register, moved as one unit). No RTL, 0 cycles | QC-TYPES-R (kit tool) | 1,187 latch endpoints; latch -> core keeps T/2 |
| 3 | Pre-GRT hold accept test: accept on endpoint / TNS gain, not WNS only; cross-tap guard reads the per-port offset lines | QC-TYPES-R (kit tool) | the 707 flop pairs (<= 64 ps = 2-3 hold cells each) |
| 4 | Compose S4q9m = l2d + cb clock rows; hold the 18 cb types (and the cb members of the 27 unheld clock types) until event_adopt:S4q9m, not S4q9l2 | QC-PLAN-R | stops L2-row cb kits |
| 5 | One pilot: cbn_q01__clab6e67f2 on S4q9m rows + r301 source, stop at the post-CTS FF hold gate. Pass: cross_tap <= 2,000 endpoints, ws >= -90, latch endpoints 0. Then the wave | QC-TYPES-R | proof for the family |

Advisory, same kit: 5 taps are over the 1,200-sink cap (clk_t115 5,422, clk_t104 2,473, clk_t42 2,403, clk_t103 2,250,
clk_t39 1,385). Not the cause here (trees matched to 2 ps on the worst pair); needs a finer tap pitch in a later event.

## 5. Stop list

- No relaunch of any cb kit on S4Q3B / S4Q3C / S4Q6D sources or on S4q9l2 rows.
- No higher GRT hold iteration count or time cap for this class; no uniform guard (guard 45 added 36,093 buffers, WNS unchanged).
- No RTL change to the lockup (no negedge flop, no second latch, no extra pipe), no CA / K re-plan: nothing here is half-cycle.
- Do not hold cb rows for l2d.
- Do not release the cb clock holds on Kf or on S4q9l2 adoption.

## Not checked

Why the worst latch pair took no buffer in the pre-GRT pass (FIRM anchor or net protection); routed numbers; other cb types'
own DBs (cbn_q00 cl622f65d2 and cbx_q10 show the same endpoint names in their time-cap lines, not re-read).
