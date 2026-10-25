#!/bin/bash
# S81/H4 face_guard on the lep IDX core (tl / ca / cb faces): Yosys generic synth + tools/die_plan/face_guard.py
set -e
W=/srv/opentallas-scratch/claude/wt/s81-h4; O=/srv/opentallas-scratch2/claude/s81-h4/fg
mkdir -p $O; cd $W
SRCS=$(sed -n '/^SRCS="/,/"$/p' rtl/dsrom_sys/s81_dv/slice/test/run_lep_idx_bench.sh | tr -d '"' | sed 's/^SRCS=//')
L=rtl/dsrom_sys/s81_link; SL=rtl/dsrom_sys/s81_dv/slice
SRCS=$(eval echo $SRCS)
# SRAM macro models are hard macros in the kit: read as black boxes (-lib), so only std-cell logic is synthesised
{ for f in $SRCS; do case $f in physical/asap7_memory_macros*) echo "read_verilog -lib $f";; *) echo "read_verilog -sv -DSYNTHESIS $f";; esac; done
  echo "hierarchy -check -top ot_s81sl_lep_mu_ab_idx -chparam CRED 12 -chparam DR 12 -chparam RX_SRAM 1 -chparam IN_PIPE 1 -chparam NATIVE32 1"
  echo "synth"
  echo "opt_clean -purge"
  echo "write_verilog -noexpr -noattr $O/lep_idx_gl.v"
  echo "stat"; } > $O/syn.ys
docker run --rm --name oth-s81h4-fg-$$ -m 24g -u $(id -u):$(id -g) -v $W:$W -v $O:$O -w $W openroad/orfs:asap7lock \
  /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l $O/syn.log -s $O/syn.ys
python3 - <<PY
import sys, json, re
sys.path.insert(0, "tools/die_plan")
import face_guard as G
r = G.guard(open("$O/lep_idx_gl.v").read(), None, skip_re=r"^(?!(tl|ca|cb)$).*")
json.dump(r, open("$O/face_guard.json", "w"), indent=1)
print("FACE_GUARD", r["verdict"], "bits", r["checked"], "ok", r["ok"], "fails", r["fail_counts"])
for k, v in r["fails"].items(): print(k, v[:5])
PY
