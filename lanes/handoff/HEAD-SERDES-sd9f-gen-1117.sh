#!/bin/bash
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
T=/srv/opentallas-scratch2/claude/kw45/src_head_pin_d0ee4a2afb10_nf15d2_pgr1
E=/srv/opentallas-scratch2/claude/fable-fix-head-serdes/sd9e_lane/sd9e
L=/srv/opentallas-scratch2/claude/fable-fix-head-serdes/sd9f_lane/sd9f
test ! -e "$L/gen"
mkdir -p "$L"
cp -a "$E/plan" "$L/plan"
cp -a "$E/rtl" "$L/rtl"
python3 -I - "$E" "$L" <<'PY'
import sys,json,hashlib
from pathlib import Path
e,l=map(Path,sys.argv[1:]);p=l/'plan/prep/source_plan.json'
d=json.loads(p.read_text());t=d['partition_types']['hd_serdes']
assert t['verilog_defines']==['OT_S81_RM_STAGED']
t['verilog_defines'].append('OT_S81_KP4_ENC_LA')
d['note']+=' | sd9f: existing exact GF evaluation-domain encoder, no extra latency versus sd9e'
p.write_text(json.dumps(d,indent=1)+'\n')
r=l/'plan/prep/wave_prepare.json';z=json.loads(r.read_text());z['prepared_plan_sha256']=hashlib.sha256(p.read_bytes()).hexdigest();r.write_text(json.dumps(z,indent=1)+'\n')
f=l/'rtl/kit_rtl.f';s=f.read_text().replace(str(e),str(l));f.write_text(s)
q=l/'rtl/kit_rtl.json';x=json.loads(q.read_text());x['defines']=['-DSYNTHESIS','OT_S81_RM_STAGED','OT_S81_KP4_ENC_LA']
x['source_sha256']={k.replace(str(e),str(l)):v for k,v in x['source_sha256'].items()}
for name,sha in x['source_sha256'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==sha,(name,sha)
x['candidate_profile']='sd9f: sd9e RXstage plus stock OT_S81_KP4_ENC_LA; delta versus sd9e0cycles'
q.write_text(json.dumps(x,indent=1)+'\n')
print('SD9F_COHERENT_INPUT_COPY_PASS')
PY
P=$L/plan/prep
cd "$T"
env OT_SIGNED_VIEW_SHA=$T/physical/die_plan/s81_head/prep/signed_view_sha_head.json OT_PLACE_MAX_FANOUT=32 \
 OT_GRT_NONPORT_HOLD=1 OT_CORE_TAP_REACH_UM=0 OT_PREGRT_FF_HOLD_AUTO=-1 OT_MAX_BUFFER_PERCENT=100 OT_GRT_POST_MAX_S=0 \
 OT_HOLD_STOP_PS=-1000000 OT_CLAND_STRIP_DENS=1.0 OT_RFLOW=0 OT_TT_SETUP_REPAIR=both OT_PG_DIE_PHASE=1 OT_PGCAP=1 \
 OT_IO_HOLD=sender_min OT_CONS_KIT=1 OT_CONS_UTIL=0.25 OT_GEN_M8_GRANT=1 OT_CONS_MAX_LAYER=M9 OT_CONS_STRIP_ROWS=1 \
 OT_GEN_SECONDARY_CLOCK=hd_serdes:pma_rck[0]:pma_rck:1000:80:210 OT_PG_TRACK_TRUTH=1 OT_PG_TRACK_TRUTH_WIDE_SPACING=1 \
 OT_PG_CELL_KEEPOUT=0 OT_PG_PIN_CHECK=warn OT_GRT_ALLOW_CONGESTION=1 OT_FLOW_TAG=head-serdes-sd9f-la \
 python3 -I tools/die_plan/gen.py phys "$P/source_plan.json" --clock-landing "$P/source_sidecar.json" --hold-ff-margin 0 \
 --types hd_serdes --kit-rtl hd_serdes=$L/rtl/kit_rtl.f --rtl-root "$T" --out "$L/gen" > "$L/gen.log" 2>&1
K=$L/gen/hd_serdes
mkdir -p "$K/source_gen_replaced"
cp -p "$K/vclk_measured_hold.tcl" "$K/pregrt_ff_hold.tcl" "$K/config.mk" "$K/source_gen_replaced/"
cp "$E/gen/hd_serdes/vclk_measured_hold.tcl" "$K/vclk_measured_hold.tcl.new"; mv "$K/vclk_measured_hold.tcl.new" "$K/vclk_measured_hold.tcl"
cp "$E/gen/hd_serdes/pregrt_ff_hold.tcl" "$K/pregrt_ff_hold.tcl.new"; mv "$K/pregrt_ff_hold.tcl.new" "$K/pregrt_ff_hold.tcl"
printf '\nexport OT_PREGRT_HOLD_SETUP_MARGIN = 60\nexport OT_TAP_FOLLOW_RE =\n' >> "$K/config.mk"
cat > "$L/gen/run_route.sh" <<EOF
#!/bin/bash
L=$L/gen
bash \$L/run_kit.sh \$L/hd_serdes \${1:-grt} 80 16 > \$L/hd_serdes/run_\${1:-grt}.log 2>&1
EOF
python3 -I "$K/kit_preflight.py" "$K" > "$K/preflight_sd9f.log" 2>&1
cat "$K/preflight_sd9f.log"
echo SD9F_GEN_READY
