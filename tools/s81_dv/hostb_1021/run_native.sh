#!/usr/bin/env bash
set -euo pipefail
O=${1:?fresh output};mkdir -p "$O";O=$(cd "$O";pwd);ROOT=$PWD;LIB=$O/lib;mkdir -p "$LIB"
IMAGE=$(docker image inspect openroad/orfs:latest --format '{{.Id}}')
printf '%s\n' "$IMAGE" >"$O/image_id.txt"
docker run --rm -v "$LIB:/techlib" "$IMAGE" bash -lc '
 set -euo pipefail
 for c in SEQ SIMPLE AO OA INVBUF;do
  src=(/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_${c}_RVT_TT_nldm*.lib*)
  test "${#src[@]}" = 1 && test -f "${src[0]}"
  if [[ ${src[0]} = *.gz ]];then gzip -dc "${src[0]}" >"/techlib/$c.lib";else cp "${src[0]}" "/techlib/$c.lib";fi
 done'
sha256sum "$LIB"/*.lib >"$O/lib_sha256.txt"
H=rtl/dsrom_sys/s81_dv/hostb
for top in ${HBE_NATIVE_TOPS:-dsdv_hostb_stage dsdv_hostb_return dsdv_hostb_head dsdv_hostb_head_egress};do
 case "$top" in dsdv_hostb_stage|dsdv_hostb_return|dsdv_hostb_head|dsdv_hostb_head_egress);;*)exit 2;;esac
 D=$O/$top;mkdir -p "$D";PARAM='';case "$top" in dsdv_hostb_stage|dsdv_hostb_head_egress) PARAM="chparam -set ENABLE 1 $top";;esac
 cat >"$D/map.ys" <<YS
read_verilog -sv -DSYNTHESIS /src/rtl/lib/ot_reset_sync.sv /src/$H/dsdv_hostb_hold.sv /src/$H/dsdv_hostb_crc512.sv /src/$H/dsdv_hostb_rx.sv /src/$H/dsdv_hostb_tx.sv /src/$H/dsdv_hostb_stage.sv /src/$H/dsdv_hostb_return.sv /src/$H/dsdv_hostb_head.sv /src/$H/dsdv_hostb_head_egress.sv
$PARAM
hierarchy -check -top $top
read_liberty -lib /techlib/SEQ.lib
read_liberty -lib /techlib/SIMPLE.lib
read_liberty -lib /techlib/AO.lib
read_liberty -lib /techlib/OA.lib
read_liberty -lib /techlib/INVBUF.lib
tcl /src/physical/common_flow/ot_keep_regs.tcl
synth -top $top -flatten -noshare
dfflibmap -liberty /techlib/SEQ.lib
abc -liberty /techlib/SEQ.lib -liberty /techlib/SIMPLE.lib -liberty /techlib/AO.lib -liberty /techlib/OA.lib -liberty /techlib/INVBUF.lib
setattr -mod -unset keep_hierarchy
flatten
opt_clean
tee -o /out/stat.txt stat -liberty /techlib/SEQ.lib -liberty /techlib/SIMPLE.lib -liberty /techlib/AO.lib -liberty /techlib/OA.lib -liberty /techlib/INVBUF.lib
write_verilog -noattr /out/flat.v
YS
 docker run --rm -v "$ROOT:/src:ro" -v "$D:/out" -v "$LIB:/techlib:ro" "$IMAGE" bash -lc 'source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1;yosys -l /out/synth.log -s /out/map.ys' >"$D/build.log" 2>&1
 args=();for f in "$LIB"/*.lib;do args+=(--liberty "$f");done
 python3 tools/ref_tile/native_census.py --netlist "$D/flat.v" --top "$top" --out "$D/census.json" "${args[@]}" >"$D/census.log" 2>&1 || true
 python3 - "$D/census.json" <<'PY'
import json,sys
r=json.load(open(sys.argv[1]));print('HBE_NATIVE',r['top'],r['status'],r['max_dynamic_loads'],len(r['violations']),len(r['role_errors']))
PY
done
