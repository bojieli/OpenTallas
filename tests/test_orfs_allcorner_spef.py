"""Run the finish annotation with a Tcl read_spef stub: every scene receives RC."""
import importlib.util
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("allcorner", ROOT / "tools/orfs_allcorner_spef.py")
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)


@pytest.mark.parametrize("corners,expected", [
    ("WC BC", ["-corner WC /results/6_final.spef", "-corner BC /results/6_final.spef"]),
    ("TC WC BC", ["-corner TC /results/6_final.spef", "-corner WC /results/6_final.spef",
                  "-corner BC /results/6_final.spef"]),
    ("WC", ["-corner WC /results/6_final.spef"]),
    ("", ["/results/6_final.spef"]),
    (None, ["/results/6_final.spef"]),
])
def test_finish_annotates_every_scene_before_metrics(corners, expected):
    # Model the scene-local read_spef behavior responsible for the actual u45 bug.
    script = "set ::env(RESULTS_DIR) /results\nproc read_spef {args} {puts $args}\n"
    if corners is not None:
        script += "set ::env(CORNERS) {" + corners + "}\n"
    script += helper.patch_final_outputs(helper.ORIGINAL + "\nputs METRICS\n")
    proc = subprocess.run(["tclsh"], input=script, text=True, capture_output=True, check=True)
    assert not proc.stderr
    assert proc.stdout.splitlines() == expected + ["METRICS"]


def test_changed_evaluator_fails_closed():
    with pytest.raises(ValueError):
        helper.patch_final_outputs("read_spef unknown.spef\n")
    with pytest.raises(ValueError):
        helper.patch_final_outputs((helper.ORIGINAL + "\n") * 2)
