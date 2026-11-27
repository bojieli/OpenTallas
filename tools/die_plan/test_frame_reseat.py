from copy import deepcopy
import shutil
import subprocess
from pathlib import Path

import pytest

import frame_reseat as FR


@pytest.fixture
def reviewed(monkeypatch):
    monkeypatch.setattr(FR, "BITS", 2)
    tn = sorted(FR.TYPES)[0]
    banks = [[[float(x), float(y)] for x in (2, 4, 6, 8)] for y in (1, 2, 3)]
    row = {
        "conn": "bus:frame_int_o0", "regs_um": [[2, y] for y in (1, 2, 3)],
        "bit_sites_um": banks, "bit_site_cell_um": [1, 0.27],
    }
    paths = []
    for bit in range(2):
        ends = [f"u_bound.u_u_lpl_5_w.foo[{bit}]$_DFF_P_", *(
            f"{FR.STATION}{i}/q[{bit}]$_DFF_P_" for i in range(3)
        ), f"{FR.BOUT}/q[{bit}]$_DFF_P_"]
        paths.extend([bit, hop, ends[hop], ends[hop + 1], 1] for hop in range(4))
    return tn, {
        "internal_stations": [row],
        "frame_data_reseat": {
            "version": 1,
            "station_sha256": FR.station_digest(banks, row["bit_site_cell_um"]),
            "paths": paths,
        },
    }


def test_default_is_inert(tmp_path):
    FR.install(tmp_path, "other", {})
    assert list(tmp_path.iterdir()) == []


def test_selected_kit_preserves_existing_hooks(tmp_path, reviewed):
    tn, t = reviewed
    for name in ("gp_guard.tcl", "face_release.tcl"):
        (tmp_path / name).write_text("# existing")
    config = tmp_path / "config.mk"
    config.write_text(
        "export PRE_RESIZE_TCL = /work/gp_guard.tcl\n"
        "export PRE_DETAIL_PLACE_TCL = /work/face_release.tcl\n"
    )
    FR.install(tmp_path, tn, t)
    assert config.read_text().count("PRE_RESIZE_TCL") == 1
    assert config.read_text().count("PRE_DETAIL_PLACE_TCL") == 1
    for phase, hook in [("pre", "gp_guard"), ("detail", "face_release")]:
        wrapper = (tmp_path / f"frame_data_reseat_{phase}.tcl").read_text()
        assert f"source /work/{hook}.tcl" == wrapper.splitlines()[-1]
    assert (tmp_path / "frame_data_reseat_data.tcl").read_text().count("$_DFF_P_") == 16


def test_scope_rejects_mutation_before_writing_kit(tmp_path, reviewed):
    tn, t = reviewed
    config = tmp_path / "config.mk"
    config.write_text("original\n")

    with pytest.raises(ValueError, match="unsupported FRAME"):
        FR.install(tmp_path, "other", t)
    case = deepcopy(t)
    case["internal_stations"][0]["bit_sites_um"][0][0][0] = 2.5
    with pytest.raises(ValueError, match="differ from the reviewed"):
        FR.install(tmp_path, tn, case)
    case = deepcopy(t)
    case["frame_data_reseat"]["paths"][3][3] = f"{FR.BOUT}/q[1]$_DFF_P_"
    with pytest.raises(ValueError, match="unexpected FRAME capture"):
        FR.install(tmp_path, tn, case)
    case = deepcopy(t)
    case["frame_data_reseat"]["paths"][3][2] = f"{FR.STATION}0/q[1]$_DFF_P_"
    with pytest.raises(ValueError, match="discontinuous FRAME"):
        FR.install(tmp_path, tn, case)
    case = deepcopy(t)
    case["frame_data_reseat"]["paths"][-1][0] = 2
    with pytest.raises(ValueError, match="invalid FRAME bit/hop"):
        FR.install(tmp_path, tn, case)
    assert config.read_text() == "original\n"
    assert len(list(tmp_path.iterdir())) == 1


def test_tcl_native_connectivity_and_site_fit():
    if not (tcl := shutil.which("tclsh")):
        pytest.skip("tclsh required")
    here = Path(__file__).parent
    subprocess.run(
        [tcl, here / "test_frame_data_reseat.tcl", here / "frame_data_reseat.tcl"],
        check=True,
    )
