# DIE-HBM-44: HBM freeze-event fold-in on d41v (OWNER 12.22), plan d44c

Base = plan of record d41v (3bccac4b3860, G0 6 / G0C 14 errors, strict bind 52 pairs / 42,416 b).
Tools = wt/die-hbm-42 (same tools as the d41v gates); results only, no shared tool change.

- d44a = d41v + 4 seam pin-window shifts (`pinshift.py`, report `d44a_pinshift_report.json`): the FF -> seam pin -> FF
  hop of L206/L206m (su01|spu0, 1 b) and L6b/L6bm (su31|b110, 828 b) ran through a pin window 63-400 um off the
  station line (489/645/836/845 um > 405). Windows moved by 0.576-um multiples into free face span (>= 2 um clear of
  every other window, asserted), width/layers/order unchanged, stations unchanged: hops 363/363/346/346.
  G0 6 -> 2, G0C 14 -> 10, 0 new; strict bind identical (52 / 42,416).
- d44b = d44a + L744/L744m (b101 -> hub, 2 b, direct abutment; `va_build.py` of DIE-HBM-42 on `rows_744.json`):
  the NE mirror again shares the L12m_1 track (G0 +4, same as the 26-pair build).
- d44c = d44b + L744m windows on q_b101 N / q_hub_ne S moved die +302.4 um (off L12m_1 and its 10-um density
  window; `d44c_l744m_shift_report.json`). G0 2 / G0C 10 (= d44a, 0 new), strict bind 52 -> 50 pairs,
  42,416 -> 42,412 b; 4 new WARN bus L744_* has no leaf binding (plan-level, the bind binds them).
  plan_of_record/d44c sha 578a4dc0ca05. Render `d44c_review.png` (red d41v, green d44c) viewed.
- Remaining G0 errors: L204/L204m (1 b NW_b000 -> b002): the b010|b001 seam next to the stations is fully taken
  by L14 (4,127 b, per-bit sites) + L11, and the b001 first station is 521 um from the only free pin -> needs
  station re-site in b010 + b001 with +1..2 stations (cycles on a 1-b lane), not built here.
  G0C adds 8 core_faces on q_hub_nw/q_hub_ne (hard-core port sides; known since DIE-HBM-15).
- Strict bind classification of the 52 d41v pairs: `bind_d41v_pairs.txt` (full bit list via
  `bindfull_runbind.py`, a report-only wrapper that lifts the 5,000-bit list cap). None is kit/wrapper local:
  big functional buses need plan lanes (V-A builds failed: no free window / no macro-free chain), the small ones are
  scorer-internal feedback (b101<->b103, +40 cycles via V-A), delivered reset b100->b103, obs/fault bits and
  cp_svg run -> router_ids (RTL connectivity).

## d44f = d44c + exp0 single core clock pin (COORD 20:43 (6), option B)
`exp0clk.py`: ot_hbm_su_static_pgslice_lg__lane_exp0_id (q_su00/q_su10 + physical_v1, 4 uses, one pins template) gets ONE
pin `clk` (M5, at the plan centre entry 207.384/103.68 = island centre, as the hc_bank centre clk pins) replacing the 19
clock roots (clk_bank, clk_insert[0..3], clk_bank_macro[0..5], clk_lane[0..7]); clock_entries port null+merged -> `clk`.
Data pins (2,049, sha in report), outline, die tap xy, island, latency targets unchanged. The kit wrapper fans clk out to
the 19 internal roots and builds one core_tree (kit lane). Gates: G0 2 / G0C 10 identical to d44c (0 new, 0 gone, warn
966 = 966), strict bind identical (50 / 42,412). Die clock rerun (`tools/die_plan/die_clock.py run --core-early pad`,
TT+FF) on d44c and d44f: arr_TT/arr_FF/spine/place/nets byte-identical, clock_report differs only in plan path/sha/runtime.
The absolute die_clock.py plan-model pair skew (487.6 ps, 325 pairs over 80) is the same on both and pre-exists d44c.
plan_of_record/d44f carries die_plan.json.gz + clock_entries.json.gz + the new pins file (rest = d44c/d40h tree).

## d44d (not adopted, one-block after the freeze)
`l204fix.py`: L204/L204m last b010 / first b001 station at the free seam pin, rest re-solved at the same count: G0 hop
errors 936/900 -> fixed, but G0C reach-margin (0.9 x 405 = 364) gets 2 new 393-um hops; reach 360 build (`REACH=360`)
gives hops <= 359 -> needs the G0C run (d44e).

## Freeze G2 at 50 it (`g50_gen.sh`)
g2.py die + part probes on d44c, iterations 30 -> 50, check_placement report-only in the probe copies (station sites
FIRM inside soft leaf regions; 0 stations in hard macros by `stinmacro.py`).
