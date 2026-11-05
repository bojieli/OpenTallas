"""KW-FIX-16 11-05: GRT resumed from 4_cts.odb follows MIN/MAX_ROUTING_LAYER (grt_layers.tcl, sourced by grt_pre.tcl)."""
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent


def test_grt_pre_sources_layer_sync_first():
    s = (HERE / "grt_pre.tcl").read_text()
    i = s.index("source [file join $gp_dir grt_layers.tcl]")
    assert i < s.index("source [file join $gp_dir vclk_corner.tcl]")        # before any hook that runs repair or GRT


def test_kit_generators_copy_layer_sync():
    for f in ("gen_phys.py", "core_flow.py"):
        assert '"grt_layers.tcl"' in (HERE / f).read_text(), f


def test_layer_sync_is_noop_when_equal_and_signal_only():
    s = (HERE / "grt_layers.tcl").read_text()
    assert "set_routing_layers -signal $lo-$hi" in s
    assert "-clock" not in re.sub(r"#.*", "", s)       # clock range untouched
    assert "no change" in s and "OT_GRT_LAYERS_SYNC" in s


ODB = os.environ.get("OT_TEST_4CTS_ODB", "")


@pytest.mark.skipif(not ODB or not shutil.which("docker"), reason="needs OT_TEST_4CTS_ODB + docker (orfs image)")
def test_layer_sync_on_real_odb(tmp_path):
    out = {}
    for hi in ("M5", "M6"):
        tcl = tmp_path / f"t_{hi}.tcl"
        tcl.write_text(f"read_db /odb/{Path(ODB).name}\nset b [ord::get_db_block]\n"
                       f"set ::env(MIN_ROUTING_LAYER) M2\nset ::env(MAX_ROUTING_LAYER) {hi}\n"
                       f"source /tools/grt_layers.tcl\nputs \"AFTER [$b getMaxRoutingLayer]\"\n")
        r = subprocess.run(["docker", "run", "--rm", "--memory", "8g", "-v", f"{Path(ODB).parent}:/odb:ro",
                            "-v", f"{HERE}:/tools:ro", "-v", f"{tmp_path}:/t:ro", "--entrypoint", "/bin/bash",
                            "openroad/orfs:asap7lock", "-c",
                            f"source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -no_init -exit /t/{tcl.name}"],
                           capture_output=True, text=True, timeout=600)
        out[hi] = int(re.search(r"AFTER (\d+)", r.stdout).group(1))
    assert out == {"M5": 5, "M6": 6}
