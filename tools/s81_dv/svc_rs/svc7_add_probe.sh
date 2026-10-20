#!/usr/bin/env bash
set -euo pipefail
MODE=${1:?bench or census}
OUT=${2:?output directory}
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)
SRC=(rtl/hdc/v41x/ot_s81svc7_add.sv rtl/hdc/v41x/ot_hdc_v41x_kreg.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv)
if [ "$MODE" = bench ]; then
    VL=$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator
    "$VL" --version
    "$VL" --binary --timing -j 4 -Wno-fatal -Wno-WIDTH --top-module tb_svc7_add \
        -Mdir "$OUT/obj" -o sim "${SRC[@]}" tools/s81_dv/svc_rs/tb_svc7_add.sv > "$OUT/build.log" 2>&1
    "$OUT/obj/sim" > "$OUT/run.log" 2>&1
    tail -n 5 "$OUT/run.log"
elif [ "$MODE" = census ] || [ "$MODE" = graph ]; then
    TOP=ot_s81svc7_add
    if [ "$MODE" = graph ]; then
        SRC=(rtl/hdc/v41x/ot_s81svc7_add_graph_input.sv rtl/hdc/ot_hdc_fp32_f12.sv rtl/hdc/ot_hdc_fastfp.sv rtl/hdc/ot_hdc_prefix.sv)
        TOP=ot_s81svc7_add_graph_input
    fi
    # All paths below are internal to the admitted container. No wall-time cap.
    {
        printf 'read_verilog -sv '
        printf '/src/%s ' "${SRC[@]}"
        printf '\nhierarchy -top %s\n' "$TOP"
        echo 'tcl /src/physical/common_flow/ot_keep_regs.tcl'
        printf 'synth -top %s -flatten -noshare\n' "$TOP"
        echo 'dfflibmap -liberty /tmp/lib/SEQ.lib'
        echo 'abc -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib'
        echo 'opt_clean'
        echo 'stat -liberty /tmp/lib/SIMPLE.lib -liberty /tmp/lib/AO.lib -liberty /tmp/lib/OA.lib -liberty /tmp/lib/INVBUF.lib -liberty /tmp/lib/SEQ.lib'
        echo 'write_verilog -noattr /out/mapped.v'
        echo 'write_json /out/mapped.json'
    } > "$OUT/probe.ys"
    docker run --rm -v "$PWD:/src:ro" -v "$OUT:/out" openroad/orfs:latest bash -lc '
        source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1
        N=/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM
        mkdir -p /tmp/lib
        for k in SIMPLE AO OA; do zcat "$N/asap7sc7p5t_${k}_RVT_TT_nldm_211120.lib.gz" > /tmp/lib/$k.lib; done
        zcat "$N/asap7sc7p5t_INVBUF_RVT_TT_nldm_220122.lib.gz" > /tmp/lib/INVBUF.lib
        cp "$N/asap7sc7p5t_SEQ_RVT_TT_nldm_220123.lib" /tmp/lib/SEQ.lib
        yosys -l /out/synth.log -s /out/probe.ys
    ' > "$OUT/synth.stdout" 2>&1
    if [ "$MODE" = graph ]; then
        python3 tools/s81_dv/svc_rs/svc7_bound_graph.py "$OUT/mapped.json" --top "$TOP" \
            --name ot_s81svc7_add_native --out "$OUT/native.v" > "$OUT/replicate.log" 2>&1
        python3 tools/textbook_lint.py check --netlist "$OUT/native.v" --out "$OUT/native32.json" \
            --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 > "$OUT/native32.log" 2>&1
    else
    python3 tools/textbook_lint.py check --netlist "$OUT/mapped.v" --out "$OUT/native32.json" \
        --set hf_report=32 hf_max=32 hf_port_refuse=32 hf_reset_refuse=32 hf_refuse=32 > "$OUT/native32.log" 2>&1
    fi
    python3 - "$OUT/native32.json" <<'PY'
import json,sys
j=json.load(open(sys.argv[1]))
bad=j.get('refuse',{}).get('high_fanout',[])
print('SVC7_NATIVE32 over32=%d verdict=%s'%(len(bad),'FAIL' if bad else 'PASS'))
sys.exit(bool(bad))
PY
else
    echo "unknown mode $MODE" >&2; exit 2
fi
