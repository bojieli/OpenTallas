# dsdv_seq_host_g -- S81 seq_host re-pack for the RL1 lk successor s10g (DIAGNOSTIC kit)

S81-SEQHP-1021, branch `claude/s81-seqhp-1021`. Spec `tools/ref_tile/specs_pl_seq/dsdv_seq_host_g.json` (generator
`tools/ref_tile/specs_pl_seq/mk_dsdv_seq_host_gh.py`, from `_d43`); parent RTL `rtl/dsrom_sys/s81_dv/unit/dsdv_seq_host_c.sv` (wires only, RL 1).
Outline / sq y / vc y: 432.0 x 972.0 518.4 712.8 (all um). lk s10g = 345.6 x 432 (p192 masters, claude/s81-shlk-1021 @254543064, gating).

- u_l0 dsdv_sh_lk: DECLARED PIN STAND-IN `standin/dsdv_sh_lk` (STANDIN_NOT_A_VIEW; built by `dsdv_seq_host_g/standin/mk_standin.py` from the
  s10f --cts stand-in: s10g outline, per-face pin regions of the s10g kit, face order alphabetical as the tool places it, positions scaled
  + snapped to the 0.192 track phase, OBS scaled, s10f timing models). at (43.2, 43.2).
- u_l1 dsdv_sh_sq: CLOSED view `dsdv_sh_sq/views/dsdv_sh_sq` at (86.4, sq y). u_l2 dsdv_sh_vc: CLOSED view `dsdv_sh_vc/views/dsdv_sh_vc` at (86.4, vc y).
- 43.2 channels lk|sq and sq|vc (~1,000 lk N -> sq S nets; children capped M5, parent M6/M7 over them); N band as d43.
- Die seqhost slot = the outline. Swap the stand-in for the closed s10g view when it closes, regate, submit_exact.
