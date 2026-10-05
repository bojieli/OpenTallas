#!/usr/bin/env python3
"""Measure the mask-ROM to 6T-SRAM bitcell area ratio inside one open PDK.

`rom.cell_to_sram_cell_area_ratio` has been an ASSUMED constant.  This runner
replaces the assumption with two drawn-geometry measurements taken in the same
installed IHP SG13G2 release:

1. the minimum DRC-legal pitch of an independently implemented via1-programmed
   NOR mask-ROM bitcell, found by proving that every dimension sits on a deck
   floor rather than by asserting it; and
2. the drawn placement pitch of IHP's own SRAM bitcell, taken from the shipped
   macro GDS and cross-checked by requiring the bitcell instance count to equal
   the datasheet bit count in every macro.

IHP SG13G2 is a 130 nm process.  No value here is scaled to N7/N6/N5/N4.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import ot_gds_reader as gdsr
import run_sky130_physical as common


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "spice" / "ihp_sg13g2" / "bitcell" / "bitcell_contract.json"
PDK_VERIFIER = ROOT / "tools" / "verify_ihp_pdk.py"


class BitcellError(RuntimeError):
    """A governed bitcell input, identity, or acceptance gate failed."""


def repository_path(value: str) -> Path:
    try:
        return common.repository_path(value)
    except common.PhysicalExperimentError as exc:
        raise BitcellError(str(exc)) from exc


def validate_contract(contract: dict[str, Any], lock: dict[str, Any]) -> None:
    if contract.get("schema_version") != 1:
        raise BitcellError("bitcell contract schema_version must be 1")
    if contract.get("experiment_id") != "ihp_sg13g2_rom_sram_bitcell_ratio_v1":
        raise BitcellError("unexpected bitcell experiment_id")
    if contract.get("pdk_lock") != "configs/pdk/ihp_sg13g2_physical_lock.json":
        raise BitcellError("bitcell contract must use the governed IHP lock")
    if lock.get("pdk", {}).get("variant") != "ihp-sg13g2":
        raise BitcellError("bitcell measurement requires IHP SG13G2")
    for value in contract["inputs"].values():
        if not repository_path(value).is_file():
            raise BitcellError(f"missing governed bitcell input: {value}")
    boundary = contract.get("claim_boundary", {})
    if (
        boundary.get("evidence_class") != "open_foundry_pdk_measured_bitcell_geometry"
        or boundary.get("target_node_scaling_rule", "missing") is not None
        or boundary.get("target_node_scaling_status") != "prohibited"
        or not boundary.get("establishes")
        or not boundary.get("forbidden_inferences")
        or not boundary.get("rule_set_asymmetry")
    ):
        raise BitcellError("bitcell claim boundary is incomplete")
    forbidden = " ".join(boundary["forbidden_inferences"])
    for marker in ("N7", "N4", "GPU speedup", "silicon"):
        if marker not in forbidden:
            raise BitcellError(f"claim boundary does not cover {marker}")
    for value in contract["reports"].values():
        repository_path(value)


def locate_pdk(explicit: Path | None) -> tuple[Path, Path]:
    candidates: list[Path] = []
    if explicit is not None:
        candidates.append(explicit)
    override = os.environ.get("OPENTALLAS_IHP_PDK_ROOT")
    if override:
        candidates.append(Path(override))
    candidates.extend(
        [
            ROOT / ".cache" / "ihp-open-pdk-v0.3.0",
            Path.home() / ".local" / "opentallas-pdk" / "ihp-open-pdk-v0.3.0",
        ]
    )
    checked: list[str] = []
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        checked.append(str(resolved))
        if resolved.exists():
            root = resolved.parent if resolved.name == "ihp-sg13g2" else resolved
            variant = root / "ihp-sg13g2"
            if (variant / "libs.tech" / "magic" / "ihp-sg13g2.magicrc").is_file():
                return root, variant
    raise BitcellError(f"cannot find the pinned IHP Open PDK v0.3.0; checked {checked}")


def verify_pdk(pdk: Path, lock: dict[str, Any]) -> dict[str, Any]:
    completed = subprocess.run(
        ["python3", str(PDK_VERIFIER), str(pdk)],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=300,
    )
    if completed.returncode != 0:
        raise BitcellError(f"IHP PDK tree verification failed:\n{completed.stdout}")
    observed = json.loads(completed.stdout)
    if observed.get("status") != "pass":
        raise BitcellError(f"IHP PDK verifier did not pass: {observed}")
    expected = lock["pdk"]["installed_tree"]
    for key in ("regular_files", "payload_bytes", "manifest_sha256"):
        if observed["tree"].get(key) != expected.get(key):
            raise BitcellError(f"IHP verified tree mismatch for {key}")
    return {
        "variant": lock["pdk"]["variant"],
        "release": lock["pdk"]["release"],
        "commit": observed["root_commit"],
        "root": str(pdk),
        "tree": observed["tree"],
    }


# --------------------------------------------------------------------------
# ROM bitcell: minimum DRC-legal drawn pitch
# --------------------------------------------------------------------------

SUBCKT_RE = re.compile(r"(?mi)^\.subckt\s+(\S+)\s*(.*)$")


def spice_logical_lines(text: str) -> list[str]:
    """Join SPICE `+` continuations. ext2spice wraps a wide .subckt line, and a
    checker that reads only the first physical line reports a port list that is
    short for a formatting reason rather than a real one."""
    lines: list[str] = []
    for raw in text.splitlines():
        stripped = raw.rstrip()
        if stripped.startswith("+") and lines:
            lines[-1] = lines[-1] + " " + stripped[1:].strip()
        else:
            lines.append(stripped)
    return lines


def expected_ports(rows: int, cols: int) -> list[str]:
    return ["VSS"] + [f"WL{i}" for i in range(rows)] + [f"BL{i}" for i in range(cols)]


def check_ports(netlist: Path, rows: int, cols: int, error: type[Exception]) -> list[str]:
    """Refuse a netlist whose port list is not exactly what was drawn.

    A label that misses its conductor produces no port, magic writes a shorter
    `.subckt` line without complaint, and ngspice then binds a longer instance
    line to it silently. That is how a whole campaign can run on a netlist whose
    ground is not connected, so the port list is checked rather than trusted.
    """
    matches = [
        SUBCKT_RE.match(line)
        for line in spice_logical_lines(netlist.read_text(encoding="utf-8"))
    ]
    found = [match for match in matches if match is not None]
    if len(found) != 1:
        raise error(f"{netlist}: expected one .subckt line, found {len(found)}")
    observed = found[0].group(2).split()
    wanted = expected_ports(rows, cols)
    if observed != wanted:
        missing = [name for name in wanted if name not in observed]
        extra = [name for name in observed if name not in wanted]
        raise error(
            f"{netlist}: extracted port list is wrong ({len(observed)} of {len(wanted)} ports); "
            f"missing {missing[:8]}, unexpected {extra[:8]}"
        )
    # A name check is not a connectivity check, and the gap between them is
    # exactly where this defect lives. The ground pin is a drawn pad with a via
    # down to the tap strip; if that via ever lands on nothing, magic still
    # names the pad `VSS`, still writes it as the first port, and the netlist
    # still simulates -- with every transistor source on a node the testbench
    # is not driving. So require the port to be electrically the same node the
    # devices sit on, which is the thing the name alone cannot say.
    devices = [
        line.split()
        for line in spice_logical_lines(netlist.read_text(encoding="utf-8"))
        if line.startswith("X") and "nmos" in line
    ]
    if not devices:
        raise error(f"{netlist}: no transistors in the extracted netlist to check VSS against")
    # `X<name> drain gate source bulk model ...`. The BULK is deliberately not
    # accepted: every nMOS in a p-substrate sits in the same well, so a check
    # that accepted the bulk would pass a netlist whose source rail is broken --
    # which is a different way to reach the same floating ground. One of drain
    # or source must be the VSS port; the other is the bitline, or a floating
    # drain where a bit is not programmed.
    grounded = sum(1 for fields in devices if "VSS" in (fields[1], fields[3]))
    if grounded != len(devices):
        raise error(
            f"{netlist}: only {grounded} of {len(devices)} row transistors have the VSS port "
            "on a source or drain terminal. The port exists by name but is not the node the "
            "array's sources are on, so the array would simulate with a floating ground and "
            "every energy number taken from it would be wrong without anything failing."
        )
    return observed


DEVICE_RE = re.compile(r"(?mi)^([XMRCDQ]\S*)\s+(.*)$")
PARASITIC_RE = re.compile(r"(?mi)^([CR])\d+\s+(\S+)\s+(\S+)\s+(\S+)\s*$")
MAG_TIMESTAMP_RE = re.compile(r"(?m)^timestamp\s+\d+\s*$")


def canonical_layout(mag_text: str) -> str:
    """A rendering of a Magic layout that two identical runs must agree on.

    Magic stamps wall-clock `timestamp` into every `.mag` it writes, and the
    GDS carries a write time in its header, so the SHA-256 of either file
    changes on every run of an unchanged generator.  A recorded hash that can
    never be reproduced looks exactly like a determinism check and is not one:
    a reader who re-runs and compares gets a mismatch on a correct run, and a
    reader who does not compare gets no guarantee at all.  This strips the
    clock and sorts each layer's rectangles so that what is hashed is the drawn
    geometry and nothing else.
    """
    section = None
    layers: dict[str, list[str]] = {}
    header: list[str] = []
    for line in MAG_TIMESTAMP_RE.sub("", mag_text).splitlines():
        line = line.rstrip()
        if not line:
            continue
        if line.startswith("<< "):
            section = line[3:].rsplit(">>", 1)[0].strip()
            layers.setdefault(section, [])
        elif section is None:
            header.append(line)
        else:
            layers[section].append(line)
    out = list(header)
    for name in sorted(layers):
        out.append(f"<< {name} >>")
        out.extend(sorted(layers[name]))
    return "\n".join(out) + "\n"


def canonical_netlist(spice_text: str) -> str:
    """A rendering of an extracted netlist that two identical runs must agree on.

    `ext2spice` does not emit the extracted parasitics in a stable order: two
    runs of the same generator produce the same 126 capacitors with the same
    values under different `C<n>` names and in a different sequence.  The
    element set is the physics; the ordering is not.  Nodes of a two-terminal
    parasitic are sorted too, because `C a b` and `C b a` are the same device.
    """
    lines = spice_logical_lines(spice_text)
    subckt: list[str] = []
    parasitics: list[str] = []
    devices: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("*"):
            continue
        if line.lower().startswith(".subckt") or line.lower().startswith(".ends"):
            subckt.append(line)
            continue
        if line.startswith("."):
            continue
        match = PARASITIC_RE.match(line)
        if match is not None:
            kind, left, right, value = match.groups()
            a, b = sorted((left, right))
            parasitics.append(f"{kind} {a} {b} {value}")
            continue
        device = DEVICE_RE.match(line)
        if device is not None:
            devices.append(line)
    return "\n".join(subckt + sorted(devices) + sorted(parasitics)) + "\n"


def canonical_digests(workdir: Path) -> dict[str, str]:
    """Order- and clock-independent digests of whatever this run drew."""
    digests: dict[str, str] = {}
    mag = workdir / "ihp_rom_bitarray.mag"
    if mag.is_file():
        digests["layout"] = hashlib.sha256(
            canonical_layout(mag.read_text(encoding="utf-8")).encode("utf-8")
        ).hexdigest()
    for key, name in (
        ("extracted", "ihp_rom_bitarray.extracted.spice"),
        ("pex", "ihp_rom_bitarray.pex.spice"),
    ):
        path = workdir / name
        if path.is_file():
            digests[key] = hashlib.sha256(
                canonical_netlist(path.read_text(encoding="utf-8")).encode("utf-8")
            ).hexdigest()
    return digests


MAGIC_PARAM_RE = re.compile(r"(?m)^OT_PARAM\|([A-Z0-9_]+)\|(.+)$")
MAGIC_TOTAL_RE = re.compile(r"(?m)^OT_DRC_TOTAL=(\d+)$")
MAGIC_RULE_RE = re.compile(r"(?m)^OT_DRC_RULE\|(\d+)\|(.+)$")


def run_generator(
    magic: Path,
    variant: Path,
    pdk: Path,
    generator: Path,
    overrides: dict[str, Any],
    workdir: Path,
    *,
    extract: bool = False,
) -> dict[str, Any]:
    workdir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(generator, workdir / generator.name)
    environment = os.environ.copy()
    environment.update({"LC_ALL": "C", "TZ": "UTC", "PDK_ROOT": str(pdk)})
    for key, value in overrides.items():
        environment[f"OT_{key}"] = str(value)
    if extract:
        environment["OT_EXTRACT"] = "1"
    log = workdir / "magic.log"
    completed = subprocess.run(
        [
            str(magic),
            "-dnull",
            "-noconsole",
            "-rcfile",
            str(variant / "libs.tech" / "magic" / "ihp-sg13g2.magicrc"),
            generator.name,
        ],
        cwd=workdir,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=3600,
    )
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise BitcellError(
            f"magic failed ({completed.returncode}) for overrides {overrides}; see {log}"
        )
    if "Error parsing" in completed.stdout:
        raise BitcellError(f"magic failed while parsing the generator; see {log}")
    params = {key: value.strip() for key, value in MAGIC_PARAM_RE.findall(completed.stdout)}
    if "OT_DRC_SKIPPED=1" in completed.stdout:
        raise BitcellError(
            "the generator skipped DRC; a skipped check is not a clean check and this "
            "runner refuses to record one"
        )
    totals = MAGIC_TOTAL_RE.findall(completed.stdout)
    if len(totals) != 1:
        raise BitcellError(f"expected exactly one DRC total; observed {totals}")
    rules = [
        {"error_tiles": int(count), "rule": rule.strip()}
        for count, rule in MAGIC_RULE_RE.findall(completed.stdout)
    ]
    return {
        "overrides": dict(overrides),
        "params": params,
        "drc_errors": int(totals[0]),
        "drc_rules": rules,
        "log_sha256": common.sha256_file(log),
        "workdir": workdir,
    }


def measure_rom_bitcell(
    contract: dict[str, Any], magic: Path, variant: Path, pdk: Path, build: Path
) -> dict[str, Any]:
    spec = contract["rom_cell"]
    generator = repository_path(contract["inputs"]["generator"])
    nominal = dict(spec["nominal_nm"])
    base = dict(nominal)
    base.update({"NROW": spec["array_rows"], "NCOL": spec["array_cols"], "PATTERN": "checker"})

    nominal_run = run_generator(
        magic, variant, pdk, generator, base, build / "rom_nominal", extract=True
    )
    if nominal_run["drc_errors"] != contract["acceptance"]["rom_nominal_drc_errors_max"]:
        raise BitcellError(
            "the nominal ROM bitcell array is not DRC clean: "
            f"{nominal_run['drc_errors']} errors, {nominal_run['drc_rules']}"
        )

    # Determinism is claimed by the report, so it is measured rather than
    # asserted: draw and extract the same array a second time and require the
    # canonical geometry and the canonical netlist to be identical. The raw
    # file hashes cannot do this job -- magic stamps a clock into the .mag and
    # the GDS header, and ext2spice reorders the parasitics -- so a runner that
    # only recorded those hashes would be recording a check that always fails
    # and is therefore never run.
    repeat_run = run_generator(
        magic, variant, pdk, generator, base, build / "rom_nominal_repeat", extract=True
    )
    digests = canonical_digests(nominal_run["workdir"])
    repeat_digests = canonical_digests(repeat_run["workdir"])
    if not digests:
        raise BitcellError("the nominal ROM array produced nothing to digest")
    if digests != repeat_digests:
        differing = sorted(k for k in digests if digests[k] != repeat_digests.get(k))
        raise BitcellError(
            "the ROM array generator is not deterministic: a second identical run "
            f"produced different {differing}. Every number below is drawn from one run "
            "and would not survive reproduction."
        )
    if repeat_run["drc_errors"] != nominal_run["drc_errors"]:
        raise BitcellError("two identical runs disagreed on the DRC error count")
    shutil.rmtree(repeat_run["workdir"], ignore_errors=True)

    px = float(nominal_run["params"]["PX"])
    py = float(nominal_run["params"]["PY"])
    cell_area_nm2 = float(nominal_run["params"]["CELL_AREA_NM2"])
    if abs(px * py - cell_area_nm2) > 1e-6:
        raise BitcellError("generator pitch and reported cell area disagree")

    step = int(spec["floor_probe_step_nm"])
    probes: list[dict[str, Any]] = []
    for name in spec["floor_probe_dimensions"]:
        shrunk = dict(base)
        shrunk[name] = nominal[name] - step
        if name == "WD":
            # the diffusion strip and the column pitch move together: shrinking
            # the strip alone only widens the gap and proves nothing.
            shrunk["PX"] = nominal["PX"] - step
        run = run_generator(
            magic, variant, pdk, generator, shrunk, build / f"rom_probe_{name}"
        )
        probes.append(
            {
                "dimension": name,
                "nominal_nm": nominal[name],
                "probed_nm": nominal[name] - step,
                "drc_errors": run["drc_errors"],
                "violated_rules": sorted({entry["rule"] for entry in run["drc_rules"]}),
            }
        )
        shutil.rmtree(run["workdir"], ignore_errors=True)
    unproven = [entry["dimension"] for entry in probes if entry["drc_errors"] == 0]
    if contract["acceptance"]["every_probed_dimension_must_fail"] and unproven:
        raise BitcellError(
            f"these ROM dimensions are not at a deck floor and are therefore not minimal: {unproven}"
        )

    # The programming via is the whole mechanism, so count the drawn shapes and
    # require them to equal the stored ones. A checkerboard stores exactly half.
    expected_bits = spec["array_rows"] * spec["array_cols"]
    programmed = int(nominal_run["params"]["PROGRAMMED_VIA1"])
    if programmed != expected_bits // 2:
        raise BitcellError(
            f"checkerboard pattern stored {programmed} ones in a {expected_bits}-bit array"
        )
    # Magic stores a via as several corner-stitched tiles, so count AREA, not
    # tiles: the drawn via is a fixed square and the total must be an exact
    # multiple of it.
    mag = (nominal_run["workdir"] / "ihp_rom_bitarray.mag").read_text(encoding="utf-8")
    section = None
    via1_area_units = 0
    for line in mag.splitlines():
        if line.startswith("<< "):
            section = line[3:].split()[0]
        elif line.startswith("rect") and section == "via1":
            _, x1, y1, x2, y2 = line.split()
            via1_area_units += (int(x2) - int(x1)) * (int(y2) - int(y1))
    scale_nm = 5  # magic internal unit for this deck
    if "V1" not in nominal_run["params"]:
        raise BitcellError("the generator did not report its drawn via1 size")
    via_area_nm2 = float(nominal_run["params"]["V1"]) ** 2
    structural = int(nominal_run["params"].get("STRUCTURAL_VIA1", -1))
    if structural < 0:
        raise BitcellError("the generator did not report its structural via1 count")
    drawn_vias = via1_area_units * scale_nm * scale_nm / via_area_nm2 - structural
    if abs(drawn_vias - programmed) > 1e-9:
        raise BitcellError(
            f"the layout holds {drawn_vias:g} programming via1 squares "
            f"(after {structural} structural) but {programmed} bits are programmed"
        )
    via1_rects = programmed

    extracted = nominal_run["workdir"] / "ihp_rom_bitarray.extracted.spice"
    if not extracted.is_file():
        raise BitcellError("the nominal ROM array did not extract")
    ports = check_ports(
        nominal_run["workdir"] / "ihp_rom_bitarray.pex.spice",
        spec["array_rows"], spec["array_cols"], BitcellError,
    )
    devices = sum(
        1 for line in extracted.read_text(encoding="utf-8").splitlines()
        if line.startswith("X") and "sg13_lv_nmos" in line
    )
    expected_devices = spec["array_rows"] * spec["array_cols"]
    if devices != expected_devices:
        raise BitcellError(
            f"extracted {devices} nMOS devices but the array holds {expected_devices} bits"
        )

    # The claim is that every bit owns an independent programming via. Read it
    # back from the extracted connectivity: each bitline must terminate on
    # exactly the cells whose via is present, and no others.
    stored = {
        (int(a), int(b))
        for a, b in (
            line.split()
            for line in (nominal_run["workdir"] / "programmed_bits.txt")
            .read_text(encoding="utf-8")
            .split("\n")
            if line.strip()
        )
    }
    attached: dict[str, int] = {}
    for line in extracted.read_text(encoding="utf-8").splitlines():
        if not line.startswith("X") or "sg13_lv_nmos" not in line:
            continue
        fields = line.split()
        for node in fields[1:4]:
            if node.upper().startswith("BL"):
                attached[node.upper()] = attached.get(node.upper(), 0) + 1
    for column in range(spec["array_cols"]):
        name = f"BL{column}"
        expected_cells = sum(1 for (c, _r) in stored if c == column)
        if attached.get(name, 0) != expected_cells:
            raise BitcellError(
                f"{name} is connected to {attached.get(name, 0)} cells but "
                f"{expected_cells} of its bits are programmed"
            )

    return {
        "topology": spec["topology"],
        "extracted_nmos_devices": devices,
        "drawn_via1_shapes": via1_rects,
        "bitline_connectivity_verified": True,
        "extracted_ports": ports,
        "canonical_digests": digests,
        "canonical_digest_note": (
            "order- and clock-independent SHA-256 of the drawn geometry and of the "
            "extracted netlists. These are the reproducibility check: two identical "
            "runs must produce identical canonical digests, and this runner refuses "
            "to record a result unless a repeat run does. The per-file sha256 under "
            "`artifacts` is ARCHIVAL IDENTITY ONLY -- magic writes a wall-clock "
            "timestamp into the .mag and the GDS header and ext2spice does not order "
            "the extracted parasitics, so those hashes change on every run of an "
            "unchanged generator and are not a determinism check"
        ),
        "repeat_run_matches": True,
        "expected_nmos_devices": expected_devices,
        "drc_style": spec["drc_style"],
        "nominal_nm": nominal,
        "array": {"rows": spec["array_rows"], "cols": spec["array_cols"]},
        "column_pitch_nm": px,
        "row_pitch_nm": py,
        "cell_area_um2": cell_area_nm2 / 1.0e6,
        "nominal_drc_errors": nominal_run["drc_errors"],
        "floor_probes": probes,
        "programming_via1_count": int(nominal_run["params"]["PROGRAMMED_VIA1"]),
        "magic_log_sha256": nominal_run["log_sha256"],
    }


# --------------------------------------------------------------------------
# Foundry SRAM bitcell: drawn placement pitch from the shipped macros
# --------------------------------------------------------------------------

SIZE_RE = re.compile(r"SIZE\s+([0-9.]+)\s+BY\s+([0-9.]+)\s*;")
DOC_SIZE_RE = re.compile(r"Size\s*:\s*(\d+) words x (\d+) bits")
DOC_AREA_RE = re.compile(r"Area \(h x w\)\s*:\s*([0-9.]+) x ([0-9.]+) = ([0-9.]+)")


def measure_sram_bitcells(contract: dict[str, Any], variant: Path) -> dict[str, Any]:
    spec = contract["sram_reference"]
    lib = variant.parent / spec["library_subdir"]
    if not lib.is_dir():
        raise BitcellError(f"missing IHP SRAM library at {lib}")
    macros: list[dict[str, Any]] = []
    pitches: dict[str, set[tuple[float, float]]] = {"1P": set(), "2P": set()}
    for gds_path in sorted(glob.glob(str(lib / "gds" / "*.gds"))):
        name = Path(gds_path).stem
        family = "1P" if "_1P_" in name else "2P"
        target = (
            spec["single_port_bitcell"] if family == "1P" else spec["dual_port_bitcell"]
        )
        lef = (lib / "lef" / f"{name}.lef").read_text(encoding="latin-1")
        size = SIZE_RE.search(lef)
        if size is None:
            raise BitcellError(f"{name}: LEF has no SIZE record")
        macro_w, macro_h = float(size.group(1)), float(size.group(2))
        doc_path = lib / "doc" / f"{name}.txt"
        words = bits = None
        doc_area = None
        if doc_path.is_file():
            doc = doc_path.read_text(encoding="latin-1")
            dims = DOC_SIZE_RE.search(doc)
            area = DOC_AREA_RE.search(doc)
            if dims is not None:
                words, bits = int(dims.group(1)), int(dims.group(2))
            if area is not None:
                doc_area = float(area.group(3))

        gdsr._bb.clear()
        cells, unit = gdsr.parse(gds_path)
        dbu = 1e-6 / unit[1]
        referenced = {ref["name"] for cell in cells.values() for ref in cell["refs"]}
        tops = [cell for cell in cells if cell not in referenced]
        if len(tops) != 1:
            raise BitcellError(f"{name}: expected one top cell, found {tops}")
        placements = gdsr.instances(cells, tops[0], target)
        if not placements:
            raise BitcellError(f"{name}: no {target} placements found")
        xs = sorted({round(point[0]) for point in placements})
        ys = sorted({round(point[1]) for point in placements})
        dx = min(xs[i + 1] - xs[i] for i in range(len(xs) - 1)) / dbu if len(xs) > 1 else None
        dy = min(ys[i + 1] - ys[i] for i in range(len(ys) - 1)) / dbu if len(ys) > 1 else None
        if dx is not None and dy is not None:
            pitches[family].add((round(dx, 4), round(dy, 4)))

        record: dict[str, Any] = {
            "macro": name,
            "family": family,
            "bitcell_instances": len(placements),
            "physical_columns": len(xs),
            "physical_rows": len(ys),
            "column_pitch_um": None if dx is None else round(dx, 4),
            "row_pitch_um": None if dy is None else round(dy, 4),
            "lef_size_um": [macro_w, macro_h],
            "lef_area_um2": macro_w * macro_h,
        }
        if words is not None:
            record["datasheet_words"] = words
            record["datasheet_bits_per_word"] = bits
            record["datasheet_bit_count"] = words * bits
            if spec["instance_count_must_equal_bit_count"] and words * bits != len(placements):
                raise BitcellError(
                    f"{name}: {len(placements)} bitcell placements but {words * bits} datasheet bits"
                )
        if doc_area is not None:
            record["datasheet_area_um2"] = doc_area
            if abs(doc_area - macro_w * macro_h) > 1.0:
                raise BitcellError(f"{name}: datasheet area and LEF SIZE disagree")
        macros.append(record)

    if len(macros) < contract["acceptance"]["sram_macros_min"]:
        raise BitcellError(f"only {len(macros)} SRAM macros were measured")
    result: dict[str, Any] = {"macros": macros}
    for family, observed in pitches.items():
        if not observed:
            continue
        if len(observed) > contract["acceptance"]["sram_pitch_families_max"]:
            raise BitcellError(f"{family} bitcell pitch is not unique: {sorted(observed)}")
        (dx, dy) = next(iter(observed))
        result[family] = {
            "column_pitch_um": dx,
            "row_pitch_um": dy,
            "cell_area_um2": round(dx * dy, 6),
            "macro_count": sum(1 for macro in macros if macro["family"] == family),
        }
    return result


def sram_array_efficiency(sram: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for macro in sram["macros"]:
        if "datasheet_bit_count" not in macro:
            continue
        pitch_area = sram[macro["family"]]["cell_area_um2"]
        bit_area = macro["datasheet_bit_count"] * pitch_area
        rows.append(
            {
                "macro": macro["macro"],
                "family": macro["family"],
                "bits": macro["datasheet_bit_count"],
                "macro_area_um2": macro["lef_area_um2"],
                "bitcell_area_um2": bit_area,
                "array_efficiency": bit_area / macro["lef_area_um2"],
            }
        )
    rows.sort(key=lambda entry: entry["array_efficiency"])
    by_family = {
        family: [entry for entry in rows if entry["family"] == family]
        for family in ("1P", "2P")
    }
    incremental: dict[str, Any] = {}
    for width in (8, 16, 32, 64):
        family = [
            entry
            for entry in rows
            if entry["family"] == "1P" and f"x{width}_" in entry["macro"]
        ]
        if len(family) < 3:
            continue
        points = sorted(
            (entry["bits"], entry["macro_area_um2"]) for entry in family
        )
        slopes = [
            (points[i + 1][1] - points[i][1]) / (points[i + 1][0] - points[i][0])
            for i in range(len(points) - 1)
        ]
        area_per_bit = sum(slopes) / len(slopes)
        incremental[f"1P_x{width}"] = {
            "points": points,
            "incremental_area_per_bit_um2": area_per_bit,
            "asymptotic_array_efficiency": sram["1P"]["cell_area_um2"] / area_per_bit,
            "slope_spread_um2": max(slopes) - min(slopes),
        }
    return {
        "per_macro": rows,
        "min": rows[0],
        "max": rows[-1],
        "single_port_min": by_family["1P"][0],
        "single_port_max": by_family["1P"][-1],
        "incremental": incremental,
    }


def sram_bitcell_drc(
    contract: dict[str, Any], magic: Path, variant: Path, pdk: Path, build: Path
) -> dict[str, Any]:
    """Check the foundry SRAM bitcell against the installed public logic deck."""
    spec = contract["sram_reference"]
    lib = variant.parent / spec["library_subdir"]
    source = sorted(glob.glob(str(lib / "gds" / "RM_IHPSG13_1P_64x64*.gds")))
    if not source:
        raise BitcellError("cannot find a single-port SRAM macro GDS to subset")
    workdir = build / "sram_drc"
    workdir.mkdir(parents=True, exist_ok=True)
    subset = workdir / "sram_bitcell_context.gds"
    written = gdsr.subset_gds(source[0], subset, [spec["drc_context_cell"], spec["single_port_bitcell"]])

    script = workdir / "sram_drc.tcl"
    cells = [spec["single_port_bitcell"], spec["drc_context_cell"]]
    lines = [f'gds read {subset.name}', "drc style drc(full)"]
    for cell in cells:
        lines.extend(
            [
                f"load {cell}",
                "select top cell",
                "drc check",
                "drc catchup",
                f'puts "OT_SRAM_CELL|{cell}|[drc list count total]"',
                "set L [drc listall why]",
                "for {set i 0} {$i < [llength $L]} {incr i 2} {",
                f'    puts "OT_SRAM_RULE|{cell}|[llength [lindex $L [expr {{$i+1}}]]]|[lindex $L $i]"',
                "}",
            ]
        )
    lines.append("quit -noprompt")
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")

    environment = os.environ.copy()
    environment.update({"LC_ALL": "C", "TZ": "UTC", "PDK_ROOT": str(pdk)})
    log = workdir / "sram_drc.log"
    completed = subprocess.run(
        [
            str(magic),
            "-dnull",
            "-noconsole",
            "-rcfile",
            str(variant / "libs.tech" / "magic" / "ihp-sg13g2.magicrc"),
            script.name,
        ],
        cwd=workdir,
        env=environment,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=3600,
    )
    log.write_text(completed.stdout, encoding="utf-8")
    if completed.returncode != 0:
        raise BitcellError(f"magic failed while checking the foundry SRAM bitcell; see {log}")
    totals = dict(re.findall(r"(?m)^OT_SRAM_CELL\|([^|]+)\|(\d+)$", completed.stdout))
    rules: dict[str, list[dict[str, Any]]] = {cell: [] for cell in cells}
    for cell, count, rule in re.findall(
        r"(?m)^OT_SRAM_RULE\|([^|]+)\|(\d+)\|(.+)$", completed.stdout
    ):
        rules[cell].append({"error_tiles": int(count), "rule": rule.strip()})
    single = int(totals.get(spec["single_port_bitcell"], -1))
    array_cell = int(totals.get(spec["drc_context_cell"], -1))
    if single <= 0 or array_cell <= 0:
        raise BitcellError(
            "the foundry SRAM bitcell passed the public logic deck; the rule-set asymmetry "
            "this run reports would then be unfounded and the ratio's direction unproven"
        )
    return {
        "subset_structures": written,
        "single_port_bitcell_drc_errors": single,
        "array_context_drc_errors": array_cell,
        "cells": {
            cell: {
                "drc_errors": int(totals.get(cell, -1)),
                "violated_rules": rules[cell],
            }
            for cell in cells
        },
        "log_sha256": common.sha256_file(log),
    }


def finfet_ratio_ladder(
    rom_units: int, sram_units: int, span: int = 3
) -> dict[str, Any]:
    """The values a cell-area ratio is allowed to take at a quantised node.

    At the FinFET node the sibling measured, BOTH cells land on exact integer
    multiples of one CPP x one fin pitch. A cell cannot be 4.3 quanta; the
    smallest legal change to either dimension is a whole quantum. So the ratio
    is a ratio of two small integers and it moves in visible steps -- and a
    sweep that samples a continuum between two endpoints spends most of its
    samples on values no layout can have.

    This enumerates the ladder around the measured pair: the ROM at its
    measured quanta and a few steps either side, over the SRAM at its measured
    quanta and a few steps either side. It is a statement about the shape of
    the constant, not a prediction of any one value.
    """
    roms = [n for n in range(rom_units - span, rom_units + span + 1) if n > 0]
    srams = [n for n in range(sram_units - span, sram_units + span + 1) if n > 0]
    rungs = sorted(
        {
            (
                round(r / s, 12),
                r,
                s,
            )
            for r in roms
            for s in srams
        }
    )
    return {
        "rom_units_measured": rom_units,
        "sram_units_measured": sram_units,
        "quantum": "one contacted poly pitch by one fin pitch",
        "measured_rung": rom_units / sram_units,
        "rungs_near_the_measurement": [
            {"ratio": value, "rom_units": r, "sram_units": s}
            for value, r, s in rungs
            if abs(r - rom_units) <= 1 and abs(s - sram_units) <= 2
        ],
        "gap_to_next_rung_down": (
            rom_units / sram_units - rom_units / (sram_units + 1)
        ),
        "gap_to_next_rung_up": (
            rom_units / (sram_units - 1) - rom_units / sram_units
            if sram_units > 1
            else None
        ),
        "why_a_continuous_sweep_is_wrong": (
            "the constant cannot take a value between two adjacent rungs at this node, "
            "so a sweep must sample the rungs. A uniform sweep over an interval reports "
            "sensitivity to values no drawn cell can have, and it reports the WRONG "
            "spacing: the rungs are not evenly spaced"
        ),
        "boundary": (
            "this ladder is a property of the PREDICTIVE 7 nm-class PDK the sibling drew "
            "in. It is not a TSMC N7/N6/N5/N4 statement and no rung is a target-node value"
        ),
    }


# --------------------------------------------------------------------------
# Reporting
# --------------------------------------------------------------------------


def markdown_report(result: dict[str, Any]) -> str:
    rom = result["rom_bitcell"]
    sram = result["sram_bitcell"]
    ratio = result["ratio"]
    eff = result["sram_array_efficiency"]
    boundary = result["claim_boundary"]
    lines = [
        "# IHP SG13G2 measured mask-ROM versus 6T-SRAM bitcell area",
        "",
        f"**Status:** **{result['status'].upper()}**  ",
        "**Evidence class:** drawn-geometry measurement in one installed open foundry PDK; **130 nm**; not silicon, not a leading node  ",
        f"**PDK:** `{result['pdk']['variant']}` / `{result['pdk']['release']}` / `{result['pdk']['commit']}`  ",
        f"**Magic:** `{result['toolchain']['magic']['version']}` / `{result['toolchain']['magic']['commit']}`",
        "",
        "## The measured ratio",
        "",
        "| Quantity | Measured | Source |",
        "|---|---:|---|",
        f"| Mask-ROM bitcell pitch | {rom['column_pitch_nm']:.0f} × {rom['row_pitch_nm']:.0f} nm | drawn here; DRC clean under `drc(full)` |",
        f"| Mask-ROM bitcell area | **{rom['cell_area_um2']:.6f} µm²** | pitch product |",
        f"| Foundry 6T SRAM bitcell pitch | {sram['1P']['column_pitch_um']:.4f} × {sram['1P']['row_pitch_um']:.4f} µm | IHP `sg13g2_sram` macro GDS |",
        f"| Foundry 6T SRAM bitcell area | **{sram['1P']['cell_area_um2']:.6f} µm²** | pitch product |",
        f"| **Measured area ratio** | **{ratio['measured']:.4f}** | ROM ÷ SRAM, same PDK |",
        f"| Assumed `rom.cell_to_sram_cell_area_ratio` | {ratio['assumed']:.4f} | `configs/hardware/technology.json` |",
        f"| Measured ÷ assumed | {ratio['measured'] / ratio['assumed']:.3f}× | |",
        "",
        f"At this node the drawn ROM bitcell is **{1.0 / ratio['measured']:.2f}× smaller** than the",
        f"foundry 6T cell, against the {1.0 / ratio['assumed']:.1f}× the model's stated "
        f"{ratio['assumed']:.4f} implies, so that value is "
        + ("*conservative*" if ratio["measured"] < ratio["assumed"] else "*optimistic*")
        + " against this",
        "130 nm measurement — and, for the reason given under \"rule-set asymmetry\" below,",
        "the true same-rule-set ratio is smaller still. Neither statement licenses moving a",
        "leading-node constant: see \"Node honesty\".",
        "",
        "The dual-port 8T bitcell in the same release measures "
        f"{sram['2P']['column_pitch_um']:.4f} × {sram['2P']['row_pitch_um']:.4f} µm = "
        f"{sram['2P']['cell_area_um2']:.6f} µm², a ratio of {rom['cell_area_um2'] / sram['2P']['cell_area_um2']:.4f}.",
        "",
        "## Why the ROM pitch is a measurement and not a choice",
        "",
        "Every drawn dimension of the ROM bitcell sits on a floor of the installed",
        "public deck. Reducing any one of them by "
        f"{result['rom_bitcell']['floor_probes'][0]['nominal_nm'] - result['rom_bitcell']['floor_probes'][0]['probed_nm']} nm"
        " produces the named violation below.",
        "",
        "| Dimension | Nominal | Probed | DRC errors | Rule that stops the shrink |",
        "|---|---:|---:|---:|---|",
    ]
    for probe in rom["floor_probes"]:
        lines.append(
            f"| `{probe['dimension']}` | {probe['nominal_nm']} nm | {probe['probed_nm']} nm | "
            f"{probe['drc_errors']} | {'; '.join(probe['violated_rules'])} |"
        )
    lines.extend(
        [
            "",
            "The probes vary **one dimension at a time**, so what they prove is that each",
            "dimension sits at a floor given the others — local minimality for this topology.",
            "They do not prove a global minimum over all mask-ROM topologies, and a report that",
            "reads them that way is claiming more than was measured.",
            "",
            "## Why the SRAM pitch is a measurement and not a choice",
            "",
            f"The bitcell placement pitch was extracted from every shipped `sg13g2_sram` macro",
            f"({len(sram['macros'])} macros). In every macro carrying a datasheet the number of",
            "bitcell placements equals the datasheet bit count exactly, and the LEF `SIZE`",
            "record equals the datasheet area, so the cell being measured is one stored bit",
            "and not a group. Exactly one pitch is observed per port family.",
            "",
            "## The rule-set asymmetry, measured",
            "",
            "The two cells are **not** drawn under the same rules, and this run measures the gap",
            "rather than assuming it away. The foundry bitcell carries the PDK's own `SRAM`",
            "recognition layer (GDS 25/0) and is **not legal** under the installed public logic deck:",
            "",
            "| Cell | DRC errors under `drc(full)` | Rules violated |",
            "|---|---:|---|",
        ]
    )
    for cell, entry in result["sram_bitcell_drc"]["cells"].items():
        rule_text = "; ".join(
            f"{item['rule']} ({item['error_tiles']})" for item in entry["violated_rules"]
        )
        lines.append(f"| `{cell}` | {entry['drc_errors']} | {rule_text or 'none'} |")
    lines.extend(
        [
            "",
            "Read the two rows differently. The isolated bitcell is checked without its array",
            "context, so its `LU.a`/`LU.b` counts are an artefact of the missing tap rows and are",
            "not push rules; they disappear in the 16 × 2 array, which carries taps. What survives",
            "**with** array context is the real rule relief: poly endcap (`Gat.c`), well overlap and",
            "spacing (`NW.c`, `NW.d`), contact enclosure (`Cnt.c`) and Metal2 minimum area (`M2.d`).",
            "",
            "The ROM cell is logic-rule legal and the SRAM cell is not. A ROM array drawn with",
            "the same relaxations available to the memory cell would be **smaller** than the one",
            "measured here, so **the reported ratio is an upper bound** on the ratio that a single",
            "rule set applied to both cells would give. It is not a floor.",
            "",
            "## Foundry SRAM array efficiency, for comparison with `rom.array_efficiency`",
            "",
            "Bitcell pitch area divided by the macro's own LEF footprint, for the shipped macros.",
            "This is a real memory's array efficiency at this node, including its decoders, sense",
            "path, control and (where present) BIST.",
            "",
            f"- single-port lowest: `{eff['single_port_min']['macro']}` at **{eff['single_port_min']['array_efficiency'] * 100:.2f}%** ({eff['single_port_min']['bits']:,} bits)",
            f"- single-port highest: `{eff['single_port_max']['macro']}` at **{eff['single_port_max']['array_efficiency'] * 100:.2f}%** ({eff['single_port_max']['bits']:,} bits)",
            f"- assumed `rom.array_efficiency` = {result['array_efficiency_reference']['assumed']:.2f}, graded `{result['array_efficiency_reference']['assumed_grade']}`",
            "",
            "| Fixed-width family | incremental area per bit | implied asymptotic array efficiency |",
            "|---|---:|---:|",
        ]
    )
    for name, entry in sorted(result["sram_array_efficiency"]["incremental"].items()):
        note = "" if entry["slope_spread_um2"] < 0.01 else " (mixed column-mux; slope not constant)"
        lines.append(
            f"| `{name}`{note} | {entry['incremental_area_per_bit_um2']:.4f} µm²/bit | "
            f"{entry['asymptotic_array_efficiency'] * 100:.2f}% |"
        )
    lines.extend(
        [
            "",
            "Efficiency rises steeply with macro size, so a single scalar `array_efficiency` is",
            "only meaningful once the macro geometry it refers to is stated.",
            "",
            "## Node honesty",
            "",
            "@NODE_SENSITIVITY@",
            "",
            "IHP SG13G2 is a **130 nm** process and the program targets N6/N5. A ratio of two",
            "bitcell areas drawn in one PDK travels further than either absolute area, because",
            "the leading terms — contact size, contact-to-gate clearance, diffusion spacing, gate",
            "length — enter both cells. It still does not travel unchanged: the ROM cell is",
            "contact-and-spacing limited while the 6T cell is additionally limited by well",
            "spacing and by the p/n boundary, and those scale differently. **No number here may",
            "be presented as an N6, N5, N4 or N7 value.**",
            "",
            "## Claim boundary",
            "",
        ]
    )
    lines.extend(f"- Establishes: {item}." for item in boundary["establishes"])
    lines.append("")
    lines.extend(f"- Does not establish: {item}." for item in boundary["forbidden_inferences"])
    lines.extend(
        [
            "",
            f"- Rule-set asymmetry: {boundary['rule_set_asymmetry']}.",
            "",
            "## Reproduction, and what \"reproducible\" means here",
            "",
            "```bash",
            "python3 tools/run_ihp_bitcell_density.py",
            "```",
            "",
            "This run draws and extracts the nominal array **twice** and refuses to record a",
            "result unless both runs produce identical canonical digests:",
            "",
            "| Canonical digest | SHA-256 |",
            "|---|---|",
        ]
    )
    lines.extend(
        f"| `{name}` | `{digest}` |"
        for name, digest in sorted(rom["canonical_digests"].items())
    )
    lines.extend(
        [
            "",
            "**The per-file `sha256` under `artifacts` is archival identity only and is not a",
            "reproducibility check.** Magic writes a wall-clock `timestamp` into the `.mag` and",
            "into the GDS header, and `ext2spice` does not emit the extracted parasitics in a",
            "stable order, so those hashes differ between two runs that drew exactly the same",
            "geometry. The canonical digests above strip the clock and sort the elements, so they",
            "compare the physics and nothing else.",
            "",
        ]
    )
    text = "\n".join(lines)
    sibling = result.get("node_sensitivity")
    if sibling:
        note = (
            f"A sibling experiment measures the same ratio in **{sibling['node']}** "
            f"and gets **{sibling['ratio']:.4f}** against this run's "
            f"**{result['ratio']['measured']:.4f}** — the ROM bitcell is "
            f"{abs(sibling['ratio'] / result['ratio']['measured'] - 1.0) * 100:.0f}% "
            f"{'larger' if sibling['ratio'] > result['ratio']['measured'] else 'smaller'} "
            "relative to 6T SRAM at the FinFET node than at 130 nm. **The ratio is therefore "
            "node-sensitive and the two numbers must never be averaged, blended or "
            f"interpolated.** Source: `{sibling['source']}`."
        )
    else:
        note = (
            "Nothing here characterises how the ratio moves between nodes. A sibling "
            "predictive-PDK measurement would be needed for that and none is present."
        )
    return text.replace("@NODE_SENSITIVITY@", note)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--pdk-root", type=Path)
    parser.add_argument("--tool-root", type=Path)
    parser.add_argument("--magic", type=Path)
    parser.add_argument("--netgen", type=Path)
    parser.add_argument("--keep-build", action="store_true")
    args = parser.parse_args()

    build: Path | None = None
    try:
        contract = common.strict_json(CONTRACT_PATH)
        lock = common.strict_json(repository_path(contract["pdk_lock"]))
        validate_contract(contract, lock)
        if args.validate_only:
            print("PASS: IHP bitcell contract and no-scaling boundary")
            return 0

        pdk, variant = locate_pdk(args.pdk_root)
        magic, netgen = common.locate_tools(lock, args.tool_root, args.magic, args.netgen)
        pdk_identity = verify_pdk(pdk, lock)
        identities = common.tool_identities(magic, netgen, lock)

        build_parent = ROOT / "spice" / "build"
        build_parent.mkdir(parents=True, exist_ok=True)
        build = Path(tempfile.mkdtemp(prefix="ihp_sg13g2_bitcell.", dir=build_parent))

        rom = measure_rom_bitcell(contract, magic, variant, pdk, build)
        sram = measure_sram_bitcells(contract, variant)
        drc = sram_bitcell_drc(contract, magic, variant, pdk, build)
        efficiency = sram_array_efficiency(sram)

        technology = common.strict_json(ROOT / "configs" / "hardware" / "technology.json")
        assumed = float(technology["rom"]["cell_to_sram_cell_area_ratio"]["value"])
        measured = rom["cell_area_um2"] / sram["1P"]["cell_area_um2"]

        destination = repository_path(contract["reports"]["artifacts"])
        destination.mkdir(parents=True, exist_ok=True)
        artifacts = []
        for name in (
            "ihp_rom_bitarray.mag",
            "ihp_rom_bitarray.gds",
            "ihp_rom_bitarray.extracted.spice",
            "ihp_rom_bitarray.pex.spice",
            "programmed_bits.txt",
            "magic.log",
        ):
            source = build / "rom_nominal" / name
            if source.is_file():
                shutil.copy2(source, destination / name)
                artifacts.append(
                    {
                        "path": (destination / name).relative_to(ROOT).as_posix(),
                        "sha256": common.sha256_file(destination / name),
                        "size_bytes": (destination / name).stat().st_size,
                        "hash_stability": (
                            "archival identity only; NOT reproducible across runs. See "
                            "rom_bitcell.canonical_digests for the digests a repeat run "
                            "must reproduce."
                        ),
                    }
                )

        result = {
            "schema_version": 1,
            "experiment_id": contract["experiment_id"],
            "status": "pass",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "contract": {
                "path": CONTRACT_PATH.relative_to(ROOT).as_posix(),
                "sha256": common.sha256_file(CONTRACT_PATH),
            },
            "inputs": {
                name: {
                    "path": value,
                    "sha256": common.sha256_file(repository_path(value)),
                    "size_bytes": repository_path(value).stat().st_size,
                }
                for name, value in sorted(contract["inputs"].items())
            },
            "pdk": pdk_identity,
            "toolchain": identities,
            "rom_bitcell": rom,
            "sram_bitcell": sram,
            "sram_bitcell_drc": drc,
            "sram_array_efficiency": efficiency,
            "array_efficiency_reference": {
                "assumed": float(technology["rom"]["array_efficiency"]["value"]),
                "assumed_grade": technology["rom"]["array_efficiency"]["grade"],
                "assumed_source": "configs/hardware/technology.json#rom.array_efficiency",
                "note": (
                    "the measured column is a foundry SRAM macro's own array efficiency at "
                    "130 nm, not a ROM macro's; a ROM macro has no write drivers, no write "
                    "assist and no BIST, so its efficiency at equal capacity should be higher"
                ),
            },
            "ratio": {
                "measured": measured,
                "assumed": assumed,
                "assumed_source": "configs/hardware/technology.json#rom.cell_to_sram_cell_area_ratio",
                "measured_over_assumed": measured / assumed,
                "dual_port_reference_ratio": rom["cell_area_um2"] / sram["2P"]["cell_area_um2"],
                "direction_of_bias": "upper bound: the ROM cell is logic-rule legal, the SRAM cell is not",
            },
            "artifacts": artifacts,
            "claim_boundary": contract["claim_boundary"],
            "reports": dict(contract["reports"]),
        }
        # Optional cross-node reference. It is a POINTER, never an input: no value
        # from a predictive PDK enters any number this runner computes.
        sibling_path = (
            ROOT / "results" / "asap7_physical" / "bitcell_density" / "bitcell_density.json"
        )
        if sibling_path.is_file():
            sibling = json.loads(sibling_path.read_text(encoding="utf-8"))
            measurement = sibling.get("measurement", {})
            if "ratio_via_programmed_rom_to_sram" in measurement:
                result["node_sensitivity"] = {
                    "node": sibling.get("node", "ASAP7 predictive 7 nm"),
                    "ratio": measurement["ratio_via_programmed_rom_to_sram"],
                    "source": sibling_path.relative_to(ROOT).as_posix(),
                    "evidence_class": sibling.get("evidence_class"),
                    "never": "these two ratios must not be averaged, blended or interpolated",
                    # What the disagreement costs, in the model's own primitive.
                    # ROM capacity density is 1e6 / (sram_cell_um2 * ratio /
                    # array_efficiency), so at a fixed SRAM cell and a fixed
                    # array efficiency it is inversely proportional to the
                    # ratio and every other term cancels. This quotient is
                    # therefore EXACT and needs no node-specific input --
                    # which is precisely why it is computed here rather than
                    # written out by hand in a document, where it would be an
                    # unchecked second derivation of the same arithmetic.
                    # The headline of docs/ROM_DENSITY_NODE_TRANSFER.md, computed
                    # rather than written down. It appeared in three documents as
                    # a hand-arithmetic "92.7%" with nothing able to check it.
                    "relative_disagreement": (
                        measurement["ratio_via_programmed_rom_to_sram"] / measured - 1.0
                    ),
                    "capacity_density_factor_this_node_over_sibling": (
                        measurement["ratio_via_programmed_rom_to_sram"]
                        / measured
                    ),
                    "capacity_density_factor_note": (
                        "ROM bits/mm2 is inversely proportional to this ratio at a fixed "
                        "SRAM bitcell area and a fixed array efficiency, so a model built "
                        "on the 130 nm ratio claims this factor MORE ROM capacity per mm2 "
                        "than the same model built on the predictive FinFET ratio. It is a "
                        "quotient of two measured ratios and is exact; it is NOT a "
                        "statement about any target node's absolute density, and neither "
                        "input may be labelled an N7/N6/N5/N4 value"
                    ),
                }
                rom_units = measurement.get("rom_via_area_in_cpp_x_finpitch_units")
                sram_units = measurement.get("sram_area_in_cpp_x_finpitch_units")
                if rom_units and sram_units:
                    result["node_sensitivity"]["admissible_ratio_ladder"] = (
                        finfet_ratio_ladder(int(rom_units), int(sram_units))
                    )
        json_path = repository_path(contract["reports"]["json"])
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        repository_path(contract["reports"]["markdown"]).write_text(
            markdown_report(result), encoding="utf-8"
        )
        print(
            "PASS: IHP SG13G2 bitcell ratio measured; "
            f"ROM {rom['cell_area_um2']:.6f} um2 / SRAM {sram['1P']['cell_area_um2']:.6f} um2 "
            f"= {measured:.4f} (assumed {assumed})"
        )
        return 0
    except (BitcellError, common.PhysicalExperimentError, OSError, subprocess.SubprocessError) as exc:
        print(f"FAIL: {exc}")
        return 1
    finally:
        if build is not None and build.exists():
            if args.keep_build:
                print(f"Kept build directory: {build}")
            else:
                shutil.rmtree(build, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
