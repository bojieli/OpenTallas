#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
B=/srv/opentallas-scratch/claude/codex-hbm-gen2e4r5-tailclasses-1020
cd "$B/src_27a01b34d"
O=$B/land0_diag; mkdir -p "$O"
python3 - "$B/artifacts/net/relays_d4g_land.json.gz" "$O/rf0044.json.gz" <<'PY'
import gzip,json,sys,hashlib
p=sys.argv[1];L=json.load(gzip.open(p,'rt'));L['relay_splice_v2']=[b for b in L['relay_splice_v2'] if b['bus']=='rf0044'];assert len(L['relay_splice_v2'])==1
with gzip.open(sys.argv[2],'wt') as f:json.dump(L,f)
print('ACTUAL_RF0044_SOURCE',hashlib.sha256(open(p,'rb').read()).hexdigest(),L['relay_splice_v2'][0]['driver'],L['relay_splice_v2'][0]['sinks'].keys())
PY
python3 tools/hbm_die_v16/relay_lockstep_bench.py --layer "$O/rf0044.json.gz" --out "$O/old_k1" --cycles 100
python3 "$B/relay_lockstep_bench_k0.py" --layer "$O/rf0044.json.gz" --out "$O/fixed_k2" --cycles 100
python3 "$B/relay_lockstep_bench_k0.py" --layer "$O/rf0044.json.gz" --out "$O/mut_land_k" --mut land_k --cycles 100
mkdir -p "$O/mut_encomb"
cp "$O/fixed_k2/tb_relay_lockstep.sv" "$O/mut_encomb/tb_relay_lockstep.sv"
python3 - "$O" <<'PY'
from pathlib import Path
import sys
for p in Path(sys.argv[1]).glob('*/tb_relay_lockstep.sv'):
 s=p.read_text();mark='  always @(negedge clk) if(cyc>=3 && cyc<=15) $display("EPOCH_TRACE cyc=%0d en=%b enq=%b wc=%0d rc=%0d k=%0d out=%h fault=%b",cyc,rs,rf0044_k02_00_l0.u_land.g_hop0.en_q,rf0044_k02_00_l0.u_land.wc,rf0044_k02_00_l0.u_land.rc,rf0044_k02_00_l0.u_land.k,rf0044_k02_00_l0__o[7:0],rf0044_k02_00_l0__f);\n'
 p.write_text(s.replace('endmodule',mark+'endmodule'))
PY
D=rtl/hbm_accel/die_glue
SRC=($D/hbfd_rly_fc_masters.sv $D/hbfd_rly_fcf_masters.sv $D/hbfd_rly_masters.sv $D/ot_hbm_rly_fc.sv $D/ot_hbm_rly_fcf.sv $D/ot_hbm_rly.sv rtl/lib/ot_rst_relay.sv $D/hbfd_lane_masters.sv $D/ot_hbm_lane.sv rtl/qwen_split/qfd_fwd_lane.sv rtl/hdc/ot_hdc_cg.sv)
VL=/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator
sha256sum "${SRC[@]}" "$B/relay_lockstep_bench_k0.py" > "$O/source_sha256.txt"
for leg in old_k1 fixed_k2 mut_land_k mut_encomb; do
 EXTRA=(); [ "$leg" != mut_encomb ] || EXTRA=(-DOT_QFD_LAND_MUT_ENCOMB)
 "$VL" --binary --timing -Wno-fatal -Wno-lint -Wno-style --x-assign fast --x-initial fast --output-split 20000 --output-split-cfuncs 2000 -MAKEFLAGS OPT_FAST=-O1 -MAKEFLAGS OPT_SLOW=-O0 --top-module tb_relay_lockstep -j 4 --Mdir "$O/build_$leg" -o sim "${EXTRA[@]}" "${SRC[@]}" "$O/$leg/tb_relay_lockstep.sv" > "$O/$leg.build.log" 2>&1
 "$O/build_$leg/sim" > "$O/$leg.sim.log" 2>&1
 echo "LEG $leg $(grep 'RELAY_LOCKSTEP ' "$O/$leg.sim.log" | tail -1)"
done
