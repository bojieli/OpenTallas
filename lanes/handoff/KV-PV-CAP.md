# KV-PV-CAP handoff (Opus 5.5, COORD split 11-23 21:0x PST)
Job: pv family over 400k placed cap -> census + structural row on KV-ALLFIX current plan, PRE + scoped strict bind, ROW-REBASED to KV-ALLFIX cc FABLE-RC-KV.
I hold the kv3_pv_v3 D29 wave hold (hold_items, kit_wave eb9e50a; from KV-PREGRT-STALL): release with kit_wave_edit when my row is in.
## Census (posted 21:07)
- D28 kits: v3 synth 425.6k (196k seq + 172k QN INV) -> nontap placed 574k + 92.5k taps; v6 (unsplit 2160) synth 438k -> 686k + 177k taps. pad-delay pd* chains dominate.
- Setup: v3 -738 bin_i_astk_E -> bout_o_vport_E_N_vo_d2_p (V3FT row), -721 u_rrl_54 -> cland_fstart (KV-PV-RSTRELAY owns); v6 -548 cross-type 2160 um.
- A3f/K3g already hold PADRAM (pad_ram min_d 8, 31 types), row B split, V3FT.
## Measuring (lane dir /srv/opentallas-scratch2/claude/kv-pv-cap on epyc8 + epyc11)
- stage1.py (epyc8): kit_rtl + PADRAM pass per pv type on D29 apply K3g (plan_c 324af451f9be) -> k3g/<type>/{files.f,top,dram.json}. log s1.otrun.log.
- stage2.sh (epyc11): yosys generic synth in docker per type dir, libs dir libs/*_tt.lib as blackboxes. cal/kv3_pv_v3_d28 = calibration vs real 425.6k.
## Rebase target
KV-ALLFIX: A3f failed G0; A3g (A3d b258e3e34f22 minus HUBA1 + IUSPLIT) gating on epyc10, rt 9b19260c1cde. Ask ad9ba7d264a476287 for the final sha.
