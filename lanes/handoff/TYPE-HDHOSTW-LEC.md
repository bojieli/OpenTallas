# TYPE-HDHOSTW-LEC handoff (2026-11-14 08:09 PST)
Problem: hd_host_w attempt_3 pre-route LEC NOT EQUIVALENT 298/56149.
Findings: see queue STATE line. (A) 266 u_ctl_tx hold[280..545] gold-only no-reset flops (fix: HOLD_REAL(1) on u_ctl_tx in host_w_core/host_ep_core). (B) 32 g_rb_safe SRAM r_ce/w_ce bb points banks 1..2 (under investigation).
Work dir: epyc9 /srv/opentallas-scratch2/claude/type-hdhostw-lec/kitA (patched RTL, old netlist), job container type-hdhostw-lec-A, result file kitA/lec_rc + kitA/lec/lec.json.
Scripts: scratchpad cone.py (AIG cone dump gold/gate from lec/*.map).
