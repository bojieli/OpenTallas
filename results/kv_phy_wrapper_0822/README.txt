MODELED PHY interface proposal, current event27f/native26b binding,0cycles/0parentABI change.
Sources: inputs/plan_e27f.json.gz (unaltered current plan), inputs/kv3_phy_part.sv (actual native bound PHY wrapper).
Reproduce:
 python3 results/kv_phy_wrapper_0822/fit_interface.py --plan results/kv_phy_wrapper_0822/inputs/plan_e27f.json.gz --rtl results/kv_phy_wrapper_0822/inputs/kv3_phy_part.sv --out results/kv_phy_wrapper_0822/fit

fit/fit.json contains complete analog reserve polygons and unchanged gross footprint. fit/digital_layout.json is native per-bit macro pin geometry decoded from real packed return words. fit/views contains modeled TT/FF/liberty/LEF/blackbox. The pinmacro alone is not a whole PHY footprint; materialize all analog reserve and PG before any wrapper P&R. G1 record in results/geom_review/kv_phy_interface_0822.md.
No physical release, no license/vendor dimensions, no timing qualification, no area saving.
