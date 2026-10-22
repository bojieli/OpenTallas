#!/bin/bash
set -euo pipefail
test ! -e unpacked02
test ! -e deps02
mkdir unpacked02
python3 -m pip install --no-deps --target deps02 z3-solver==4.14.1 > deps02.install.log 2>&1
export PYTHONPATH="$PWD/deps02${PYTHONPATH:+:$PYTHONPATH}"
tar -xzf input.tgz -C unpacked02
cd unpacked02/results/arch/s81_hb1_private_source_1019
hostname > host.txt
free -b > free_before.txt
df -B1 . > disk_before.txt
python3 -c 'import z3; print(z3.get_version_string())' > z3_version.txt
/usr/bin/time -v -o nextstate_resources.txt python3 nextstate.py out_next02
