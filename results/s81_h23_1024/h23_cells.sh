#!/usr/bin/env bash
# S81/H23 (10-24): yosys cell-count deltas of the H2 / H3 RTL changes (base = origin/main files, new = this branch).
# usage: h23_cells.sh <src root (this branch)> <base root (origin/main files at the same paths)> <outdir>
# Flow: yosys 0.68, read -sv -DSYNTHESIS, blackbox the unchanged children, chparam, hierarchy, proc / opt, memories kept
# as $mem (memory -nomap: the svc / seqhost arrays are SRAM or unchanged; only logic is compared), flatten, techmap,
# dfflibmap (ASAP7 SEQ RVT TT), abc (ASAP7 RVT TT comb libs), stat.  Prints one CELLS line per (target, base|new).
set -u
SRC=$(readlink -f $1); BASE=$(readlink -f $2); O=$(readlink -m $3); mkdir -p $O
Y=${YOSYS:-$HOME/.local/opentallas-tools/yosys-0.68/bin/yosys}
L=$HOME/.local/opentallas-pdk-asap7/lib/NLDM
SEQ=$L/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib
CL="-liberty $L/asap7sc7p5t_SIMPLE_RVT_TT_nldm_211120.lib -liberty $L/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib -liberty $L/asap7sc7p5t_OA_RVT_TT_nldm_211120.lib -liberty $L/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib"
# yosys 0.68's reader has no `inside`: rewrite `X inside {a, b}` -> `(X == a || X == b)` in a scratch copy (base + new alike)
fix() { python3 - "$1" "$2" <<'PY'
import re, sys, pathlib
src, dst = sys.argv[1], sys.argv[2]
t = pathlib.Path(src).read_text()
t = re.sub(r"\(\s*([A-Za-z_][\w\[\]:]*)\s+inside\s*\{([^}]*)\}\s*\)",
           lambda m: "(" + " || ".join(f"{m.group(1)} == {v.strip()}" for v in m.group(2).split(",")) + ")", t)
pathlib.Path(dst).parent.mkdir(parents=True, exist_ok=True); pathlib.Path(dst).write_text(t)
PY
}
run() {   # name root top "blackboxes" "chparams k=v" "-I dirs" files...
  local n=$1 r=$2 top=$3 bb=$4 prm=$5 inc=$6; shift 6
  {
    for f in "$@"; do fix $r/$f $O/src_$n/$f; done
    echo "read_verilog -sv -DSYNTHESIS $inc $(for f in "$@"; do echo -n "$O/src_$n/$f "; done)"
    for b in $bb; do echo "blackbox $b"; done
    for kv in $prm; do echo "chparam -set ${kv%%=*} ${kv#*=} $top"; done
    echo "hierarchy -top $top"
    echo "proc; opt -fast; memory -nomap; opt -fast; flatten; opt; wreduce; alumacc; share; opt; fsm; opt -fast; memory -nomap"
    echo "techmap; opt -fast"
    echo "dfflibmap -liberty $SEQ"
    echo "abc $CL"
    echo "opt_clean"
    echo "tee -o $O/$n.stat stat"
  } > $O/$n.ys
  $Y -q -l $O/$n.log -s $O/$n.ys > /dev/null 2>&1
  echo "CELLS $n $(grep -m1 -E 'Number of cells|cells$' $O/$n.stat | grep -oE '[0-9]+' | head -1)"
}
U=rtl/dsrom_sys/s81_dv/unit; I=rtl/dsrom_sys/s81_dv/idx; S=rtl/dsrom_sys/s81_dv/svc_rs
for v in base new; do
  R=$SRC; [ $v = base ] && R=$BASE
  # H2: dsdv_svc_att (engine blackboxed; PFIFO 8 to keep the unchanged p store small -- it is a $mem either way)
  run svc_att_$v $R dsdv_svc_att "ot_hdc_v41x_attn_s" "PFIFO=8" "" $S/dsdv_svc_att.sv
  # H3 bk_sel: the die master glue (selector / tx / vmux blackboxed) -- new = + encoder + vo_n merge register
  run bk_vmtx_$v $R dsdv_bk_sel_vmtx "dsdv_bk_sel dsdv_idx_tx_n32 dsdv_idx_vmux" "" "" $I/dsdv_idx_l20s.sv
  # H3 seqhost: L0 link leaf (host ingest + host decode blackboxed) -- new = SELR 1 (sink gate + relay + merge register)
  if [ $v = base ]; then P=""; else P="SELR=1"; fi
  run sh_lk_$v $R dsdv_sh_lk "dsfd_host_native dsdv_sh_sd ot_rst_relay" "$P" "" $U/dsdv_seq_host.sv
  # H3 svc entry: dsdv_svc_rs_c ENTRY 1 with every child blackboxed -- new = + dsdv_svc_selq + the r1 q mux
  run svc_rs_entry_$v $R dsdv_svc_rs_c "dsdv_svc_att dsdv_svc_sx ot_s81_su_sms dsfd_svc_pc ot_s81_svc_job dsdv_sm_so_target dsdv_svc_sot dsdv_sm_gw dsdv_sm_gx dsdv_svc_rs_up dsdv_pv_den_stamp dsfd_dvrly_276_SN dsfd_dvrly_276_NS" "ENTRY=1" "-I$R/$S" $S/dsdv_svc_rs.sv
done
run bk_selids_new $SRC dsdv_bk_selids "" "" "" $I/dsdv_idx_l20s.sv
run sh_selr_new $SRC dsdv_sh_selr "" "" "" $U/dsdv_seq_host.sv
run svc_selq_new $SRC dsdv_svc_selq "" "" "" $S/dsdv_svc_rs.sv
