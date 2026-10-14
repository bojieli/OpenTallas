#!/usr/bin/env bash
# Run under ot-run in an isolated frozen staging directory. This script does
# not compile RTL, supply expected intermediates, or reset between segments.
set -euo pipefail
core_obj=${1:?actual fullshape archive directory}
image=${2:?actual eight-rank image root}
program=${3:?actual fused eight-rank program root}
oracle=${4:?production two-level oracle root}
collective_runtime=${5:?actual collective runtime.py}
collective_exe=${6:?actual collective RTL executable}
output=${7:?fresh output directory}
catalog=${8:-}
fields=${9:?independently resolved SU field catalog}
front=/srv/opentallas-scratch/codex/native-services-frontend-1014/library-v1/obj
sector=/srv/opentallas-scratch/codex/native-services-frontend-1014/sector-library-v1/obj
pc=/srv/opentallas-scratch/codex/qwen-native-hbm-pc-provider-1014/library_v2/obj
vroot=/home/ubuntu/.local/opentallas-tools/verilator-5.050/share/verilator
[[ ! -e "$output" ]]
mkdir -p "$output"
for input_path in src/* kernel/*; do if [[ -f "$input_path" ]]; then sha256sum "$input_path"; fi; done > "$output/source_inputs.sha256"
sha256sum "$core_obj/Vot_hdc_core_vector_weight_native_candidate__ALL.a" \
 "$front/Vot_qwen_tp8_native_services_frontend__ALL.a" "$sector/Vot_qwen_tp8_kv_sector_adapter__ALL.a" \
 "$pc/Vqwen_native_hbm_pc_provider__ALL.a" "$collective_runtime" "$collective_exe" >> "$output/source_inputs.sha256"
python3 - "$image" "$program" "$oracle" "$output" <<'PY'
import hashlib,json,sys
from pathlib import Path
image,program,oracle,out=map(Path,sys.argv[1:])
report=json.loads((oracle/'oracle.json').read_text())
assert report['production_tp8_collective_compatible']
pins={}
for rank in range(8):
 manifest=json.loads((image/f'die{rank}'/'layer0_rom.json').read_text())
 assert manifest['image_sha256']==report['ranks'][str(rank)]['image_sha256']
 for path in ((image/f'die{rank}').glob('*')):
  if path.is_file():
   digest=hashlib.sha256(path.read_bytes()).hexdigest()
   pins[str(path)]=digest
   if path.name in manifest['image_sha256']:assert digest==manifest['image_sha256'][path.name]
 p=program/f'die{rank}'/'program.hex'
 digest=hashlib.sha256(p.read_bytes()).hexdigest()
 assert digest=='cc5bc8fc17d4068ac9a49e8bf79f34e74350d56d114dd7fe5cde433d2ac82796'
 assert digest==report['ranks'][str(rank)]['lowered_program_sha256']
 pins[str(p)]=digest
 for kind in ('K','V'):
  p=oracle/f'die{rank}'/f'prior_{kind}_fp8.bin'
  digest=hashlib.sha256(p.read_bytes()).hexdigest()
  assert digest==report['ranks'][str(rank)][f'prior_{kind}_sha256']
  pins[str(p)]=digest
pins[str(oracle/'oracle.json')]=hashlib.sha256((oracle/'oracle.json').read_bytes()).hexdigest()
(out/'payload_inputs.json').write_text(json.dumps(pins,indent=2)+'\n')
PY
c++ -std=c++17 -O1 -pthread -I"$core_obj" -I"$front" -I"$sector" -I"$pc" -Ikernel -Isrc \
 -I"$vroot/include" -I"$vroot/include/vltstd" src/full_layer.cpp \
 "$core_obj/Vot_hdc_core_vector_weight_native_candidate__ALL.a" \
 "$front/Vot_qwen_tp8_native_services_frontend__ALL.a" "$sector/Vot_qwen_tp8_kv_sector_adapter__ALL.a" \
 "$pc/Vqwen_native_hbm_pc_provider__ALL.a" kernel/Vot_qwen_tp8_attention_service__ALL.a \
 kernel/sim_hdc_v41x_fastfp_dpi.o kernel/sim_nhb_fp_lat_dpi.o \
 "$vroot/include/verilated.cpp" "$vroot/include/verilated_threads.cpp" "$vroot/include/verilated_dpi.cpp" \
 -o "$output/full_layer" > "$output/link.log" 2>&1
set +e
"$output/full_layer" "$image" "$program" "$oracle" "$collective_runtime" "$collective_exe" "$output" > "$output/run.log" 2>&1
run_status=$?
set -e
printf '%s\n' "$run_status" > "$output/executable_status.txt"
[[ "$run_status" == 0 ]]
catalog_args=()
if [[ -n "$catalog" ]]; then catalog_args=(--catalog "$catalog"); fi
python3 src/verify_full_layer.py --oracle "$oracle" --actual "$output" --fields "$fields" "${catalog_args[@]}" > "$output/effects.log"
cat "$output/run.log" "$output/effects.log"
