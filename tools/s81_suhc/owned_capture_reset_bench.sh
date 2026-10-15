#!/bin/bash
# Lockstep against immutable pre-move leaves and actual region capture flops; random traffic + repeated reset.
set -euo pipefail
out=$1; mut=${2:-0}; mkdir -p "$out"; out=$(realpath "$out")
python3 - "$out" "$mut" <<'PY'
import pathlib,re,sys
out=pathlib.Path(sys.argv[1]);mut=int(sys.argv[2])
def block(path,name):
 text=pathlib.Path(path).read_text();return re.search(r'^module '+name+r'\b.*?^endmodule',text,re.M|re.S).group()
cth='rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_cth.sv';nt='rtl/dsrom_sys/s81_suhc/hier/ot_s81_hc_ntree.sv'
a=block(cth,'ot_s81_hc_ctfx_cap');b=block(nt,'ot_s81_hc_ctfx_nt')
if mut==1:
 old='else fv_local <= fv;';assert a.count(old)==1;a=a.replace(old,'else fv_local <= 0;')
elif mut==2:
 old='\n            if (!rst_n) v <= 0; else v <= fv;';assert b.count(old)==1;b=b.replace(old,'\n            if (!rst_n) v <= 0; else v <= 0;')
else:assert mut==0
(out/'leaf_subset.sv').write_text(a+'\n'+b+'\n'+block(cth,'ot_s81_hc_ctq')+'\n'+block('rtl/hdc/ot_hdc_sfu.sv','ot_hdc_vline')+'\n'+block('rtl/hdc/ot_hdc_delay.sv','ot_hdc_delay')+'\n')
PY
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing --top-module tb_s81_owned_capture -Wno-fatal -Wno-WIDTH -j 4 -Mdir "$out/build" "$out/leaf_subset.sv" tools/s81_suhc/ownership_reset_reference.sv rtl/dsrom_sys/s81_suhc/test/tb_s81_owned_capture.sv > "$out/build.log" 2>&1
"$out/build/Vtb_s81_owned_capture" | tee "$out/run.log"
