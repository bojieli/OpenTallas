set -uo pipefail
R=/srv/opentallas-scratch/claude/ref_gate/ot_qwen_tile_ctl_tp8_query40_resized-20261014-030918; mkdir -p $R/src $R/bin
ACTUAL=$(sha256sum $R.tgz | cut -d' ' -f1)
[ "$ACTUAL" = "c17baa185af807379d8f7b4e8c21a1dd8ed41a1685e3eb67d875e5e18f2d0793" ] || { echo GATE_SOURCE_BINDING_FAIL; exit 1; }
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
docker image inspect --format 'GATE_TOOL_IMAGE_ID={{.Id}} GATE_TOOL_IMAGE_DIGESTS={{json .RepoDigests}}' openroad/orfs:latest 2>/dev/null
printf 'GATE_TOOL_CTS_MACRO_CLUSTER=%s\n' "${OT_CTS_MACRO_CLUSTER:-}"
cd $R/src && echo snapshot-sha256:b842392f29e232d9d70750de33d1255cb1f6283528d7dd2231b02a4ddfae22fc > SOURCE_COMMIT
T0=$(date +%s)
# the gate builds the tree at the ROUTE's corner (ref_tile.py ROUTE_PREFIX: setup at TT, owner option B): a cluster spine
# balanced at SS against the children's TT insertion targets measured a mixed-corner spread (dsfd_sp_pq_c, dscoll_ces0_sp)
export OT_ORFS_CORNER_OVERRIDE=TC
# pin groups exactly as the job's route command sets them (ref_tile.gen_job; the kit.env's own export wins in both)
SRC=$R/src SYNTH_TIMEOUT=2700 OT_PIN_GROUP_MAX=32 bash tools/ref_tile/ref_route.sh physical/ref_tile/ot_qwen_tile_ctl_tp8_query40_resized/kit.env gate $R/routes floorplan; FRC=$?
echo "GATE_FLOW_RC=$FRC GATE_FLOW_S=$(( $(date +%s) - T0 ))"
C=$R/routes/gate/work/orfs; B=$(ls -d $C/results/asap7/*/base 2>/dev/null | head -1)
grep -hE "^\[ERROR|Error:|ERROR \[|timed out|TimeoutExpired|exceeded" $R/routes/gate/flow.log $C/*.log 2>/dev/null | head -8 | sed 's/^/GATE_FLOWERR /'
[ $FRC -eq 0 ] || exit 0
NB=${B#$C/}
docker run --rm -v $R/src:/src:ro -v $C:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base /work/$NB/3_2_place_iop.odb" > $R/iop.log 2>&1; echo "GATE_IOP_RC=$?"
grep -hE "\[ERROR" $R/iop.log | head -4 | sed 's/^/GATE_FLOWERR /'
printf 'read_db /work/%s/3_2_place_iop.odb\nsource /src/tools/fp_margin_lint.tcl\not_fp_lint_dump /work/gate_dump.json\nexit\n' $NB > $C/gate_dump.tcl
docker run --rm -v $R/src:/src:ro -v $C:/work openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /work/gate_dump.tcl > $R/dump.log 2>&1; echo "GATE_DUMP_RC=$?"
python3 tools/textbook_lint.py check --netlist $B/1_2_yosys.v --dump $C/gate_dump.json --out $R/textbook.json --mode refuse --refuse-checks clock_domain,high_fanout,wire_reach | sed 's/^/GATE_TB /'
python3 - $B/1_2_yosys.v ot_qwen_tile_ctl_tp8_ctx <<'EOP'
import re,sys,json
t=open(sys.argv[1]).read(); m=re.search(r"module\s+\\?"+re.escape(sys.argv[2])+r"\s*\((.*?)\);(.*?)endmodule",t,re.S)
ports={}
if m:
  for d in re.finditer(r"\b(input|output|inout)\b\s*(?:signed\s*)?(\[[^\]]*\])?\s*([^;]+);",m.group(2)):
    for n in d.group(3).split(","): ports[n.strip().lstrip("\\")]=[1 if not d.group(2) else None, bool(d.group(2))]
print("GATE_PORTS "+json.dumps(ports))
EOP
grep -h "Chip area\|chip area" $C/reports/asap7/*/base/synth_stat.txt 2>/dev/null | tail -1 | sed 's/^/GATE_AREA /'
if [ "1" = 1 ]; then
  docker run --rm -v $R/src:/src:ro -v $C:/work -w /OpenROAD-flow-scripts/flow openroad/orfs:latest bash -lc "source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; python3 /src/tools/orfs_hold_mm.py /OpenROAD-flow-scripts/flow/scripts >/dev/null && make DESIGN_CONFIG=/work/config.mk WORK_HOME=/work FLOW_VARIANT=base cts" > $R/cts.log 2>&1; echo "GATE_CTS_RC=$?"
  grep -h "\[ERROR" $R/cts.log | head -3 | sed 's/^/GATE_CTSERR /'
  grep -h "^OT_SPINE iter\|^REF_TILE spine" $R/cts.log | tail -2 | sed 's/^/GATE_SPINE /'
  grep -h "OT_SPINE done port" $R/cts.log $C/logs/asap7/*/base/4_1_cts.log 2>/dev/null | head -1 | sed 's/^/GATE_SPINE_DONE /'
  grep -h "^global_placement -density\|Placement target density" $R/cts.log | head -2 | sed 's/^/GATE_GPLD /'
  python3 tools/closure_loop/ck_insertion.py --base $B --all-clocks --output $R/ck.json > $R/ck.log 2>&1; echo "GATE_CK_RC=$?"
  python3 -c "import json;d=json.load(open('$R/ck.json'));print('GATE_CK '+'; '.join(c+' insertion all '+str(d[c]['all']['min'])+'..'+str(d[c]['all']['max'])+' ps (spread '+str(round(d[c]['all']['max']-d[c]['all']['min'],1))+'), boundary mean '+str(d[c]['boundary']['mean']) for c in ('ss','tt','ff') if isinstance(d.get(c),dict) and d[c].get('all'))+'; macro_clk flag '+str((d.get('macro_clk') or {}).get('flag')))" 2>/dev/null
  python3 -c "import json;d=json.load(open('$R/ck.json'));[print('GATE_CK_DOMAIN '+json.dumps({'source':pin,'clock':r.get('clock'),'tt':r.get('tt')})) for pin,r in d.get('clock_measurements',{}).items()]" 2>/dev/null
  docker run --rm -v $R/src:/src:ro -v $C:/work openroad/orfs:latest /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /src/tools/ref_tile/path_classes.tcl > $R/pc.log 2>&1
  grep "^GATE_PC" $R/pc.log
fi
echo GATE_DONE
