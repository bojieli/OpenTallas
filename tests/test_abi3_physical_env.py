"""Environment assertions for the ABI 3.0 physical characterisation flow.

These tests do not run synthesis, timing or place-and-route.  They assert that
the exact pinned tools and PDK files ``tools/run_abi3_physical.py`` depends on
are present, are the pinned versions, and match the identities recorded in the
``configs/pdk/*_lock.json`` files.

Tests that need a tool or PDK root that is not installed are skipped rather
than failed, so the suite stays useful on a machine that only has one view.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import run_abi3_physical as flow  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_lock(name: str) -> dict:
    path = ROOT / "configs/pdk" / name
    if not path.is_file():
        pytest.skip(f"lock file not present: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Pinned tools
# ---------------------------------------------------------------------------


def test_pinned_yosys_is_0_68():
    assert flow.YOSYS.is_file(), f"pinned Yosys missing at {flow.YOSYS}"
    out = subprocess.run(
        [str(flow.YOSYS), "-V"], capture_output=True, text=True, timeout=120
    ).stdout
    assert "Yosys 0.68" in out, f"unexpected Yosys version: {out!r}"
    # The system Yosys (0.9) must not be what the flow picks up.
    assert "0.9" not in out.split()[1]


def test_pinned_yosys_abc_present():
    assert flow.YOSYS_ABC.is_file(), f"pinned yosys-abc missing at {flow.YOSYS_ABC}"


def test_pinned_opensta_is_3_1_0():
    assert flow.STA.is_file(), f"pinned OpenSTA missing at {flow.STA}"
    result = subprocess.run(
        [str(flow.STA), "-version"], capture_output=True, text=True, timeout=120
    )
    text = (result.stdout or "") + (result.stderr or "")
    assert "3.1.0" in text, f"unexpected OpenSTA version: {text!r}"


def test_flow_uses_absolute_pinned_tool_paths():
    """The flow must never resolve tools from PATH; system versions are too old."""
    for tool in (flow.YOSYS, flow.YOSYS_ABC, flow.STA):
        assert tool.is_absolute(), f"{tool} is not an absolute path"


# ---------------------------------------------------------------------------
# SKY130 HD view (mature implementation view)
# ---------------------------------------------------------------------------


def test_sky130_full_root_has_high_density_cells():
    if not flow.SKY130_HD.is_dir():
        pytest.skip(f"full SKY130 root not installed at {flow.SKY130_HD}")
    for sub in ("lib", "lef", "techlef", "gds", "verilog"):
        assert (flow.SKY130_HD / sub).is_dir(), f"sky130_fd_sc_hd/{sub} missing"


def test_sky130_view_liberty_files_exist_and_match_lock():
    lock = load_lock("sky130_full_physical_lock.json")
    key_files = lock["pdk"]["key_files"]
    root = Path(lock["pdk"]["root"]) / "sky130A"
    if not root.exists():
        pytest.skip(f"SKY130 root not installed at {root}")
    for relative, expected in sorted(key_files.items()):
        path = root / relative
        assert path.is_file(), f"locked SKY130 file missing: {path}"
        assert path.stat().st_size == expected["size_bytes"], f"size drift: {path}"
        assert sha256_file(path) == expected["sha256"], f"sha256 drift: {path}"


def test_sky130_all_corners_resolvable():
    view = flow.VIEWS["sky130hd"]
    if not flow.SKY130_HD.is_dir():
        pytest.skip("full SKY130 root not installed")
    for corner_name, corner in sorted(view["corners"].items()):
        for liberty in corner["liberty"]:
            assert Path(liberty).is_file(), f"{corner_name}: missing {liberty}"


def test_sky130_liberty_time_unit_matches_view_declaration():
    """A unit mismatch would silently scale every reported Fmax."""
    view = flow.VIEWS["sky130hd"]
    liberty = Path(view["corners"][view["default_corner"]]["liberty"][0])
    if not liberty.is_file():
        pytest.skip("SKY130 liberty not installed")
    head = liberty.read_text(errors="ignore")[:20000]
    match = re.search(r'time_unit\s*:\s*"(\S+)"', head)
    assert match, "no time_unit in SKY130 liberty"
    assert match.group(1) == "1ns"
    assert view["time_unit_ns"] == 1.0


def test_existing_sky130_device_lock_is_untouched():
    """The full-PDK install must not have disturbed the SPICE evidence root."""
    lock = load_lock("sky130_physical_lock.json")
    assert lock["pdk"]["included_libraries"] == ["sky130_fd_pr"], (
        "the pre-existing sky130 lock must still describe the device-model-only "
        "root; the ABI 3.0 flow installs a separate root"
    )
    device_root = Path.home() / ".local/opentallas-pdk/sky130A"
    if not device_root.exists():
        pytest.skip("device-model SKY130 root not installed")
    libs = sorted(p.name for p in (device_root / "libs.ref").iterdir())
    assert libs == ["sky130_fd_pr"], f"device-model root gained libraries: {libs}"


# ---------------------------------------------------------------------------
# ASAP7 view (predictive view)
# ---------------------------------------------------------------------------


def test_asap7_local_liberty_matches_lock():
    lock = load_lock("asap7_local_liberty_lock.json")
    root = Path(lock["root"])
    if not root.is_dir():
        pytest.skip(f"ASAP7 local liberty root not installed at {root}")
    for relative, expected in sorted(lock["files"].items()):
        path = root / relative
        assert path.is_file(), f"locked ASAP7 liberty missing: {path}"
        assert path.stat().st_size == expected["size_bytes"], f"size drift: {path}"
        assert sha256_file(path) == expected["sha256"], f"sha256 drift: {path}"


def test_asap7_container_sources_match_archived_asap7_lock():
    """The extracted liberty must trace back to the archived ASAP7 identities."""
    local = load_lock("asap7_local_liberty_lock.json")
    archived = load_lock("asap7_physical_lock.json")
    container_files = archived["toolchain"]["asap7"]["files"]
    for relative, entry in sorted(local["files"].items()):
        source = entry["container_source_path"]
        key = source.split("/platforms/asap7/", 1)[1]
        assert key in container_files, f"{key} absent from archived ASAP7 lock"
        assert container_files[key] == entry["container_source_sha256"], (
            f"{key} sha256 disagrees with the archived ASAP7 lock"
        )


def test_asap7_view_liberty_files_exist():
    view = flow.VIEWS["asap7"]
    if not flow.ASAP7_NLDM.is_dir():
        pytest.skip("ASAP7 local liberty root not installed")
    for corner_name, corner in sorted(view["corners"].items()):
        for liberty in corner["liberty"]:
            assert Path(liberty).is_file(), f"{corner_name}: missing {liberty}"


def test_asap7_liberty_time_unit_is_picoseconds():
    """ASAP7 liberty is in ps; the view must declare 0.001 ns or Fmax is 1000x off."""
    view = flow.VIEWS["asap7"]
    liberty = Path(view["corners"]["TT"]["liberty"][-1])
    if not liberty.is_file():
        pytest.skip("ASAP7 liberty not installed")
    head = liberty.read_text(errors="ignore")[:20000]
    match = re.search(r'time_unit\s*:\s*"(\S+)"', head)
    assert match, "no time_unit in ASAP7 liberty"
    assert match.group(1) == "1ps"
    assert view["time_unit_ns"] == 0.001


# ---------------------------------------------------------------------------
# Place-and-route container
# ---------------------------------------------------------------------------


def docker_available() -> bool:
    if shutil.which("docker") is None:
        return False
    return subprocess.run(
        ["docker", "info"], capture_output=True, timeout=120
    ).returncode == 0


def test_orfs_image_present_and_is_the_pinned_image():
    if not docker_available():
        pytest.skip("docker not available")
    result = subprocess.run(
        ["docker", "image", "inspect", flow.ORFS_IMAGE, "--format", "{{.Id}}"],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if result.returncode != 0:
        pytest.skip(f"ORFS image {flow.ORFS_IMAGE} not pulled")
    image_id = result.stdout.strip()
    assert image_id == flow.ORFS_EXPECTED_IMAGE_ID, (
        f"ORFS image id {image_id} differs from the pinned id "
        f"{flow.ORFS_EXPECTED_IMAGE_ID}; place-and-route results would not be "
        "comparable with results/asap7_physical/"
    )


def test_orfs_image_id_matches_archived_asap7_lock():
    archived = load_lock("asap7_physical_lock.json")
    assert (
        archived["toolchain"]["container"]["image_id"] == flow.ORFS_EXPECTED_IMAGE_ID
    ), "the pinned ORFS image id must equal the archived ASAP7 campaign's image id"


def test_orfs_platforms_available_for_both_views():
    if not docker_available():
        pytest.skip("docker not available")
    probe = subprocess.run(
        [
            "docker", "run", "--rm", flow.ORFS_IMAGE, "bash", "-lc",
            "ls /OpenROAD-flow-scripts/flow/platforms/",
        ],
        capture_output=True,
        text=True,
        timeout=600,
    )
    if probe.returncode != 0:
        pytest.skip("ORFS image not runnable")
    platforms = set(probe.stdout.split())
    for view_name, view in sorted(flow.VIEWS.items()):
        if not view.get("pnr"):
            continue
        assert view["pnr"]["platform"] in platforms, (
            f"view {view_name} needs ORFS platform {view['pnr']['platform']}"
        )


# ---------------------------------------------------------------------------
# Flow self-consistency
# ---------------------------------------------------------------------------


def test_every_view_declares_a_lock_file_that_exists():
    for view_name, view in sorted(flow.VIEWS.items()):
        lock = ROOT / view["pdk_lock"]
        assert lock.is_file(), f"view {view_name} references missing lock {lock}"


def test_every_view_default_corner_is_defined():
    for view_name, view in sorted(flow.VIEWS.items()):
        assert view["default_corner"] in view["corners"], (
            f"view {view_name} default corner {view['default_corner']} undefined"
        )


def test_every_registered_block_source_exists():
    for block_name, block in sorted(flow.BLOCKS.items()):
        for source in block["sources"]:
            assert (ROOT / source).is_file(), (
                f"block {block_name} references missing RTL {source}"
            )


def test_registered_block_tops_are_declared_in_their_sources():
    for block_name, block in sorted(flow.BLOCKS.items()):
        declared = False
        for source in block["sources"]:
            text = (ROOT / source).read_text(encoding="utf-8", errors="ignore")
            if re.search(rf"^module\s+{re.escape(block['top'])}\b", text, re.M):
                declared = True
                break
        assert declared, (
            f"block {block_name} top {block['top']} is not declared in its sources"
        )


def test_two_technology_views_are_separated_by_node():
    """The programme requires a mature view and a predictive view, not two of one."""
    mature = {n for n, v in flow.VIEWS.items() if not v["predictive"]}
    predictive = {n for n, v in flow.VIEWS.items() if v["predictive"]}
    assert mature, "no mature implementation view registered"
    assert predictive, "no predictive view registered"
    nodes = {v["node_nm"] for v in flow.VIEWS.values()}
    assert len(nodes) == len(flow.VIEWS), "views must not share a process node"
