"""Fresh GRT scenes must retain the generated kit's PG legality constraints."""
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TCLSH = shutil.which("tclsh")


def _run(tmp_path, config, body, missing=()):
    kit = tmp_path / "kit"
    kit.mkdir()
    (kit / "config.mk").write_text(config)
    helpers = {
        "pg_cell_keepout.tcl": 'proc ot_pgcko_add {} {lappend ::calls keepout_add}\nproc ot_pgcko_remove {} {lappend ::calls keepout_remove}\n',
        "pg_track_truth.tcl": 'proc ot_pgtt_add {} {lappend ::calls [list truth_add $::env(OT_PG_TRACK_TRUTH_MODE) $::env(OT_PG_TRACK_TRUTH_REGION_LAYERS)]}\nproc ot_pgtt_remove {} {lappend ::calls truth_remove}\n',
        "pg_pair_cap.tcl": 'proc ot_pgcap_add {} {lappend ::calls [list cap_add $::env(OT_PGCAP_ADJ)]}\n',
    }
    for name, text in helpers.items():
        if name not in missing:
            (kit / name).write_text(text)
    driver = tmp_path / "driver.tcl"
    driver.write_text(
        f'set calls {{}}\nsource {{{HERE / "grt_pg_replay.tcl"}}}\nset kit {{{kit}}}\n' + body
    )
    return subprocess.run([TCLSH, str(driver)], capture_output=True, text=True)


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_reloaded_scene_replays_all_opted_constraints_once_and_cleans_before_write(tmp_path):
    config = """export OT_PG_CELL_KEEPOUT = 1
export OT_PG_TRACK_TRUTH = 1
export OT_PG_TRACK_TRUTH_MODE = region
export OT_PG_TRACK_TRUTH_REGION_LAYERS = M5 M6 M7
export OT_PGCAP = 1
export OT_PGCAP_ADJ = 0.75
"""
    out = _run(tmp_path, config, """
ot_grt_pg_replay_begin $kit
ot_grt_pg_replay_begin $kit
lappend calls incremental_route
ot_grt_pg_replay_end
ot_grt_pg_replay_end
lappend calls write_db
puts "CALLS $calls"
""")
    assert out.returncode == 0, out.stderr
    assert "CALLS keepout_add {truth_add region {M5 M6 M7}} {cap_add 0.75} incremental_route truth_remove keepout_remove write_db" in out.stdout


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_generated_off_overrides_ambient_on_and_does_not_add_constraints(tmp_path):
    out = _run(tmp_path, "export OT_PGCAP = 0\n", """
set ::env(OT_PGCAP) 1
ot_grt_pg_replay_begin $kit
ot_grt_pg_replay_end
puts "CALLS $calls"
""")
    assert out.returncode == 0, out.stderr
    assert "CALLS \n" in out.stdout


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_missing_opted_helper_refuses_instead_of_silently_unprotected_route(tmp_path):
    out = _run(tmp_path, "export OT_PGCAP = 1\n", "ot_grt_pg_replay_begin $kit\n", missing=("pg_pair_cap.tcl",))
    assert out.returncode != 0
    assert "OT_PGCAP=1 but helper missing" in out.stderr


@pytest.mark.skipif(not TCLSH, reason="tclsh")
def test_nonliteral_generated_capacity_value_refuses(tmp_path):
    out = _run(tmp_path, "export OT_PGCAP_ADJ = $(CAP_ADJ)\n", "ot_grt_pg_replay_begin $kit\n")
    assert out.returncode != 0
    assert "nonliteral generated value" in out.stderr


def test_tt_repair_restores_before_incremental_route_and_removes_before_checkpoint():
    text = (HERE / "tt_setup_repair.tcl").read_text()
    assert text.index("ot_grt_pg_replay_begin") < text.index("global_route -start_incremental")
    assert text.index("global_route -end_incremental") < text.index("ot_grt_pg_replay_end") < text.index("write_db $out")
