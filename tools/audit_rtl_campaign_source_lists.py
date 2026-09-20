#!/usr/bin/env python3
"""Every module and package a campaign's source list names, and the ones it omits.

A campaign hands an explicit list of files to iverilog and Verilator. Both refuse
a module they were never given -- ``%Error-MODMISSING: Cannot find file
containing module`` -- and Verilator resolves a package only from a file in the
list. So when the RTL grows an instantiation, every campaign whose list did not
follow it stops elaborating, and the failure reads like a campaign regression
rather than a stale list.

Measured on 2026-09-20: FIVE of the six ABI 3.0 campaigns could not elaborate at
HEAD. All of them build ``ot_a3_engine_array``, which now instantiates the
PIPELINED scaler, and none but the engine campaign listed it; all that build the
correctly-rounded transcendental were missing the three sequential primitives it
became; and ``ot_a3_wafer_multicast_adapter`` had moved to the CRC tree package.
Three separate walls, one cause.

So this derives what each list SHOULD contain from the files themselves -- the
modules they instantiate and the packages they name -- and reports the difference.
It is a parse, not an elaboration, which is the point: it runs in a second and can
gate, where finding this by elaboration costs a campaign launch each time.

Exit status is 1 if any campaign's list is incomplete.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "opentallas.derived.rtl_campaign_source_lists.v1"
TOOL = "tools/audit_rtl_campaign_source_lists.py"

#: Every tool that hands a fixed file list to a simulator.  A campaign absent
#: here is not checked, which the report says.
CAMPAIGNS = (
    "tools/rtl_abi3_engine_campaign.py",
    "tools/rtl_abi3_reduced_token_campaign.py",
    "tools/rtl_abi3_shipped_prefix_campaign.py",
    "tools/rtl_abi3_row_shard_campaign.py",
    "tools/rtl_abi3_shipped_prefix_multicast_campaign.py",
    "tools/run_a3_operator_admission_rtl_campaign.py",
    "tools/run_a3_qwen_gqa_rtl_campaign.py",
    "tools/run_a3_hc_transcendental_rtl_campaign.py",
)

_PKG_REF = re.compile(r"([A-Za-z_][A-Za-z0-9_$]*)\s*::")
_IMPORT = re.compile(r"(?m)^\s*import\s+([A-Za-z_][A-Za-z0-9_$]*)\s*::")


def _without_comments(text: str) -> str:
    out = list(text)
    index, end = 0, len(text)
    while index < end:
        if text.startswith("//", index):
            stop = text.find("\n", index)
            stop = end if stop < 0 else stop
            for position in range(index, stop):
                out[position] = " "
            index = stop
        elif text.startswith("/*", index):
            stop = text.find("*/", index + 2)
            stop = end if stop < 0 else stop + 2
            for position in range(index, stop):
                if out[position] != "\n":
                    out[position] = " "
            index = stop
        else:
            index += 1
    return "".join(out)


def _index_rtl() -> tuple[dict[str, str], dict[str, str]]:
    """``module -> file`` and ``package -> file`` over the whole tree."""
    modules: dict[str, str] = {}
    packages: dict[str, str] = {}
    for path in sorted((ROOT / "rtl").rglob("*.sv")):
        if "build" in path.relative_to(ROOT / "rtl").parts:
            continue
        try:
            text = _without_comments(path.read_text(encoding="utf-8"))
        except OSError:
            continue
        relative = str(path.relative_to(ROOT))
        for m in re.finditer(r"(?m)^\s*module\s+([A-Za-z_][A-Za-z0-9_$]*)", text):
            modules.setdefault(m.group(1), relative)
        for m in re.finditer(r"(?m)^\s*package\s+([A-Za-z_][A-Za-z0-9_$]*)", text):
            packages.setdefault(m.group(1), relative)
    return modules, packages


def _needs(files: list[str], known_modules: set[str]) -> tuple[set[str], set[str]]:
    """The modules instantiated and the packages named by ``files``."""
    instantiated: set[str] = set()
    named: set[str] = set()
    for relative in files:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = _without_comments(path.read_text(encoding="utf-8"))
        named.update(_IMPORT.findall(text))
        named.update(_PKG_REF.findall(text))
        #: ``name instance (`` and ``name #( ... ) instance (``.  Restricted to
        #: names the tree actually defines as modules, so a task call or a type
        #: is not mistaken for an instantiation.
        for m in re.finditer(
            r"(?m)^\s*([A-Za-z_][A-Za-z0-9_$]*)\s*(?:#\s*\(|[A-Za-z_])", text
        ):
            if m.group(1) in known_modules:
                instantiated.add(m.group(1))
    return instantiated, named


def _source_lists(module_path: str) -> dict[str, list[str]]:
    """Every tuple of ``.sv`` paths a campaign module defines at import time."""
    spec = importlib.util.spec_from_file_location("campaign_under_audit", ROOT / module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules["campaign_under_audit"] = module
    try:
        spec.loader.exec_module(module)
    except SystemExit:
        pass
    found: dict[str, list[str]] = {}
    for name in dir(module):
        value = getattr(module, name)
        if isinstance(value, tuple) and value and all(
            isinstance(v, str) for v in value
        ):
            paths = [v for v in value if v.endswith(".sv")]
            if paths:
                found[name] = paths
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "results/rtl/campaign_source_lists.json",
    )
    args = parser.parse_args()

    modules, packages = _index_rtl()
    known = set(modules)

    rows: list[dict] = []
    incomplete = 0
    for campaign in CAMPAIGNS:
        if not (ROOT / campaign).is_file():
            rows.append({"campaign": campaign, "status": "missing"})
            continue
        #: The UNION of the campaign's lists, because that is what reaches the
        #: simulator: several of these tools keep the bench files in a second
        #: tuple and concatenate at invocation, so checking each list alone
        #: reports a testbench as missing the device it instantiates.
        union: list[str] = []
        for _, files in sorted(_source_lists(campaign).items()):
            for relative in files:
                if relative not in union:
                    union.append(relative)
        for list_name, files in (("<union of all source tuples>", union),):
            defined: set[str] = set()
            defined_packages: set[str] = set()
            for relative in files:
                path = ROOT / relative
                if not path.is_file():
                    continue
                text = _without_comments(path.read_text(encoding="utf-8"))
                defined.update(
                    m.group(1)
                    for m in re.finditer(
                        r"(?m)^\s*module\s+([A-Za-z_][A-Za-z0-9_$]*)", text
                    )
                )
                defined_packages.update(
                    m.group(1)
                    for m in re.finditer(
                        r"(?m)^\s*package\s+([A-Za-z_][A-Za-z0-9_$]*)", text
                    )
                )
            instantiated, named = _needs(files, known)
            missing_modules = sorted(instantiated - defined)
            missing_packages = sorted(
                p for p in (named - defined_packages) if p in packages
            )
            if not missing_modules and not missing_packages:
                continue
            incomplete += 1
            rows.append(
                {
                    "campaign": campaign,
                    "source_list": list_name,
                    "files": len(files),
                    "missing_modules": [
                        {"module": m, "defined_in": modules[m]}
                        for m in missing_modules
                    ],
                    "missing_packages": [
                        {"package": p, "defined_in": packages[p]}
                        for p in missing_packages
                    ],
                }
            )

    report = {
        "schema": SCHEMA,
        "producer": {
            "tool": TOOL,
            "git": {
                "commit": subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout.strip()
            },
        },
        "campaigns_checked": len(CAMPAIGNS),
        "incomplete_list_count": incomplete,
        "incomplete": rows,
        "not_a_claim": [
            "this is a PARSE, not an elaboration: a module reached only through "
            "a generate construct the regex does not read would be missed, and a "
            "complete list here is not proof the campaign elaborates",
            "file ORDER is not checked; Verilator wants a package before its user",
            "the UNION of a campaign's source tuples is checked, not each tuple: "
            "the bench files usually live in a second tuple and are concatenated "
            "at invocation, so a per-tuple check reports false gaps",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(f"{len(CAMPAIGNS)} campaigns checked, {incomplete} incomplete source lists")
    for row in rows:
        if row.get("status") == "missing":
            print(f"  {row['campaign']}: not found")
            continue
        print(f"  {row['campaign']} :: {row['source_list']} ({row['files']} files)")
        for entry in row["missing_modules"]:
            print(f"      module  {entry['module']:42} -> {entry['defined_in']}")
        for entry in row["missing_packages"]:
            print(f"      package {entry['package']:42} -> {entry['defined_in']}")
    print(f"-> {args.output}")
    return 1 if incomplete else 0


if __name__ == "__main__":
    sys.exit(main())
