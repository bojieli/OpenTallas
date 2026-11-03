#!/usr/bin/env bash
# Assemble the HEAD tail-publisher (option A) gate packet: Codex's passed B-pilot native ROM/PART1 sources and genuine
# tile0/tile639 contexts (PART1 rc14 source replaced by the rc16 TAILPUB copy), the original rc14 PART1 module renamed
# ref_w12_matvec_part as the lockstep reference, the lockstep bench, and the yosys FF census script.
# usage: prepare_head_tailpub_gate.sh <codex-B-pilot-packet> <out-dir>
set -euo pipefail
B=$1; O=$2; R=$(cd "$(dirname "$0")/../.." && pwd)
test ! -e "$O"; mkdir -p "$O/src" "$O/contexts"
(cd "$B" && sha256sum -c SHA256SUMS >/dev/null)
for f in "$B"/src/*; do case "$(basename "$f")" in 015_*) ;; *) cp "$f" "$O/src/";; esac; done
RC14=$R/rtl/physical/a0_rc14_selected_2000/ot_qwen_w12_matvec_land32.sv
cp "$R/rtl/physical/a0_rc16_head_tailpub/ot_qwen_w12_matvec_land32.sv" "$O/src/015_ot_qwen_w12_matvec_land32_tailpub.sv"
python3 - "$RC14" "$O/ref_part.sv" <<'PY'
import sys
s=open(sys.argv[1]).read();i=s.index('module ot_qwen_w12_matvec_part #(');j=s.index('endmodule',i)+len('endmodule')
open(sys.argv[2],'w').write('`timescale 1ns/1ps\n'+s[i:j].replace('module ot_qwen_w12_matvec_part #(','module ref_w12_matvec_part #(',1)+'\n')
PY
cp "$B/native_head_rom_return_cut.sv" "$R/rtl/test/qwen_dv/head_tailpub/tb_head_tailpub_lockstep.sv" "$O/"
cp "$R/tools/qwen_layerbench/run_head_tailpub_gate.sh" "$O/run.sh"
cp "$R/tools/qwen_layerbench/head_tailpub_ffcount.ys" "$R/tools/qwen_layerbench/head_tailpub_ff_wrap.sv" "$O/"
cp -a "$B/contexts/tile0" "$B/contexts/tile639" "$O/contexts/"
cp "$RC14" "$O/src_rc14_part1.sv"
(cd "$O" && ls src/* > source.f && sha256sum src/* src_rc14_part1.sv ref_part.sv *.sv run.sh head_tailpub_ffcount.ys > SHA256SUMS)
echo "packet $O"
