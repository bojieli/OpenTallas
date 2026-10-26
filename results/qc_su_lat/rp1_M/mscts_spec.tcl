# QC-SU-LAT rp1 variant M (2026-10-26): structured MSCTS for qfd_dv_s8_crh_rp1 259.2 x 276.48 (was TritonCTS + core_taps, TT 383).
# ck pin S face (19.93, 0). Sinks (f62 render): S clusters at both lower corners, W column x 0-43 and E column x 218-260 beside
# the two SRAMs (x 43.2-217.9, y 86.4-156.9 / 181.4-251.9). Trunk BUFx16f, 110-um equal stages (L_max 405 -> 4 stages).
set ot_ms_port ck
set ot_ms_root {20 6}
set ot_ms_taps {
  {SW {20 6 30 6 30 14}            {{0 0 120 40}}}
  {SE {20 6 215 6 215 14}          {{120 0 260 40}}}
  {W0 {20 6 22 6 22 100}           {{0 40 43 140}}}
  {W1 {20 6 22 6 22 175 30 175}    {{0 140 43 280}}}
  {E0 {20 6 236 6 236 105}         {{218 40 260 140}}}
  {E1 {20 6 236 6 236 195}         {{218 140 260 280}}}
}
set ot_ms_macros {
  {g_crb*0*.u_m W0 {36.5 86.7}}
  {g_crb*1*.u_m W1 {36.5 182.0}}
}
