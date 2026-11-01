#!/bin/bash
set -eu
K=$1
GOAL=${2:-grt}
[ "$GOAL" = grt ] || { echo 'GRT-only diagnostic runner: refused non-GRT scope' >&2; exit 2; }
MEM=${3:-24}
CPUS=${4:-2}
odb=$(find "$K/run/results/asap7" -path '*/base/4_cts.odb' -type f | head -n 1)
test -n "$odb" || { echo 'GRT NOT RUN: current CTS checkpoint missing' >&2; exit 1; }
logdir=${odb%/4_cts.odb}
logdir=${logdir/\/run\/results\//\/run\/logs\/}
mkdir -p "$logdir"
cat > "$K/codex_grt50.tcl" <<'TCL'
set paths [glob -nocomplain /work/run/results/asap7/*/base/4_cts.odb]
if {[llength $paths] != 1} { error "expected one CTS source checkpoint" }
set source [lindex $paths 0]
read_db $source
set b [ord::get_db_block]
set count 0
foreach n [$b getNets] {
 if {[$n getSigType] eq "CLOCK"} {
  incr count
  if {[$n isSpecial]} { $n clearSpecial }
  foreach it [$n getITerms] { $it clearSpecial }
 }
}
puts "CODEX_CLOCK_INCLUSIVE clock_nets=$count congestion_iterations=50"
set_routing_layers -signal M2-M5 -clock M2-M5
set_global_routing_layer_adjustment M2-M5 0.25
global_route -congestion_iterations 50 -congestion_report_file /work/codex_cong50.rpt -allow_congestion -verbose
write_guides [file join [file dirname $source] codex_grt50.guide]
write_db [file join [file dirname $source] 5_1_grt.odb]
puts "CODEX_GRT_DONE no detailed-route or signoff scope"
TCL
DOCKER=docker
$DOCKER info >/dev/null 2>&1 || DOCKER='sudo docker'
# Preserve the original CTS image.txt invocation receipt for the adopted CTS row.
cp /srv/opentallas-scratch2/claude/codex-qc-su-trials/cts_measure.tcl "$K/codex_cts_measure.tcl"
# Harvest TT/FF frame measurements once while the same admitted diagnostic job is alive; never write SIGNED views.
$DOCKER run --rm --cpus "$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work -w /work openroad/orfs:asap7lock bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; for C in TT FF; do OT_CORNER=$C openroad -exit /work/codex_cts_measure.tcl > /work/cts_measure_${C}.log 2>&1 || exit $?; done; openroad -exit /work/codex_grt50.tcl' > "$logdir/5_1_grt.log" 2>&1
rc=$?
printf 'grt goal exit %s\n' "$rc" > "$K/codex_grt50.exit"
tail -n 6 "$logdir/5_1_grt.log"
exit "$rc"
