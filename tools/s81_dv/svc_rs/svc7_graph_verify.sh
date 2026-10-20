#!/usr/bin/env bash
set -euo pipefail
G=${1:?graph output directory}
G=$(cd "$G" && pwd)
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
cd "$ROOT"
O=$G/${2:-verify}
mkdir -p "$O"
# Functional primitive models come from exactly the mapped RVT TT libraries.
docker run --rm -v "$O:/out" openroad/orfs:latest bash -lc '
    source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
    N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
    mkdir -p /tmp/lib
    for k in SIMPLE AO OA; do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /tmp/lib/$k.lib; done
    zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /tmp/lib/INVBUF.lib
    cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /tmp/lib/SEQ.lib
    for k in SIMPLE AO OA INVBUF SEQ; do echo "read_liberty -ignore_miss_func /tmp/lib/$k.lib"; done > /out/models.ys
    echo "write_verilog -noattr /out/cells.v" >> /out/models.ys
    yosys -l /out/models.log -s /out/models.ys
' > "$O/models.stdout" 2>&1
CELLS=$O/cells.v
if [ -n "${SVC7_COUPON_DIR:-}" ]; then
    SHA=$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["canonical_SEQ_sha256"])' "$SVC7_COUPON_DIR/canonical_model_identity.json")
    python3 tools/qwen_kv_die/canonical_seq_coupon.py \
        --pdk-seq "$SVC7_COUPON_DIR/canonical_SEQ.v" --pdk-sha256 "$SHA" \
        --imported-model "$CELLS" --out "$O/coupon" > "$O/coupon.log" 2>&1
    CELLS=$O/coupon/library_model_pdk.v
fi
VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
"$VL" --version
"$VL" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH -DSVC7_GRAPH_PROBE \
    --top-module tb_svc7_add -Mdir "$O/obj" -o sim \
    "$G/native.v" "$CELLS" rtl/hdc/ot_hdc_fp32_f12.sv \
    rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv tools/s81_dv/svc_rs/tb_svc7_add.sv > "$O/build.log" 2>&1
"$O/obj/sim" > "$O/run.log" 2>&1
tail -n 5 "$O/run.log"
