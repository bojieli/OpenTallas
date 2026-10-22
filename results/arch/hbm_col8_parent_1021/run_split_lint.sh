#!/bin/bash
set -euo pipefail
out=${1:?};mkdir -p "$out"
python3 - "$out" <<'PY'
import pathlib,re,shlex,sys
out=pathlib.Path(sys.argv[1]);s=pathlib.Path('rtl/hdc/v41x/ot_hbm_idx_col8_sram_face.sv').read_text();start=s.index('module ot_hidx_col8_sram_face_col');end=s.index(');',start)+2;(out/'column_ports_stub.sv').write_text(s[start:end]+'\nendmodule\n')
s=pathlib.Path('rtl/test/hbm_idx_static/run_chunk_col8_rejoined_equiv.sh').read_text();a=shlex.split(re.search(r'src=\((.*?)\)\ndef=',s,re.S)[1]);a=[p for p in a if not any(k in p for k in ['ot_hbm_idx_chunk_col8_rejoined','ot_hbm_idx_col8_sram_face','ot_hbm_idx_col8_sram_landed','ot_hbm_idx_col8_landed','ot_hbm_idx_score_col8','tb_idx_chunk_col8_rejoined'])]
a += ['rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_quarter_col8_split.sv','rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_quarter_col8_control.sv','rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_leaf_col8_control.sv','rtl/hbm_accel/index/quad_1017/ot_hbm_idx_score_fault_static.sv','rtl/hdc/v41x/ot_hidx_meta_sram146.sv','physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2/ot_sram_1r1w_256x256_m2_r2c2.v',str(out/'column_ports_stub.sv')]
(out/'sources.list').write_text('\n'.join(dict.fromkeys(a))+'\n')
PY
mapfile -t src < "$out/sources.list"
"$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator" --lint-only --timing -GTP=192 -Wno-fatal --top-module ot_hbm_idx_score_quarter_col8_split "${src[@]}" > "$out/lint.log" 2>&1 || { tail -35 "$out/lint.log";exit 1; }
echo COL8_SPLIT_TP192_PORT_ELABORATION_PASS
