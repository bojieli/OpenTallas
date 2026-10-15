#!/usr/bin/env bash
# Exact bench of the banked PQ stream ROM (4 x ot_rom_4096x72_m8 + ot_s81_pq_stream_rom4_sel) vs a 16,384-row
# two-cycle reference; MUT=1 = bank select not aligned to the macro sample edge (must FAIL).
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd); W=$(mkdir -p "$1" && cd "$1" && pwd); MUT=${2:-0}
V=${OT_VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
cd "$W"; python3 - "$ROOT" <<'PY'
import sys; sys.path.insert(0,sys.argv[1]+'/tools/s81_static_control')
from pq_calendar import viamap
w=lambda k:((k&0x3fff)<<34)|(((k*40503)^0x25a5a1234)&((1<<34)-1))
for b in range(4): open(f'rom4_b{b}.viamap.hex','w').write(viamap([w(b*4096+r) for r in range(4096)]))
PY
D=(); [ "$MUT" != 0 ] && D=(+define+OT_S81_PQ_ROM4_MUT_SEL)
"$V" --binary --timing -Wno-fatal -Wno-lint -Wno-style "${D[@]}" --top-module tb_s81_pq_stream_rom4 --Mdir obj \
  "$ROOT/rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv" "$ROOT/rtl/test/dsrom_sys/tb_s81_pq_stream_rom4.sv" \
  "$ROOT/physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" > build.log 2>&1
set +e; ./obj/Vtb_s81_pq_stream_rom4 > run.log 2>&1; set -e; grep ROM4 run.log | tail -n 1
