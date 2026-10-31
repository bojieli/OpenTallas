#!/bin/bash
# DIE-QC-50/gen47ndr collect: usage collect.sh TAG RUNDIR[,RUNDIR..]   (on epyc2; waits for every RUNDIR/status)
# For each finished DRT+RCX run dir (drt2_full, path2_C, reg2_A/B): DRC summary; RCX with PG-stripe context
# (run_rcx_pg.sh -> clk_rcx_pg.spef, PRIMARY; the in-session clk_rcx.spef has no PG neighbours = INFO); then per SPEF
# basis ONE mixed readout per corner (all SPEFs read over the GRT-NDR estimate; a whole-die SPEF overrides every clock
# net) via ot-run, OT_EDGES, tap arrivals (main trial_tap_arrivals.py), comparison vs the GRT-NDR proof, and main
# die_sta_related (DIE-QC-45 args).  Output: collect_TAG.log, cmp_TAG*.json, sta_mix_TAG*.log/.status, proofM_TAG*.
set -u
TAG=$1; DIRS=$2; R=/srv/opentallas-scratch2/claude/die-qc-50/gen47ndr; T=/srv/opentallas-scratch2/claude/wt/die-qc-50-gen47ndr/tools/die_plan
cd $R; L=$R/collect_$TAG.log; exec >> $L 2>&1; echo "START $(date)"
SP=""; SPN=""
for d in ${DIRS//,/ }; do
  until [ -f $R/$d/status ]; do sleep 60; done
  grep -q "rc=0" $R/$d/status || { echo "FAIL $d $(cat $R/$d/status)"; exit 1; }
  python3 -I drc_sum.py $R/$d/drc.rpt > $R/$d/drc_sum.json; head -3 $R/$d/drc_sum.json
  [ -s $R/$d/clk_rcx_pg.spef ] || ./run_rcx_pg.sh $d || { echo "FAIL rcx_pg $d"; exit 1; }
  grep -E "PGCTX|RCX-0045" $R/$d/rcx_pg.log
  SP="${SP:+$SP,}$R/$d/clk_rcx_pg.spef"; SPN="${SPN:+$SPN,}$R/$d/clk_rcx.spef"
done
one() { local TG=$1 S=$2
  for C in TT FF; do ssh -o ControlPath=none hub "~/.local/bin/ot-run --mem 40 --threads 16 --disk 5 --hosts epyc2 --dir $R --priority die -- $R/run_mix.sh $TG $C $S" & done; wait
  mkdir -p proofM_$TG; cp proofG/tree.json proofG/mesh.json proofG/droop_regions.json proofM_$TG/
  for C in TT FF; do grep -q rc=0 mix_${TG}_$C/status || { echo "FAIL mix $TG $C"; return 1; }
    python3 -I mk_edges47.py mix_${TG}_$C/edges_raw.txt mix_${TG}_$C/arr_$C.txt mix_${TG}_$C/census.json
    python3 -I $T/trial_tap_arrivals.py proofM_$TG/tree.json mix_${TG}_$C/arr_$C.txt $C proofM_$TG/tap_arrivals_$C.json; done
  grep MIX_ mix_${TG}_TT/run.log
  python3 -I cmp_arr.py proofG/tap_arrivals_TT.json proofM_$TG/tap_arrivals_TT.json c_E1_bn_11,c_E1_bf_11,c_W3_bn_11,c_W3_bf_11 \
    t_c_E1_bn_11__clk_t12:t_c_E1_bn_11__clk_c0 t_c_W3_bn_11__clk_t12:t_c_W3_bn_11__clk_c0 t_c_E1_bf_11__clk_t27:t_c_E1_bf_11__clk_t12 t_c_W3_bf_11__clk_t27:t_c_W3_bf_11__clk_t12 > cmp_$TG.json
  cat cmp_$TG.json
  ./run_sta.sh proofM_$TG mix_$TG; cat sta_mix_$TG.status; grep -E "^proofM_$TG (TT|FF) (intra|seam) " sta_mix_$TG.log
}
one $TAG $SP
one ${TAG}_nopg $SPN
echo "DONE $(date)"
