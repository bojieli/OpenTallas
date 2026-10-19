#!/bin/bash
set -euo pipefail
T=tools/hbm_hidx_wrapper
IMG=openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29
python3 "$T/binding.py"
python3 "$T/arc_domains.py"
for corner in TT FF;do
 docker run --rm --network none -e CORNER="$corner" -v "$PWD:/work" -w /work "$IMG" /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit "$T/min_inventory.tcl" >out/min_inventory_$corner.log 2>&1
 if grep -Eq '\[ERROR|^Error:' out/min_inventory_$corner.log;then exit 1;fi
 grep -q 'MIN_INVENTORY_DONE ff=2904 output=2304' out/min_inventory_$corner.log
done
python3 "$T/min_summary.py"
for f in netlist.json netlist.v native.json direct_caps.json loaded_caps.json identifier_escape_map.json roundtrip.json;do gzip -n -c out/$f >out/$f.gz;done
sha256sum tools/hbm_hidx_wrapper/* canonical/* out/*.json out/*.log out/*.v out/*.lib out/*.sdc out/*.tcl out/*.gz >out/SHA256SUMS_FINAL
