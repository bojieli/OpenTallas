#!/bin/bash
# PATH-QC-N59 LEC (epyc1 /srv/opentallas-scratch2/claude/path-qc-n59/lec): gold = main qfd_native59_qbank (read_verilog)
# with the main per-bit-mask macro as black box; gate = the 16-enable qbank read by yosys-slang (gen_gate.ys -> gate.v)
# reaching the SAME black box through the macro's documented mask expansion (mask_x = w_mask_bits of the regenerated
# model).  Both sides share one black box: its 1,549 pin bits per instance are compare points / free inputs.
set -e
K=${1:-kit}
docker run --rm -m 16g -v $PWD/$K:/work -v $PWD/$K:/out openroad/orfs:asap7lock bash -lc \
  "/OpenROAD-flow-scripts/tools/install/yosys/bin/yosys -q -l /out/gen_gate.log -s /work/gen_gate.ys; chown -R $(id -u):$(id -g) /out"
python3 lec.py $K --netlist $K/gate.v --out ${2:-out} --mem 24 --jobs 4   # lec.py = tools/die_plan/lec.py @ main 5236ba8c1
