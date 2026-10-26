# QC-SU-LAT vmr variant B (2026-10-26): A (110-um BUFx16f 3-stage trunk) + SW (1080 sinks) and W1 (1115) split in two taps each
# so no tap exceeds ~640 sinks (shallower local tree, smaller pad window). Pins/placement/macros unchanged (vmr_s6kc 3_place).
set ot_ms_port ck
set ot_ms_root {93 6}
set ot_ms_taps {
  {SWa {93 6 57 6 57 14}            {{40 0 75 80}}}
  {SWb {93 6 92 6 92 14}            {{75 0 110 80}}}
  {SEa {93 6 125 6 125 12}          {{110 0 160 80}}}
  {SEb {93 6 195 6 195 14}          {{160 0 260 80}}}
  {W0 {93 6 25 6 25 110}            {{0 0 40 150}}}
  {W1a {93 6 33 6 33 180 20 180}    {{0 150 40 210}}}
  {W1b {93 6 33 6 33 245 20 245}    {{0 210 40 280}}}
  {E  {93 6 232 6 232 150}          {{222 80 260 280}}}
}
set ot_ms_macros {
  {g_bank*0*.u_m W0 {37.0 87.2}}
  {g_bank*1*.u_m W1a {37.0 182.2}}
}
