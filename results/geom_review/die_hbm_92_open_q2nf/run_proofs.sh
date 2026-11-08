#!/bin/bash
# DIE-HBM-92-OPEN/Q2NF vD source proofs (small, 2 GB): FLOWADDR lemma miter (Codex extract.py re-run on the vD base RTL)
# and the DNZ register-retiming induction, each with a mutant that must FAIL.
set -u
D=/srv/opentallas-scratch2/claude/die-hbm-92-open/q2nf/proof
docker run --rm --memory=4g --memory-swap=4g --cpus=2 -v "$D":/work -w /work openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
yosys -Q -T -p "read_verilog -sv fa/miter.sv; hierarchy -check -top q2nf_flowaddr_miter; proc; flatten; opt; sat -verify -prove ok 1" > fa_good.log 2>&1; a=$?
yosys -Q -T -p "read_verilog -sv fa/mutant.sv; hierarchy -check -top q2nf_flowaddr_miter; proc; flatten; opt; sat -verify -prove ok 1" > fa_mut.log 2>&1; b=$?
yosys -Q -T -p "read_verilog -sv dnz/miter_dnz.sv; hierarchy -check -top dnz_miter; proc; flatten; opt_clean; sat -verify -tempinduct -prove ok 1 -seq 1 -set-init-undef -set-def-inputs -maxsteps 4" > dnz_good.log 2>&1; c=$?
yosys -Q -T -p "read_verilog -sv dnz/mutant_dnz.sv; hierarchy -check -top dnz_miter; proc; flatten; opt_clean; sat -verify -tempinduct -prove ok 1 -seq 1 -set-init-undef -set-def-inputs -maxsteps 4" > dnz_mut.log 2>&1; d=$?
printf "fa_good %s\nfa_mutant %s\ndnz_good %s\ndnz_mutant %s\n" $a $b $c $d > proof.rc
chown -R 1000:1000 /work'
cat "$D/proof.rc"
