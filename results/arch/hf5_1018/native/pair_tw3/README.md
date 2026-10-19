TW3-SMHATTN 10-19: link-pair native check for smh_attn front children fc_xl -> fc_xr2 (u_rw/u_re) -> fc_b.
Views: fc_xl c600feccf (smh_fcxl_ref_p40-r1-9214bae8b), fc_b 245485d92 (smh_fcb_ref_p40-r1-9214bae8b),
fc_xr2 arg2 1a1dc1acb (smn_fcxr2_ref_fa-r2-dd7fca4ca-arg2). Tools: tools/hier_contract from origin/main.
Per bit: launch(O-R, TT) + capture(S+R, TT) vs 410 = 220+190 (both tiles clocked at their boundary mean).
Own-R: fc_xl FAIL launch 261.4 (11 xw_w pins), fc_b FAIL capture 214.2 (11 xi pins); no single C passes either
(fc_xl window C>=355.8 & <=327.7; fc_b C>=273.4 & <=269.1). Spread fc_xl 42.3/41.0, fc_b 36.6/31.1 (PASS).
Pair vs arg2: xl.xw_w->xr2.xi 6 bits >410 (worst 449.5 bit 1199), xr2.xo->b.xi 32 bits >410 (worst 444.4 bit 462).
arg2 is being replaced by fc_xr2 r4 (no boundary hold pads, H.STA.BLK.14.4): re-run pair_audit.py with the r4 view;
if both links <=410 fc_xl/fc_b bind as-is (0 routes); else re-route fc_xl/fc_b with flops at those 11 pins.
