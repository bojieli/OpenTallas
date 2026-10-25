set -eu
M=/srv/opentallas-scratch2/claude/codex-kv-cores-0719/miter; D=/srv/opentallas-scratch2/claude/path-kv/s3miter
H=/srv/opentallas-scratch2/claude/wt/path-kv-head-1025/physical/die_plan/qwen_kvsys/cores/harden
python3 $H/head_master_miter.py $M/old4 $D/s3_6 $D/c4 --port-map $M/portmap4.json --new-mod kv3_head_eighth_e6 --strap "strap_bsel=2'b10" > $D/c4.gen.log 2>&1
export PATH=/home/ubuntu/.local/opentallas-tools/bin:$PATH
cd $D/c4 && verilator --binary --timing -j 8 -MAKEFLAGS OBJCACHE= -Wno-fatal -Wno-lint -Wno-style -Wno-MULTIDRIVEN -DSYNTHESIS -Io -In --top-module tb --Mdir obj -f files.f > build.log 2>&1 && ./obj/Vtb > sim.log 2>&1; grep "CORE MITER" sim.log || tail -3 build.log
