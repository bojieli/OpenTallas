#!/bin/bash
# usage: run_xs_car_lockstep.sh ; expects exact match at u_ck/u_cf widths, a mismatch on each mutant AZ
set -u; D=$(cd "$(dirname "$0")/.." && pwd); T=$(mktemp -d); rc=0
git -C "$D" show 4d6f5439dcee43b97baffaa731aae826fdcb6a66:rtl/hbm_next/sm/hnx_xs3.sv | sed -n "/^module hnx_xs_car/,/^endmodule/p" | sed "s/module hnx_xs_car/module hnx_xs_car_old/" > $T/old.sv
sed -n "/^module hnx_xs_car/,/^endmodule/p" "$D/hnx_xs3.sv" > $T/new.sv
run() { iverilog -g2012 -s tb_xs_car_lockstep -P tb_xs_car_lockstep.NB=$1 -P tb_xs_car_lockstep.AZ=$2 -P tb_xs_car_lockstep.AZM=$3 -o $T/s $T/old.sv $T/new.sv "$D/tb/tb_xs_car_lockstep.sv" && vvp $T/s | grep ^NB=; }
for row in "532 2 2 0" "256 4 4 0" "532 2 3 1" "532 2 4 1"; do set -- $row
  o=$(run $1 $2 $3); echo "$o"
  m=${o##*mismatches=}; if [ "$4" = 0 ] && [ "$m" != 0 ]; then rc=1; fi; if [ "$4" = 1 ] && [ "$m" = 0 ]; then echo "MUTANT SURVIVED"; rc=1; fi
done; rm -rf $T; echo "rc=$rc"; exit $rc
