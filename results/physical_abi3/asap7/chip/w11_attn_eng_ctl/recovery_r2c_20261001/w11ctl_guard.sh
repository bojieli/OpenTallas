#!/bin/bash
# W11 attention controller route with a fail-fast sequential-count guard.
# usage: w11ctl_guard.sh <name> <cts|finish> <expected_flops>
# The host synth writes <workdir>/stat.txt first; if its flop count is below 80% of expected, the flow is
# killed and guard.json (next to physical.json) records the reason. guard.json is written in every case.
name=$1; stop=$2; EXP=$3
cd /tmp/claude-1000/wt/w11-ctlphys
export OT_SYNTH_TIMEOUT_SECONDS=43200 OT_FLOW_TIMEOUT_SECONDS=86400
W=/home/ubuntu/w11ctl_$name/work
OUT=results/physical_abi3/asap7/chip/w11_attn_eng_ctl/wc833_d512_$name
mkdir -p $OUT
/tmp/claude-1000/w11s/jobs/harden_wc.sh $name --top ot_v41_attn_eng_ctl_phys \
  --source rtl/chip/physical/ot_v41_attn_eng_ctl_phys.sv --source rtl/hdc/v41x/ot_hdc_v41x_attn.sv \
  --param BREG=1 --param REPL=2 --param D=512 --param PHYS=1 --param NSTAGE=2 --orfs-var ADDER_MAP_FILE= \
  --routing-layers M2 M5 --max-transition-ns 0.32 --purpose characterization --core-utilization 40 --place-density 0.6 \
  --pnr-stop-after $stop --keep-workdir $W --output $OUT/physical.json &
FLOW=$!
verdict=pending; seq=-1
while kill -0 $FLOW 2>/dev/null; do
  if [ "$verdict" = pending ] && [ -s $W/stat.txt ] && grep -q "Chip area" $W/stat.txt; then
    seq=$(awk '/DFF|DHLx|DLLx|SDF/ && $1 ~ /^[0-9]+$/ {s+=$1} END {print s+0}' $W/stat.txt)
    if [ $seq -lt $((EXP * 8 / 10)) ]; then
      verdict=aborted
      pkill -P $FLOW; kill $FLOW
      for c in $(docker ps -q); do docker inspect --format "{{range .Mounts}}{{.Source}} {{end}}" $c | grep -q "$W" && docker kill $c; done
    else verdict=passed; fi
  fi
  sleep 30
done
python3 - "$OUT/guard.json" "$verdict" "$seq" "$EXP" <<'PY'
import json,sys
o,v,s,e=sys.argv[1],sys.argv[2],int(sys.argv[3]),int(sys.argv[4])
json.dump(dict(check='sequential cells after host synthesis (stat.txt) vs expected', expected_sequential=e,
               threshold=e*8//10, observed_sequential=s, verdict=v,
               reason=('flops below 80% of expected: the stubbed datapath was optimised away; flow killed'
                       if v=='aborted' else 'datapath survived synthesis' if v=='passed' else 'synthesis did not finish')),
          open(o,'w'), indent=1)
PY
