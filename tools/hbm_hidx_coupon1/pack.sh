#!/bin/bash
set -euo pipefail
cd ..
gzip -c out/native.json >out/native.json.gz
sha256sum tools/hbm_hidx_coupon1/*.py tools/hbm_hidx_coupon1/*.sv tools/hbm_hidx_coupon1/*.sh tools/hbm_hidx_coupon1/*.tcl tools/hbm_hidx_coupon1/oracle/closure_loop/safe_source_contract.py tools/hbm_hidx_coupon1/oracle/dft/liberty.py out/*.log out/*.json out/*.gz out/*.lib out/*.v out/image.txt out/*version.txt >out/SHA256SUMS
