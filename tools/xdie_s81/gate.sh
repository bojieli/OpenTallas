#!/bin/bash
# gate.sh <tag> <LAT_S> <LAT_N> <PER_S> <PER_N> <cfg verilator args...> : TOKEN-XDIE-S81 gate run with the compiled
# deadlines (static-schedule check) + the mutant bench (cwd = staged repo root).  Each mutant must print "FAIL xdie_s81".
#   base   the configuration, deadlines on: must PASS
#   swap   +define+OT_S81SL_LEP_MUT_SWAP (lep puts the beat halves on the wrong lanes)       -> MISMATCH
#   kp4d   -GDMUT=2 (KP4 decoder mutant in every ot_pdie_serdes)                              -> corrupted / fault
#   late   -GLATE_MUT=40 (die 1 ES lane 1 crossing 40 cycles longer than compiled)            -> LATE (static check)
set -u; T=$1; LS=$2; LN=$3; PS=$4; PN=$5; shift 5; O=out_$T; mkdir -p $O
python3 tools/xdie_s81/gen_golden.py --out $O/g --gap ${GAP:-100} --lat S=$LS,N=$LN --per S=$PS,N=$PN > $O/gen.txt 2>&1 || { echo GEN_FAILED; exit 2; }
python3 tools/xdie_s81/gen_golden.py --out $O/gm --reps 1 --only a_allgather,stage_hop --lat S=$LS,N=$LN --per S=$PS,N=$PN > $O/genm.txt 2>&1
r() { n=$1; g=$2; shift 2; ( J=6 bash tools/xdie_s81/run_xdie_s81.sh $O $n $O/$g ep "$@" > $O/$n.txt 2>&1; echo "EXIT $?" >> $O/$n.txt ) & }
r base g "$@"
r swap gm "$@" -GMAXCYC=40000 +define+OT_S81SL_LEP_MUT_SWAP
r kp4d gm "$@" -GMAXCYC=40000 -GDMUT=2
r late gm "$@" -GMAXCYC=40000 -GLATE_MUT=40
wait; touch $O/DONE
