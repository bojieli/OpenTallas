# DIE-QC-101 handoff (QC die owner; COORD coordinates) -- started 2026-11-13 17:41 PST

## Scope
QC ONE FINAL event s29 (R-PROFILE/R-MINIMAL): strict bind + LATCHECK clean -> adopt in wave with KIT-OPS-2 -> relaunch all QC types;
pilot one type per family in parallel (OWNER: do not wait for pilots). Coordinate KIT-FIX-F (kit snapshot / srcs27 losses).

## Where
- Event tree (Codex, reused): epyc9 /srv/opentallas-scratch2/claude/wt/qc-s29-tree2 (branch claude/qc-s29-tree2-1113 @1e3b302be8; plan files untracked in POR).
- Codex scripts: epyc9 /srv/opentallas-scratch2/claude/qc-s29-reach (finish_bind_codex.sh, run_bind_isolated_codex.sh).
- My dir: epyc9 /srv/opentallas-scratch2/claude/die-qc-101 (kitwin_f547_delta.json, zz_s29_qc101_win.json copy).
- Bind outputs: epyc9 /srv/opentallas-scratch2/claude/qc-s28-hf1c/bind/bind_s29_qc101{a,w}_{pre,final}(.log).
- Local scratch: localhost scratchpad qc101/ (post.sh = queue poster, bind_*.log ot-run client logs).

## Event content
- forms f547f1a6f7a4 (POR zz_postphase_reset_ctl8inc1_geometry_codex.json) + per-port windows (kitwin delta from qc-region-1/htdme2/gate/kitwin.json,
  CTL __v1 copy parent) = POR zz_s29_qc101_win.json 1c34c43d3544. Identity sidecar qc-s29-reach/side_ctl8inc2_identities_codex.json 2dc5994fc2a0.
- Regional clock: f547 STA/K proof = qc-region-1/htdme2 (third-chain recipe; CA FAIL 0, START 763 clean).
- OPEN: extra c_* clock entries (320 ports / 11 types > 208 ps, capped at 208); advisory under R-MINIMAL.

## State
- 17:46 STATE posted (coord 3ba28f80475). Binds running: s29_qc101a (f547), s29_qc101w (windowed = adoption candidate).

## 19:0x state (read first after a restart)
- Plan chain (epyc9 tree2 POR, copies in die-qc-101/): f547 -> _win (per-port windows) -> _f (+clock.pregrt_ff_hold) -> _g (cbn_q00__cl622f65d2 relay 120/121
  rebalance, fix_cbn622_relay.py) -> _h/_i (cbn_q00__cldbcda913: ALL hard ring children deferred to soft = HELD type, soft_rings_type.py)
  -> _j (fe cl1cbb7497 start_0 local reset dropped) -> _k (ALL landing_local_resets dropped die-wide, 1213 copies/115 types) and
  _k2 (fe family only, 130 copies). Binds k and k2 RUNNING in parallel (finish_bind_codex.sh: pre -> R8 derive -> final).
- Bind EMITs stop at the first error; each run ~15 min (pre) + R8 derive + final.
- Adoption packet once a final bind is 0: plan = POR/zz_s29_qc101_<x>.json, src = tree2 (protect from cleanup), kit_rtl.bind_out =
  qc-s28-hf1c/bind/bind_s29_qc101<x>_final, asbuilt = tree2 runtime zz_manifest_iso_s29_qc101<x>_final.json, --clock-landing =
  tree2 runtime zz_sidecar_s29_qc101<x>_final.json; hold only cbn_q00__cldbcda913 (+phy_* as before); drop PHYS-QC item_inputs.
- D8 child local32 SIGNED (TT +40.94 / FF +14.96 / DRC 0); parent adoption needs ring knobs DSREP4/READ32/WRITE16/RSTREP73/PLACEREP1.
- OPEN: coll_s clk_serdes/clk_coll windows + region (PHYS-QC); c_* extra clock entries; local reset re-pick after adoption.
