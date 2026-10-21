# DRIVE-S81-SVCPLAN (10-20 22:35-23:55): S81 attention-service re-plan -- NOT FROZEN, blocked on a die-architecture call
Base: Codex codex/s81-service-plan-1020 @39419dd43 (G4_split112 geometry). MODEL + allocator evidence; no plan GEN, no GRT.

## (1) 112-frame capacity / calendar (inventory f92ee719, the 10 row-0 frames removed; same for every 112 plan here)
- Actual all-frame pinned allocator probes (Codex unit, ep9 codex-token-svc112-1020/out/probes): 9/9 PASS, 112 frames,
  slope 72 words/expert (= 122-frame), dense N0 q L0 480 / L1 1024 / L2 576 / L14 1120 / L20 576 / L24 576.
- build_stage_model.py -> **139 stages** (556 layer + 32 copy-B + 52 = 640 dies, vs 644 at 140/122 frames). stage_model.json.
- Exact full-stage capacity at 139 and 147 LIVE ep9 /srv/opentallas-scratch/claude/s81-svcplan-1020/cap (run_cap.sh N;
  units oth-ubuntu-3136401 / -3136615; s112_N.{exact,merge,qualify}.log). Verdict PENDING (~5 h, host 1.6x cores).
- MU calendar MODEL on the 139 map (dv_mu_calendar_phys.py @3fe699d4d --compose romopt --alap --unqualified, G16 attention):
  AR 42 x 1,011.8 = 42,494; MTP 8 x 2,991.2 = 23,929 (checker PASS, N+1 FAULT, inject FAULT). calendar_s112_139_model_*.json.
  With G4 attention (SVCFIT: AR -3.30 %, MTP -1.38 %): AR ~978, **MTP ~2,950 < 3,000 floor**. vs CAL3 1,065.9 / 3,286
  (different composer; ROMOPT pinned-140 = 1,011.7 / 3,026.5). Rebalance (MUCAL140B rb) not applied yet (+2 AR users there).

## (2) Geometry verdicts (fit_check.py -> fit_check.json)
- Codex G4_split112 is NOT buildable under the 405-um die rule: the rest<->engine cut of dsdv_svc_att/ot_hdc_v41x_attn_s is
  6,877 b per service (q 513, kv 1,065, scores 2,132, p 1,025, P.V 2,121); rest y <= 3,326 to islands y >= 10,066 crosses
  frame row 1 (3,000 tall) or the S-tier slice (4,600) with no relay site (frame gap 8.7 um, slice side strips 25 um) ->
  gen_safety W2 FAIL by construction; 16 x 6.9 kb x >= 6.7 mm = 742k bit-mm (die total today 403k).
- G8 (attention 1814.4 x 2160) has NO geometry at >= 112 frames: slice-column voids are 1,000 wide (32 G4-width halves
  needed, <= 20 void places) and the south band with only row-0 frames removed holds 12 tall slots + no G8 centre slot.
- Co-located G4 (rest + attention in ONE svc_rs slot, no die cut): 12 tall slots 1728 x 3758.4 in the W/E outer band
  (x 300..11.4 mm / mirror, y ~640..4,396) + 4 wide slots 2160 x 2548.8 over the controllers fits 112 frames, but 12
  services' HBM rq/rd (7.5 kb a side) must escape the controller row through a <= 323-um channel -> high GRT risk.
- **Overriding (SLICEP 10-20): real slice parents are 1252.8 x 6739.2 (k8a) and the MU end slices 2462.4 x 5788.8 vs
  950 x 4600 slots.** Die width with real slices: 8 columns 36.8 mm (34.4 if end slices compact to k8a) vs <= 32.0
  reticle -> the 8-column die (16 slices, 122 or 112 frames) does not fit at ANY service variant. 7 columns 32.6 / 30.2 mm
  (112 frames max before any service drop), 6 columns 28.4 / 26.0 mm (96 frames, 12 slices; leaves 3.6-6 mm for services).
  Fewer than 112 frames breaks today's dense allocator (448 a_proj rows / 4 per frame), so dense layers need a 2-die or
  multiphase split -> architecture decision (owner accepts more dies).
## Not done (by design): dv_plan GEN / gen_safety / trial GRT -- DRIVE-S81: no trial GRT with undersized slice slots.

## (3) 23:59 DRIVE-S81 ask: fewer frame columns + dense split (MODEL + actual allocator)
- The compiler (xs_place.py NSLICE 16; heads/dims dealt per slice) and the dim-sliced RTL need 16 slices: a 7/6-column die
  (14/12 slices) fails the allocator outright (IndexError in xs_topo.nfr). So "7 col" = keep 8 slice columns (16 slices) with
  14 frame columns: 840 + 14 x 1445.5 + 8 x 1302.8 = 31.5 mm with compact ends (fits); "6 col" = 12 frame columns, MU end
  slices 2512.4: 31.2 mm (fits). Service band then as today's width -> co-located G4 16 services, all row-0 frames dropped.
- Frames: 7-equiv 98 (112 positions - 14 row-0); 6-equiv 84 (96 - 12). Actual allocator (capacity_cols.py, probes_lt112.txt):
  FAIL at 98 / 84 and even at 108 frames: 'a_proj one-phase capacity wq_a 320 rows' vs 70 / 60 / 77 -> one-phase dense needs 112.
- Dense split over 2 consecutive stage die-groups (dense_split_model.py, scaled from the actual 112 probes, validated: F112 = 139):
  | frames | stages | dies | AR/user G16 -> G4 | MTP/user G16 -> G4 |
  | 112 one-phase | 139 | 640 | 1,011.8 -> 978.4 | 2,991.2 -> 2,949.9 |
  | 98 split | 161 | 728 | 1,003.3 -> 970.2 | 2,973.3 -> 2,932.3 |
  | 84 split | 201 | 888 | 988.2 -> 955.6 | 2,941.4 -> 2,900.8 |
  Inter-die traffic: the A group forwards its half of the a_proj outputs (q_a/kv_a latent ~1.06 k values ~2.1 KB/token/layer) on
  the existing stage link with x; no new link class. MU users not modelled. MTP < 3,000 floor in every G4 row (already at 112).
- Needs a compiler feature (dense ownership over 2 die-groups / multiphase a_proj) before any exact receipt; not built here.
