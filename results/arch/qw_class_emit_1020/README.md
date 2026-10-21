
## Second takeover handback, 23:07 PT

Source is pushed through 3ec0cf38c. It includes directional reservations,
actual-outline packing with matching-bit <=405um checks, final GEN facts 6926,
the production receiving-clock reset repair ed5, pinned g5 clocking and regional
reset lookup, and the scalar reset-lane data / wide gate-enable join repair.
Six component checks pass. Actual closed TT/FF/SS views bind both generated
classes at full width (2 masters, 4 instances); a missing native row is refused.
Full production geometry and native binding remain unqualified.

All three GEN attempts are terminal and preserved:
- classgen2220: maximum envelope exhausts tree-pad sites (q3h_col_47_1, pad0).
- classpack2247: compact planning passes that stage; scalar reset.b -> wide.en
  composition bug is then exposed, fixed in 3ec0cf38c with regression evidence.
- classpack2258: fixed composition reaches actual closed-outline packing, which
  refuses rly_dv_ch_E1_ar_ard_0 (qfd_landh0_600_EN_104x106): no legal <=405um site,
  last blocker dvs_E2. Full log is committed under compact_geometry_fail/.
  Remote unit oth-ubuntu-2140011-1792562322, PID2140037 has exited.

The bind report hid intermediate/reset families. Actual old g5 die.v contains
1063 data frames (91 rlyh0, 373 rlyh, 508 landh0, 91 landh) and 17 reset frames
(4 rlyr0, 8 rlyr, 5 rlyrl): total1080. The running-source snapshots lack used
views for rlyh_1_SN (104 instances), landh_1_EW (8), rlyr_1_EN (2), rlyrl_1_NE (2).
Current main already contains rlyh_1_SN and landh_1_EW; use actual main views for
those two. The conventional canonical main view paths for rlyr_1_EN and
rlyrl_1_NE remain absent. Verify archive/provenance or close them; no waiver.

Future full-case binding must set OT_BIND_FWD_CLASSES=1 so intermediate/reset
stations cannot hide in the plain-relay skip, then run audit_fwd_class_bind.py.
The regional A/B source work belongs to the parent. No combined GEN was launched.
No further source, test, launch or merge work after CLAUDE IS BACK.
