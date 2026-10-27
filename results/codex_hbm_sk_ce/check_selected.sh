#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
grep -q "SPLIT PASS MUT=0 errors=0 results=40" run_result0.log
grep -q "SPLIT FAIL MUT=1 errors=20763" run_result1.log
grep -q "SHELL PASS LAND=1 ADV=0 CAPADD=3 DELAY=2 errors=0 results=40" shellrun_v3_land1_pass.log
grep -q "SHELL FAIL LAND=1 ADV=0 CAPADD=3 errors=20759" shellrun_v2_result1.log
grep -q "SHELL FAIL LAND=0 ADV=0 CAPADD=2 DELAY=2 errors=20760" shellrun_v3_land0_rejected.log
echo SELECTED_CE_CONTRACT_PASS
