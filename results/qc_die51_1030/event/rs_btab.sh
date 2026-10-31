#!/bin/bash
# DIE-QC-51: RE-SIGN BTAB P8eco SAME routed DB (copy of epyc2 die-qc-50/btab/P8eco) at flow-20261030-f-qc (QC-RP1-1 recipe)
D=/srv/opentallas-scratch2/claude/die-qc-51/btab
python3 -I /home/ubuntu/OpenTallas/tools/die_plan/resign.py run --kit $D/P8eco --tag flow-20261030-f-qc --repo /home/ubuntu/OpenTallas \
  --tools /srv/opentallas-scratch2/claude/signoff-sprint-5/t_ffa6bde25fb/tools/die_plan --out $D/btab_fqc --name qcbtab-fqc --lane DIE-QC-51 \
  --pincmp "signal pins 1318/1318 == plan_qc52 cores/su/qfd_dv_s8x_btab_pins_p8eco.json (extracted from this 6_final.def), outline 293.76x155.52 == plan_qc52 sle_su_c/slw_su_c u_suvm_u_vm8q_u_bt; plan_qc52 = last QC event (DIE-QC-51, READY pending)" \
  --note "routed DB = epyc2 die-qc-50/btab/P8eco (DIE-QC-50 P2 -> P4s15 PRD-SPEF-HOLD -> P8eco route-keeping post-route ECO) copied byte-exact by tar to intel2 die-qc-51/btab/P8eco" "$@"
