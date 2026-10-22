"""Stage the exact selected TOPK component readset without changing canonical RTL."""
from pathlib import Path
import argparse,hashlib,json,shutil
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--repo',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
p.add_argument('--inputs',type=Path,required=True);p.add_argument('--layouts',type=Path,required=True)
a=p.parse_args();repo=a.repo.resolve();out=a.out.resolve()
if out==repo or repo in out.parents or out in repo.parents:
 raise ValueError('Staging source and destination must be disjoint directories')
if out.exists():raise ValueError('Use a new staging directory; existing build objects are preserved')
packet=repo/'results/token_pass/hbm_su_gather_lower_2000/topk_native_commit'
hashes=json.loads((packet/'source.sha256.json').read_text());selected=json.loads((packet/'selected_source_map.json').read_text())
# Materialize only after every canonical or selected artifact has been checked.
chosen={}
for name,expected in hashes.items():
 source=packet/selected[name]['fixture'] if name in selected else repo/name
 if hashlib.sha256(source.read_bytes()).hexdigest()!=expected:
  raise ValueError('Source differs from measured component readset: '+name)
 chosen[name]=source
out.mkdir(parents=True)
# Python support is not RTL: the measured fixture generator remains hash checked.
shutil.copytree(repo/'tools',out/'tools',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
for name,source in chosen.items():
 dest=out/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,dest)
# Exact source file list avoids rediscovering unrelated canonical RTL variants.
shutil.copy2(packet/'files.f',out/'topk_pinned_files.f')
shutil.copytree(a.inputs,out/'inputs');shutil.copy2(a.layouts,out/'gsc_layouts.json')
(out/'staging_manifest.json').write_text(json.dumps(dict(scope='Selected d76 component only',source_commit='d76bf51b4',selected_overrides=selected,measured_readset=hashes),indent=2)+'\n')
(out/'reproduce.sh').write_text("""#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
OUT=$(realpath -m "${1:-out_reproduction}")
mkdir -p "$OUT"
python3 tools/hbm_layer_vehicle/topk_hub_fixture_2000.py inputs gsc_layouts.json "$OUT/fixtures"
VL=${VERILATOR:-$HOME/.local/opentallas-tools/verilator-5.050/bin/verilator}
"$VL" --binary --timing -j 2 -Wno-fatal --top-module tb_topk_native_commit -Mdir "$OUT/obj" -f topk_pinned_files.f rtl/test/hbm_topk_native_commit_2000/tb_topk_native_commit.sv > "$OUT/build.log" 2>&1
for mut in 0 1 2 3; do
 set +e
 "$OUT/obj/Vtb_topk_native_commit" "+DIR=$OUT/fixtures" "+MUT=$mut" > "$OUT/run$mut.log" 2>&1
 status=$?
 set -e
 if [[ $mut == 0 ]]; then test "$status" = 0; grep -q 'TOPK_NATIVE_COMMIT PASS' "$OUT/run$mut.log"
 else test "$status" != 0; grep -q 'TOPK_NATIVE_COMMIT FAIL' "$OUT/run$mut.log"; fi
done
""")
(out/'reproduce.sh').chmod(0o755)
print(out)
