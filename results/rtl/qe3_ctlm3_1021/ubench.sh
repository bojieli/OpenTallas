#!/bin/bash
# QE3-CTLM3 unit benches with CALREG default flipped (1 = FQREG, 5 = FQREG+ISSUEFLAT): edge-identical expected
export PATH=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin:$PATH
for v in 1 5; do cd /srv/opentallas-scratch/claude/qe3-ctlm3/u/c$v/src
  for m in 0 34 2; do bash rtl/test/qwen_dv/calr_port/run_calr_port.sh /srv/opentallas-scratch/claude/qe3-ctlm3/u/c$v/cp_m$m $m > /srv/opentallas-scratch/claude/qe3-ctlm3/u/c$v/cp_m$m.log 2>&1; echo "C$v CALR_PORT_M$m rc=$?"; tail -2 /srv/opentallas-scratch/claude/qe3-ctlm3/u/c$v/cp_m$m.log; done
  bash rtl/test/mu_qwen_seq/run_mu_seq.sh /srv/opentallas-scratch/claude/qe3-ctlm3/u/c$v/museq 0 4 5 11 12 13 14 15 33 > /srv/opentallas-scratch/claude/qe3-ctlm3/u/c$v/museq.log 2>&1; echo "C$v MUSEQ rc=$?"; cat /srv/opentallas-scratch/claude/qe3-ctlm3/u/c$v/museq.log | grep -v "^Verilator"
done
