# DIE-HBM-7 (2026-10-28) — results only, ESTIMATES (no build, no adoption)

Plan: C20j die_plan.json sha d59040633ac4 (intel2 codex-hbm-die-1028/c20j). Tool runs CHECKED; models UNCHECKED.

## (1) collq2 (Codex finalff3 reduce route, intel1)
Route FAILED at detail route: DRT-0255 on mp_isl0_rst_i / mp_isl1_rst_i / mp_isl2_rst_o. This is the legacy 2.16-um island pin
in the M5 VSS/VDD gap (root cause HBM-CORES-REBAL-2; COORD 06:43 said not to count it as new). The final-FF hook PASSED before that:
FF hold -0.341 -> +0.0095 ps, TT setup 27.43 ps, clock freeze OK. There is no 6_final.v, so routed LEC and bound-FF sign-off were
NOT launched. Successor: the HBM-CORES-REBAL-2b reduce kit _c20ek2p (pins 1.08, hold margin 5), queued AUTO.

## (2) Hub estimate — hub/
- Duty basis (b_cost.py, ds S2 schedule, 576,702 cyc): COLL 0.583, SU 0.236, SM 0.220, FUSED 0.124, HC 0.075, DMA 0.070,
  IDX 0.033; VM aggregate (all clients) 0.80. A link is eligible for 2:1 if unit duty x current serial_k <= 0.5. COLL and VM are never eligible.
- hub_replace_est.py, 4x3 grid, worst face / 6 pins/um (full face length, no hard-body subtraction, so optimistic):
  | form | NW | NE |
  |---|---|---|
  | base (endpoint L paths) | 2.56 | 2.78 |
  | B full (SU,SM,IDX,HC,FUSED) | 1.96 | 1.80 |
  | B cheap (IDX,HC,FUSED) | 2.35 | 2.44 |
  | A (SA re-placement, same outline/cores, 3 seeds) | 0.85-1.04 | 1.08-1.25 |
  | A+B full (seeds 1-3) | 0.79-0.86 | 0.81-1.04 |
  | A+B cheap | 0.98-1.13 | 1.02-1.21 |
  All regions stay under 360k soft cells, unbanked (max 234k).
- B tok/s cost (b_cost.json). There are two forms. Latency form (+1 cycle per record; valid only if the op is not limited by
  that link): full 0.25 %, cheap 0.04 %. Link-bound form (the op takes 2x): full 46.7 %, cheap 15.5 % (SU 19.6, SM 16.1,
  FUSED 12.2, IDX 3.3, HC 0.0 %).
- 12.13 rework (hub_locality.py; COORD 07:1x). Station bits are 301.6k (NW) and 293.5k (NE).
  - Client-anchored scatter: 55.6 / 56.4 % of the bits are local to one client, 10.9 / 8.2 % to one function group, and 33.5 / 35.4 % (~100k) are die-wide. So R9 "lane geography" still holds; it comes from the fan-out cores: pgp, cxij_q, calendar, sucore and coll body go to 4 SU slices, and smw goes to 4 SM rows.
  - Bit-mm is today 945k (NW) / 953k (NE): hub-internal 557k/582k plus external lanes 389k/372k. COORD's 424k/394k uses a different metric and was not reproduced. Scatter gives 1606k/1551k (+70 / +63 %) with up to 47 hops. All slices are under 360k; the worst faces are 1.92 / 2.01 (PHY_N slice).
  - Hybrid (only cores with more external than internal bits move): 79-80 % of the bits stay in the hub. Bit-mm is 882k/826k (701k/639k with B). The hub group slices are still 1.7-2.0x over: svg_vmks, vm_bank and pc_ctl.
  - Straddle cores (no client above 60 %): calendar, cxij_q, coll body_core/body_n2, pgp, smw, sucore, svg_Q3, vmb_Q2/Q6/Q7.
- ca_ocv_est.py uses the approved 0.21 %/mm table + droop. Branch 0.223 ns/mm + core latency 250. Window = ocv_su + ocv_ho + 60 + 25 <= 833 ps.
  - Scatter, LCA at the die root: up to 8.3 ns unshared; 36 crossings / 2.8k bits FAIL (923 ps).
  - Scatter, LCA at the crossing midpoint: max 607 ps, 0 fail.
  - Hybrid: max 736 ps (root) / 554 ps (mid), 0 fail.

## (3) Canonical partition map — bind/
mk_asbuilt_canon.py maps 375 leaves:
- 321 from census (285 direct, 32 NE index shift, 3 module match, 1 partition-only).
- 12 census slice rules OPEN.
- 28 fold-contract slots (S role -> q0 half of the folded hub):
  - 10 halves: calendar / hb_vms / hb_idx op, q, qctl, SW/SE.
  - 16 vmb_S*k -> u_vmb_Q<k>_mu1 hard cores. UNCHECKED: the _mu1 name may mean these slots are reserved for MU banks.
  - 2 mu_fused_n4_nw/ne -> the hub's u_mu_fused_n4.
- 2 hb_idx__s_SW/SE slices OPEN on the N-twin group.
- 3 proposed for root, still needing plan contents: hb_ckgen, mu_fused_programme, mu_fused_root.

Strict bind running: intel2 pids 3719511/3719537, out /srv/opentallas-scratch2/claude/die-hbm-7/sbind_canon. It runs in WT die-hbm-7-canon (codex/hbm-die-1028 a5f2f63b2a + copied untracked canonical_storage + the local bind_reset guard).
