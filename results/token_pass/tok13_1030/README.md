# TOK-13 (2026-10-30): HBM exact exposures on d41c + V-A; S81 station-form pricing

Model: DS native S2 (tools/hgi_sim/ds_native_timing.py), base 576702.4178 (asserted), record IDX+31 SU+3 = 610734.93 = 1799.79 tok/s.
Floor 1721.8 (= 1812.4 - 5 %). Extra terms are per record; IDX value REPLACES the record IDX 31 (TOK-12 convention).

Exact exposure map (d41c die_plan, RTL read):
- South ring: COLL ring B is a 2-stop NW<->NE ring (tools/hbm_b2/make_wiring.py W-RING); L700 18 / L701 21 vs Northern 11.
  1-cross COLL = +10, 2-cross (ALL_REDUCE_SUM / GROUP_REDUCE_MCAST) = +7+10 = +17 (TOK-12 pair17/cross = bound).
- EP flit hub->PHY 17 / PHY->hub 19 run parallel to EP_S1 L200/L201 19/19: +0. sm3->hub L721 7 <= sibling max 8: +0.
- tnode: HC_PRE_NORM +48 / HC_POST +32 per record.
- SFU: per SU.sfu record (246 of 4120) = 2*(max tap-2) + 2*(max ctl<->lane-2); hub->ctl issued ahead (bound row adds it).
- L28: SM +1.

Files: price_tok13.py (L1 rows; L1 later found unbuildable, HBM-LOC-1 15:57), price_tok13b.py (V-A plan of record + recovery
options), price_tok13c.py (lane-core gather), *.log / *_price.json. s81_stform_terms.py(.json): S81 composer terms.
