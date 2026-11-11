#!/usr/bin/env python3
"""HEAD-94 11-11 post-cut: hd_mesh re-form step 1 (clock density taps from the ds8d register bins, DIE-LAYOUT-KVHEAD
l48hp1_mesh_sinkbins) on the MERGED cut plan.  usage: mesh_event.py REPO OUT
 REPO/physical/.../l48hp1_head_cut1111/source_plan_cut.json.gz -> hd_mesh.clock.sink_bins_file = plan_of_record/sink_bins/hd_mesh.json
 -> mesh_resel.py (reset exports + stage/local-reset raw refs re-selected on the re-solved hd_mesh reset tree).
OUT/source_plan.json = result; OUT/pd = sidecar dir (l48hp1 + H2 pins) the tree solver needs."""
import gzip, hashlib, json, shutil, subprocess, sys
from pathlib import Path
R = Path(sys.argv[1]).resolve(); OUT = Path(sys.argv[2]).resolve(); OUT.mkdir(parents=True, exist_ok=True)
POR = R / "physical/die_plan/s81_head/plan_of_record"
raw = gzip.open(POR / "l48hp1_head_cut1111/source_plan_cut.json.gz").read()
assert hashlib.sha256(raw).hexdigest() == "a09b33bc23b216ce601a188364239a90c6f251adb86c06e59131a74d910493a5", "cut plan differs"
pd = OUT / "pd"
if pd.exists(): shutil.rmtree(pd)
shutil.copytree(POR / "l48hp1", pd)
shutil.copy(POR / "l48hp1_h2/ot_s81hd_he_epc_pins.json", pd / "core_pins/ot_s81hd_he_epc_pins.json")
(pd / "base_plan.json").write_bytes(raw)
P = json.loads(raw)
clk = P["partition_types"]["hd_mesh"]["clock"]
assert "sink_bins_file" not in clk
clk["sink_bins_file"] = "physical/die_plan/s81_head/plan_of_record/sink_bins/hd_mesh.json"
(pd / "mesh_plan.json").write_text(json.dumps(P, indent=1))
subprocess.run([sys.executable, "-I", str(POR / "l48hp1_mesh_sinkbins/mesh_resel.py"), str(pd / "base_plan.json"), str(pd / "mesh_plan.json"), str(R)], check=True)
# the larger tap set deepens the hd_mesh reset tree by one level (consumers of landing_local_resets now sit at depth 5): re-select every
# local-reset raw to depth(consumer)-1 (gen reports the required depth); iterate until the bootstrap GEN passes
import gzip as _gz
(pd / "source_sidecar.json").write_bytes(_gz.open(POR / "l48hp1/source_sidecar.json.gz").read())
subprocess.run([sys.executable, "-I", str(Path(__file__).with_name("fix_local_depth.py")), str(R), str(pd / "mesh_plan.json"), str(pd / "source_sidecar.json")], check=True)
text = (pd / "mesh_plan.json").read_text() + "\n"
(OUT / "source_plan.json").write_text(text)
print("mesh event plan sha256", hashlib.sha256(text.encode()).hexdigest())
