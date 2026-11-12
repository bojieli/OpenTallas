"""raw_patch.py PLAN KIT TYPE : apply the HEAD kit_rtl raw-reset patches (head_wave_kit_rtl.export: alias_patch +
private_patch) to a gen.py phys kit wrapper, so the rst_start_raw_N ports the plan declares exist (port_bind)."""
import json, sys
from pathlib import Path
ROOT = Path("/srv/opentallas-scratch2/claude/wt/head-95-rfsr")
sys.path[:0] = [str(ROOT / "tools/die_plan"), str(ROOT / "tools/s81_head")]
from head_start_raw_private import patch_rtl as private_patch
from head_start_reset_aliases import patch_rtl as alias_patch
plan, kit, typ = json.load(open(sys.argv[1])), Path(sys.argv[2]), sys.argv[3]
t = plan["partition_types"][typ]
w = kit / "_rtl" / (t["module"] + ".sv"); k = kit / typ / "rtl" / w.name
text = alias_patch(w.read_text(), t.get("reset_start_raw_exports", []))
text, private = private_patch(text, t)
for p in (w, k): p.write_text(text)
print("patched", w.name, "raw ports", text.count("output wire rst_start_raw_"), "private", bool(private))
