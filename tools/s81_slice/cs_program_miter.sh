#!/bin/bash
# Directed standard-slice ring program: OUT MUT HB SEED EXTRA_VERILATOR_ARGS.
# Exact fixture command recorded; mutants1/2 and UV must fail, baseline passes.
# Full two-slice Verilator measured47.6GB; admit64GB,8threads.
set -u; export OT_VL_JCAP=0; O=$1; M=${2:-0}; HB=${3:-0}; SEED=${4:-1}; X=${5:-}; mkdir -p $O/old
BASE=${CSF_BASE:-3947653943}
python3 tools/s81_slice/vs_gold.py tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl $O/fixture L0 > $O/fixture.log 2>&1 || exit 4
python3 - "$O/fixture" <<'PYFIX' || exit 4
from pathlib import Path
import sys
p=Path(sys.argv[1]); rows=[int(x,16) for x in (p/"img.mem").read_text().split()]
(p/"pairs.mem").write_text("".join(f"{rows[2*i] | rows[2*i+1]<<128:064x}\n" for i in range(512)))
commands=[int(x,16) for x in (p/"prog.mem").read_text().split()]
c=next(x & ((1<<160)-1) for x in commands if x>>188==1 and (x&15)==8 and ((x>>43)&1))
(p/"swcmd.mem").write_text(f"{c:040x}\n")
print(f"fixture=L0 realSWquant cmd={c:040x} ringRD512pairs eachleaf0/2 POST0/32 HSTORE/RDOUT900")
PYFIX
V=verilator; [ -x ~/.local/opentallas-tools/verilator-5.050/bin/verilator ] && V=~/.local/opentallas-tools/verilator-5.050/bin/verilator
S=rtl/dsrom_sys/s81_dv/slice
SRCS="$S/ot_s81sl_aq12x.sv $S/ot_s81sl_vn.sv $S/ot_s81sl_vp.sv $S/ot_s81sl_vq.sv $S/ot_s81sl_vs.sv $S/ot_s81sl_vsw.sv rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_rxh.sv rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_sw.sv rtl/dsrom_sys/s81_suhc/ot_s81_su_rw.sv rtl/dsrom_sys/s81_suhc/ot_s81_su_rx.sv rtl/hdc/ot_hdc_delay.sv rtl/hdc/ot_hdc_fastfp_lat_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_fp32_add_lat.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fp32_mul_lat.sv rtl/hdc/ot_hdc_fp32_mul_pipe.sv rtl/hdc/ot_hdc_fpu.sv rtl/hdc/ot_hdc_prefix.sv rtl/hdc/ot_hdc_sfu.sv rtl/hdc/v41/ot_hdc_actquant.sv rtl/hdc/v41/ot_hdc_fdiv.sv rtl/hdc/v41/ot_hdc_fsqrt.sv rtl/hdc/v41/ot_hdc_softplus.sv rtl/hdc/v41x/ot_dsrom_aq12.sv rtl/hdc/v41x/ot_dsrom_divc.sv rtl/hdc/v41x/ot_dsrom_fp32_add_l6.sv rtl/hdc/v41x/ot_dsrom_su_add6.sv rtl/hdc/v41x/ot_dsrom_su_f12.sv rtl/hdc/v41x/ot_dsrom_su_fdiv_f12.sv rtl/hdc/v41x/ot_dsrom_su_hcpost_lane_pr.sv rtl/hdc/v41x/ot_dsrom_su_hcpost.sv rtl/hdc/v41x/ot_dsrom_su_norm.sv rtl/hdc/v41x/ot_dsrom_su_swiglu.sv rtl/hdc/v41x/ot_hbm_norm_split_p.sv rtl/hdc/v41x/ot_hbm_norm_split.sv rtl/hdc/v41x/ot_hdc_v41x_sfu.sv rtl/hdc/v41x/ot_hdc_v41x_spshort.sv rtl/lib/ot_rst_relay.sv rtl/proto/ot_fp32_add_rne_pipe.sv physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2/ot_sram_1r1w_128x256_m1_r2c2.v physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v physical/asap7_memory_macros_v2/ot_rom_4096x72_m8/ot_rom_4096x72_m8.v rtl/hdc/v41x/ot_hdc_v41x_vec_side.sv rtl/dsrom_sys/engram/mix/ot_s81_engram_mix.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve.sv rtl/dsrom_sys/s81_dv/eng/ot_s81sl_eg.sv rtl/dsrom_sys/s81_dv/ot_s81dv_norm.sv $S/ot_s81sl_rstop.sv $S/ot_s81sl_xg.sv $S/ot_s81sl_xr.sv rtl/v41rom/ot_v41_kreg.sv rtl/common/ot_prefix.sv rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_reader.sv rtl/dsrom_sys/s81_static_control/ot_s81_pq_calendar_rom.sv rtl/dsrom_sys/s81_ph/pq/ot_s81_pq_stream_rom4_sel.sv rtl/dsrom_sys/s81_die_bind/dsfd_sp_pq_n.sv $S/ot_s81sl_xs_ctl.sv $S/ot_s81sl_xs.sv rtl/dsrom_sys/s81_static_net/ot_s81_retn_static.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_node_NNfu.sv rtl/dsrom_sys/s81_static_net/gen/dsfd_rstg.sv rtl/hdc/ot_hdc_cg.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_lane_cross_hr.sv rtl/dsrom_sys/s81_die_bind/ot_s81_static_column_ingress_hr.sv rtl/dsrom_sys/s81_die_bind/glue/dsfd_cfifo_crs.sv $S/ot_s81sl_cap.sv $S/ot_s81sl_cap_tr.sv $S/ot_s81sl_cap_rt.sv $S/ot_s81sl_cap_p1.sv $S/ot_s81sl_capc2.sv $S/ot_s81sl_cap_ed.sv $S/ot_s81sl_cap_ld.sv rtl/hdc/ot_hdc_delay_rf.sv $S/ot_s81sl_slice.sv $S/ot_s81sl_slice_glue.sv"
# the ve leaf's fp file (leaf_bench.sh) when present
[ -f rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv ] && SRCS="$SRCS rtl/dsrom_sys/s81_dv/eng/ot_s81sl_ve_fp.sv"
python3 - "$O/old" "$BASE" $SRCS <<'EOF' || { echo "OLD_EXTRACT_FAILED"; exit 4; }
import re, subprocess, sys, os
out, base, files = sys.argv[1], sys.argv[2], sys.argv[3:]
txt = {}
for f in files:
    r = subprocess.run(["git", "show", f"{base}:{f}"], capture_output=True, text=True)
    if r.returncode == 0: txt[f] = r.stdout
names = set()
for t in txt.values(): names |= set(re.findall(r"^\s*(?:module|macromodule)\s+(\w+)", t, re.M))
pat = re.compile(r"\b(" + "|".join(sorted(names, key=len, reverse=True)) + r")\b")
with open(os.path.join(out, "old.f"), "w") as fl:
    for f, t in txt.items():
        p = os.path.join(out, f.replace("/", "__")); open(p, "w").write(pat.sub(lambda m: "O_" + m.group(1), t)); fl.write(p + "\n")
print(f"old: {len(txt)} files from {base[:12]}, {len(names)} modules renamed O_*")
EOF
NEW=""; for f in $SRCS; do [ -f $f ] && NEW="$NEW $f"; done
/usr/bin/time -v -o $O/time.log $V --binary --timing -O1 -Wno-fatal -Wno-lint -Wno-style -Wno-TIMESCALEMOD -Wno-WIDTHCONCAT \
  -DDSFD_PQ_STATIC_X2 $X -GMUT=$M -GHB=$HB -GSEED=$SEED --top-module tb_s81sl_slice_csprogram -Mdir $O/obj $(cat $O/old/old.f) $NEW \
  $S/test/tb_s81sl_slice_csprogram.sv --build-jobs ${J:-8} -MAKEFLAGS "OPT_FAST=-O1 OPT_SLOW=-O0 OPT_GLOBAL=-O0" > $O/build.log 2>&1 \
  || { echo "BUILD_FAILED"; grep -m8 -E "%Error" $O/build.log; tail -n 4 $O/build.log; exit 3; }
$O/obj/Vtb_s81sl_slice_csprogram +fixture=$O/fixture > $O/run.log 2>&1
grep -E "^CSP|CSP_PUBLIC_MISMATCH" $O/run.log | head -8
if [ "$M" = 0 ] && [ -z "$X" ]; then grep -q '^CSP PASS' $O/run.log && { echo "EXPECTED PASS MUT=0"; exit 0; }; echo "UNEXPECTED FAIL MUT=0"; exit 1; fi
grep -q '^CSP FAIL' $O/run.log && { echo "EXPECTED FAIL (mutant caught) MUT=$M $X"; exit 0; }; echo "MUTANT NOT CAUGHT MUT=$M $X"; exit 1
