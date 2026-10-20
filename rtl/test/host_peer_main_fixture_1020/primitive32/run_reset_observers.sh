#!/bin/bash
# Private proof-only source-pinned runtime observers. No gate policy changes.
set -euo pipefail
REPO=$(cd "$1" && pwd); OUT=$2; MODE=${3:-exact}
P=$REPO/rtl/test/host_peer_main_fixture_1020/primitive32
mkdir -p "$OUT/models"; cd "$OUT"
zcat "$P/original.v.gz" > original.v
zcat "$P/qkd_hr_core_peer_n32.sv.gz" > qkd_hr_core_peer_n32.sv
cp "$P/canonical_ASR_normalized.v" "$P/canonical_DFF_normalized.v" .
cp "$P/models/comb_models.v" models/
cp "$REPO/physical/asap7_memory_macros/ot_sram_1r1w_32x546_m1_p192_mir/ot_sram_1r1w_32x546_m1_p192_mir.v" macro_bb.v
python3 - "$P" "$MODE" <<'PY'
from pathlib import Path
import sys,hashlib,re,json
p=Path(sys.argv[1]);mode=sys.argv[2];s=Path('qkd_hr_core_peer_n32.sv').read_text();assert hashlib.sha256(s.encode()).hexdigest()=='1277bb49de6e8e577c431282c5d8a057211f6e0ff06e6674b78b37393fce4336'
r=Path('original.v').read_text();assert 'module qkd_hr_core_peer_sram(' in r;Path('reference_native.v').write_text(r.replace('module qkd_hr_core_peer_sram(','module qkd_hr_core_peer_ref_native(',1))
t=(p/'tb_peer_native_copycheck.sv').read_text();i=t.rfind('endmodule');assert i>0;Path('tb_peer_native.sv').write_text(t[:i]+(p/'reset_observers.svh').read_text()+t[i:])
if mode in ('early_final','early_final_isolate'):
 m=re.search(r'(?m)^.*\bu59981_c1 \(.*?\);$',s);assert m
 body,n=re.subn(r'\.D\([^()]+\)',".D(1'b1)",m[0]);assert n==1
 s=s[:m.start()]+body+s[m.end():];Path('qkd_hr_core_peer_n32.sv').write_text(s)
elif mode!='exact':raise ValueError(mode)
if mode=='early_final_isolate':
 t=Path('tb_peer_native.sv').read_text();lines=t.splitlines(True);hit=[i for i,l in enumerate(lines) if 'PEER_NATIVE FAIL COPY_STATE' in l];assert len(hit)==1
 lines[hit[0]]='// Existing copy-state checker disabled only to isolate new reset-age observer.\n';Path('tb_peer_native.sv').write_text(''.join(lines))
Path('run_binding.json').write_text(json.dumps({'mode':mode,'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'tb_sha256':hashlib.sha256(Path('tb_peer_native.sv').read_bytes()).hexdigest()}))
PY
V=/opt/verilator-5.050/bin/verilator; [ -x "$V" ] || V=$(command -v verilator)
"$V" --version | tee version.txt; grep -q 'Verilator 5.050' version.txt
"$V" --binary --timing --x-initial unique --x-assign unique -Wno-fatal -DOT_MEM_NO_INIT -j 4 --top-module tb_peer_native --Mdir obj reference_native.v qkd_hr_core_peer_n32.sv models/comb_models.v canonical_ASR_normalized.v canonical_DFF_normalized.v macro_bb.v tb_peer_native.sv > build.log 2>&1
obj/Vtb_peer_native +verilator+seed+27 +verilator+rand+reset+2 > run.log 2>&1
