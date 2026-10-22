#!/bin/bash
set -u
cd /srv/opentallas-scratch/claude/codex-s81-xr2-line-timing-1019
D=/srv/opentallas-scratch/claude/mu-die-s81-tok
mkdir -p out
run_layer() {
 L=$1
 python3 src/tools/s81_dv/dv_layer_compile.py --layer $L --out out/prog_$L --die-src tree_mu --fixtures fixtures/$L > out/compile_$L.log 2>&1 || { cat out/compile_$L.log; exit 2; }
 python3 src/tools/s81_dv/dv_cut_replay.py gen --die-v tree_mu/results/arch/s81_dv_1016/bind9/die.v.gz --prog out/prog_$L --cut cut_3S --out out/replay_$L > out/gen_$L.log 2>&1 || { cat out/gen_$L.log; exit 3; }
 n=$(python3 -c "import json;print(json.load(open('out/replay_$L/replay.json'))['ncyc']+200)")
 OBJ=$D/out_cut_3S_idle/obj bash $D/K_cut_3S/run_dv_slice.sh $D/K_cut_3S out/run_$L +IN=$PWD/out/replay_$L/in.txt +OUT=$PWD/out/replay_$L/out.txt +NCYC=$n +TRACE=$PWD/out/run_$L/trace.txt > out/run_$L.log 2>&1
 python3 src/tools/s81_dv/dv_cut_replay.py check --replay out/replay_$L --run out/run_$L --out out/check_$L.json | tee out/check_$L.log
 }
 pids=""
 for L in L0 L2 L14 L20; do run_layer $L & pids="$pids $!"; done
 for p in $pids; do wait $p || exit 5; done
 python3 src/tools/s81_dv/dv_cut_replay.py gen --die-v tree_mu/results/arch/s81_dv_1016/bind9/die.v.gz --prog out/prog_L0 --cut cut_3S --out out/replay_mut --mutant shift-kind:CTL:1 > out/gen_mut.log 2>&1 || exit 4
 n=$(python3 -c "import json;print(json.load(open('out/replay_mut/replay.json'))['ncyc']+200)")
 OBJ=$D/out_cut_3S_idle/obj bash $D/K_cut_3S/run_dv_slice.sh $D/K_cut_3S out/run_mut +IN=$PWD/out/replay_mut/in.txt +OUT=$PWD/out/replay_mut/out.txt +NCYC=$n +TRACE=$PWD/out/run_mut/trace.txt > out/run_mut.log 2>&1
 python3 src/tools/s81_dv/dv_cut_replay.py check --replay out/replay_mut --run out/run_mut --out out/check_mut.json | tee out/check_mut.log
 echo XR2_CHAIN_DONE
