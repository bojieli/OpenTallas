#!/bin/bash
# lec_async.sh -- pre-route LEC off the placement critical path (COORD 11-01 05:1x, OWNER 12.28b closure first).
# FLOW-21 class fix, default-on in every kit runner (gen_phys type kits, S81/QC/KV/HBM core kits); OT_LEC_ASYNC=0
# restores the inline (blocking) LEC.
#   start  K NAME IMAGE MEM_GB CPUS [DOCKER]  host, before the flow container: arms K/lec_async.on and a watcher.
#          The flow container, at its LEC step, writes K/lec_async.ready (line 1 stop policy "1" = exit 1 stops
#          (lec.py NOT EQUIVALENT), "nz" = any non-zero exit stops (legacy_gate); line 2 = the command) and goes on
#          to floorplan/place/CTS/route at once.  The watcher runs that command in its own container NAME-lec (same
#          image, /work = K, its own memory cap).  A stopping result writes K/lec_async.stop + the FAIL_PREFLOOR
#          "LEC NOT EQUIVALENT" marker and stops the flow container NAME: the route ends there, the kit is FAIL LEC.
#   finish K RC [STOP_RC=5]                    host, after the flow container: waits for the LEC (aborts it if the
#          flow never reached its LEC step), prints the kit rc (STOP_RC = the runner's LEC exit code when the LEC
#          stopped the kit, else RC).
# Sign-off is unchanged: a kit is only countable with a routed LEC EQUIVALENT receipt.
set -u
cmd=$1; shift
case $cmd in
start)
  K=$1; NAME=$2; IMAGE=$3; MEM=$4; CPUS=$5; DK=${6:-docker}
  rm -f "$K"/lec_async.{on,ready,rc,stop,abort,done,pid}
  touch "$K/lec_async.on"
  setsid nohup bash "$0" watch "$K" "$NAME" "$IMAGE" "$MEM" "$CPUS" "$DK" >> "$K/lec_async.log" 2>&1 < /dev/null &
  echo $! > "$K/lec_async.pid"
  ;;
watch)
  K=$1; NAME=$2; IMAGE=$3; MEM=$4; CPUS=$5; DK=$6; LN="$NAME-lec"
  trap '$DK rm -f "$LN" >/dev/null 2>&1; touch "$K/lec_async.done"' EXIT
  trap 'exit 143' TERM INT HUP
  echo "LEC_ASYNC watcher $(date '+%F %T') pid $$ waiting for the flow's LEC step"
  t0=$(date +%s)
  until [ -f "$K/lec_async.ready" ] || [ -f "$K/lec_async.abort" ]; do
    sleep "${OT_LEC_ASYNC_POLL:-5}"
    # the flow container must exist while we wait (a killed runner never calls finish)
    if [ $(( $(date +%s) - t0 )) -gt 180 ] && [ "$($DK inspect -f '{{.State.Running}}' "$NAME" 2>/dev/null)" != true ] \
       && [ ! -f "$K/lec_async.ready" ]; then touch "$K/lec_async.abort"; fi
  done
  [ -f "$K/lec_async.ready" ] || { echo "LEC_ASYNC aborted: the flow ended before its LEC step"; exit 0; }
  sleep 1
  POL=$(sed -n 1p "$K/lec_async.ready"); RUN=$(sed -n '2,$p' "$K/lec_async.ready")
  echo "LEC_ASYNC $(date '+%F %T') start ($POL): $RUN"
  $DK run --rm --name "$LN" --cpus="$CPUS" --memory="${MEM}g" --memory-swap="${MEM}g" -v "$K":/work \
    -e OT_LEC_HINTS_PRESEED -e OT_LEC_EARLY_COMPARE -e OT_LEC_SUPERSET_VEC -e OT_LEC_RESET_CYCLES \
    -w /OpenROAD-flow-scripts/flow "$IMAGE" bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; $RUN; r=\$?; chown -R $(id -u):$(id -g) /work/lec /work/lec_run.log 2>/dev/null; exit \$r" \
    >> "$K/lec_async.log" 2>&1
  lr=$?
  echo $lr > "$K/lec_async.rc"
  tail -1 "$K/lec_run.log" 2>/dev/null
  if { [ "$POL" = nz ] && [ $lr != 0 ]; } || { [ "$POL" = 1 ] && [ $lr = 1 ]; }; then
    touch "$K/lec_async.stop"
    echo "FAIL_PREFLOOR LEC NOT EQUIVALENT (lec/lec.json; pre-route LEC ran beside the flow, exit $lr: route stopped)" >> "$K/FAIL_PREFLOOR"
    echo "LEC_ASYNC $(date '+%F %T') FAIL LEC exit $lr: stopping flow container $NAME"
    $DK stop -t 10 "$NAME" >/dev/null 2>&1
  elif [ $lr != 0 ]; then
    echo "LEC WARNING (exit $lr): not proved, recorded in lec/lec.json; the flow continues"
  else
    echo "LEC_ASYNC $(date '+%F %T') LEC exit 0"
  fi
  ;;
finish)
  K=$1; RC=$2; SRC=${3:-5}
  [ -f "$K/lec_async.ready" ] || touch "$K/lec_async.abort"
  P=$(cat "$K/lec_async.pid" 2>/dev/null)
  until [ -f "$K/lec_async.done" ] || { [ -n "$P" ] && ! kill -0 "$P" 2>/dev/null; }; do sleep "${OT_LEC_ASYNC_POLL:-5}"; done
  rm -f "$K/lec_async.on"
  grep -h "^LEC_ASYNC\|^LEC WARNING" "$K/lec_async.log" 2>/dev/null | tail -2 >&2
  if [ -f "$K/lec_async.stop" ]; then echo "$SRC"; else echo "$RC"; fi
  ;;
*) echo "usage: lec_async.sh start|finish ..." >&2; exit 2;;
esac
