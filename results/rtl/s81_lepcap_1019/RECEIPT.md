# LEPCAP 10-19 bench receipt (Verilator 5.050, ot-epyc6 /srv/opentallas-scratch/claude/s81-lepcap/src-eec2dca41)
RTL eec2dca41 (ot_s81sl_lep_core IN_PIPE, ot_s81sl_lep_vcopy), bench tools/s81_dv/mu_kit_bench.sh (MU_RX_SRAM=1 MU_IN_PIPE=1).
- Added edges: +1 on ro, t_host, t_kd, mu_c of ot_s81sl_lep_mu_a / _h at IN_PIPE 1 (all four together; relative timing unchanged).
  Priced by the die schedule (LEAD2-S81 INBOX); TB reference fed through one face register -> every same-cycle check holds.
- PASS: pass_lepmu_s1/s5, pass_lepmuh_s1/s5 (IN_PIPE 1); pass_inpipe0_lepmu_s1 / pass_inpipe0_lepmuh_s1 (default 0 unchanged); lint_inpipe.
- Mutants FAIL (witnesses): lepmu TAGDROP/LANDCUT/STALEHD/VSKEW; lepmuh HSTAMP/TAGDROP/LANDCUT/KSOFF/VSKEW.
