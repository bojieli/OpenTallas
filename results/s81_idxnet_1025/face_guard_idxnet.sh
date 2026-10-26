#!/bin/bash
# S81/IDXNET (2026-10-25) face_guard on the changed hard-core faces: Yosys generic synth (ORFS asap7lock image) +
# tools/die_plan/face_guard.py, as results/s81_h4_1024r/face_guard_lep_idx.sh.  usage (cwd = repo root):
#   face_guard_idxnet.sh OUT TOP FACES_REGEX     e.g. ot_s81sl_lep_mu_ab_idxq '(tl|ca|cb|tm|qc|ql)'
# lep wrappers at the LP-slice opt-ins (CRED 12, DR 12, RX_SRAM 1, IN_PIPE 1, NATIVE32 1); dsdv_idx_qfs as is.
set -e
O=$1; TOP=$2; FACES=$3; W=$(pwd); mkdir -p $O
SRCS=$(sed -n '/^SRCS="/,/"$/p' rtl/dsrom_sys/s81_dv/slice/test/run_lep_idx_bench.sh | tr -d '"' | sed 's/^SRCS=//')
L=rtl/dsrom_sys/s81_link; SL=rtl/dsrom_sys/s81_dv/slice
SRCS=$(eval echo $SRCS)
CH="-chparam CRED 12 -chparam DR 12 -chparam RX_SRAM 1 -chparam IN_PIPE 1 -chparam NATIVE32 1"
case $TOP in dsdv_idx_qfs) SRCS="rtl/dsrom_sys/s81_dv/idx/dsdv_idx_tree.sv rtl/dsrom_sys/s81_dv/idx/dsdv_idx_qfs.sv"; CH="";; esac
{ for f in $SRCS; do case $f in physical/asap7_memory_macros*) echo "read_verilog -lib $f";; *) echo "read_verilog -sv -DSYNTHESIS $f";; esac; done
  echo "hierarchy -check -top $TOP $CH"
  echo "synth"
  echo "opt_clean -purge"
  echo "write_verilog -noexpr -noattr $O/${TOP}_gl.v"
  echo "stat"; } > $O/$TOP.ys
docker run --rm --name oth-s81idxnet-fg-$TOP-$$ -m 24g -u $(id -u):$(id -g) -v $W:$W -v $O:$O -w $W openroad/orfs:asap7lock \
  /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l $O/$TOP.syn.log -s $O/$TOP.ys
python3 - <<PY
import sys, json
sys.path.insert(0, "tools/die_plan")
import face_guard as G
r = G.guard(open("$O/${TOP}_gl.v").read(), None, skip_re=r"^(?!$FACES\$).*")
json.dump(r, open("$O/face_guard_$TOP.json", "w"), indent=1)
print("FACE_GUARD $TOP", r["verdict"], "bits", r["checked"], "ok", r["ok"], "fails", r["fail_counts"])
for k, v in r["fails"].items(): print(k, v[:5])
PY
