"""Narrow HWIN sizing evidence; never a substitute for placed occupancy.

The source area remains the measured source area. A ROOT reviewed receipt may
reuse the actual clock/repair population of the identical native source only
while planning its band. The placed-cell checker does not call this module.
"""

import collections
import gzip
import hashlib
import json
import math
import re
from pathlib import Path


TOP = "dsdv_mu_hwin_capture_1019"
MAPPED_SHA256 = "4ea21c9bb75a199a0ade71fb740fb740fced289a3c7c83d4ac02a474d89099c2"
SOURCE_CELLS = 59580
SOURCE_IDENTITIES = "05ca8a08f601188f05442910fe1d0a3fcd0283c22a87a82d2e5e5740b78b2040"
SOURCE_MASTERS = "23d964fe5003d91f7e6e602803b525dc0ec0bf792c6982660ce0e7412a67d0c4"
SOURCE_AREA = 9151.137
NATIVE_SOURCE_AREA = 8964.76086
CTS_CELLS = 82834
CTS_AREA = 11063.90178
CTS_IDENTITIES = "d125e8bba132bf348875d8d18d03ee87f569a229e2de2c15e5d5ac213779bc56"
CTS_MASTERS = "2e45099c3c4aff67ddb05e619b4a09ca668c7eadb114581eb6094445fa88c33c"
SCHEMA = "opentallas.hwin.planning_birth_budget.v1"


def source_contract(spec):
    fields = ("top", "sources", "params", "defines", "pin_regs", "reset_landing",
              "reset_relays", "clock_port", "reset_ports", "recipe", "inhold", "outhold",
              "keep_pin_regs", "pin_reg_split", "io_flop_at_pins", "reset_relay_split",
              "kind", "clock", "clock_ports", "hold_budget", "hold_pad",
              "pin_hook_before_flops", "pin_hook_after_flops")
    result = {k: spec.get(k) for k in fields}
    result["synth_keep_modules"] = (spec.get("route") or {}).get("synth_keep_modules")
    # Only the candidate's placement fences may change. Other ORFS overrides
    # can change the elaborated/mapped source and cannot inherit this budget.
    placement_hooks = {"PRE_GLOBAL_PLACE_TCL", "PRE_GLOBAL_PLACE_SKIP_IO_TCL", "PRE_DETAIL_PLACE_TCL"}
    result["source_orfs_vars"] = {k: v for k, v in (spec.get("orfs_vars") or {}).items()
                                  if k not in placement_hooks}
    return result


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(label + " must be a finite number")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(label + " must be finite") from exc
    if not math.isfinite(value):
        raise ValueError(label + " must be a finite number")
    return value


def _equal(value, expected, label):
    value = _number(value, label)
    if abs(value - expected) > 0.0001:
        raise ValueError(label + " differs from the approved measured inventory")
    return value


def _path(root, name):
    if not isinstance(name, str) or not name:
        raise ValueError("missing repository-relative evidence path")
    p = Path(name)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("evidence path must be repository relative")
    p = (root / p).resolve()
    if not p.is_relative_to(root):
        raise ValueError("evidence path escapes repository")
    return p


def _read(root, record, *, json_data=True):
    if not isinstance(record, dict):
        raise ValueError("missing evidence record")
    p = _path(root, record.get("path", ""))
    raw = p.read_bytes()
    sha = record.get("sha256")
    if not isinstance(sha, str) or len(sha) != 64 or hashlib.sha256(raw).hexdigest() != sha:
        raise ValueError("evidence SHA256 mismatch: " + str(record.get("path")))
    data = gzip.decompress(raw) if p.suffix == ".gz" else raw
    if not json_data:
        return data
    value = json.loads(data)
    if not isinstance(value, dict):
        raise ValueError("evidence JSON must be an object")
    return value


def _population(data, count, area, label, *, identities=None, master_digest=None):
    if data.get("schema") != "opentallas.native_master_population.v1":
        raise ValueError(label + " census schema")
    cells, masters = data["cells"], data["masters"]
    if not isinstance(cells, list) or not isinstance(masters, dict) or any(not isinstance(r, list) or len(r) != 2 for r in cells):
        raise ValueError(label + " malformed cell/master census")
    if len(cells) != count or len({r[0] for r in cells}) != count:
        raise ValueError(label + " cell identity/count mismatch")
    if identities and hashlib.sha256(json.dumps(sorted(cells), separators=(",", ":")).encode()).hexdigest() != identities:
        raise ValueError(label + " exact mapped cell identities changed")
    counts = collections.Counter()
    for name, master in cells:
        if not isinstance(name, str) or not name or master not in masters:
            raise ValueError(label + " missing cell/master identity")
        counts[master] += 1
    if set(counts) != set(masters):
        raise ValueError(label + " stale master census")
    total = 0.0
    for master, record in masters.items():
        size = _number(record["area_um2"], label + " master area")
        if size <= 0 or type(record["count"]) is not int or record["count"] != counts[master]:
            raise ValueError(label + " master area/count mismatch")
        total += size * counts[master]
    _equal(total, area, label + " native area")
    digest = hashlib.sha256(json.dumps(masters, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    if master_digest and digest != master_digest:
        raise ValueError(label + " exact mapped master census changed")
    return digest


def planning_area(spec, source_area, root):
    """Return the verified sizing budget, or reject; no callers may use it after placement."""
    if root is None:
        raise ValueError("planning receipt verification needs repository root")
    root = Path(root).resolve()
    approval = spec.get("planning_birth_budget")
    if (not isinstance(approval, dict) or approval.get("approved_by") != "ROOT"
            or not isinstance(approval.get("why"), str) or not approval["why"].strip()):
        raise ValueError("missing ROOT planning-only approval/reason")
    receipt = _read(root, approval)
    if (receipt.get("schema") != SCHEMA or receipt.get("scope") != "PLANNING_ONLY"
            or spec.get("top") != TOP or receipt.get("top") != TOP):
        raise ValueError("unsupported planning-only source/schema")
    _equal(source_area, SOURCE_AREA, "source area argument")
    _equal(spec.get("std_area_um2"), SOURCE_AREA, "source std_area_um2")
    _equal(receipt.get("source_std_area_um2"), SOURCE_AREA, "receipt source area")
    budget = _equal(spec.get("planning_std_area_um2"), CTS_AREA, "planning area")
    _equal(receipt.get("previous_cts_area_um2"), CTS_AREA, "receipt CTS area")
    if not source_area < budget <= source_area * 1.25:
        raise ValueError("planning area exceeds the narrow measured budget")
    previous = _read(root, receipt["previous_spec"])
    if source_contract(spec) != source_contract(previous):
        raise ValueError("source contract/parameters differ from measured source")
    _equal(previous.get("std_area_um2"), SOURCE_AREA, "previous source area")
    gate = _read(root, receipt["previous_gate"])
    binding = gate["source_binding"]
    if (gate.get("cts") is not True or binding.get("schema") != "opentallas.ref_tile.source_snapshot.v1"
            or binding.get("identity") != "exact_content_snapshot"
            or binding.get("start_commit") != receipt.get("source_commit")
            or not re.fullmatch(r"[0-9a-f]{40}", str(receipt.get("source_commit", "")))):
        raise ValueError("previous CTS source provenance is not exact")
    snapshot = {r["path"]: r["sha256"] for r in binding["files"]}
    if snapshot.get(receipt["previous_spec_source_path"]) != receipt["previous_spec"]["sha256"]:
        raise ValueError("previous spec is not in the exact source snapshot")
    views = sorted({m["view"] for m in spec.get("macros", [])})
    instances = lambda s: collections.Counter((m["view"], m.get("inst")) for m in s.get("macros", []))
    if not views or instances(spec) != instances(previous):
        raise ValueError("macro master identities changed")
    expected_files = set(spec.get("sources", [])) | {
        p for p in snapshot if any(p.startswith(view + "/") for view in views)}
    source_files = receipt["source_files"]
    if set(source_files) != expected_files:
        raise ValueError("source/master file inventory incomplete")
    for path, sha in source_files.items():
        if snapshot.get(path) != sha or hashlib.sha256(_path(root, path).read_bytes()).hexdigest() != sha:
            raise ValueError("current source/master differs from measured source: " + path)
    netlist = _read(root, receipt["mapped_netlist"], json_data=False)
    if hashlib.sha256(netlist).hexdigest() != MAPPED_SHA256:
        raise ValueError("mapped source netlist changed")
    native = _read(root, receipt["native_census"])
    if (native.get("schema") != "opentallas.pre_gate_native_census.v1"
            or native.get("status") != "PASS" or native.get("top") != TOP
            or native.get("netlist", {}).get("sha256") != MAPPED_SHA256
            or native.get("limit") != 32 or native.get("max_dynamic_loads") != 32
            or native.get("roots_examined") != 49488
            or native.get("role_errors") != [] or native.get("violations") != []):
        raise ValueError("mapped native source census is not the approved PASS")
    master_digest = _population(_read(root, receipt["source_population"]), SOURCE_CELLS,
                                NATIVE_SOURCE_AREA, "source", identities=SOURCE_IDENTITIES,
                                master_digest=SOURCE_MASTERS)
    if master_digest != receipt.get("source_master_sha256"):
        raise ValueError("source master identity changed")
    _population(_read(root, receipt["cts_population"]), CTS_CELLS, CTS_AREA, "CTS",
                identities=CTS_IDENTITIES, master_digest=CTS_MASTERS)
    measured = gate.get("measured_band_fill") or {}
    if measured.get("valid") is not True or measured.get("errors") != []:
        raise ValueError("previous CTS actual cell/row census invalid")
    _equal(measured.get("std_area_um2"), CTS_AREA, "previous CTS actual occupancy")
    return budget


def evidence_paths(spec, root):
    """The exact receipt inputs must travel with both gate and route snapshots."""
    planning_area(spec, spec.get("std_area_um2"), root)
    approval = spec["planning_birth_budget"]
    receipt = _read(Path(root).resolve(), approval)
    return sorted({approval["path"], *(receipt[k]["path"] for k in (
        "previous_spec", "previous_gate", "mapped_netlist", "native_census",
        "source_population", "cts_population"))})
