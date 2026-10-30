#!/bin/bash
# DIE-S81-32/MACRO kit regen on the branch plan (S81-KITS-A gen_v2 recipe: kit RTL = the bind7 kit sources S81-KITS-A
# staged (gen2/gen3 rtl copies, native_glue included), plan COPY with verilog_defines = kit_rtl.json defines).
set -u
src=/srv/opentallas-scratch2/claude/wt/die-s81-32-macro
out=/srv/opentallas-scratch2/claude/die-s81-32/macro/kits
A=/srv/opentallas-scratch2/claude/s81-kits-a
cd "$src"
for t in $TYPES; do
  D=$(ls -d $A/gen2/$t/$t $A/gen3/$t/$t 2>/dev/null | head -1)
  mkdir -p $out/plan/$t $out/gen
  sed -n "s/^export VERILOG_FILES = //p" $D/config.mk | tr " " "\n" | sed "s#^/work/rtl/#$D/rtl/#" | grep . > $out/plan/$t/kit_rtl.f
  python3 - "$t" "$out/plan/$t/die_plan.json" <<PY
import json,sys
t,po=sys.argv[1:]
p=json.load(open("physical/die_plan/s81/plan_s13r2.json"))
p["partition_types"][t]["verilog_defines"]=json.load(open("$A/rtl/"+t+"/kit_rtl.json"))["defines"]
json.dump(p,open(po,"w"),indent=1)
PY
  rm -rf $out/gen/$t
  python3 tools/die_plan/gen.py phys $out/plan/$t/die_plan.json --out $out/gen/$t --types $t --rtl-root $src --kit-rtl "$t=$out/plan/$t/kit_rtl.f" --hold-ff-margin 10 --max-wire-um 100 > $out/gen_$t.log 2>&1; echo "$t gen rc $?" >> $out/status
  python3 tools/die_plan/kit_preflight.py $out/gen/$t/$t --plan-dir $out/plan/$t --contract --out $out/preflight_$t.json > $out/preflight_$t.log 2>&1; echo "$t preflight rc $?" >> $out/status
done
