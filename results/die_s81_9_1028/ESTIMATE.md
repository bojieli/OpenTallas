# DIE-S81-9 estimate before build (12.14b) -- S81 revised plan event, F1-independent parts

Base: Codex packed-G clock (clock_G_body, fresh GRT0 TT/FF, proof_body arrivals), plan_s5 d29050658673.
Data: intel2:/srv/opentallas-scratch2/claude/die-s81-9/{est,wi}. Labels: CHECKED = own run of main tools / own script on
measured arrivals; UNCHECKED = not independently re-derived.

## 1. Routed stage fit on all 398 regions (scripts/est_fit_all.py)
Fit of 15,856 routed region-DME legs on packed G: TT d0 30.41 / k1 0.1131 / k2 9.5e-5, rms 6.56 ps; FF 24.16 / 0.0984 /
8.5e-5, rms 5.55 (CHECKED; TT = DIE-S81-7 kit-F fit to 0.1 ps). Per DME partition, the fit-predicted spread on the as-built tree
is the part a fit-model DME rebuild removes; range(routed - fitpred) estimates what stays:

| TT (FF) | routed now | after fit rebuild (est) |
|---|---|---|
| worst partition range | 118.4 (95.3) | 92.3 (76.0) |
| p90 / median | 82.8 / 53.6 (65.7 / 42.3) | 68.0 / 42.3 (56.9 / 34.9) |
| partitions > 100 | 7 (0) | 0 (0) |
| neighbour taps < 200 um: mean / p99 / max abs(d) | 6.2 / 44.6 / 69.8 (5.1 / 36.5 / 60.8) | 4.9 / 41.8 / 74.3 (4.2 / 35.9 / 64.7) |

Verdict: the fit rebuild trims in-region range by ~25 ps but does NOT reduce the neighbour-leaf damage that drives FF hold
(p99 44.6 -> 41.8, max goes UP). The leaf-to-leaf error is per-leg residual (detour/load), not model bias. In-region range
already passes (134.01 TT / 109.68 FF incl. OCV <= 150). So the fit rebuild is optional, and it is not the hold fix.

## 2. FF hold -162.5: die HB4 vs kit tap window (wi/run.sh, main die_sta_related, WHAT-IF --intra-window-ps)
- The die-level HB4 BOUND with the plan pin files resolved (the predecessor's run read 0 bits: plan copied out of the repo, so
  inputs/core_pins did not resolve) = 9,161,376 core data bits x the partition's worst k = 24,728,019 HB4 cells, 2.52 mm2
  (CHECKED own run). Not a usable form: intra paths are inside the partitions, so the die cannot insert into them.
- Kit tap window form (gen_phys clock.tap_window, kit SDC -source -early -W on every tap port, so the kit's own hold repair
  covers every cross-tap pair inside W): needed W = 109.68 nominal / 159.84 with clock OCV (bk_sel t40->t11). WHAT-IF W=165:
  kit-contract hold +55.32 nominal / +5.16 with OCV, 0 neg pairs, PASS (CHECKED). Per partition with OCV: median 84.5,
  98/397 need > 100, 7 > 130, 1 > 150 (bk_sel). W = 180 <= T/4 = 208.25 keeps ~20 ps for the rebuilt tree.
- Cost: the kit times cross-tap setup with W tighter (T - W = 653 ps at W=180 for cross-tap paths). The kit's hold repair
  count is the REAL HB4 count, measured at kit regen. UNCHECKED: which kits keep >= 180 ps cross-tap setup slack.
- BLOCKER (measured): gen_phys.tap_window_tcl raises "clock.tap_window with early core taps (banned by 12.8d)". plan_s5
  already has core_taps on 29 types, and with the CORELAT table 119/205 types (309/398 partitions) hold an early-tap core.
  12.8d was superseded by v5.0 (early taps ALLOWED). Lifting it is a shared gen_phys change.

## 3. CA crossings < 100 ps with clock OCV (DIE-S81-8 nc_ca_ocv.json)
23 ports / 14 tags below 100 in TT or FF (min 50.1 TT / 59.0 FF). Every one has margin_hi >= 1747 ps, so +1 cycle (833 ps)
gives lo >= 883 and hi >= 914: PASS by estimate (UNCHECKED until the planner flag exists; the CA-OCV-1 lane owns the shared fix).
Cost +1 cycle on 14 tags; the static schedule absorbs it (12.15c).
