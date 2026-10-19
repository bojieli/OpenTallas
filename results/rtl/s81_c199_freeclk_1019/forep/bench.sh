#!/bin/bash
# S81-C199-FANOUT bench: sync src to epyc6, run baseline/forep/mutants on fleet Verilator 5.050 via ot-run
set -e
WT=/home/ubuntu/wt/c199-fanout-1019; H=ot-epyc6; R=/srv/opentallas-scratch/claude/c199-fanout; TAG=${1:-b1}
ssh $H "mkdir -p $R/src"

rsync -a --delete $WT/rtl/ $H:$R/src/rtl/
rsync -a --delete $WT/tools/ $H:$R/src/tools/
rsync -aR $WT/./results/rtl/s81_bf_compact_20261010/compact199_pinreg_1018/bench_5050/prep $H:$R/src/
git -C $WT rev-parse HEAD > /tmp/c199f_sc; scp -q /tmp/c199f_sc $H:$R/src/SOURCE_COMMIT
B='OT_BMUL_RSPLIT+OT_BF_TAGREP'; F="$B+OT_BF_TILE_FREECLK+OT_BF_RSTPART+OT_BF_FOREP"
P='QZE=1,TCG=1,BXST=2,FXST=2,PINLAT=1,HCOL=1'
/home/ubuntu/bin/ot-run --mem 64 --threads 32 --dir $R -- bash -c "cd $R/src && python3 tools/s81/bf_forep_bench.py --variant recut --params $P --jobs 8 --prep $R/src/results/rtl/s81_bf_compact_20261010/compact199_pinreg_1018/bench_5050/prep --no-default-mutants --positive-define baseline=$B --positive-define forep=$F --mutant fe_mut_add=$F+OT_BF_FOREP_MUT_ADD --mutant fe_mut_chain=$F+OT_BF_FOREP_MUT_CHAIN --mutant fe_mut_tree=$F+OT_BF_FOREP_MUT_TREE --work $R/out_$TAG --only baseline forep fe_mut_add fe_mut_chain fe_mut_tree"
