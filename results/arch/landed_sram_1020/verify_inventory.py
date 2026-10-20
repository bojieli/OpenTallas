"""Recompute the source inventory, cost and centre-distance model; no EDA/build."""
from pathlib import Path
import hashlib
import json
import math

root = Path(__file__).resolve().parent
inventory = json.loads((root / "inventory.json").read_text())
area = 553.589568
for name, expected in inventory.items():
    record_bytes = (root / (name + "_record.json")).read_bytes()
    spec_bytes = (root / (name + "_spec.json")).read_bytes()
    assert hashlib.sha256(record_bytes).hexdigest() == expected["record_sha256"]
    assert hashlib.sha256(spec_bytes).hexdigest() == expected["spec_sha256"]
    record, spec = json.loads(record_bytes), json.loads(spec_bytes)
    landings = record["landings"]
    writers = {str(x.get("ring_of", x["name"])): x for x in landings}
    assert len(landings) == expected["readers"]
    assert len(writers) == expected["writers"]
    assert sum(x["width"] for x in landings) == expected["reader_width_sum"]
    assert sum(x["width"] for x in writers.values()) == expected["writer_width_sum"]
    full = sum(math.ceil(x["width"] / 64) for x in landings)
    large = [x for x in landings if x["width"] * record["D"] > 2048]
    required = sum(math.ceil(x["width"] / 64) for x in large)
    assert full == expected["full_reader_copy_macros32x64"]
    assert required == expected["sram_required_macros32x64"]
    assert math.isclose(area * required, expected["sram_required_macro_area_um2"])
    centres = {x["name"]: x.get("centre") for x in spec["regions"]}
    by_name = {x["name"]: x for x in landings}
    for pair in expected["pairs"]:
        crossing = by_name[pair["name"]]
        src, dst = centres[crossing["src_region"]], centres[crossing["dst_region"]]
        distance = sum(abs(a - b) for a, b in zip(src, dst))
        assert math.isclose(distance, pair["manhattan_um"])
    print(name, "readers", len(landings), "writers", len(writers),
          "required_macros", required, "macro_area_um2", area * required,
          "centre_pairs_over810", sum(x["manhattan_um"] > 810 for x in expected["pairs"]))
print("SOURCE MODEL VERIFIED; no phase, physical, timing, or RTL qualification")
