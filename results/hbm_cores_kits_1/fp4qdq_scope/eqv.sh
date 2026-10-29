#!/bin/bash
# fp4qdq old (main) vs new (scoped loop ints): yosys equiv per parameter set, plus check -assert on new.
D=/srv/opentallas-scratch2/claude/hbm-cores-kits-1/eqv; mkdir -p $D
cp /srv/opentallas-scratch2/claude/hbm-cores-kits-1/fp4qdq_orig.sv $D/gold.sv
cp /srv/opentallas-scratch2/claude/wt/hbm-cores-kits-1/rtl/hbm_accel/generic/ot_hgi_fp4qdq.sv $D/gate.sv
sed -i 's/module ot_hgi_fp4qdq/module gold/' $D/gold.sv; sed -i 's/module ot_hgi_fp4qdq/module gate/' $D/gate.sv
for P in 0 1; do for Q in 0 1; do for X in 0 1; do
cat > $D/e_$P$Q$X.ys <<Y
read_verilog -sv /work/gold.sv
read_verilog -sv /work/gate.sv
chparam -set PACKED $P -set PIPE $Q -set XEXT $X gold gate
proc; opt_clean
tee -o /work/check_gate_$P$Q$X.txt check -assert gate
memory; flatten; opt -fast
async2sync
equiv_make gold gate eq
hierarchy -top eq
equiv_simple -seq 2
equiv_induct -seq 2
tee -o /work/eq_$P$Q$X.txt equiv_status -assert
Y
done; done; done
docker run --rm --name hck1-eqv-$$ --cpus=8 --memory=32g --memory-swap=32g -v $D:/work -w /work openroad/orfs:asap7lock bash -lc '
source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
for f in /work/e_*.ys; do b=$(basename $f .ys); ( timeout 3000 yosys -q -s $f > /work/$b.log 2>&1; echo "$b rc=$?" >> /work/rc.txt ) & done; wait; chown -R '$(id -u):$(id -g)' /work'
cat $D/rc.txt
