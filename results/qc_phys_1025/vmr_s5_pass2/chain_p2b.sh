#!/bin/bash
# QC-PHYS 2026-10-25: pass-2 hold step re-run after the ot_ms_assign_corr unit fix (set_assigned_delay takes user units ps,
# the 1e-12 factor made every corrected trunk arc ~0 ps -> bogus -201 ps), then route + RCX + signoff tt,ff.
set -uo pipefail
cd /srv/opentallas-scratch2/claude/qc-cqb/vmr_s5
./hold_s5.sh || exit 1
./run_s5.sh rt do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc do-6_1_fill do-6_1_fill.sdc do-6_report do-generate_abstract || exit 2
python3 signoff.py run --base /srv/opentallas-scratch2/claude/qc-cqb/vmr_s5/run/results/asap7/kq_qfd_dv_s8x_vmr_rw60/base --kit /srv/opentallas-scratch2/claude/qc-cqb/vmr_s5 --out /srv/opentallas-scratch2/claude/qc-cqb/vmr_s5/signoff --corners tt,ff > signoff.log 2>&1
tail -5 signoff.log
