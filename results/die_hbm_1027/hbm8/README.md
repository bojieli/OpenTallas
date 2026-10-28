# DIE-HBM-8 (2026-10-28) — ESTIMATES only (no build, no adoption)

Basis: plan C20j die_plan.json (intel2 codex-hbm-die-1028/c20j), ds S2 schedule (accepted_cost, g25 rank0, 4,120 records).
Tool runs CHECKED; models UNCHECKED. COORD 07:29 conditions (1)-(5) + 12.16 / 12.16e + COORD 08:0x CLK-LOCAL note.

## (1) Strict bind (sbind_canon, intel2 pid 3719537)
Not finished at write time: elab done 07:25 (asbuilt.json 121 MB), bind step running >30 min, bind.log empty. Not polled further.
Collect: /srv/opentallas-scratch2/claude/die-hbm-7/sbind_canon/bind_report.json (kinds). Expected fail-closed on the 14 open slices
+ 3 root slots + 88 fold provider nets.

## (2) B per-op link-bound check — bperop/
b_perop.py: link width W per unit and direction = B-eligible NW-hub station bits (c20j). Per record S = max(bits_in/W_in,
bits_out/W_out) cycles of full-width link use (descriptor n x m x esz; VM word 4 B). rho = S / cost. Under 2:1 a record costs
c + S + 1 (conservative) or max(c, 2S) + 1 (optimistic).
| unit | rho (stream/cycles) | link-bound records (S > c/2) | B cost alone cons / opt |
|---|---|---|---|
| SM | 0.832 | 923 / 1095 ops (all MATVEC, 89.3k of 126.9k cyc) | 14.4 / 15.5 % |
| SU | 0.039 | 4 / 1356 records, 0 / 412 ops | 0.41 / 0.21 % |
| FUSED | 0.098 | 0 / 201 | 1.22 / 0.03 % |
| IDX | 0.084 | 0 / 48 | 0.28 / 0.01 % |
| HC | 0.006 | 0 / 80 | 0.00 / 0.00 % |
- SM is link-bound: its hub links carry the HBM weight stream at full width; 2:1 doubles every matvec. SU/IDX/HC/FUSED are
  latency-bound (small per-token vectors, depth-dominated).
- CHOSEN B SET = {SU, IDX, HC, FUSED} (SM excluded): 0 of 741 ops link-bound; schedule cost 0.24 % (opt) - 1.91 % (cons) tok/s, <= 5 %.
- B on SM would cost ~15 % -> owner territory; not proposed (it does not close the faces either, see (3)).

## (3) A+B face ratios with hard-core spans subtracted — hub/
hub_face_net.py: 4x3 grid, capacity = 6/um x (face length - union of hard-core spans touching the face, halo 20 um); SA objective
on the net capacity ('_net'); hbm7-style SA scored net ('_rescore'). 3 seeds.
| form | NW worst (full / net) | NE worst (full / net) | faces > 1.0 (net) |
|---|---|---|---|
| A+B, B = chosen set (no SM) | 1.48-1.81 net | 1.42-1.70 net | 8-13 of 17 |
| A+B, B incl. SM (~15 % tok/s) | 1.16-1.31 net | 1.22-1.39 net | 4-9 of 17 |
| hbm7 SA placements rescored net | 9-93 (cores sit on the grid lines) | 3-54 | 7-11 |
VERDICT: FAIL (every face set has faces > 1.0). The worst faces are the vertical cuts (x-bisection: 3 x 1440 um = 4.32 mm,
25.9k pins vs ~35-38k bits); span subtraction is small there (0-160 um), the deficit is the hub's x-bisection transport.
What would fix it (not built, needs its own estimate):
- (a) Replicate the fan-out source cores per hub half (pgp, cxij_q, calendar, sucore, coll body, smw: the 33-35 % die-wide bits of
  hbm7) so their broadcast does not cross the x-bisection; area cost of the replicas. First candidate.
- (b) Region cuts in core channels (non-uniform grid) recover the full-length ratio but that is still 0.79-1.15 (no SM), so (b)
  alone does not close.
- (c) B on SM (~15 %) -> owner; still 1.16-1.39, so not sufficient.

## (4) Hub crossings in the LOCAL form (12.16 / 12.16e) — hub/hub_ca_local.py, ca_local_noSM_s2.json
Shared model only: locality.py score (clk_aocv g021, 0.21 %/mm, one-sided droop, class-B core latency 250/202.5, wander 5 %) +
cap_reading (= count_align_plan unchanged). v = 349 x 1.0485 = 365.9 ps/mm (CLK-LOCAL-EST-1 HBM value, ASSUMED). 12 cells =
regions; every face is a neighbour crossing (far links are hop chains of face crossings), 34 crossings per hub.
| feed | tree-edge unshared max | off-tree crossings | depth | fail | min margin | max lat |
|---|---|---|---|---|---|---|
| spine (PROPOSED) | 1.39 ns | 12 (6 face pairs, ~35k bits) | D4 34 | 0 | 138.7 NW / 235.7 NE ps | 5 |
| fish | 0.79 ns | 12 | D4 34 | 0 | 104.2 ps | 5 |
| top (die-wide form, STOPPED by 12.16e, reference) | - | 34 | D4 34 | 0 | 160.7 ps | 3 |
- Standard depth: D8 (smallest standard of 12.16 b(iii)); every crossing fits D4 on the bound, so D8 adds >= 4 T of high margin.
- Start / reset release: dedicated start port per feed edge, sync flop ON the forwarded spine at the fork tap (COORD 08:0x):
  unshared 0, width 20 ps, 11/11 edges clean (<= 208 ps). Reference: sync at child root 89.7 ps, at far leaf 145.3 ps, all clean.
  Reset release to both ring counters rides the same port: same bound.
- RESIDUAL: the 12 off-tree crossings close loops of up to 5.1-5.6 ns unshared (rows ua+ub). They pass (>= 138 ps at D4) but are
  long loops under 12.16 b(i); allowed only at >= 100 ps at D8 on the plan bound + built recheck (COORD 08:0x). Fix in the plan
  event: re-tree so the heavy pairs are tree edges.
- Die-wide: CLK-LOCAL-EST-1 HBM (claude/clk-local-est-1-1028@ff58db4baa): 7 FAIL (3 x T059<->T060, 4 unreached), all pass with
  spine-tap start sync; T059/T060 re-tree is a die plan-event item. Its T029 (8.2 x 4.3 mm, 2.29 ns insertion) is the hub as ONE
  region; the 4x3 hub regions above replace it (max cell insertion 0.64 ns).

## (5) Partition map: open slices, root slots, _mu1
- u_vmb_Q<k>_mu1 CONFIRMED a VM bank slot, not an MU bank: c20j type_views module_family hnx_vms_bank_q0_faces (same as u_vmb_Q<k>);
  canonical RTL (aliased_hbm_current_native_top.sv) instantiates vmb_SW<k>/vmb_SE<k> as hfd_vms_bank_native_q0_faces with sid 00/01,
  served by su_S*, smw_S*, calendar_S* (S role). '_mu1' names the bank's pairing with u_mu_fused_<2k+1> in the plan stations. The
  16 fold_bank_slot rows stand.
- 14 slices: STILL OPEN. Rule basis located: the plan's hard_cores per partition give the child split (IDX score: r/c/k/h hcol
  cores over b100-b103; SFU: lane0-3 b110, 4-8 b111, 9-13 b112, 14-15 + opstore_a/b + ctl b113; SU pgslice: lane_exp even + plain
  0_3/8_11 + softplus + pretree -> su_x0, odd + lane_exp_l + plain 4_7/12_15 + side_rest -> su_x1). The child-path -> core mapping
  needs the native split recipes (core_macros.json 'native family member'); per-child rules not written yet.
- 3 root slots: hb_ckgen (hfd_ckgen_nolink), u_mu_fused_programme (ot_hnx_fused_host_program), u_mu_fused_root
  (ot_hnx_fused_hub_n4ext) have NO content in any c20j partition. Proposed: root partition (hb_ckgen = the clock source at the
  feed root of the local form). Needs plan contents (canonical source/slot event).
