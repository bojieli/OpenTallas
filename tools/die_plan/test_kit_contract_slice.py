"""KV-KITS-7 (RM37 hold): partition kit pins_canonical on the --master-slice path (12.7c): the slice-placed pins are
the plan pins + slice; freeze.json / plan_pins.json stay the die-plan pin set."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_contract as KC        # noqa: E402
import test_master_slice as TMS  # noqa: E402


def test_slice_kit_pins_canonical(tmp_path):
    sd = TMS.write_slices(tmp_path / "slices")
    assert TMS._gen(tmp_path, tmp_path / "k", "--master-slice", str(sd)).returncode == 0
    assert TMS._gen(tmp_path, tmp_path / "b").returncode == 0
    kd, base = tmp_path / "k/src", tmp_path / "b/src"
    # the recorded plan pin set is the die plan's, with or without a slice
    assert (kd / "freeze.json").read_bytes() == (base / "freeze.json").read_bytes()
    assert (kd / "plan_pins.json").read_bytes() == (base / "plan_pins.json").read_bytes()
    rewritten = json.loads((kd / "master_slice_io.json").read_text())["rewritten"]
    assert rewritten, "fixture slice must move at least one pin"
    for d in (kd, base):
        errors, info = KC.pins_canonical(d)
        assert not errors, errors
    assert KC.pins_canonical(kd)[1]["slice"] is True
    # a slice pin put back at its pre-slice position (not where the slice says) fails
    name = sorted(rewritten)[0]
    io = (kd / "io.tcl").read_text().splitlines()
    orig = {l.split()[2].strip("{}"): l for l in (base / "io.tcl").read_text().splitlines() if l.strip().startswith("place_pin")}
    io = [orig[name] if l.strip().startswith("place_pin") and l.split()[2].strip("{}") == name else l for l in io]
    (kd / "io.tcl").write_text("\n".join(io) + "\n")
    errors, _ = KC.pins_canonical(kd)
    assert errors and "master slice" in errors[0]
