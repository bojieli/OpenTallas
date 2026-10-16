#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output};mkdir -p "$out";cd "$out"
PYTHONPATH="$root/tools/s81_hc_programme:$root/tools/s81_static_control" python3 - <<'PY'
from image import image,issuer_done_row
from program import encode_program
commands=[dict(op=i,y_tag=0x81c00000+i*32,scalar_age=0x81c00001+i*32,ss_age=0x81c00002+i*32,done_age=0x81c00003+i*32,post_ages=[0x81c00004+i*32+j for j in range(20)],stream_issue=4+i*24)for i in range(6)]
open('hc_programme.viamap.hex','w').write(image(commands))
rows=[dict(engine=2,arg=(i<<20)+i*32,issue=2+i*24,done=issuer_done_row(2+i*24,8))for i in range(6)]+[dict(engine=15,arg=0,issue=160,done=0)]
p=encode_program(rows,7,1)
open('program.hex','w').write(''.join(f'{w["word"]:09x}\n'for w in p['writes']))
PY
sources=("$root/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" "$root/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv" "$root/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_mailbox.sv" "$root/rtl/dsrom_sys/s81_static_control/ot_s81_hc_programme_source.sv" "$root/rtl/dsrom_sys/s81_static_control/ot_s81_hc_programme_endpoint.sv" "$root/rtl/dsrom_sys/s81_static_control/test/tb_s81_hc_issuer_programme.sv")
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_s81_hc_issuer_programme --Mdir obj "${sources[@]}" > build.log 2>&1
obj/Vtb_s81_hc_issuer_programme +OT_ROM_DIR="$out" > run.log 2>&1
cat run.log
sha256sum "${sources[@]}" "$root/tools/s81_hc_programme/image.py" > source.sha256
