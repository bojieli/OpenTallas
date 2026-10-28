KV-PLAN-DELTA-6 FT what-if coupons (ft_station_probe --segmented --iterations 50 --signal-max M7, derate 0.75, OpenROAD GRT).
Run dir: intel2:/srv/opentallas-scratch2/claude/kv-plan-d6-1027/ft/<coupon>/grt/route.log
Result: removing all ~3,280 approved FT bits (hub_Wi ft5+ft6, v8 ft4/L663) leaves ~25k M6 overflow in each tile at only 20-25% M6 usage
-> residual is a localized W-face hotspot (congestion.rpt top gcells at tile W face), not bulk capacity. Approved move is necessary-insufficient.
d6_ft.py (full move) FAILS: neighbour faces (pv/hgi/hg rows) hold one ~1118-bit <=8 b/um window per row off macro rows (CLEAR 20 um); a 2nd bundle has no window.
