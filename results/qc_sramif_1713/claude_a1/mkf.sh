#!/bin/bash
# PATH-QC-SRAMIF2 variant F: SRAM macros MY (LEF SYMMETRY X Y) so every macro pin (rd_out, wd_in, addr, clk) faces EAST,
# toward the E-face read ports; same sites, same recipe as M (face_flops + macro_pin_flops); mscts macro taps on E side.
set -euo pipefail
kind=$1; R=/srv/opentallas-scratch2/claude/path-qc-sramif2; S=/srv/opentallas-scratch2/claude/codex-qc-sramif-1713/${kind}_aspect_a1; D=$R/${kind}_a1f
[ -e $D ] && { echo exists; exit 1; }
cp -a $S $D
sed -i 's/kq_qfd_dv_s8x_\(btab\|prog\)_adj0/kq_qfd_dv_s8x_\1_aspect1713a1/g' $D/*.sh $D/*.tcl 2>/dev/null || true
sed -i "s#/srv/opentallas-scratch2/claude/codex-qc-sramif-1309/[a-z_0-9]*#$D#" $D/so_only.sh
cp $R/${kind}_a1m/go_a1.sh $D/
sed -i 's/ R0}/ MY}/g' $D/macro_place.tcl; grep -c " MY}" $D/macro_place.tcl
python3 - $D/mscts_spec.tcl $kind <<'PY'
import re,sys
f,kind=sys.argv[1:];s=open(f).read()
mx,mw=(129.6,94.824) if kind=='btab' else (90.72,172.824)
def rep(m):return '{%s E%s {%.3f %s}}'%(m.group(1),m.group(2),mx+mw+7,m.group(3))
s2=re.sub(r'\{(g_\S+) W(\d) \{[\d.]+ ([\d.]+)\}\}',rep,s)
s2=s2.replace('# NEW R0 profile1713','# NEW R0 profile1713 + PATH-QC-SRAMIF2 variant F (SRAM MY: macro clk pins on the E edge)')
assert s2!=s;open(f,'w').write(s2)
PY
tail -5 $D/mscts_spec.tcl
