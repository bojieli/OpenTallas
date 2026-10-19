# PGSTREAM SAFE2 (LH-PGVM 2026-10-19) -- source fix of the 14 roots > 32 left by 47d9b210c

Top `ot_hbm_su_static_pg_stream_split_safe2` (rtl/hbm_accel/generic/adapters/static_su/top/ot_hbm_su_static_pg_stream_safe2.sv,
branch claude/lh-pgvm-pgsafe-1019 @165fb..., source r4). Same ports as `ot_hbm_su_static_pg_stream_split`; legacy files untouched.
Reuses the 47d9b210c regional bridge regions (7-bit serial request / 15-bit return / 15-bit stream request regions).

## What changed (all same-edge; no data / valid / fault / seam-calendar edge added)
- **bridge_rst_n (1,726 loads)**: the kit lands it in ONE face stage (kit TODO: reset_landing.stages 1); the source owns a
  balanced tree: serial = face -> 5 kept stage-A cells -> 129 kept serial terminals (one per bridge_q region, done copy,
  inject_q region); stream = face -> 3 kept clk_ctl feeders -> 3 kept pg_clk cells (2q setup / 1q hold related window)
  -> 86 kept pg_clk terminals (one per bridge_s region, monitor group, inject_s region, MUT14 term).
  BOTH domains leave reset on the same coincident edge 12q after the face flop.
- **rst_n**: two kept serial source stages after the face flop (old: 3 kit stages).
- **leaf (73) / tap (92) reset synchronisers**: first stage unchanged, second stage replicated: leaf 5 copies (per bank
  leaf: read calendar + fault / write calendar; fault publication), tap 8 copies (per tap bank: control + read selects,
  read calendar, write calendar, write-select copies). Same two pg_clk ages.
- **tap selects (write_d 564 x2, read_d 36 x2)**: kept per-region select cells sampled from local_write / local_read on
  the write_d / read_d edge and reset (20 x 14-bit write regions, 2 x 8-bit read regions per tap bank).
- **bridge_s monitor (46)**: verbatim equations, two reset groups.
- **inject (83/82/81/81/41/41/35)**: five kept group-aligned regions per side ({v[g], row g} x4, {bad}), each with its own
  slot counter (sp / sq) and, on the stream side, its own decode cone (10-bit bank enables / selects).
- **pos strap**: registered into 6 kept per-consumer copies (static strap; valid long before reset release).

## Evidence (Verilator 5.050, fleet; bench/ = q_165fb)
- tb_hbm_su_pg_stream_safe2 = the regional actual-parent lockstep vs the current two-root ot_hbm_su_static_pg_stream with
  the per-group seam-window checker (request 4q/2q, return 2q/4q, inject 3q/7q). The DUT gets the kit face stage (1 flop);
  the reference gets the DESIGNED release (100 ps before a coincident edge) delayed by one epoch (12q).
- Positives PASS: rr18 (checks 7194, windows 9228), rr10, qid0. Causal mutants FAIL: m1, m2, m3, m6, m8, m12 (window-only),
  m13, m14. `bench/results.json`.
- Native TT map (`map/`, yosys 0.68, keep_hierarchy regions, flattened all-driver BUF/INV-transparent census):
  9,033 FF, 29.4k cells, 4,008 um2. **Roots > 32: 2** (was 14 / max 1,726): `inj_addr[123]` 37, `inj_addr[126]` 33 --
  unregistered inject input ports (slot-3 group bits) feeding the decode cones. Fix = pin capture of inj_rd/inj_addr
  (+1 stream edge, inj_q +1 -> H-D4G pricing; NEXT.md step 2 says ROOT decides) -- NOT done here.

## FINDING (kitland bench, applies to the frozen 53cbcc9a8 kit / gate95463)
`tb_hbm_su_pg_stream_kitland`: the CURRENT regional top behind the CURRENT kit's 3 clk_ctl landing stages, reference as
above. Result: **FAIL errors=12716 window_errors=7909**; measured windows request setup 0.278 ns (1q, declared 4q),
return hold 0.278 ns (1q, declared 4q). Cause: a clk_ctl-released reset frees the stream flops at the next stream edge
(C+9q) but the serial flops at C+12q, so the stream side starts one stream edge early relative to the calendar that the
bench (raw release before a coincident edge) and the seam_windows SDC assume. The gate times the declared 4q/2q windows,
so it cannot see this. SAFE2 releases stream-domain loads from pg_clk terminals (C+9q -> count from C+12q).

## SAFE-DESIGN checklist (source level; physical items need the SAFE2 kit gate)
1 Pins: OPEN -- inj_rd/inj_addr still decode straight into the bank flops (2 port roots 33/37); reset lands 1 kit + 2 source stages.
2 Reach: tile 216x259.2 (diameter 475 > 405) -- needs the placed census at gate.
3 Fanout: 2 roots > 32 (ports above), every register / reset / select <= 32.
4 Depth: unchanged decode depth (boundary pos->inject bank was 10 levels; pos now registered).
5 Storage: unchanged (bridge banks < 2 kb each; no new delay lines).
6 Floorplan: kit TODO (same 216x259.2 pin-bound outline expected).
7 Clock: two regional roots as the B kit; new related crossing feeder->P (2q/1q) to declare in the kit.
8 Schedule: no edge added; reset release constant unchanged (3 serial edges after the die reset release, both domains).

## Kit TODO (hbm_su_pg_stream_b_safe2_1019)
top _split_safe2; sources + multirate_bridge_regional.sv + ot_hbm_su_static_pg_stream_safe2.sv; reset_landing.stages 1;
seam_windows globs -> region cells (*u_bq.req*, *u_bs.ret*, *u_s.g_ij*); cdc_synchronizers chains -> u_s.rq_s0 /
u_s.g_lr[*].u.r and u_s.rs_s0 / u_s.g_tr[*].u.r; declare g_bsf feeder->P window (2q setup / 1q hold).
