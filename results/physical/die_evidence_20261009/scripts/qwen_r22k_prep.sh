#!/bin/bash
# die-evidence-2 2026-10-09 (Claude): localhost prep of the Qwen ROM die r22k evidence (the generator needs scipy, which
# the EPYC hosts' python lacks; light, niced, single-threaded), then rsync to the run host and start the chain.
#   case (r22k recipe, PDN r5) | strict die-top lint (qwen_rom r22k + qwen_kv) | assumed element libs + ETM-bound libs
#   (slab_m8 / cst / chead ETMs as r21b; the rest ASSUMED) | IR window cases
# usage: qwen_r22k_prep.sh <src worktree> <local scratch> <host> <remote run dir>
set -u
WT=$1; L=$2; H=$3; R=$4
Q3=/srv/opentallas-scratch/claude/qwen-die-r20          # EPYC3: the r21b ETMs (slab_m8, cst, chead) and PHY libs
LOG=$L/prep.log; mkdir -p $L/ir $L/etm_in $L/st/cst $L/st/chead $L/lint $L/lint_kv
say() { echo "$(date '+%F %T %Z') $*" >> $LOG; }
cd $WT; say "prep start $(git rev-parse --short=9 HEAD)"
[ -f $L/case/run.tcl ] || nice python3 tools/qwen_rom_fulldie_b3r2.py pdn --recipe r22k --pdn-rev r5 --work $L/case > $L/gen.log 2>&1 || { say "GEN FAIL"; exit 1; }
git rev-parse --short=9 HEAD > $L/case/SOURCE_COMMIT; echo "--recipe r22k --pdn-rev r5" > $L/case/SOURCE_NOTE
say "case: $(python3 -c "import json;d=json.load(open('$L/case/manifest.json'));print(d['instances'],'insts',d['nets'],'nets',d['die'])")"
nice python3 tools/die_top_lint.py lint --die qwen_rom --qwen-recipe r22k --out $L/lint > $L/lint.log 2>&1; say "lint r22k rc=$? $(tail -1 $L/lint.log | cut -c1-300)"
nice python3 tools/die_top_lint.py lint --die qwen_kv --out $L/lint_kv > $L/lint_kv.log 2>&1; say "lint kv rc=$? $(tail -1 $L/lint_kv.log | cut -c1-300)"
ST=$(ls $L/lint/*_stubs.sv 2>/dev/null | head -1); [ -n "$ST" ] || { say "NO STUBS"; exit 1; }
for c in ss ff; do scp -q ot-epyc3:$Q3/etm/slab_m8/ot_qwen_slab_port_group_$c.lib $L/etm_in/
  for f in cst chead; do scp -q ot-epyc3:$Q3/etm/$f/ot_qwen_die_station_${f}_$c.lib $L/st/$f/; done; done
scp -q ot-epyc3:$Q3/etm_tt/slab_m8/ot_qwen_slab_port_group_tt.lib $L/etm_in/
for f in cst chead; do scp -q ot-epyc3:$Q3/etm_tt/$f/ot_qwen_die_station_${f}_tt.lib $L/st/$f/; done
( nice python3 tools/qwen_die_element_lib.py --stubs $ST --lef $L/case/elements.lef --out $L/assumed &&
  nice python3 tools/qwen_die_etm_map.py --etm $L/etm_in --lef $L/case/elements.lef --assumed $L/assumed --out $L/libs --recipe r22k \
    --stubs $ST --station-etm $L/st --corners ss,tt,ff ) > $L/libs.log 2>&1 || say "ETM LIBS FAIL (assumed only)"
[ -f $L/libs/views.json ] || { mkdir -p $L/libs; cp $L/assumed/qfd_elements_*.lib $L/libs/; }
say "libs: $(tail -3 $L/libs.log | tr '\n' ' ' | cut -c1-400)"
for w in io_edge tile_field shoreline_w spine_hub spine_slab; do
  nice python3 tools/qwen_rom_fulldie_b3r2.py ir --recipe r22k --window $w --ir-guard 200 --work $L/ir/ir_$w > $L/ir/gen_$w.log 2>&1 || say "IR gen $w failed"
done
ssh $H "mkdir -p $R/case_r22k $R/libs $R/ir" && rsync -a $L/case/ $H:$R/case_r22k/ && rsync -a $L/libs/ $L/assumed $H:$R/libs/ && \
  rsync -a $L/ir/ $L/lint $L/lint_kv $L/gen.log $L/libs.log $H:$R/ || { say "RSYNC FAIL"; exit 1; }
say "prep done -> $H:$R"
