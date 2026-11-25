# QC-TTCTLM-DEPTH handoff (lane memory), started by QC-ALLFIX 11-24 17:15 PST
Job: C1j tt_ctlm GRT probe setup -839.7 / hold -113.3 (kit private/QC-ALLFIX/tt_ctlm_1124114913 on intel1).
Dir: intel1 /srv/opentallas-scratch2/claude/QC-TTCTLM-DEPTH/{in,rs,tmp}. in/t20_staged.sv = kit core 43059362f4bf (T20); in/t20_raw.sv = unstaged (f16_stage.sh round trip exact).
CAUSE: kit core is the UN-resynthesized generated bmath core (flat gates, keep_hierarchy, each gate mapped alone). Path u_11127 -> u_12845 = 71 bmath levels (190 STA cells), the known loop SCC around u_12820/u_12854 (QC-TTC-RETIME Howard 39.5 lv/reg). Only 1 endpoint above depth 38; next deepest 38.
Known fix: QC-TTC-RETIME/R2 ABC resynth (rs1, 71->22) + fix_po + fix_dd (+ replicate rep10 for class b), LEC with QC-TTC-R2/tool/lec_comb.sh. Never applied to T20.
HOLD -113: f16_auth[22] -> u_bin_f16_auth (ot_dp_st W83 on clk, no landing ring): vclk ideal 202.5 + min in -85 = launch 117.5 +14 buf; capture tap clk_t9 217.75 + unc 12.5 + hold 14.6 => need ~113 ps pad. Port-hold class, pad at ports / OT_GRT_PORT_HOLD_PORTS; not RTL.
STATE: resynth running (ot-run oth-ubuntu-4172784-1795569787, rs/run.sh -> rs/out_unkeep.sv).
