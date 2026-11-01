# DIE-QC-58A: QC A0 NK/NL variant (A) = declared frame + A0 frame event + V3 CTS (COORD 22:5x ruling (3))

Result: variant (A) does NOT pass the CTS structural FF hold gate (orfs_hold_mm OT_HOLD_STRUCTURAL, ws >= -100) on
either tile, at any frame. The frame only trades I2R against R2O. The binding term is the frame-independent R2R floor
(face register -> gated body register across the 37-ICG tree split): NK -121.10, NL -107.77. TT setup at CTS also
fails on the ICG enable paths (NK u_hop_node/ENA -238.68, NL u_hop_ck/ENA -153.32 after CTS setup repair). Kit LEC is
NOT EQUIVALENT on both DIE-QC-34 netlists (7 points u_me.nb[0..6]; nb_t removed by synthesis), with both the kit
lec.py and main tools/die_plan/lec.py. No route and no sign-off.

## Frame measurement (meas58a.tcl, DIE-QC-57d V3 CTS ODBs, setRC_rcx placement RC, CHECKED)
| tile | input-face regs FF min / median / max | TT median / max |
|---|---|---|
| NK (1552) | 583.3 / 668.3 / 745.2 | 841.5 / 928.5 |
| NL (524)  | 631.8 / 672.1 / 686.2 | 849.1 / 863.7 |

## CTS probes on the reviewed rr1/rr2 3_place (V3 tree, no re-place; FF hold ws / true-failing endpoints, CHECKED cts_probe.log)
| kit frame TT/FF | NK | NL |
|---|---|---|
| DIE-QC-18 declared 665.8/576.5 (NK), 692.6/601.9 (NL) (DIE-QC-57d) | -179.32 / 3026 (I2R -179, R2R -121) | -108.47 / 2101 |
| max face 928.5/745.2 (NK), 863.7/686.2 (NL) | -169.71 / 2687 (R2O side) | -107.77 / 2318 |
| median face 841.5/668.3 (NK), 849.1/672.1 (NL) = this event | -121.10 / 3398 | -107.77 / 2357 (I2R 268@-38, R2O 516@-45, R2R 1573@-108) |

The event commits the MEDIAN frame (DIE-QC-18 form, mk_ev_a0icg2.py): it is the frame that keeps both I2R and R2O inside
the -100 limit. G0C plan_qc52 base vs event: identical findings (3 ERR / 320 WARN, 0 new / 0 gone).
Scratch: intel2:/srv/opentallas-scratch2/claude/die-qc-58a/{meas,kits/*f58,kits/*med58,g0c_*}.
