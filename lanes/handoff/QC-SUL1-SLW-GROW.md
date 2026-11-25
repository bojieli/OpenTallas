# QC-SUL1-SLW-GROW lane memory (child of QC-SUL1-SLW-REFLOOR, parent QC-ALLFIX)

Task (QC-ALLFIX ruling 08:4x-2): slw_su_l1 +86.4 um x growth as a die-level row SUL1-SLW-GROW, separate from SUL1-SLW-CHAN (27e842fb253f).
Base C1o v13 aa3a14fb7484 / sidecar a142fe516f24 (epyc10 launch_c1o_bind). Work dir epyc10 /srv/opentallas-scratch2/claude/QC-SUL1-SLW-GROW.

## Design (11-25 09:0x)
- W quads only (W5..W0, 6 x 86.4): die W 31216.32 -> 31734.72. E quads + W strip rigid (E shifts +518.4).
- su/fw/ctl/hc rows: column-0 types (slw_su_l1 x2, slw_fw x4, slw_st_a x4, slw_hc0 x2; all W-only) widen +86.4 at E;
  frame stretch phi x[432,622.08]->[432,708.48] (same phi in all four, N/S seams between them stay aligned).
  su_l1 S face and hc0 N face (abut cb-left, unmoved) keep their windows/face pins.
- cb rows: slab at local 1235.52 (cb-left|cb-right), DX gap -> die.channels rows (_01 rows carry a00/nb_i12 across; _00 voids).
- NS fixups: su_c cws1 -> bn_00 bc_i10, hc1 cw_n1 -> tn_00 bc_i10: cb-left bc_i10 landing +86.4 in type frame.
  cbn_q00__cl622f65d2 shared with E0 -> W clone cbn_q00__cl622f65d2__gx86 (11 inst); cbn_q00__cld7bf7197 in place.
- Script grow_x.py (generic: also run on SLW-CHAN 27e842fb253f, HC0-GROW v4/v5, PHY 98201d985d5a for cross-check).
- Host note: die-priority ot-run on epyc10 blocked by DIE-RESERVE disk (645 GB reserved); small jobs run normal priority.
