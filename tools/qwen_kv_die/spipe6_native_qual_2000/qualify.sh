#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
fixture="$root/tools/qwen_kv_die/spipe6_native_qual_2000"
out=${1:?need output directory}
mkdir -p "$out"
out=$(cd "$out" && pwd)
for f in generate_fixture.py kv_ingest_ref.py seed_desc.mem seed_pay.mem seed_native.mem seed_fixture.json ot_hdc_ingest_fp8q.sv ot_sram_1r1w_32x128_m1.v qkd_host_native_engine.sv check.py tb_stream.sv adapt.py tb_truth.sv map_inputs.json; do cp "$fixture/$f" "$out/$f"; done
cp "$root/rtl/qwen_sys/host_spipe6_native_1021/qkd_host_native_engine_sp6_n32.sv" "$out/native_sp6.v"
cd "$out"
python3 - <<'PY'
from pathlib import Path
import hashlib,json
b=Path('native_sp6.v').read_bytes();old=b.replace(b'qkd_host_native_engine_sp6_n32',b'qkd_host_native_engine_n32');assert hashlib.sha256(old).hexdigest()=='d71e1d45996f9a438e0526973ffb4e2951fd491a0791864b8122e1c446092103'
assert hashlib.sha256(Path('qkd_host_native_engine.sv').read_bytes()).hexdigest()=='999bf9c27c1529cff7a48ccbd032a82be1d2e6088a2a6ad14b983eb13cc76529'
Path('actual_inputs.json').write_text(json.dumps({p.name:hashlib.sha256(p.read_bytes()).hexdigest()for p in Path('.').glob('*')if p.is_file()},indent=2)+'\n')
PY
image='openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29'
docker run --rm --user "$(id -u):$(id -g)" -v "$out:/work" -w /work --entrypoint bash "$image" -lc '
 set -euo pipefail
 mkdir -p libs
 for stem in AO INVBUF OA SEQ SIMPLE; do
  case $stem in AO|OA|SIMPLE) stamp=211120;;INVBUF) stamp=220122;;SEQ) stamp=220123;;esac
  src="/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_${stem}_RVT_TT_nldm_${stamp}.lib"
  # Preserve the frozen map input basename; the verified OA body is identical.
  target="libs/asap7sc7p5t_${stem}_RVT_TT_nldm_${stamp}.lib"
  if [ "$stem" = OA ]; then target=libs/asap7sc7p5t_OA_RVT_TT_nldm_220122.lib; fi
  if [ -f "$src" ]; then cp "$src" "$target"; else gzip -dc "$src.gz" > "$target"; fi
 done
 L="";for f in libs/*.lib;do L="$L $f";done
 yosys -Q -T -p "read_liberty -ignore_miss_func $L; write_verilog -noattr models.original.v"
' >models.log 2>&1
python3 - <<'PY'
from pathlib import Path
import hashlib,json
expected=json.loads(Path('map_inputs.json').read_text())['files']
for p in Path('libs').glob('*.lib'):assert hashlib.sha256(p.read_bytes()).hexdigest()==expected[str(p)],p
PY
python3 adapt.py
export PATH="$HOME/.local/opentallas-tools/verilator-5.050/bin:$PATH"
verilator --binary --timing -j 2 -Wno-fatal --top-module tb_truth --Mdir obj_truth adapter.v tb_truth.sv >truth.build.log 2>&1
./obj_truth/Vtb_truth >truth.log 2>&1
python3 generate_fixture.py >fixture.log
read -r nd np < <(python3 -c 'import json;j=json.load(open("fixture.json"));print(j["descriptors"],j["beats"])')
verilator --binary --timing -O2 -j 8 --x-initial unique --x-assign unique -DOT_MEM_NO_INIT -Wno-fatal -Wno-lint -Wno-style -Wno-WIDTH -Wno-MULTIDRIVEN --top-module tb_stream -GND="$nd" -GNP="$np" --Mdir obj tb_stream.sv qkd_host_native_engine.sv native_sp6.v models.v ot_hdc_ingest_fp8q.sv ot_sram_1r1w_32x128_m1.v >build.log 2>&1
for seed in 31 997 3187;do
 ./obj/Vtb_stream +MUT=0 +verilator+rand+reset+2 +verilator+seed+"$seed" >"seed${seed}.log" 2>&1
 python3 check.py >"seed${seed}.check.log"
 cp result.json "seed${seed}.json"
done
printf '%s\n' SPIPE6_MAPPED_NATIVE_BOUNDED_COLD_PASS
