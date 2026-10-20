#!/bin/bash
set -eu
for kind in host nh; do
 top=ot_s81sl_lep; kit=s81sl_lep_std32; bandtop=298.08
 if [ "$kind" = nh ]; then top=${top}_nh; kit=s81sl_lepnh_std32; bandtop=294.84; fi
 docker run --rm -v "$PWD/src:/work:ro" -v "$PWD:/run" openroad/orfs:asap7lock yosys -Q -T -p "read_verilog /work/native_orfs_${kind}_land5/results/asap7/${top}/base/1_2_yosys.v; write_json /run/mapped_${kind}_land5.json" > "mapped_${kind}_land5.log" 2>&1
 python3 src/results/rtl/s81_standard_lep_native32_1020/band_model/build_model.py --root src --mapped "mapped_${kind}_land5.json" --spec "src/tools/ref_tile/specs/${kit}.json" --source 91d1b58f1 --band 2.16 259.2 473.04 "$bandtop" --out "band_${kind}_land5.json"
done
