cd "$(dirname "$0")"
for t in eq eq_mut; do
docker run --rm -u $(id -u):$(id -g) -v $PWD:/w -w /w openroad/orfs:latest bash -c "export PATH=/OpenROAD-flow-scripts/tools/install/yosys/bin:\$PATH; yosys -V; yosys -q -l $t.log $t.ys >/dev/null 2>&1; echo YOSYS_RC_$t=\$?"
grep -E "SUCCESS|FAIL|failed|Induction step proven|Number of cells" $t.log | tail -6
done
for d in src mut; do
verilator --binary -Wno-fatal -Wno-lint -Wno-style --top-module tb -j 8 --Mdir obj_$d lockstep.sv $d/ot_hdc_prefix.sv $d/ot_hdc_fastfp.sv $d/ot_hdc_fp32_add_lat.sv $d/ot_hgi_coll_pring.sv $d/ot_hgi_coll_pring_static.sv -o lockstep >vl_$d.log 2>&1 || tail vl_$d.log
echo "== lockstep $d"; ./obj_$d/lockstep +verilator+rand+reset+2 | tail -4
done
