#!/usr/bin/env bash
# KV (qwen_kvsys) landed bottom-up fallback -- UNEXECUTED launch script (FALLBACK-PLAN-PREP-2, 2026-10-27).
# DRY-RUN by default: prints every command, runs nothing.
# Real run needs ALL of: FALLBACK_TRIGGER=FIRED, now >= 2026-10-29 12:00 PDT, DRY_RUN=0, and a COORD ruling id as $1.
# Usage: FALLBACK_TRIGGER=FIRED DRY_RUN=0 bash launch_fallback.sh "COORD-2026-10-29-12xx" [stage...]
#   stages: s1 s2 s3 s4 s5 s6 s7 s8 s9 b7   (default: all, in dependency order; s7/s9 wait on signed views)
set -euo pipefail

RULING="${1:-}"; shift || true
DRY_RUN="${DRY_RUN:-1}"
TRIGGER_EPOCH=$(TZ=America/Los_Angeles date -d '2026-10-29 12:00' +%s)
NOW=$(date +%s)
if [[ "$DRY_RUN" != "1" ]]; then
  [[ "${FALLBACK_TRIGGER:-}" == "FIRED" ]] || { echo "REFUSE: FALLBACK_TRIGGER!=FIRED" >&2; exit 2; }
  (( NOW >= TRIGGER_EPOCH )) || { echo "REFUSE: before 2026-10-29 12:00 PDT trigger" >&2; exit 2; }
  [[ -n "$RULING" ]] || { echo "REFUSE: COORD ruling id required as \$1" >&2; exit 2; }
fi

OTRUN=(ssh -o ControlPath=none intel2 '~/.local/bin/ot-run')
# Pin these at T0 (defaults = the 10-27 reference inputs; the plan of record WILL move before T0):
MAIN_SHA="${MAIN_SHA:-60b5ddf523}"
PLAN_REF="${PLAN_REF:-38c1ed8519:results/clock_kv_r26/plan/hm_r26.json.gz}"
PINS_REF="${PINS_REF:-517b37f88}"
if [[ "$DRY_RUN" != "1" && -z "${PINNED_AT_T0:-}" ]]; then echo "REFUSE: set MAIN_SHA/PLAN_REF/PINS_REF to T0 values and PINNED_AT_T0=1" >&2; exit 2; fi
RUN=/srv/opentallas-scratch2/claude/fallback-kv-run      # same absolute path on intel1/intel2/epyc2 (rsync before ot-run)
PREP=d06cccbc4                                           # Codex KV fallback prep packet (recipe scripts)

run() { echo "+ $*"; [[ "$DRY_RUN" == "1" ]] || eval "$@"; }
sync_hosts() { for h in intel1 epyc2; do run "ssh -o ControlPath=none intel2 rsync -a $RUN/ $h:$RUN/"; done; }
otrun() { local mem=$1 dir=$2; shift 2; run "${OTRUN[*]} --mem $mem --dir $dir -- $*"; }

s1() { # pinned source + plan of record + regenerate 128 groups / crossings (plan only, minutes)
  run "ssh -o ControlPath=none intel2 'mkdir -p $RUN && cd $RUN && git -C ~/OpenTallas archive $MAIN_SHA tools | tar x \
     && git -C ~/OpenTallas archive $PREP results/kv_fallback_prep_1027 | tar x \
     && mkdir -p pd fallback && git -C ~/OpenTallas show $PLAN_REF | zcat -f > pd/plan.json \
     && git -C ~/OpenTallas archive $PINS_REF physical/die_plan/qwen_kvsys/cores | tar x && cp -r physical/die_plan/qwen_kvsys/cores pd/'"
  # recipe = fallback_row_groups.py (expects pd/hm_r26.json; symlink the T0 plan to that name)
  run "ssh -o ControlPath=none intel2 'cd $RUN && ln -sf plan.json pd/hm_r26.json && cp results/kv_fallback_prep_1027/fallback_row_groups.py . && python3 -I fallback_row_groups.py \
     && python3 -I -c \"import json;r=json.load(open(\'results/kv_fallback_prep_1027/row_groups_roots.json\'));json.dump(dict(groups=[g[\'parts\'] for g in r]),open(\'fallback/groups.json\',\'w\'))\"'"
  echo "NOTE: row_groups_roots.json is the R26 grouping; regenerate the roots with the same rule if the T0 plan changed partitions"
}
s2() { # PHY boot landings hosted in PC wrappers + collector re-root: ENGINEERING step (code + tests), not a job
  echo "S2 MANUAL: host the 32 PHY boot/reset landings in PC wrappers (row_groups_phy_reset.json), re-root the collector,"
  echo "           regenerate wavefront/START offsets; land as a reviewed branch before s3. See README section 9."
}
s3() { # compose landed plan + G0/G0C
  otrun 24 "$RUN" "python3 -I -c \"import json,sys;sys.path.insert(0,'tools/die_plan');import clock_landing_plan as CP;\
from pathlib import Path;P=json.load(open('pd/plan.json'));T=json.load(open('fallback/row_groups_crossings.json'));\
raw,side=CP.compose(P,T,plan_path=Path('pd/plan.json').resolve(),observer_part='hub_C',observer=dict(module='qkd_seq_core_static_s',instance_suffix='u_seq_u_core',fault_port='hf',ready_port='lp_run'));\
json.dump(raw,open('pd/landed_plan.json','w'));json.dump(side,open('pd/landed_sidecar.json','w'))\""
  otrun 24 "$RUN" "python3 -I tools/die_plan/gen.py latency pd/landed_plan.json --inplace"
  otrun 24 "$RUN" "python3 -I tools/die_plan/check.py pd/landed_plan.json --completeness --out fallback/g0c.json"
  echo "GATE: G0C errors == T0 base error set (no new); GEOM G1 on render before s4/s5"
}
s4() { # region-local clock trees (equal legs, site-legal, 405-um repeaters)
  run "ssh -o ControlPath=none intel2 'cd $RUN && python3 -I tools/die_plan/fallback_regions.py pd/landed_plan.json --lat pd/landed_plan.json --out fallback/regions.json --groups fallback/groups.json'"
  otrun 32 "$RUN" "python3 -I tools/die_plan/die_trial.py kit pd/landed_plan.json --out trial --region-trees fallback/regions.json --htree-full-depth --tree-site-legal --tree-site-slide --rep-um 405"
  otrun 16 "$RUN" "python3 -I tools/die_plan/die_trial.py render trial --plan pd/landed_plan.json"
  echo "GATE: predicted landed |d| <= 416.5 ps TT/FF, 0 tree cells on cores/PHY, render VIEWED by GEOM"
}
s5() { # landing RTL + kits (47 non-PHY types) + bind
  otrun 48 "$RUN" "python3 -I tools/die_plan/gen.py rtl pd/landed_plan.json --out rtl --rtl-root ."
  otrun 48 "$RUN" "python3 -I tools/die_plan/gen.py phys pd/landed_plan.json --out kits --rtl-root . --hold-mcmm --master-slice master_slice"
  otrun 48 "$RUN" "python3 -I tools/die_plan/bind.py pd/landed_plan.json --strict --out bind"   # flags per bind.py --help at T0
  otrun 8  "$RUN" "python3 -I tools/die_plan/clock_landing_verify.py pd/landed_plan.json rtl"
  sync_hosts
}
s6_s7() { # per-type synth/LEC/P&R/signoff: 47 kits, <=400k cells each, 48 GB honest (METHODOLOGY 5.4 32-48 GB)
  run "ssh -o ControlPath=none intel2 'ls $RUN/kits'"
  for k in $( [[ "$DRY_RUN" == "1" ]] && echo 'KIT_DIR_EACH' || ssh -o ControlPath=none intel2 "ls -d $RUN/kits/*/" ); do
    otrun 48 "$k" "bash run_kit.sh"     # autopilot carries GEOM-PASS kits through route/RCX/signoff/LEC/publish (OWNER 10-27)
  done
}
s8() { # die GRT incl clock >= 50 it (die_trial generated run_*.sh; honest mem = the generator's own: grt 256 GB/16 thr, clock 32 GB/4 thr)
  otrun 32  "$RUN/trial" "bash run_clock.sh"
  otrun 256 "$RUN/trial" "bash run_grt.sh"
  otrun 16  "$RUN" "python3 -I tools/die_plan/die_trial.py report trial --plan pd/landed_plan.json"
  echo "GATE: GRT overflow 0 at >= 50 iterations (TT+FF RC), clock nets included; landed |d| from routed tree <= 416.5 ps"
}
s9() { # related-pair die STA, shared model, real views
  for c in tt ff; do
    otrun 96 "$RUN" "python3 -I tools/die_plan/die_sta_related.py --plan pd/landed_plan.json --out sta_$c --corner $c \
      --clock-aocv-table tools/die_plan/clk_aocv_table_g021.json --cppr-lca --droop-region tree \
      --landing-window-ps 416.5 --hold-buffers HB4 \$(sed 's/^/--core-view /' signed_core_views.txt) \$(sed 's/^/--kit /' signed_kits.txt)"
  done
  echo "GATE: TT setup >= 0, FF hold >= 0 on all related pairs + ring windows; NUMBER-CHECK before reporting"
}
b7() { otrun 32 "$RUN" "echo 'token compile on landed latency table: R8 + native calendars (TOK lanes recipe at T0)'"; }

stages=("$@"); [[ ${#stages[@]} -gt 0 ]] || stages=(s1 s2 s3 s4 s5 s6_s7 s8 s9 b7)
echo "KV fallback launch: ruling=${RULING:-<none>} dry_run=$DRY_RUN main=$MAIN_SHA plan=$PLAN_REF"
for s in "${stages[@]}"; do echo "== $s"; "$s"; done
