#!/bin/bash
# BINDER4-S81: remaining svc split-lint pieces on the fleet (localhost OOM order), ot-run --mem 32, 2 at a time
P=/home/ubuntu/scratch/binder4-1023/s81
one() { d=$1; ot-run --mem 32 --threads 1 --dir $P/b3r8/lint/$d -- bash -c "ulimit -s unlimited; /usr/bin/time -f %M -o maxrss.txt /home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator_bin -f verilator_lint.f > relint.log 2>&1; echo rc=\$? err=\$(grep -c '^%Error' relint.log) maxrss_kb=\$(cat maxrss.txt); grep '^%Error' relint.log | head -5" 2>&1 | sed "s|^|$d |" | grep -v "^$d ot-run: \(picked\|start\)" ; }
export -f one; export P
tr ' ' '\n' < $P/remote_runs.txt | xargs -P 2 -I{} bash -c 'one {}'
