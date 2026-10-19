# G7 (S81-LBGAP/G2 finding) reconciled by S81-LINKTO, 10-18

The S81-LBGAP G7 audit found that the closed dsfd_coll_lane_w views (dscoll_lane_w_rt, dscoll_lane_w_cxea) were built
from a pinned snapshot (physical/ref_tile/dscoll_lane_w_rt/src/...). In that snapshot dsfd_coll_lane_w, ot_s81ph_coll_lane,
link_ep, link_gbx and mem1r1w differ from rtl/. The pinned_audit.py re-run (claude/s81-lbgap-g2-1018 tool) is in
pinned_audit_lane.json. It still reports the 5 DIFF modules for dscoll_lane_w_rt.

The fix is to retire the snapshot views, not to keep them in lockstep. The p4l die needs CH_BOARD 700 + LCR 1 (TOKEN-XDIE-S81),
and the rt/cxea views do not carry that RTL (CH_BOARD 400), so they cannot serve the switched die anyway. The new kits
dscoll_lane_w_lt and dscoll_lane_e_lt list ONLY rtl/ files in SRCS, so the audit has no pinned source to check for them.
A die built from them elaborates exactly the rtl/ text.
Die bind action (S81-DIE7 DIE sub-lane): bind dsfd_coll_lane_w/_e to the *_lt views once they are CLOSED
(dv_bind --ref-tile-prefer dscoll_lane_w_lt,dscoll_lane_e_lt). Never bind dscoll_lane_w_rt or dscoll_lane_w_cxea in p4l.
