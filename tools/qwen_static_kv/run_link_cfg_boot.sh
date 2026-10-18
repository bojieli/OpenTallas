#!/bin/bash
# run_link_cfg_boot.sh OUT (KVJ-SMALL 2026-10-17, KV-INT gap item 12): the KV link end's calendar cfg boot-loaded through
# qkd_static_kv_boot_dispatch LINKCFG=1 (image target 11, order 1..9, 11, 0); tb_kv_link_cfg_boot.sv.
#   image: tools/qwen_kv_die/kv_static_programme.link_cfg_words on a fresh d2d_link_calendar.py compile; that compile must
#          regenerate the committed d2d_cal_image.svh byte for byte (the reference sequencer's constants)
#   must PASS: SCN 0 (66 writes == qkd_d2d_cal_seq init stream, identical tables/bases, admission + layer runs identical,
#              setup_ready), SCN 1 (no target 11 -> no setup), SCN 2 (bad padding refused), SCN 3 (LINKCFG=0 refuses 11)
#   must FAIL: MUT 5 (TX/RX swapped), MUT 6 (bases into entry 0) in SCN 0
#   regression at LINKCFG=0: run_die_cfg_boot.sh (KVJ-F DIECFG scenarios + KVJ-A lockstep / 160 CDC / unit receipt)
set -u
O=$(readlink -f "$1"); mkdir -p "$O"; W=$(pwd)
S=rtl/qwen_sys/static_kv_20261014; D=rtl/qwen_sys/d2d_static_20261015
rc=0
python3 -c "
import sys;sys.path.insert(0,'tools/qwen_kv_die')
import kv_static_programme as P
from pathlib import Path
P.link_calendar('$O'); w=P.link_cfg_words(Path('$O')/'cal')
open('$O/target11.hex','w').write(''.join(f'{x:016x}\n' for x in w))" || { echo "FAIL image"; exit 1; }
python3 tools/qwen_split/d2d_cal_seq_image.py "$O/cal" "$O/img.svh" && cmp -s "$O/img.svh" $D/d2d_cal_image.svh \
  && echo "image: compile == committed d2d_cal_image.svh" || { echo "FAIL image differs from d2d_cal_image.svh"; rc=1; }
run(){ # tag scn mut expect
  iverilog -g2012 -I $D -o "$O/$1" -s tb_kv_link_cfg_boot -P tb_kv_link_cfg_boot.SCN=$2 -P tb_kv_link_cfg_boot.MUT=$3 \
    $S/qkd_static_kv_boot_dispatch.sv $D/ot_qwen_d2d_cal_seq.sv $D/ot_qwen_d2d_cal_seq_dies.sv $D/ot_qwen_d2d_static.sv \
    rtl/test/qwen_static_kv/tb_kv_link_cfg_boot.sv > "$O/$1.build.log" 2>&1 || { echo "BUILD FAIL $1"; rc=1; return; }
  l=$( (cd "$O" && vvp -n "$O/$1") 2>&1 | tee "$O/$1.log" | grep -E '^(PASS|FAIL) kv_link_cfg_boot' | tail -1)
  echo "$1 (must $4): ${l:-no result line}"
  case "$l" in $4*) ;; *) rc=1;; esac
}
for s in 0 1 2 3; do run scn$s $s 0 PASS; done
run mut5 0 5 FAIL; run mut6 0 6 FAIL
bash tools/qwen_static_kv/run_die_cfg_boot.sh "$O/regress" > "$O/regress.log" 2>&1 && echo "regression (LINKCFG=0): $(tail -1 "$O/regress.log")" \
  || { echo "regression FAIL (see $O/regress.log)"; rc=1; }
[ $rc = 0 ] && echo "PASS link_cfg_boot: 4 scenarios, 2 mutants caught, DIECFG/KVJ-A regressions unchanged at LINKCFG=0" || echo "FAIL link_cfg_boot"
exit $rc
