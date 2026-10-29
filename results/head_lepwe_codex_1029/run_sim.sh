#!/usr/bin/env bash
# run_sim.sh WT OUT NCYC [MUT]: verilator compare; MUT=1 builds a mutant new design (slot enable off by one) that must FAIL
set -euo pipefail
W=$1; OUT=$2; N=$3; M=${4:-0}
mkdir -p "$OUT"; cd "$OUT"
cp "$W/physical/die_plan/s81/bind/source_modules/portfix178/ot_s81_mu72_lnland.sv" "$W/rtl/dsrom_sys/s81_dv/slice/mu72/ot_s81_mu72_land.sv" \
   "$W"/rtl/common/landed_parent/ot_pl_land.sv "$W"/rtl/common/landed_parent/ot_pl_land_kept_enable.sv \
   "$W"/rtl/common/landed_parent/ot_pl_land_reset_forest.sv "$W"/rtl/common/landed_parent/ot_pl_land_field_copies.sv .
# the new landing modules only (lep_pair top needs the coll lane; not part of this compare)
python3 - "$W/rtl/dsrom_sys/s81_head/ot_s81hd_lep_pair.sv" "$M" <<'PY'
import re,sys
s=open(sys.argv[1]).read()
mods=re.findall(r"module (ot_s81hd_(?:lnland_dw|mu72_land_dw|land_vector_dw_w|land_local_dw)\b.*?endmodule)", s, re.S)
assert len(mods)==4, len(mods)
t="`timescale 1ns/1ps\n`default_nettype none\n"+"\n".join("module "+m for m in mods)+"\n`default_nettype wire\n"
if sys.argv[2]=="1":
    t=t.replace("wire we = (wc[AW-1:0] == s);","wire we = (wc[AW-1:0] == ((s+1)%D));"); assert "(s+1)%D" in t
open("new_dw.sv","w").write(t)
PY
cp /srv/opentallas-scratch2/claude/dh21-lepwe/eq/tb_lnland_dw.sv .
export PATH=$HOME/.local/opentallas-tools/bin:$PATH
verilator --binary --timing -O2 -Wno-fatal -DNCYC=$N -j 4 --top-module tb_lnland_dw --Mdir obj *.sv > build.log 2>&1 || { tail -20 build.log; exit 2; }
obj/Vtb_lnland_dw +verilator+seed+7 > run.log 2>&1 || true
tail -2 run.log
