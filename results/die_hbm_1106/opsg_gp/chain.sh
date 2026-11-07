#!/bin/bash
# chain.sh CORE VIEW FORM TAG TYPE: gen (unless SKIPGEN) then queue the kit in ot-run from the hub, detached.
S=/srv/opentallas-scratch3/claude/die-hbm-83-opsg; C=$1; VW=$2; T=$4
if [ -z "$SKIPGEN" ]; then bash $S/gen_kits.sh "$@"; fi
K=$(dirname $(ls -d $S/kits/${C}_$T/*/freeze.json 2>/dev/null | head -1) 2>/dev/null)
[ -n "$K" ] && [ -f "$K/run_kit_hbm.sh" ] || { echo "NO KIT $C $T"; exit 1; }
cat >> $K/max_fanout.tcl <<'TT'
# DIE-HBM-83-OPSG (11-06, rb_vB/vK form): every repair_design repeats signal wires at 100 um, for the reg->reg hauls (opsb vF slew 1631).
if {[info commands ot_rd_orig_mw] eq ""} {
  rename repair_design ot_rd_orig_mw
  proc repair_design {args} { puts "OT_MAXWIRE 100"; return [uplevel 1 [list ot_rd_orig_mw -max_wire_length 100 {*}$args]] }
}
TT
echo "{\"form\":\"$3 hub OT_OPSG_GP\",\"by\":\"DIE-HBM-83-OPSG\",\"pin_cycles\":\"rd +5, flt 0\",\"date\":\"$(date)\"}" > $K/FORM_GP.json; touch $K/.keep
ssh -n -o ControlPath=none hub "mkdir -p ~/die-hbm-83-opsg-logs; setsid nohup ~/.local/bin/ot-run --mem 40 --threads 16 --dir $K -- bash $K/run_kit_hbm.sh $K finish 40 16 > ~/die-hbm-83-opsg-logs/${C}_$T.otrun.log 2>&1 < /dev/null &"
echo "QUEUED $C $T $K $(date)"
