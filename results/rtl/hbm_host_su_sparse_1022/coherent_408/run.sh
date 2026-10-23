#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
for c in 0 2 3 4 5 6 7;do
  iverilog -g2012 -s tb_hostprog -P tb_hostprog.N=462 -P tb_hostprog.LINES=125 -P tb_hostprog.CASE=$c -o final$c.vvp tb_sparse_final.sv ingress.sv collar_sparse_final.sv root.sv rst.sv pgcol.sv programme.sv sram.v > final_compile$c.log 2>&1
  vvp -n final$c.vvp | tee final$c.log
done
