# NEW R0 profile1713 + PATH-QC-SRAMIF2 variant F (SRAM MY: macro clk pins on the E edge); 12 regional banks, max local cluster16/35um. No old RCX corrections.
# PATH-QC 10-25 TRIAL bt (GEOM-REVIEW-5 20:13 (b')): ONE band tap per SRAM row (branch node in the row top channel at x 177.1, region = full row width), macro leaf off its row band tap in the channel at x 268; S taps unchanged; MACRO_EARLY 0. twd1 banding (placement region) NOT yet applied.
# PATH-QC 10-25 WHAT-IF wi (diagnostic, REQ [PATH-QC-SRAMIF2-F-POSTCTS] fix (a)): each SRAM clock leaf fed from the W tap that owns its W-face write IF regs (was E tap) -> common path to the tap
set ot_ms_port ck
set ot_ms_root {177.132 6}
set ot_ms_taps {
 {S0 {177.132000 6 44.280000 6 44.280000 16} {{0.000000 0 88.560000 25.92}}}
 {S1 {177.132000 6 132.840000 6 132.840000 16} {{88.560000 0 177.120000 25.92}}}
 {S2 {177.132000 6 221.400000 6 221.400000 16} {{177.120000 0 265.680000 25.92}}}
 {S3 {177.132000 6 309.960000 6 309.960000 16} {{265.680000 0 354.240000 25.92}}}
 {B0 {177.132000 6 78.720000 6 78.720000 79.0 177.132000 79.0} {{0.000000 25.92 354.240000 79.2}}}
 {B1 {177.132000 6 78.720000 6 78.720000 135.0 177.132000 135.0} {{0.000000 79.2 354.240000 135.36}}}
 {B2 {177.132000 6 78.720000 6 78.720000 191.0 177.132000 191.0} {{0.000000 135.36 354.240000 191.52}}}
 {B3 {177.132000 6 78.720000 6 78.720000 245.0 177.132000 245.0} {{0.000000 191.52 354.240000 259.2}}}
}
set ot_ms_macros {
 {g_prog*0*.u_hi B0 {268.0 79.0}}
 {g_prog*0*.u_lo B1 {268.0 135.0}}
 {g_prog*1*.u_hi B2 {268.0 191.0}}
 {g_prog*1*.u_lo B3 {268.0 245.0}}
}
