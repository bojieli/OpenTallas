#!/usr/bin/env bash
# Run this script inside an admitted ot-run/ot-heavy unit (4 GB, one thread).
# It measures synthesis area and clock/reset census; it does not run P&R.
set -euo pipefail
repo=$(git rev-parse --show-toplevel)
run=${1:?Provide an empty scratch directory}
mkdir -p "$run"
cp "$repo/rtl/qwen_split/qfd_res_train_static.sv" "$run/source.sv"
cp "$repo/tools/qwen_split/res_train_inventory.py" "$run/"
docker run --rm -v "$run:/work" --entrypoint sh openroad/orfs:asap7lock -c '
for g in SIMPLE INVBUF; do
 zcat /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_${g}_RVT_TT_nldm_*.lib.gz > /work/$g.lib
done
cp /OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib /work/SEQ.lib'
python3 - "$run" <<'PY'
from pathlib import Path
import re,sys
p=Path(sys.argv[1]);s=(p/'SIMPLE.lib').read_text();b=(p/'INVBUF.lib').read_text()
b=b[re.search(r'\bcell\s*\(',b).start():b.rfind('}')]
(p/'COMB.lib').write_text(s[:s.rfind('}')]+b+'\n}\n')
for band in range(3):
 (p/f'band{band}.ys').write_text(f'''read_verilog -sv source.sv
hierarchy -top qfd_res_train_static -chparam BAND {band}
synth -top qfd_res_train_static -noabc
dfflibmap -liberty SEQ.lib
abc -liberty COMB.lib
clean
stat -liberty SEQ.lib -liberty COMB.lib
write_json parent{band}_mapped.json
''')
PY
cd "$run"
for b in 0 1 2; do
 /usr/bin/time -v docker run --rm -v "$run:/work" -w /work --entrypoint yosys openroad/orfs:asap7lock -s band$b.ys > band$b.log 2>&1
 python3 res_train_inventory.py --mapped parent${b}_mapped.json --libs SEQ.lib COMB.lib --source source.sv --out inventory_band${b}.json > inventory_band${b}-summary.json
done
