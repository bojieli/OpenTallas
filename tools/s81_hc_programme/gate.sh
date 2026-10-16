#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../.." && pwd)
out=${1:?fresh output};mkdir -p "$out";cd "$out"
PYTHONPATH="$root/tools/s81_hc_programme" python3 - <<'PY'
from image import image,validate_issue_edges
commands=[dict(op=i,y_tag=0x81c00000+i*32,scalar_age=0x81c00001+i*32,ss_age=0x81c00002+i*32,done_age=0x81c00003+i*32,post_ages=[0x81c00004+i*32+j for j in range(20)],stream_issue=4+i*24)for i in range(128)]
assert len(validate_issue_edges(commands))==128
open('hc_programme.viamap.hex','w').write(image(commands))
PY
sources=("$root/physical/asap7_memory_macros/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v" "$root/rtl/dsrom_sys/s81_static_control/ot_s81_hc_programme_source.sv" "$root/rtl/dsrom_sys/s81_static_control/test/tb_s81_hc_programme_source.sv")
for mut in 0 1 2;do
 verilator --binary --timing -j 2 -Wno-fatal +define+HC_SOURCE_MUT="$mut" --top-module tb_s81_hc_programme_source --Mdir "obj$mut" "${sources[@]}" > "build$mut.log" 2>&1
 if "obj$mut/Vtb_s81_hc_programme_source" +OT_ROM_DIR="$out" > "run$mut.log" 2>&1;then
  if [[ $mut != 0 ]];then echo "FAIL mutant$mut escaped";exit 1;fi
 else
  if [[ $mut == 0 ]];then cat run0.log;exit 1;fi
 fi
 cat "run$mut.log"
done
# Corrupt actual ROM cells while the independent expected command fields stand.
cp hc_programme.viamap.hex original.hex
python3 - <<'PY'
p='hc_programme.viamap.hex';r=open(p).read().splitlines();r[0]=f'{int(r[0],16)^1:0144x}';open(p,'w').write('\n'.join(r)+'\n')
PY
if obj0/Vtb_s81_hc_programme_source +OT_ROM_DIR="$out" > rom_mut.log 2>&1;then echo 'FAIL ROM cell mutant escaped';exit 1;fi
cat rom_mut.log
sha256sum "${sources[@]}" "$root/tools/s81_hc_programme/image.py" > source.sha256
