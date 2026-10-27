#!/bin/bash
# HEAD-CORE-R14 2026-10-27 (COORD RULING HEAD-CORE-R13 ASK3, flow change; canary = elemA R12b routed kit):
# warm post-route ECO of a ROUTED s81_head hard core, then sign-off, then the ROUTED LEC, which ALWAYS runs.
#   head_post_route_eco.sh KIT OUT GOLD [MEM_GB=48] [CPUS=16]     (run ON the kit host, e.g. through ot-run --hosts)
# KIT  = routed head kit (run/results/asap7/<nick>/base/5_2_route.odb + 6_final.spef, signoff.py bundle, constraint.sdc,
#        bind_ff_actual.tcl PRE_GLOBAL_ROUTE hook = HB4-only hold wrapper + FF bound 202.5).
# OUT  = new dir (never reused).  GOLD = LEC gold kit (config.mk, rtl/, macros/, lec.py), e.g. KIT.lec_r11.
# Steps:
#  1 stage OUT: kit files (no run/ signoff*/), 5_2_route.odb as 4_cts.odb, 6_final.spef, 4_cts.sdc = constraint.sdc +
#    propagated clock; POST_GLOBAL_ROUTE_TCL = head_eco_post.tcl (+ KV eco_route.tcl); SKIP_INCREMENTAL_REPAIR=1.
#  2 do-5_1_grt (ECO: RCX repair_design, setup, HB4 hold) -> constraint.sdc installed as 5_1_grt.sdc -> 5_2_route (DRT
#    re-routes the changed nets) -> fill -> 5_route -> finish -> abstract.
#  3 signoff.py tt,ff RCX (FF bound 202.5, same call as actual_head_route.sh); its exit code is RECORDED, not fatal.
#  4 routed LEC of 6_final.v vs GOLD: runs whenever a 6_final.v exists, whatever the sign-off verdict (R13 root cause 4:
#    set -e skipped it on NOT SIGNED).  Export removes only portless TAPCELL/FILLER/DECAP; refuses any with ports.
# Log: OUT/eco_chain.log, lines HEAD_ECO_CHAIN_* (grep '^HEAD_ECO_\|^SIGNOFF').
set -uo pipefail
KIT=$(realpath "$1"); OUT=$2; GOLD=$(realpath "$3"); MEM=${4:-48}; CPUS=${5:-16}
HERE=$(cd "$(dirname "$0")" && pwd)
IMAGE=${OT_ORFS_IMAGE:-openroad/orfs:asap7lock}
test ! -e "$OUT" || { echo "head_post_route_eco: $OUT exists (never relaunch into a run dir)"; exit 2; }
RS=$(ls -d "$KIT"/run/results/asap7/*/base); NICK=$(basename "$(dirname "$RS")")
for f in 5_2_route.odb 6_final.spef; do test -s "$RS/$f" || { echo "head_post_route_eco: $RS/$f missing"; exit 2; }; done
for f in config.mk lec.py rtl macros; do test -e "$GOLD/$f" || { echo "head_post_route_eco: gold $GOLD lacks $f"; exit 2; }; done
mkdir -p "$OUT"; OUT=$(realpath "$OUT")
exec >> "$OUT/eco_chain.log" 2>&1
echo "HEAD_ECO_CHAIN start $(date -Is) kit $(hostname):$KIT nick $NICK gold $GOLD"
rsync -a --exclude /run --exclude '/signoff*' --exclude '/*.log' --exclude /rc.txt "$KIT"/ "$OUT"/
B=$OUT/run/results/asap7/$NICK/base
mkdir -p "$B" "$OUT/run/logs/asap7/$NICK/base" "$OUT/run/reports/asap7/$NICK/base" "$OUT/run/objects/asap7/$NICK/base"
cp "$RS/5_2_route.odb" "$B/4_cts.odb"
for f in 6_final.spef 1_2_yosys.v 1_synth.v 1_synth.sdc clock_period.txt mem.json ot_face_flops.txt ot_unreg_pins.txt; do
  test -f "$RS/$f" && cp "$RS/$f" "$B/"; done
rsync -a "$KIT/run/objects/asap7/$NICK/base/" "$OUT/run/objects/asap7/$NICK/base/" 2>/dev/null || true
{ cat "$OUT/constraint.sdc"; echo 'set_propagated_clock [all_clocks]'; } > "$B/4_cts.sdc"
cp "$HERE/head_eco_post.tcl" "$HERE/../../physical/die_plan/qwen_kvsys/cores/harden/eco/eco_route.tcl" "$OUT/"
grep -q 'hold_pad_hb4.tcl' "$OUT/bind_ff_actual.tcl" || { echo "HEAD_ECO_CHAIN FAIL: bind_ff_actual.tcl lacks the HB4-only hold wrapper"; exit 2; }
cat >> "$OUT/config.mk" <<'CFG'
# HEAD-CORE-R14 warm post-route ECO (tools/s81_head/head_post_route_eco.sh): RCX DRV + setup + HB4-only data hold
override export POST_GLOBAL_ROUTE_TCL = /work/head_eco_post.tcl
override export SKIP_INCREMENTAL_REPAIR = 1
CFG
ENV="-e OT_MAX_FANOUT=24 -e OT_SLEW_MARGIN=${OT_SLEW_MARGIN:-20} -e OT_SETUP_MARGIN=${OT_SETUP_MARGIN:-10} -e OT_HOLD_MARGIN=${OT_HOLD_MARGIN:-10} -e OT_HOLD_ALLOW_SETUP=1 -e OT_HOLD_MAXBUF=40 -e OT_DRV_LAST=0 -e OT_DRV_PLACE=0 -e OT_PAD_MASTERS= -e OT_RETIME_LAST=0"
printf '{"flow": "HEAD-CORE-R14 head_post_route_eco.sh", "source_kit": "%s:%s", "source_route": "%s/5_2_route.odb", "gold": "%s", "env": "%s"}\n' \
  "$(hostname)" "$KIT" "$RS" "$GOLD" "$ENV" > "$OUT/ECO.json"
docker run --rm --name "hd-eco-$NICK-$$" --memory="${MEM}g" --memory-swap="${MEM}g" --cpus="$CPUS" -v "$OUT":/work $ENV \
  -e CPUS="$CPUS" -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
    M=(make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work/run FLOW_VARIANT=base NUM_CORES="$CPUS" CORNER=TC "CORNERS=tc bc")
    "${M[@]}" do-5_1_grt SKIP_INCREMENTAL_REPAIR=1
    B=$(dirname $(find /work/run/results/asap7 -name 5_1_grt.odb))
    cp --remove-destination /work/constraint.sdc $B/5_1_grt.sdc
    "${M[@]}" do-5_2_route do-5_3_fillcell do-5_route do-5_route.sdc
    "${M[@]}" do-finish
    "${M[@]}" do-generate_abstract
  ' > "$OUT/eco_route.log" 2>&1
rrc=$?
docker run --rm -v "$OUT":/work "$IMAGE" chown -R "$(id -u):$(id -g)" /work >/dev/null 2>&1
echo "HEAD_ECO_CHAIN route rc=$rrc $(date -Is)"
grep -h '^HEAD_ECO_\|KVCORES_ECO\|R10_HOLD_DONE\|OT_HB4PAD: after' "$OUT"/run/logs/asap7/"$NICK"/base/5_1_grt.log 2>/dev/null | tail -n 20
src=NA
if [ "$rrc" = 0 ]; then
  python3 -I "$OUT/signoff.py" run --kit "$OUT" --run-dir "$OUT/run" --corners tt,ff \
    --ff-vclk bound-ff --ff-bound-ps 202.5 \
    --ff-vclk-contract 'HEAD actual standalone clock contract: actual_contract.json; primary ft_mstrap_i; zero source offset' \
    --docker docker --image "$IMAGE" --out "$OUT/signoff_actual" > "$OUT/signoff_actual.log" 2>&1
  src=$?
fi
echo "HEAD_ECO_CHAIN signoff rc=$src $(date -Is)"; grep -h '^SIGNOFF' "$OUT/signoff_actual.log" 2>/dev/null || true
# ---- routed LEC: ALWAYS (independent of the sign-off verdict) ----
V=$(find "$OUT/run/results/asap7" -name 6_final.v | head -1)
if [ -z "$V" ] || [ ! -s "$V" ]; then echo "HEAD_ECO_CHAIN LEC not possible: no 6_final.v"; echo "HEAD_ECO_CHAIN done $(date -Is)"; exit 3; fi
echo "HEAD_ECO_FINAL_V $V $(stat -c %y "$V")"
F=$OUT.lec_final; rm -rf "$F"; mkdir -p "$F"; cp -a "$GOLD/config.mk" "$GOLD/rtl" "$GOLD/macros" "$GOLD/lec.py" "$F/"
python3 -I - "$V" "$F/final_functional.v" <<'PY'
import re, sys, json
from pathlib import Path
src, out = map(Path, sys.argv[1:3]); t = src.read_text()
phys = r"(?:TAPCELL_ASAP7_75t_R|FILLER\w*|FILLERxp5\w*|DECAP\w*)"
clean, n = re.subn(r"(?m)^\s*%s\s+\S+\s*\(\s*\);\s*$" % phys, "", t)
left = re.findall(r"(?m)^\s*(%s)\s+\S+" % phys, clean)
if left: raise SystemExit("Refusing physical-only master with ports: %s" % sorted(set(left))[:5])
out.write_text(clean)
out.with_suffix(".physical_only.json").write_text(json.dumps(dict(source=str(src), portless_physical_removed=n, functional_cells_or_nets_changed=0), indent=1)+"\n")
print("HEAD_ECO_EXPORT portless physical-only removed", n, "HB4", clean.count("HB4xp67"))
PY
python3 -I "$F/lec.py" "$F" --netlist "$F/final_functional.v" --out "$F/lec" --jobs 8 --mem 16 > "$F/lec.run.log" 2>&1 || echo "lec.py rc=$?"
tail -n 1 "$F/lec.run.log"
python3 -I - "$F/lec" <<'PY'
import json, sys
from pathlib import Path
o = Path(sys.argv[1]); d = json.loads((o/'lec.json').read_text()); kr = d.get('kept_registers', {})
print('HEAD_ECO_POSTROUTE_LEC verdict', d['verdict'], d.get('counts'), 'kept missing', kr.get('missing', {}).get('n'))
PY
echo "HEAD_ECO_CHAIN done $(date -Is)"
