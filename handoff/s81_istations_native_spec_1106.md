# S81 kit_istations on flat native binds (kv_leaf t1/t3/t4/t5, col_h9/h10): successor spec

DIE-S81-69, 2026-11-06 10:5x. Status: COORD DEFAULT (A) of 10:02 (realise the plan stations). The next DIE-S81 lane writes it.

## Where things stand
- The plan side is fixed, pending merge: the hi/ho coverage (claude/die-s81-69-hcov-1106@9769adc775a) plus the tool (claude/die-s81-69-hlanes-1106@05bbeb31243). With both, kit_istations passes on a synthetic `ot_s81sl_leaf u_lf` bind.
- Real kits still stop with `kit_istations: core<->core stations planned but the bound module has no ot_s81sl_leaf u_lf`.
  - The s81p binds are flat. Examples: `u_u_vn_u_a`, `u_u_vp_g_ln_<l>_u_l`.
  - Source: epyc5 /srv/opentallas-scratch3/claude/die-s81-69/hl_verify/t3/s81p_ot_s81sl_kv_leaf__t3_bound.sv:3505-3548.
- The as-built leaf was elaborated with CS_*_D = 0, so every station is a pass-through assign.
  - `w_u_vp_g_hig_<g>_u_cst_<k>_Y`: the shared hi group (GS_IN), a concatenation of 4 lanes.
  - `w_u_vp_g_ln_<l>_u_cst_hi_<k>_Y`: a lane slice of the hig group.
  - `w_u_vp_g_hog_<g>_u_cst_<k>_Y`
  - `w_u_vp_g_ln_<l>_u_cst_ho_<k>_Y` (= `u_l_o` / `{fault, vo}`).
  - Note: here `<k>` is the bus element (0 = data, 1 = valid). It is NOT the stage index.
- The plan puts depth 1 on hi/ho (also sw/swr/rar etc. on other leaves), "+1 cycle(s)". As built, the RTL has 0 stages, so that +1 cycle exists nowhere. The die latency table has no core stations either.
- col_h9/h10 (`core:u_r0.u_s0.st -> u_r0.u_t0`, 1-2 FIRM stations):
  - The bound RTL wires `w_u_r0_u_s0_st[1:0]` straight into `u_t0 .c0`, with no ot_dp_st.
  - Source: col_h10_r0_p1__t1__cl574cc59d attempt_9 _bound.sv:2454/2586.

## Preferred form (A1): re-bind with the plan depths, not a netlist patch
1. Check first whether the native bind step accepts leaf parameter overrides (CS_HI_D, CS_HO_D, CS_H_G, CS_HI_GS, CS_HO_GS, and the other CS_*_D).
2. If it does:
   - Bind each kv_leaf type with the depths kit_istations computes: `depth` per class, `want` in core_stations().
   - The leaf's own CS chains then carry the schedule compensation they were designed with (static schedule kept by the leaf RTL).
   - LEC/EQ: compare against the hierarchical leaf elaborated with the same CS_* values, which is the normal bind EQ.
3. kit_istations native mode then needs:
   - Detection: no `ot_s81sl_leaf u_lf` but bind_overlay says native.
   - Skip the CS param rewrite, since the depths are already bound. Assert that the bound depths equal the plan depths. The assert can read the bind record or count the stage regs.
   - Map station names to flat globs. For example, `u_lf.u_vp.g_ln[l].u_cst_hi.gd.s[j].u` becomes `*u_vp?g_ln_<l>_u_cst_hi*` (the flattened reg names).
   - CORE_CLASSES regexes then match `core:u_vn_u_a...`-style flat launch names. Alternatively, keep the plan's hierarchical names and translate them with a name map from the bind.

## Finding (10:5x): where the depths live
- The release sets the leaf depths at the slice level. `rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice.sv:247-301` has per-leaf `LF_CS_HI_D/LF_CS_HO_D/LF_CS_HI_GS/LF_CS_HO_GS` (4 bits per leaf k). All of them default to 0.
- The native bind captured that 0. So (A1) means:
  1. Set the slice/die instance's `LF_CS_*[4k+:4]` for the leaf types to the plan depths.
  2. Re-bind natively.
- Inside vp the timeline is derived from the depths, so the leaf schedule stays self-consistent:
  - `u_wi` delay = HPL+HQX+CS_HI_D+CS_HO_D, and `u_wv` likewise (`ot_s81sl_vp.sv:51-52, 322-323`).
  - hc_post write-back latency grows by CS_HI_D+CS_HO_D.
- The open question for the S81 schedule owner: is the slice-level write-back latency observed outside the leaf, by the token schedule or the compiler?
  - If yes, re-price it there. Pin cycles are cheap per owner rule 11-03.
  - If no, A1 is a parameter-only change.

## Fallback (A2): netlist patch on the flat bind
Insert d registered stages on each class assign, keeping data and valid aligned and covering all 16 lanes. This changes cycles in a flat netlist, so it needs both of these before any count:
- An EQ-with-latency proof.
- A sign-off by the S81 schedule owner on the leaf's hi/ho timing (the downstream controls expect 0 stages as built).

Use A2 only if A1 is impossible.

## col st -> t0
This is the same decision: the stations exist only in the plan.
- (A1) means the col bind realises its st station (2 bits, one ot_dp_st per stage) and the schedule owner confirms the +1.
- Otherwise drop the col st stations from the plan and close the 657 um hop by buffering. That is (B), and needs a COORD ruling.

## Acceptance
- kit_topology prepare_stations passes on the real kv_leaf t1/t3/t4/t5 kits.
- Bound depths equal plan depths.
- LEC EQ.
- face_guard PASS.
- Then KW-FIX-22 relaunches the rows as one batch.
