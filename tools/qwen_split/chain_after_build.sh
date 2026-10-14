#!/bin/bash
# chain_after_build.sh TAG : (on the host, under ot-run) bind real views on TAG/out/case, build the STA libs, run the die chain
# (real case -> PDN r5 -> GRT 12 iters -> STA tt / ff; SS is sensitivity only and not run) into TAG/chain
set -u
T=$1; S=/srv/opentallas-scratch/claude/qwen-split-compute/$T; R=$S/chain
grep -q '^rc=0' $S/out.log || { echo "build $T not rc=0"; exit 7; }
mkdir -p $R/libs $R/case_r22k
cd $S/src
python3 tools/qwen_tp8/bind_real.py --case ../out/case --repo . --out ../bind.json > $R/bind.log 2>&1 || { echo bind failed; exit 8; }
python3 tools/qwen_tp8/die_sta_libs.py --case ../out/case --repo . --bind ../bind.json --out $R/libs > $R/libs.log 2>&1 || { echo libs failed; exit 9; }
rsync -a ../out/case/ $R/case_r22k/
cp ../bind.json ../out/relay_run.json $R/
cat SOURCE_COMMIT > $R/case_r22k/SOURCE_COMMIT
echo "$(date '+%F %T %Z') qwen-split compute chain $T (src $(cat SOURCE_COMMIT)); real views: $(python3 -c "import json;b=json.load(open('../bind.json'));print(b['masters_bound'],'masters /',b['instances_bound'],'of',b['instances'],'instances')")" >> $R/STATUS.log
exec env OT_ADMIT=pass OT_ITERS=12 OT_ROUTE_RESET=1 OT_CORNERS="tt ff" OT_STA_CLOCKS=$R/libs/clocks.tcl bash $S/src/tools/qwen_kv_die/chain/die_chain.sh r22k $R $S/src
