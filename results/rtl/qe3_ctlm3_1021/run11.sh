#!/bin/bash
# QE3-CTLM3 10-21: regenerate the CTLM bounded netlist with CALREG=15 (run10.sh recipe) -> lp9f_np -> npl -> rr, then benches.
set -uo pipefail
R=/srv/opentallas-scratch/claude/qe3-ctlm3/chain
docker run --rm -u $(id -u):$(id -g) -v $R:/work -w /work/src openroad/orfs:latest bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; bash chain9.sh' > $R/chain11.log 2>&1; echo "CHAIN_RC $?" >> $R/chain11.log
docker run --rm -u $(id -u):$(id -g) -v $R:/work -w /work/src openroad/orfs:latest bash -lc 'bash depth7.sh' > $R/depth11.log 2>&1; echo "DEPTH_RC $?" >> $R/depth11.log
echo CHAIN_DONE
mkdir -p $R/out/np $R/out/npl $R/out/rr
cp $R/generic7c/qfd_tt_ctlm_dv_np_lp.sv $R/generic7c/qfd_tt_ctlm_dv_np_helpers.sv $R/out/np/
python3 $R/namemap2.py $R $R/nm > $R/namemap.log 2>&1; tail -2 $R/namemap.log
python3 $R/src/tools/qwen_dv/npl_rename.py $R/out/np/qfd_tt_ctlm_dv_np_lp.sv $R/nm/namemap.json $R/out/npl/qfd_tt_ctlm_dv_np_lp.sv
cp $R/out/np/qfd_tt_ctlm_dv_np_helpers.sv $R/out/npl/; cp $R/out/np/qfd_tt_ctlm_dv_np_helpers.sv $R/out/rr/
python3 $R/src/tools/qwen_dv/replica_role_split.py $R/out/npl/qfd_tt_ctlm_dv_np_lp.sv $R/out/rr/qfd_tt_ctlm_dv_np_lp.sv $R/out/rr/replica_role_split_record.json > $R/rr.log 2>&1; echo "RR_RC $?" >> $R/rr.log
python3 $R/src/tools/qwen_dv/rr_equiv.py $R/out/npl/qfd_tt_ctlm_dv_np_lp.sv $R/out/rr/qfd_tt_ctlm_dv_np_lp.sv > $R/rr_equiv.log 2>&1; echo "RREQ_RC $?" >> $R/rr_equiv.log
echo RR_DONE
cd $R/src && bash bench10.sh > $R/bench11.log 2>&1; echo "BENCH_RC $?" >> $R/bench11.log
echo ALL_DONE
