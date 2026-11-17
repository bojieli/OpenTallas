# FABLE-PLAN-KV-HG6 2026-11-17 07:55 PST: structural review of KV plan event HG6

Reviewer: FABLE-PLAN-KV-HG6 (Fable). Technical PD / plan structure only. Read-only.
Reviewed plan: **candidate `de55ed71a889`** (epyc10 `kv-r3/plan_hg6.json` at 07:40 PST, snapshot `/tmp/fable_hg6/plan.json`), base D16 `340b90be33dd`.
The posted plan `eaa5302a1c5a` (tree D17) is already dead: its gate stopped at PRE with 15 `GEOM-STATION-IN-CORE` (bank centroids inside kvpc0 / kvpc1_f / kvpc2_f). G0, bind and LATCHECK have **not run on any HG6 plan**.
Probes: plain python on epyc10 over the plan JSON, plus one `reach_fix.py check` (4 threads). Not sent through ot-run; no build jobs.

Verdict: **do not bind `de55ed71a889` as is.** Two site-legality findings (S1, S2) are fixed in the composer in minutes, cost no cycles, and should go into the same event. Latency table is consistent. Nothing outside rows / stations / lanes is churned.

## (1) Station sites: legal, every hop <= 405 um?

Real size of the event: **40 banks, 1,208 FIRM flops per type** (20 buses, 607 bit paths), not 25 stations.

Passes, measured on the plan's hard-core boxes (nominal and track-offset union):
- 0 of 1,208 cells off the 0.054 x 0.27 grid, 0 outside the core (4.32 margin), 0 inside a hard core, 0 mutual footprint overlaps.
- 1,815 per-bit hops (ring -> s1 -> ... -> sk -> old bin). Max **380.8 um** (`i_ectl_Q_N_kf` epoch). Obstacle-aware shortest path equals Manhattan on all of them (0 detours), so the 405 claim holds for the declared chain.
- Site displacement from the ideal route point: <= 7.1 um on 19 buses, 101.2 um on `i_slg_Q_N_o_dn` (272-bit bank spread in x).

Fails:

**S1. Station cells sit on reserved rects (blocks).** `compose_hg6.py place()` tests macros only, not `clock.reserved_sites_um`.

| type | on `die_clock_tree` (M1-M7 reserved) | on `channel_keepout` |
|---|---|---|
| cl23f6a148 | 9 | 2 |
| cl7f648944 | 10 | 2 |
| cl4ea58a5c | 5 | 2 |

Cells (cl23f6a148): `i_hsl_Q_N_sko` b1 bit32 (810.756, 516.24); `i_idpc_Q_N_y` b0 bit4 (848.502, 195.48), bit5 (872.91, 61.29); `i_slg_Q_N_o_dn` b0 bits 30/144/154/159/162 (x 849.9-852.8, y 1159.1-1220.7), b1 bit4 (848.502, 919.08); `i_slg_Q_N_af__fault` b2 bit0 (486.432, 284.85) and b3 bit0 (486.432, 498.42) inside the new keepout rows [483, 246, 552, 360.99] and [483, 490.32, 552, 514]. The reserved rows differ per type (128 / 122 / 124 clock rects), the station table is one table, so sites must clear the union. This is the he12h / sd9f class (flop pins under a reserved clock site: M2 spacing + M7 shorts).
Lane check: add footprint (1.404 x 0.27) vs every `reserved_sites_um` rect of all 3 types to `place()`; expect 0 / 0 / 0.

**S2. 147 flops per type are FIRM inside the 8.64-um pcc|pcf slots (blocked channel).** kvpc2 ends x 846.72, kvpc2_f starts 855.36; the two faces carry **298 facing pin pairs** (pins files, E edge of pcc / W edge of pcf). `i_slg_Q_N_o_dn` bank 0 puts **138** cells there; 9 more on kvpc1|kvpc1_f and kvpc3_f|kvpc3 (`fault_o` 3, `idpc_y` 2, `kf` 1, `sko` 1, `embgw_est` 1, `px_tok` 1). 80 cells are < 1.08 um from a macro edge, minimum 0.75 um: the composer clearance (2.14) is tested on the cell origin, not the footprint.
Lane check: clearance on the footprint, and no site in a macro-to-macro gap < 12 um. `o_dn` bank 0 has free rows in the east strip (x 946-1032).

**S3. Form: last station is one segment short of the bin (advisory, numbers).** kit_istations puts in-bus stations after `u_bin`. The composer sites station j at L*j/(k+1), so ring -> u_bin -> s1 spends two registers on the first segment, and the readers are driven from sk, which is L/(k+1) away from the old bin = consumer position. Final hop = 379.6 (`kf`), 367.4 (`sdo`), 343.5 (`co`) **plus the consumer stub, not measured**; margin 25 / 38 / 62 um. KV-PC-DELTA's own mechanism says "last station at the old bin / consumer position".
Fix at 0 cycles: stations at L*(j+1)/(k+1), `u_bin` pinned at L/(k+1) with `face_bit_sites_um` (supported on the `u_ist` form; refused on a packed `u_lpad`).

## (2) Cycles through latency

- Plan table is consistent: 480 lanes, `cycles` = `fixed` = `natural` += k on each (216 x2, 168 x1, 72 x4, 24 x3 = 960). 0 lanes into a stationed bus left unchanged. k is uniform per (type, bus) on all 24 partitions.
- The 3 R8 replica groups (`r8_px_tok`, `r8_px_tep`, `r8_boot_go`) are untouched (delta 0).
- D16 as-built: the old fixed 3 / 6 on `rq`, `embgw_est`, `rst_n` x2, `px_tep`, `px_tok` live at the **source** (`bound_ist`); the PC receiver has lpad 0, pads 0, kit_ist 0 on all 20 buses. So the +k must appear at the receiver as kit_ist (or lpad) = k.
- **Not proven yet: LATCHECK.** Read at the D17 gate: 2404 / 2404 delta {}, receiver kit_ist|lpad = k on the 480 lanes, and `bind_r8pad_strap_audit` PASS. The PC wrappers hold R8 strap pads on the same consumers (`u_r8b_strap_r8pad_slg_afu` DMAX 2, `slg_x_tok` DMAX 2, `slg_i_up` 2 + DMAX 1): `af__fault` +4 and `px_tok` +4 against `o_ctl` +0 moves the group by 4, beyond today's pad range. If the bind does not re-size these pads the token schedule is wrong while LATCHECK still passes per lane.
- Reset: `i_host_*_rst_n` +1 is inside the 64-clock rst_n hold.

## (3) Congestion and clock reach

- Cell load is negligible: worst 27 x 27 um bin holds 65 station flops (3.4 % utilisation). The congestion risk is S2 only.
- Carve: 36,718 / 36,767 / 36,767 um2 of keepout in x 483-552, y 246-1274. 0 planned FIRM points (START stages, raw branches, sink sites, old stations) inside a keepout row.
- Clock, `reach_fix check`, D16 -> HG6 (same on all 3 types): sinks 11,979 -> 13,187; c1 2 -> 4, max 205.1 -> **246.8 um**; c2 1 -> 2. New: 2 station flops beyond the 200-um radius ((358.8, 126.5) 222.8 um, (277.7, 48.7) 246.8 um) and `clk_t21` 1,148 -> **1,235** sinks (cap 1,200). `clk_t23` 1,652.9 and the 2 landing sinks are already in D16.
- `rfix.sh` (reach_fix fix classes 1,2 on the HG6 plan) was running at 07:47. That re-cuts taps for the pre-existing rows too, so the "clock rows byte-identical" property is lost and the event stops being rows + stations. Cheaper: move the 2 cells <= 47 um; leave t21 / t23 to the kit tap cap.

## (4) Churn outside rows / stations

None. Full diff D16 -> `de55ed71a889`: `lanes[].fixed_cycles` + note (480), `latency.lanes` (480 x 3 fields), top `note`, and on the 3 types `clock.reserved_sites_um` (+38 / +32 / +32 `channel_keepout`) and `internal_stations` (5 -> 25). The 128 / 122 / 124 `die_clock_tree` rects are identical and in order, the 5 old station rows are identical, hard cores / taps / pins / `latency_groups` unchanged.

## (5) What can fail at type build, and the one check

1. S1: flop on a reserved clock site -> placement overlap or routed DRC.
2. S2: 138 flops + their routes in a slot crossed by 298 pin pairs -> pin access / GRT overflow in the slot.
3. kit_istations form: exact banks on a packed `u_lpad` need depth == banks, an observed epoch needs its flop ("missing observed/unproved epoch"), `face_bit_sites_um` is refused on the packed form.
4. Consumer stub after sk (S3) -> setup on `kf` / `sdo` / `co`.

**Single check before kits: dry GEN (kit_istations --apply + GEN_LINT) of `kv3_pc_v1__cl23f6a148` on the HG6 tree.** The publish gate's dry GEN runs the pilot `kv3_hg_v1`, which has none of the 20 rows, so today nothing exercises them before the wave.

## Stop list

| # | item | blocks? | numbers | lane check |
|---|---|---|---|---|
| S1 | cells on reserved rects | **yes** | 11 / 12 / 7 per type | footprint vs `reserved_sites_um` of all 3 types in `place()` -> 0 |
| S2 | cells in pcc\|pcf slots | **yes** | 147 per type, 138 on `o_dn` b0; min macro gap 0.75 um; 298 pin pairs per slot | footprint clearance >= 2.16, no site in a gap < 12 um -> 0 |
| S3 | last station short of the bin | no | final hop 379.6 + stub, margin 25 um | shift banks one segment, pin `u_bin`; or measure the stub at placement |
| S4 | LATCHECK / R8 pads | gate | not run on HG6 | 2404 / 2404, receiver = k on 480 lanes, r8pad audit PASS with re-sized slg pads |
| S5 | reach_fix fix 1,2 inside HG6 | no | c1 +2 (246.8 um), `clk_t21` 1,235 | no tap re-cut in this event; move 2 cells |
| S6 | no PC dry GEN before the wave | no | 0 of 20 rows exercised by the pilot | dry GEN of one PC type on the tree |

Bank re-site to the type centre: not cheaper. It halves the cycles at best and re-opens the clock landing; keep stations.
