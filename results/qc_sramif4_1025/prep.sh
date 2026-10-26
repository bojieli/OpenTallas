#!/bin/bash
# PATH-QC-SRAMIF4 kit prep: copy Codex fullhalf kit -> own variant kit; optional joint pads ODB; IO-HOLD A vector inputs.
set -euo pipefail
SRC=$1; DST=$2; SENDER=$3; PADODB=${4:-}
rsync -a --exclude 'FAIL_*' "$SRC/" "$DST/"
NICK=$(sed -n 's/^export DESIGN_NICKNAME = //p' "$DST/config.mk" | tail -1)
R=$DST/run/results/asap7/$NICK/base
cp -a "$R/5_1_grt.odb" "$R/5_1_grt_fullhalf_codex.odb"
if [ -n "$PADODB" ]; then cp "$PADODB" "$R/5_1_grt.odb"; cp "$PADODB" "$R/5_1_grt_prehold.odb"; echo "5_1_grt.odb := $PADODB (joint pads P0,R0W,R2E,S1 BUFx16f)" >> "$DST/image.txt"; fi
tar -C "$DST" -xf /tmp/so_exact.tar
python3 - "$DST" "$SENDER" <<'PY'
import json,sys,re
k,s=sys.argv[1],float(sys.argv[2])
d=json.load(open(k+'/sdc_lint.json'))
sdc=open(k+'/constraint.sdc').read()
# vector inputs = buses wider than 1 bit in the kit pin set (scalars/rst keep -40, COORD 15:23)
pins=open(k+'/io.tcl').read()
vec=sorted({m for m in d['inputs'] if re.search(r'-pin_name \{'+re.escape(m)+r'\[1\]\}',pins)})
d['hold_in_min_ports_ps']={v:s for v in vec}
d['io_hold_note']=f"PATH-QC-SRAMIF4 {s:g}: IO-HOLD option A (COORD 10:23 (1), hard-core vector inputs COORD 15:23); sender basis {'plan contract 12.5' if s==12.5 else 'PROPOSED measured registered-sender output-min (pending COORD)'}; scalars keep -40; parent io_hold_parent check required"
json.dump(d,open(k+'/sdc_lint.json','w'),indent=1)
sdc+=(f"# PATH-QC-SRAMIF4 IO-HOLD A: vector data inputs take the sender's guaranteed output-min (+{s:g} ps after vclk); scalars keep -40\n"
      f"set_input_delay -min {s:.4f} -clock vclk [get_ports {{{' '.join(v+'[*]' for v in vec)}}}]\n")
open(k+'/constraint.sdc','w').write(sdc)
print('IOHOLD_A', s, vec)
PY
# hold step GRT frame = the kit's own GRT profile (config ROUTING_LAYER_ADJUSTMENT 0.0); 0.25 is the wrong frame (Codex native0 diagnostic: 359 ovf)
sed -i 's/^set_global_routing_layer_adjustment M2-M5 0.25$/set_global_routing_layer_adjustment M2-M5 0.0/' "$DST/hold_grt_s6.tcl"
grep -n "layer_adjustment" "$DST/hold_grt_s6.tcl"
rm -f "$DST/s6_grt_gate.txt" "$DST/postcts_gate_FAIL.txt"
echo "prep $(date -Is) src $SRC sender $SENDER pad ${PADODB:-none}" >> "$DST/image.txt"
