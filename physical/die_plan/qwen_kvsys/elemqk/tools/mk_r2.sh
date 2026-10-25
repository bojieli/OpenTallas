#!/bin/bash
# mk_r2.sh SRC_KITDIR DST_KITDIR : copy a placed kit, drop CTS+ results, add ELEM-QK round-2 kit-local knobs
set -e; S=$1; D=$2; mkdir -p $(dirname $D); rm -rf $D
tar cf - -C $(dirname $S) --exclude=signoff --exclude="*/run/results/asap7/*/base/4_*" --exclude="*/run/results/asap7/*/base/5_*" --exclude="*/run/results/asap7/*/base/6_*" --exclude="*/run/results/asap7/*/base/route.guide" --exclude="*/run/logs/asap7/*/base/4_*" --exclude="*/run/logs/asap7/*/base/5_*" --exclude="*/run/logs/asap7/*/base/6_*" $(basename $S) | tar xpf - -C $(dirname $D)
[ "$(basename $S)" = "$(basename $D)" ] || mv $(dirname $D)/$(basename $S) $D
cp -a $(dirname $S)/run_kit.sh $(dirname $D)/
cd $D
cat > wirelen_grt.tcl <<'T'
# ELEM-QK kit-local (10-24 r2): repeaters every <= 120 um before global route (RCX slews on 250 um segments broke 635 um hops)
log_cmd estimate_parasitics -placement
log_cmd repair_design -max_wire_length 120 -verbose
T
sed -i 's/^export OT_TAP_TARGET_PS = .*/export OT_TAP_TARGET_PS = 280/; s/^export HOLD_SLACK_MARGIN = .*/export HOLD_SLACK_MARGIN = 45/' config.mk
grep -q PRE_GLOBAL_ROUTE_TCL config.mk || printf "export PRE_GLOBAL_ROUTE_TCL = /work/wirelen_grt.tcl\n" >> config.mk
sed -i '1a # ELEM-QK r2 kit-local edits: OT_TAP_TARGET_PS 280 (SPEF insertion landed 204..239 vs plan 250), HOLD_SLACK_MARGIN 45 (FF hold -11..-28 after TC repair at 15), PRE_GLOBAL_ROUTE repair_design -max_wire_length 120' config.mk
grep -E "TAP_TARGET|HOLD_SLACK|GLOBAL_ROUTE_TCL|RESIZE_TCL" config.mk | tr '\n' ';'; echo
