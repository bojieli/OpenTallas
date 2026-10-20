# HBM-FCX-NATIVE receipt (2026-10-19)

fc_xr2 r4 `smn_fcxr2_ref_fa-r4-637a35abf` is CLOSED (record main 12615c9e9, TT +353.22 / FF +13.25 ps, DRC 0). Native audit PASS: launch 155.8 <=220 ps, capture 100.0 <=190 ps; TT/FF pin-flop spread 76.6/72.4 <=80 ps; no combinational pins. This receipt qualifies the native interface; the CLOSED record remains TT pathfinding evidence.

The TW3-SMHATTN per-bit pair check passes with exact historical fc_xl c600feccf and fc_b 245485d92: 2,069 matched bits per link, xl.xw_w->xr2.xi worst 341.0 ps, xr2.xo->b.xi worst 326.5 ps, zero bits over 410 ps. The <=410 ps rule is the existing TT launch+capture contract, with each child compensated to its own boundary mean. fc_xl/fc_b own native FAILs remain preserved; this is pair qualification, not an own-native waiver on other links.

A second check with current main fc_xl re-export 184cb9f5e also passes (worst 347.1 ps). fc_b 245485d92 is not present on main as of 47c0b67c45: integration must import that exact closed view before binding. fc_xr2 r4 replaces u_rw/u_re; preserve the previously handed-off calendar +1 edge. xs qualification remains separate, so H.STA.BLK.14.1 stays open.

## Reproduce

From an isolated worktree on tool_base in sources.json, restore fc_xl views from c600feccf and fc_b views from 245485d92 (worktree only), retain r4 view from main, then run:

```
python3 tools/hier_contract/native_pin_audit.py --view physical/ref_tile/smn_fcxr2_ref_fa/views/ot_hbm_accel_smh_fc_xr2
python3 results/arch/hbm_fcx_native_1019/pair_audit.py
```

sources.json pins every Liberty and insertion.json by SHA256. pair_audit.py is unchanged from claude/hf5-1018:results/arch/hf5_1018/native/pair_tw3/pair_audit.py. No RTL, clocks, data constraints, masks, or schedule changes are made by this audit.
