#!/bin/bash
# chain_after_build.sh TAG : (on the host, under ot-run) bind real views on TAG/out/case, build the STA libs, run the die chain
# (real case -> PDN r8 -> GRT 12 iters -> STA tt / ff / ss; SS is reported sensitivity) into TAG/chain; port-bind verdict first
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
# r3 (2026-10-14): PDN r7 -- M8 on the 2.16-um-commensurate 8.64 lattice, no macro grid for die relays (pdngen costs
# ~2 s per instance grid: the r5 case PDN of C3 ran > 5 h); the r5 file is kept beside it
# r8 (Q-COMPUTE-DIE 2026-10-15, default): r7 + die-top tie cells on local rows stacked M2->M9 (die_tie_rows.tcl), no
# die-wide M3..M7 stdcell ladder -- that ladder (58533b5a0) drove C19s / C21sa PDN to the 420 GiB cgroup kill
PDN_REV=${OT_PDN_REV:-r8}
TIE_LOCAL=; UP4SKIP="--skip-prefix up4_sel_"
# r8: up4_sel_* (3 M7/M8-pin selector blocks) get their macro grid: without the ladder they were PG islands
[ "$PDN_REV" = r8 ] && { TIE_LOCAL=--tie-local; UP4SKIP=; }
if [ "$PDN_REV" = r7 ] || [ "$PDN_REV" = r8 ]; then
  cp $R/case_r22k/pdn.tcl $R/case_r22k/pdn_r5.tcl
# licensed link-PHY abstracts (io_serdes*, io_ucie) carry their own M4 PG straps under a full M1-M5 OBS: no die macro
# grid reaches them (PDN-0006); their PG hookup is the PHY IP integration, recorded open (OT_PGCHECK reports it)
  python3 tools/qwen_split/pdn_regroup.py $R/case_r22k --skip-prefix rly_ $UP4SKIP --skip-prefix io_serdes --skip-prefix io_ucie --pos ../out/rom_tp8b.json --out pdn.tcl $TIE_LOCAL > $R/pdn_$PDN_REV.json || { echo pdn regroup failed; exit 10; }
fi
# owner no-stub gate (08:05): the chain still runs for the die timing diagnosis, but its result is labelled by this verdict
bash tools/qwen_split/port_bind_compute.sh $R/case_r22k/die.v $R/port_bind > $R/port_bind.line 2>&1; pb=$?
echo "$(date '+%F %T %Z') port-bind (no stubs): $(cat $R/port_bind.line) rc=$pb" >> $R/STATUS.log
echo "$(date '+%F %T %Z') qwen-split compute chain $T (src $(cat SOURCE_COMMIT)); real views: $(python3 -c "import json;b=json.load(open('../bind.json'));print(b['masters_bound'],'masters /',b['instances_bound'],'of',b['instances'],'instances')")" >> $R/STATUS.log
exec env OT_ADMIT=pass OT_ITERS=12 OT_ROUTE_RESET=1 OT_CORNERS="tt ff ss" OT_STA_CLOCKS=$R/libs/clocks.tcl bash $S/src/tools/qwen_kv_die/chain/die_chain.sh r22k $R $S/src
