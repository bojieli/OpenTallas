"""Exercise the actual route image checkpoint chooser against mixed flow stages."""
import re
import subprocess
from pathlib import Path


def test_route_images_prefer_final_then_grt_then_placement(tmp_path):
    script = Path(__file__).with_name("ref_route.sh").read_text()
    function = re.search(r"select_layout_odb\(\) \{.*?\n\}", script, re.S).group()
    base = tmp_path / "root with spaces" / "results/asap7/design/base"
    base.mkdir(parents=True)
    paths = [base / (stage + ".odb") for stage in ("6_final", "5_1_grt", "3_place")]
    for path in paths:
        path.write_text(path.stem)
    for expected in paths:
        result = subprocess.run(["bash", "-c", function + '\nselect_layout_odb "$1"', "chooser",
                                 str(tmp_path / "root with spaces")], capture_output=True, text=True, check=True)
        assert result.stdout.strip() == str(expected)
        expected.unlink()
    empty = subprocess.run(["bash", "-c", function + '\nselect_layout_odb "$1"', "chooser",
                            str(tmp_path / "root with spaces")], capture_output=True, text=True, check=True)
    assert empty.stdout == ""
