#!/bin/bash
set -eu
python3 - <<'REF'
from pathlib import Path
s=Path('original.v').read_text();assert 'module qkd_hr_core_peer_sram(' in s
Path('reference_native.v').write_text(s.replace('module qkd_hr_core_peer_sram(','module qkd_hr_core_peer_ref_native(',1))
REF
V=/opt/verilator-5.050/bin/verilator;[ -x "$V" ] || V=$(command -v verilator)
"$V" --version
"$V" --binary --timing --x-initial unique --x-assign unique -Wno-fatal -DOT_MEM_NO_INIT -j 4 --top-module tb_peer_native --Mdir obj_peer_native reference_native.v qkd_hr_core_peer_n32.sv models/comb_models.v canonical_ASR_normalized.v canonical_DFF_normalized.v macro_bb.v tb_peer_native.sv > build_peer_native.log 2>&1
obj_peer_native/Vtb_peer_native +verilator+seed+27 +verilator+rand+reset+2 > run_peer_native.log 2>&1
cat run_peer_native.log
