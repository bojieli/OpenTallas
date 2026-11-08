#!/bin/bash
set -euo pipefail
cd /
R=/srv/opentallas-scratch2/claude/codex-hbm-types-1551/q2r_memory
M=$1
(
 flock 9
 if [ ! -f "$R/prepared.ok" ]; then
  mkdir -p "$R/in" "$R/gen"
  python3 -I -c 'import gzip,pathlib;r=pathlib.Path("/srv/opentallas-scratch2/claude/codex-hbm-types-1551/q2r_memory");(r/"in/p.sv").write_bytes(gzip.decompress((r/"native_p.sv.gz").read_bytes()))'
  python3 -I "$R/gen_directed.py" "$R/in/p.sv" "$R/gen" > "$R/prepare.log" 2>&1
  touch "$R/prepared.ok"
 fi
) 9> "$R/prepare.lock"
D=$R/run/m$M
mkdir -p "$D"
/usr/bin/iverilog -g2012 -DOT_Q2NF_TGTQ1 -o "$D/sim.vvp" "$R/gen/tb.sv" "$R/gen/old_w.sv" "$R/gen/n$M.sv" "$R"/mac/*.v > "$D/build.log" 2>&1
/usr/bin/vvp -n "$D/sim.vvp" +SEED=1 +NPROG=1 +MUT=$M > "$D/run.log" 2>&1
