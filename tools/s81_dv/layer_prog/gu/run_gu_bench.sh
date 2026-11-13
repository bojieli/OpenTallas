#!/bin/bash
# run_gu_bench.sh <src root R> <kits dir K> <out dir O> [measure]: build tb_gu_layer (REAL dsdv_seq_host + dsdv_gunit of
# the tree R: the file lists of tools/s81_dv/layer_prog/run_seqhost_prog.sh and rtl/dsrom_sys/s81_dv/unit/test/
# run_gunit_bench.sh) with Verilator 5.050 (the closure daemon's pin), run the positive kit K/kit0 and every mutant kit
# K/m_* (each must FAIL), write O/<kit>.log, O/verilator.version, O/sources.sha256.  Prints GU_BENCH PASS / FAIL.
# DIE-S81-89 11-13: the bench compiles the bf hard core dsdv_gunit_l1f_bf in the SAME form the lowering schedules: the define
# set of lower_gu.bf_defines() (recipes.json [dsdv_gunit_l1f_bf].defines, or $OT_GUNIT_BF_DEFINES; "" = gf2), and every kit's
# prog/gu/ffn.router.plan.json must carry that set (a kit lowered for another form -> GU_BENCH FAIL before any sim).
# With measure = 1 the router latency (last SC beat on vi_n -> router ids row on vo_n / vo_s) is read from the kit0 log
# and printed beside the lowering's RT_LAT (GU_RT_LAT measured ... computed ...).
set -u
R=$(realpath $1); K=$(realpath $2); O=$3; mkdir -p $O; O=$(realpath $O); MEAS=${4:-0}
H=$(cd "$(dirname "$0")" && pwd)
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
U=$R/rtl/dsrom_sys/s81_dv/unit
F="$R/rtl/lib/ot_async_fifo.sv $R/rtl/lib/ot_reset_sync.sv $R/rtl/lib/ot_rst_relay.sv $R/rtl/link/ot_link_afifo.sv
   $R/rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv $R/rtl/hdc/ingest/ot_hdc_ingest_fp8q.sv $R/rtl/hdc/ingest/ot_hdc_kv_ingest.sv
   $R/rtl/hdc/ingest/ot_rom_host_ingest.sv $R/physical/rom_host_ingest/rtl/dsfd_host.sv
   $R/rtl/dsrom_sys/s81_ingest/ot_s81_ingest_visibility_fence.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_native.sv
   $R/rtl/dsrom_sys/s81_ingest/dsfd_host_sd.sv $R/rtl/dsrom_sys/s81_ingest/dsfd_host_c.sv
   $R/rtl/dsrom_sys/s81_static_control/ot_s81_fixed_issue.sv $U/ot_dsdv_fixed_issue.sv $U/ot_dsdv_walk_issue.sv $U/ot_dsdv_vstop.sv $U/dsdv_sh_sd.sv $U/dsdv_seq_host.sv
   $R/physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v
   $R/rtl/hdc/ot_hdc_fastfp_lat_f12.sv $R/rtl/hdc/ot_hdc_delay.sv $R/rtl/hdc/ot_hdc_sfu.sv $R/rtl/hdc/v41x/ot_dsrom_su_norm.sv
   $R/rtl/hdc/ot_hdc_fastfp.sv $R/rtl/hdc/ot_hdc_fp32_f12.sv $R/rtl/hdc/ot_hdc_fp32_mul_lat.sv $R/rtl/hdc/ot_hdc_fp32_add_lat.sv
   $R/rtl/hdc/ot_hdc_prefix.sv $R/rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv $R/rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv
   $R/rtl/hdc/v41x/ot_dsrom_su_f12.sv $R/rtl/hdc/v41x/ot_dsrom_su_add6.sv $R/rtl/hdc/v41x/ot_dsrom_divc.sv $R/rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv
   $R/rtl/hdc/v41/ot_hdc_select_tree.sv $R/rtl/hdc/v41x/ot_dsrom_su_bias_select.sv $R/rtl/hdc/v41x/ot_hdc_v41x_sfu.sv
   $R/rtl/hdc/v41/ot_hdc_fdiv.sv $R/rtl/hdc/v41/ot_hdc_sinkhorn_p.sv $R/rtl/hdc/v41/ot_hdc_skp_predecode.sv $R/rtl/hdc/v41/ot_hdc_sinkhorn_fs.sv
   $R/rtl/hdc/v41/ot_hdc_skf_predecode.sv $R/rtl/hdc/v41/ot_hdc_sinkhorn.sv $R/rtl/hdc/v41/ot_hdc_sk_arith.sv $R/rtl/hdc/v41/ot_hdc_sk_recip_rom.sv
   $R/rtl/lib/ot_rst_region16.sv $R/physical/asap7_memory_macros_v2/ot_sram_1r1w2c_32x64_m1/ot_sram_1r1w2c_32x64_m1.v
   $R/rtl/hdc/ot_hdc_cg.sv $U/dsdv_gunit_pass.sv $U/dsdv_gunit_tail.sv $U/dsdv_gunit_tail_fs.sv $U/dsdv_gunit_l0.sv $U/dsdv_gunit_l1.sv $U/dsdv_gunit_l2.sv
   $U/dsdv_gunit_l3.sv $U/dsdv_gunit_l4.sv $U/dsdv_gunit_l5.sv $U/dsdv_gunit_l0r.sv $U/dsdv_gunit_l4r.sv $U/dsdv_gunit_l5f.sv
   $U/dsdv_gunit_sel.sv $U/dsdv_gunit_sel_n32.sv $R/rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv $U/dsdv_gunit_l1f.sv $U/dsdv_gunit_l1c.sv
   $U/dsdv_gunit.sv"
# TOK-ALL-16: CW_AGE = the die tree's cw_seqhost link age (kit prog/gu/*.plan.json cw_age; tb default 25 = bind9).
# TOK-ALL-16: GU_DEFS unset = the native-32 L5 configuration of rtl/dsrom_sys/s81_dv/unit/test/run_gunit_bench.sh (same
# defaults); GU_DEFS="" = the RTL defaults, i.e. the define set the selected b178 bind manifest compiles (no GUNIT defines)
GUNIT_L5_DEFS="${GU_DEFS-+define+OT_S81_GUNIT_PIN_COPY=${GUNIT_PIN_COPY:-1} +define+OT_S81_GUNIT_CONTROL_SAFE=${GUNIT_CONTROL_SAFE:-1} +define+OT_S81_GUNIT_Q4=${GUNIT_Q4:-1} +define+OT_S81_GUNIT_FANOUT_SAFE=${GUNIT_FANOUT_SAFE:-1} +define+OT_S81_GUNIT_NAT32=${GUNIT_NAT32:-1} +define+OT_S81_VE_LOADSAFE5}"
BF=$(python3 -I $H/../lower_gu.py) || { echo "GU_BENCH FAIL lower_gu"; exit 3; }
echo "$BF" > $O/lower_gu.json
BF_DEFS=$(python3 -I -c 'import json,sys; print(" ".join("+define+" + d for d in json.loads(sys.argv[1])["bf_defines"]))' "$BF")
echo "GU_BF $BF"
for k in $K/kit0 $K/m_*; do
  [ -d $k ] || continue
  python3 -I -c 'import json,sys; a=json.loads(sys.argv[1]); b=json.load(open(sys.argv[2]))
sys.exit(0 if (sorted(b.get("bf_defines", [])), b.get("rt_lat")) == (sorted(a["bf_defines"]), a["rt_lat"]) else 1)' "$BF" $k/prog/gu/ffn.router.plan.json \
    || { echo "GU_BENCH FAIL kit $(basename $k) was lowered for another bf form / RT_LAT than $BF"; exit 3; }
done
$V --version > $O/verilator.version
sha256sum $F $H/tb_gu_layer.sv $H/gu_kit.py $H/../lower_gu.py $(dirname $(dirname $(dirname $H)))/../physical/die_plan/s81/cores/legacy/recipes.json > $O/sources.sha256
if [ ! -x $O/obj/tb ]; then
  $V --binary --timing -j ${J:-8} -O2 -Wno-fatal -Wno-WIDTH -Wno-lint -Wno-style -Wno-UNOPTFLAT -Wno-TIMESCALEMOD \
    +define+DSFD_HOST_C_STATIC $GUNIT_L5_DEFS $BF_DEFS ${CW_AGE:++define+CW_AGE=$CW_AGE} --top-module tb_gu_layer --Mdir $O/obj -o tb $F $H/tb_gu_layer.sv -CFLAGS -O1 > $O/build.log 2>&1 \
    || { echo "GU_BENCH BUILD_FAIL"; grep -m8 %Error $O/build.log; exit 3; }
fi
bad=0
for k in $K/kit0 $K/m_*; do
  [ -d $k ] || continue
  n=$(basename $k)
  $O/obj/tb $(cat $k/tb.args | sed "s#+dir=[^ ]*#+dir=$k#") +measure=$MEAS > $O/$n.log 2>&1
  r=$(grep -m1 '^GU_LAYER' $O/$n.log); echo "$n: $r"
  if [ $n = kit0 ]; then echo "$r" | grep -q '^GU_LAYER PASS' || bad=1
  else echo "$r" | grep -q '^GU_LAYER FAIL' || bad=1; fi
done
if [ "$MEAS" != 0 ] && [ -f $O/kit0.log ]; then
  python3 -I - $K/kit0/prog/gu/ffn.router.plan.json $O/kit0.log "$BF" <<'PY' | tee $O/rt_lat.json
import json, re, sys
pl = json.load(open(sys.argv[1])); bf = json.loads(sys.argv[3]); tl = pl['t_last_sc']; m = {}
for line in open(sys.argv[2]):
    g = re.match(r'GU OUT ([NS]) (\d+) ([0-9a-f]+)', line)
    if g and (int(g.group(3), 16) >> 47) & 0x3FF == pl['row'] and g.group(1) not in m:
        m[g.group(1)] = int(g.group(2)) - tl     # ids row = first CTL row write to the router row (payload a [26 +: 10])
meas = [m.get('N'), m.get('S')]
print(json.dumps(dict(bf_defines=bf['bf_defines'], t_last_sc=tl, measured=meas, computed=bf['rt_lat'], equal=meas == bf['rt_lat'])))
print('GU_RT_LAT measured %s computed %s %s' % (meas, bf['rt_lat'], 'EQUAL' if meas == bf['rt_lat'] else 'DIFFERENT'), file=sys.stderr)
PY
fi
[ $bad = 0 ] && echo "GU_BENCH PASS" || echo "GU_BENCH FAIL"
exit $bad
