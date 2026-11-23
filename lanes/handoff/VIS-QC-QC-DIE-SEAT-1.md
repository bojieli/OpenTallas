# QC-DIE-SEAT-1 (VIS-QC, 11-23 01:4x PST). Replaces VISQC-DIE-1, which is DROPPED (FABLE-RC-QC: WRONG-CAUSE; COORD ruling)

One die row with three parts, applied per family. No die growth. Growth only where a probe shows it is needed (fe/fw, su_l1 E channel).
Target event: V4 (single QC event, cut 11-23 14:00, owner post 6079af4; V5 is gone). Rows must be GATED by 13:00. PROBE-PASS uses the full-cause census rule (fe8a2a5): every cluster >=50 ovfl or >=1 %, total overflow <10 % of baseline, and every path class worse than -42 TT or hold <0 has a row.

## (a) No hard macro inside a bus corridor
- Corridor demand comes from station legs, ft legs, relay-site density, pin-escape strips (200 um deep) and pin-window -> band legs (tool: intel1 /srv/opentallas-scratch3/claude/VIS-QC/sta1/seat_find.py).
- A macro seat is legal only with corridor demand 0, at least 10 um clear of other cores and at least 5 um clear of bands. Channels are 30.24 um or more; 5-48 um slits are not allowed.
- **st_a (built):** STA-2 seats the btab column above the E pins.
  - col4 at x 505.44, y 864.0 + k*71.304 on 9 types; x 488.16, y 920.16 on the 2 clfc5867a6 types.
  - This replaces the STA-1 seat x449-544 y661-916, which sat in the E output corridor (FABLE PARTIAL).
  - Plan: intel1 sta1/plan_t2.json (PLAN 203d8a7f576f) = V3 + l0b st_a + STA-2.
  - The strict bind, LATCHECK, PGP and G0 chain is running (sta2/). Then a GRT probe on slw_st_a_v2 cl9f076a5c and clf4365a62.
  - Per COORD 01:19 this is the placement arm for the route-wall class only. It does NOT fix the btab SRAM -> g_read arc, which is inside the closed view (see the gap replies).
- **cb:** cbn_q00 street variant (cb1s, PLAN ff8e792599a8) is binding; cbx re-site is in CB-1 (cb1d, b7eadc0810be).
- **coll:** g_pf[1] W edge cluster (440-500,450-560). The same seat rule applies: spread the W-packed macro set into the empty SE quarter. It belongs to COLL-1 (OPUS-FIX-QC-COLL-R3), and I asked R3 to extend it beyond the g_xf row.

## (b) Landings seated at their own pin window
- Rule: each cland ring/band rect is flush to the window of its own bus, at depth <= 30 um from the edge, and not shared with another bus's corner.
- Instances:
  - **coll** shr_p_rx_i (-97 at place, 12 buffers): re-seat u_cland_shr_p_rx_i to the shr_p_rx window. Folded into the COLL-BANDS row (VIS-QC-DIE-COLL-BANDS.json, which already moves in_last/in_valid off the g_sring pin edges).
  - **cb** cbf_q11 SW corner piles (20-80,0-100): na/nb/bc rings each go to their own S window segment instead of the shared 69 um corner. Applies to all cbf/cbx types (CB-1 re-sites only q00 + cbn_q00).
  - **st_a** clf4 b_hw landing (300-600,50-110): band is flush to its window, and nothing routes under the landing.

## (c) Taps sized from placed sinks; pin-register bands on their own taps
Coordinated with TAP-GRID-R5, which owns the tap generator.
1. **Load.** tap_split from PLACED sinks: `tap_split.py --sinks-dir <placed bins> --cap 900 --radius-um 150`, with Row D affinity max_group 64 / radius 150.
   - Built for cb in CB-1: loads 7374 -> 2412 max. Residual over-cap remains where no legal site exists near macro-packed sinks; that residual needs (a).
2. **Pin-register taps.** Every pin-register band (sinks within 30 um of a bus pin window / landing band) gets its own tap at the band. It is not padded by OT_TAP_BALANCE_TO=slowest.
   - Its target is clock.insertion_ps (vclk, 250). The bound is the type clock.insertion_ps (gen_phys insertion_binding, per TAP-GRID-R5).
   - Rule: tap_slowest_max_ps <= insertion_ps for pin-register taps.
   - Today 107 types have slowest_max 265 vs vclk 250, which is the 265-307 ps pin-register insertion.
3. **Neighbour pairs.** Pad flop -> first station, and reset relay -> its sinks, go on ONE tap (tap_chain_affinity group).
   - This closes the 35-52 ps neighbour-tap gaps behind su_l1 u_lpad_x_su_c_i hold -17..-28 and station hold -36, and the st_a reset removal -8..-27 (relay tap 221-233 vs sink tap 257-272).
4. **Ownership.** TAP-GRID-R5 regenerates (2)+(3) on the composed plan after (a)/(b) move macros (same order as the S81 XGA2 flow). VIS-QC probes it on st_a, cb and su_l1.

## Per-family status
| family | (a) | (b) | (c) | probe |
|---|---|---|---|---|
| st_a | STA-2 built | b_hw flush | pinreg taps | sta2 bind -> GRT probe slw_st_a_v2 x2 |
| cb | CB-1 cbx + cbn_q00 street | per-window rings (all cbf/cbx) | CB-1 placed split done | cb1d / cb1s bind -> GRT probe cbn_q01 cldd6ea846, cbf_q01_s2, cbn_q00 cl622f65d2 |
| su_l1 | E channel: ft_slot re-site (SLWSLE, after cl5ea486db read ~03:00); growth only if probe says | - | one tap for pad + first stations | V4-R2 sealed v5b clcc9d0155 / own |
| coll | SE-quarter spread (COLL-R3) | shr_p_rx + in_last/in_valid bands | pinreg taps | COLL-R3 pkit_core5a |
| fe/fw | growth by probe (75-80 % usage) | - | pinreg taps | V4-R2 |
