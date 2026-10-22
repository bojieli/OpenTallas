set -uo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/qfd_native59_dv_service_safe3-20261019-113209; mkdir -p $R/src $R/bin
# Keep the original full measurement stream on the host. GNU tee -p continues
# writing this file if SSH closes its output pipe; the admitted job must finish
# and retain its terminal receipt rather than dying at the next echo.
exec > >(tee -p "$R/execution.log") 2>&1
# Intentional early exits (for example failed floorplan geometry) are terminal
# too. The trap records script status; tool status remains in GATE_*_RC.
trap 'rc=$?; echo "GATE_SCRIPT_RC=$rc"; echo GATE_DONE' EXIT
ACTUAL=$(sha256sum $R.tgz | cut -d' ' -f1)
[ "$ACTUAL" = "971ba70755cbace9d667bf1066ab010804ff2d6f0f5fd4ae9662c993158095ce" ] || { echo GATE_SOURCE_BINDING_FAIL; exit 1; }
echo "GATE_SOURCE_ARCHIVE_SHA256=$ACTUAL"
tar -xzf $R.tgz -C $R/src || exit 1
rm -f $R.tgz
cat > $R/bin/docker <<'EOS'
#!/bin/bash
for e in ${PATH//:/ }; do if [ -x "$e/docker" ] && ! [ "$e/docker" -ef "$0" ]; then
  if [ "${1:-}" = run ]; then shift; exec "$e/docker" run -e LEC_CHECK=0 -e OT_CTS_MACRO_CLUSTER "$@"; fi
  exec "$e/docker" "$@"; fi; done; exit 127
EOS
chmod +x $R/bin/docker; export PATH=$R/bin:$PATH
# GATE STEP CAP (ROOT 2026-10-15): a CTS / trial-GRT step that has not finished in 14400 s is a stall (a 15 h
# dsfd_vm_write_dispatch_b24 gate sat in the DPL negotiation legalizer at 150k illegal cells after repair_design tripled
# the instance count); kill the named container and report GATE_STALL instead of holding a fleet slot for days
ot_capped() {  # ot_capped NAME docker run --name NAME ...
  local n=$1 t0=$(date +%s) rc; shift
  timeout -k 60 14400 "$@"; rc=$?
  if [ $(( $(date +%s) - t0 )) -ge 14400 ]; then docker kill "$n" >/dev/null 2>&1; echo "GATE_STALL $n exceeded 14400 s"; fi
  return $rc
}
docker image inspect --format 'GATE_TOOL_IMAGE_ID={{.Id}} GATE_TOOL_IMAGE_DIGESTS={{json .RepoDigests}}' openroad/orfs:latest 2>/dev/null
printf 'GATE_TOOL_CTS_MACRO_CLUSTER=%s\n' "${OT_CTS_MACRO_CLUSTER:-}"
cd $R/src && echo snapshot-sha256:4952b9cb859e795cbc1b4a3aa9c1a5ddd73dc2664c128e9f71284eb6f1d87c54 > SOURCE_COMMIT
T0=$(date +%s)
# the gate builds the tree at the ROUTE's corner (ref_tile.py ROUTE_PREFIX: setup at TT, owner option B): a cluster spine
# balanced at SS against the children's TT insertion targets measured a mixed-corner spread (dsfd_sp_pq_c, dscoll_ces0_sp)
export OT_ORFS_CORNER_OVERRIDE=TC
export HM=0.03
export OT_ROUTE_HOLD_CORNERS=mm
export OT_MM_FF_SDC=physical/ref_tile/qfd_native59_dv_service_safe3/signoff.sdc
export OT_CTS_FIX_HOOKS='physical/common_flow/cg_pushdown.tcl physical/common_flow/clk_net_protect.tcl physical/common_flow/link_budget_hook.tcl'
# pin groups exactly as the job's route command sets them (ref_tile.gen_job; the kit.env's own export wins in both)
SRC=$R/src SYNTH_TIMEOUT=2700 OT_PIN_GROUP_MAX=32 bash tools/ref_tile/ref_route.sh physical/ref_tile/qfd_native59_dv_service_safe3/kit.env gate $R/routes floorplan; FRC=$?
echo "GATE_FLOW_RC=$FRC GATE_FLOW_S=$(( $(date +%s) - T0 ))"
C=$R/routes/gate/work/orfs; B=$(ls -d $C/results/asap7/*/base 2>/dev/null | head -1)
grep -hE "^\[ERROR|Error:|ERROR \[|timed out|TimeoutExpired|exceeded" $R/routes/gate/flow.log $C/*.log 2>/dev/null | head -8 | sed 's/^/GATE_FLOWERR /'
[ $FRC -eq 0 ] || exit 0
NB=${B#$C/}
docker run --rm -v $R/src:/src:ro -v $C:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base /work/$NB/3_2_place_iop.odb" > $R/iop.log 2>&1; echo "GATE_IOP_RC=$?"
grep -hE "\[ERROR" $R/iop.log | head -4 | sed 's/^/GATE_FLOWERR /'
printf 'read_db /work/%s/3_2_place_iop.odb\nsource /src/tools/fp_margin_lint.tcl\not_fp_lint_dump /work/gate_dump.json\nexit\n' $NB > $C/gate_dump.tcl
docker run --rm -v $R/src:/src:ro -v $C:/work openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/gate_dump.tcl > $R/dump.log 2>&1; DUMPRC=$?; echo "GATE_DUMP_RC=$DUMPRC"
[ "$DUMPRC" -eq 0 ] || exit 0
# Validate the actual placed-IO dump before CTS or any PASS evidence is accepted.
python3 tools/fp_margin_lint.py pins $C/gate_dump.json --out $R/pin_geometry.json > $R/pin_geometry.log 2>&1; PINRC=$?
sed 's/^/GATE_FP /' $R/pin_geometry.log
echo "GATE_PIN_GEOMETRY_RC=$PINRC"
[ -s $R/pin_geometry.json ] && python3 -c 'import json,sys;print("GATE_PIN_GEOMETRY_RESULT "+json.dumps(json.load(open(sys.argv[1])),separators=(",",":")))' $R/pin_geometry.json
[ "$PINRC" -eq 0 ] || exit 0
# LAYOUT IMAGES (owner rule 20:45 10-15): the floorplan the route starts from (macros, pins, PG) -> PNG on the gate side
ot_layout() {  # ot_layout ODB TAG: tools/ref_tile/layout_dump.tcl on the odb, json back as one zlib+base64 line
  printf 'read_db /work/%s\nsource /src/tools/ref_tile/layout_dump.tcl\nexit\n' "$1" > $C/gate_layout_$2.tcl
  docker run --rm -e OT_LAYOUT_OUT=/work/gate_layout_$2.json -e OT_LAYOUT_CLOCKS=ck -e OT_LAYOUT_TOP=qfd_native59_dv_service_r1 -v $R/src:/src:ro -v $C:/work openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/gate_layout_$2.tcl > $R/layout_$2.log 2>&1
  [ -s $C/gate_layout_$2.json ] && python3 -c "import zlib,base64,sys;print('GATE_LAYOUT_B64 '+sys.argv[2]+' '+base64.b64encode(zlib.compress(open(sys.argv[1],'rb').read(),9)).decode())" $C/gate_layout_$2.json $2
}
ot_layout $NB/3_2_place_iop.odb floorplan
python3 tools/textbook_lint.py check --netlist $B/1_2_yosys.v --dump $C/gate_dump.json --out $R/textbook.json --mode refuse --refuse-checks clock_domain,high_fanout,wire_reach,reset_landing --set reset_ports=rst_n | sed 's/^/GATE_TB /'
echo "GATE_TB_RC=${PIPESTATUS[0]}"
python3 - $B/1_2_yosys.v qfd_native59_dv_service_r1 <<'EOP'
import re,sys,json
t=open(sys.argv[1]).read(); m=re.search(r"module\s+\\?"+re.escape(sys.argv[2])+r"\s*\((.*?)\);(.*?)endmodule",t,re.S)
ports={}; ranges={}
if m:
  for d in re.finditer(r"\b(input|output|inout)\b\s*(?:signed\s*)?(\[[^\]]*\])?\s*([^;]+);",m.group(2)):
    for n in d.group(3).split(","): ports[n.strip().lstrip("\\")]=[1 if not d.group(2) else None, bool(d.group(2))]
    if d.group(2):
      bounds=re.fullmatch(r"\[\s*(-?\d+)\s*:\s*(-?\d+)\s*\]",d.group(2))
      if bounds:
        a,b=map(int,bounds.groups())
        for n in d.group(3).split(","): ranges[n.strip().lstrip("\\")]=[min(a,b),max(a,b)]
print("GATE_PORTS "+json.dumps(ports))
print("GATE_PORT_RANGES "+json.dumps(ranges))
EOP
grep -h "Chip area\|chip area" $C/reports/asap7/*/base/synth_stat.txt 2>/dev/null | tail -1 | sed 's/^/GATE_AREA /'
# MEMORY-FF LINT (ROOT 2026-10-17, S-ELEM static14 TT -57.9): yosys PROC_ROM / MEMORY_BMUX2ROM turn a case table into a
# $mem ROM and MEMORY_DFF then folds the neighbouring register into its read port; the register vanishes from the netlist
grep -h "merging output FF to cell\|merged .*FF to cell\|merging .*FF to cell\|^Converted [0-9]* switch" $C/logs/asap7/*/base/1_*yosys*.log 2>/dev/null | head -60 | sed 's/^/GATE_MEMFF /'
# KEEP-MODULE AUDIT (ROOT-KEEP 10-18, HBM lgtap 6a79110b8): every kit keep entry must survive synthesis as hierarchy; a
# $paramod-renamed module is missed by SYNTH_KEEP_MODULES (yosys only warns) and its replicated copies get merged back
grep -h "did not match any module" $C/logs/asap7/*/base/1_*yosys*.log 2>/dev/null | sort -u | head -40 | sed 's/^/GATE_KEEPWARN /'
python3 tools/ref_tile/keep_module_audit.py netlist $B/1_2_yosys.v qfd_native59_dv_service_r1
# PORT-LATENCY (ROOT 2215): the elaborated pin-register table + wrapper of this synthesis (ot_pin_regs.tcl) come back for
# tools/ref_tile/port_latency.py; the closure loop records the same export from the route at CLOSE for the compilers
[ -s $B/ot_pin_regs.tsv ] && [ -s $B/ot_pin_regs_wrapper.v ] && python3 -c "import zlib,base64,sys;print('GATE_PIN_REGS_B64 '+' '.join(base64.b64encode(zlib.compress(open(f,'rb').read(),9)).decode() for f in sys.argv[1:]))" $B/ot_pin_regs.tsv $B/ot_pin_regs_wrapper.v
if [ "1" = 1 ]; then
  ot_capped gate_cts_${R##*/} docker run --rm --name gate_cts_${R##*/} -v $R/src:/src:ro -v $C:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base cts" > $R/cts.log 2>&1; CTSRC=$?; echo "GATE_CTS_RC=$CTSRC"
  grep -h "\[ERROR" $R/cts.log | head -3 | sed 's/^/GATE_CTSERR /'
  grep -h "^OT_SPINE iter\|^REF_TILE spine" $R/cts.log | tail -2 | sed 's/^/GATE_SPINE /'
  grep -h "OT_SPINE done port" $R/cts.log $C/logs/asap7/*/base/4_1_cts.log 2>/dev/null | head -1 | sed 's/^/GATE_SPINE_DONE /'
  grep -h "^global_placement -density\|Placement target density" $R/cts.log | head -2 | sed 's/^/GATE_GPLD /'
  # A failed prerequisite must not restart placement through a downstream make target.
  if [ "$CTSRC" -ne 0 ]; then
    echo "GATE_CK_SKIPPED=cts_failed"
    echo "GATE_PATH_CLASSES_SKIPPED=cts_failed"
    echo "GATE_PLACED_LAYOUT_SKIPPED=cts_failed"
    [ "1" != 1 ] || echo "GATE_GRT_SKIPPED=cts_failed"
    exit 0
  fi
  python3 tools/closure_loop/ck_insertion.py --base $B --all-clocks --raw-source --output $R/ck.json > $R/ck.log 2>&1; echo "GATE_CK_RC=$?"
  python3 -c "import json;d=json.load(open('$R/ck.json'));print('GATE_CK '+'; '.join(c+' insertion all '+str(d[c]['all']['min'])+'..'+str(d[c]['all']['max'])+' ps (spread '+str(round(d[c]['all']['max']-d[c]['all']['min'],1))+'), boundary mean '+str(d[c]['boundary']['mean']) for c in ('ss','tt','ff') if isinstance(d.get(c),dict) and d[c].get('all'))+'; macro_clk flag '+str((d.get('macro_clk') or {}).get('flag')))" 2>/dev/null
  python3 -c "import json;d=json.load(open('$R/ck.json'));[print('GATE_CK_DOMAIN '+json.dumps({'source':pin,'clock':r.get('clock'),'tt':r.get('tt'),'ff':{k:(r.get('ff') or {}).get(k) for k in ('boundary','all','child_flop','macros')}})) for pin,r in d.get('clock_measurements',{}).items()]" 2>/dev/null
  docker run --rm -e OT_GATE_SIGNOFF_SDC=/src/physical/ref_tile/qfd_native59_dv_service_safe3/signoff.sdc -v $R/src:/src:ro -v $C:/work openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/tools/ref_tile/path_classes.tcl > $R/pc.log 2>&1
  grep -E "^GATE_(PC|XCLK)" $R/pc.log
  ot_layout $NB/4_1_cts.odb placed
fi
# TRIAL ROUTE (owner rule 20:45 10-15; every kit since ROOT-0330-GRT 10-18, was parent / cluster kits only): place +
# global-route here (no detailed route): overflow, per-layer usage and the congestion hotspots come back; overflow > 0
# refuses the kit.  Single tiles (HBM qcore r5, S81 bk g2, KV landh0_548, Qwen h16b) passed the gate and failed GRT hours
# into the route; the trial costs minutes.  ROOT-0630 (coordinator HANDOFF 0gi, 10-18): a SINGLE-tile kit's trial is a
# congestion screen and runs SKIP_INCREMENTAL_REPAIR=1 (first GRT only, no post-GRT repair_design / repair_timing /
# incremental re-route: ~2 min instead of ~25); parent / cluster kits keep the full trial.
if [ "1" = 1 ]; then
  GT0=$(date +%s)
  ot_capped gate_grt_${R##*/} docker run --rm --name gate_grt_${R##*/} -v $R/src:/src:ro -v $C:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base GLOBAL_ROUTE_ARGS='-allow_congestion -verbose' GENERATE_ARTIFACTS_ON_FAILURE=1 grt" > $R/grt.log 2>&1; echo "GATE_GRT_RC=$? GATE_GRT_S=$(( $(date +%s) - GT0 ))"
  GL=$(ls $C/logs/asap7/*/base/5_1_grt.log 2>/dev/null | head -1)
  [ -n "$GL" ] && grep -E "^(M[0-9]+|Total) +[0-9]+ +[0-9]+ +[0-9.]+%" $GL | tail -12 | sed 's/^/GATE_GRT_LAYER /'
  [ -n "$GL" ] && grep -hE "GRT-0116|Total overflow|overflow" $GL | tail -3 | sed 's/^/GATE_GRT_NOTE /'
  CR=$(ls $C/reports/asap7/*/base/congestion.rpt 2>/dev/null | head -1)
  [ -n "$CR" ] && python3 -c "import zlib,base64,sys;print('GATE_CONG_B64 '+base64.b64encode(zlib.compress(open(sys.argv[1],'rb').read()[:20000000],9)).decode())" $CR
  ot_layout $NB/5_1_grt.odb placed
fi
