#!/usr/bin/env python3
"""Prove the ABI 3.0 control-plane RTL elaborates under the pinned synthesis front ends.

[OI-43] in ``docs/UNIFIED_EXECUTION_CHECKLIST.md``: the pinned Yosys Verilog
frontend rejects ``import pkg::*`` in a module header and in a module body
alike (``syntax error, unexpected TOK_IMPORT``), so every control-plane block
that carried a wildcard package import could be simulated but never
synthesised or routed by this toolchain.  The fix is ``pkg::name`` references.
This tool is the evidence that the fix landed: it elaborates each block, on
its own, under

* the pinned local Yosys (``tools/run_abi3_physical.py``'s ``YOSYS``, the
  sky130hd synthesis path), and
* the Yosys inside the pinned OpenROAD-flow-scripts image (the asap7 path),
  with the repository mounted read-only at ``/src`` exactly as that flow
  mounts it,

and records, per front end and per block, the return code, every ERROR line,
every Warning line and the ``check`` problem count.  Optionally the same
checks run against ``git archive`` of a baseline commit so the artifact
carries the failure it retires beside the pass that retires it.

Elaboration only: ``hierarchy -top``, ``proc``, ``check``.  No technology
mapping, no timing, no area.  A Yosys memory-to-register note is recorded as
the warning it is, not waived and not counted as a failure.

The artifact records the SHA-256 of every source file read, the identity of
every tool and image, the git commit and whether the tree was dirty.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import run_abi3_physical as physical  # noqa: E402

DEFAULT_OUTPUT = ROOT / "results/rtl/abi3_control_plane_yosys_elaboration.json"
SCHEMA = "opentallas.rtl.abi3_control_plane_yosys_elaboration.v1"

PACKAGES = {
    "ot_a3_pkg": "rtl/abi3/ot_a3_pkg.sv",
    "ot_a3_link_pkg": "rtl/abi3/ot_a3_link_pkg.sv",
    "ot_fp32_rne_pkg": "rtl/ot_fp32_rne_pkg.sv",
}

# The eight blocks [OI-43] names plus the asynchronous front end's five and
# the device top, each with the packages it references by scope and the
# blocks it instantiates.  Order is dependency order.
BLOCKS: tuple[dict[str, Any], ...] = (
    {"top": "ot_a3_program_header", "packages": ["ot_a3_pkg"], "instantiates": []},
    {"top": "ot_a3_instruction_decoder", "packages": ["ot_a3_pkg"], "instantiates": []},
    {"top": "ot_a3_event_scoreboard", "packages": ["ot_a3_pkg"], "instantiates": []},
    {"top": "ot_a3_loop_stack", "packages": ["ot_a3_pkg"], "instantiates": []},
    {"top": "ot_a3_state_controller", "packages": ["ot_a3_pkg"], "instantiates": []},
    {"top": "ot_a3_view_resolver", "packages": ["ot_a3_pkg"], "instantiates": []},
    # The asynchronous front end (docs/CHIP_ARCHITECTURE_DESIGN.md section
    # 11.4 item 4, second half): the shared divider, the symbol file, the
    # six-lane resolver bank, the issue record store and the dependence table.
    {"top": "ot_a3_shared_divider", "packages": ["ot_a3_pkg"], "instantiates": []},
    {"top": "ot_a3_symbol_file", "packages": ["ot_a3_pkg"], "instantiates": []},
    {"top": "ot_a3_issue_record_store", "packages": ["ot_a3_pkg"], "instantiates": []},
    {"top": "ot_a3_dependence_table", "packages": ["ot_a3_pkg"], "instantiates": []},
    {
        "top": "ot_a3_resolver_bank",
        "packages": ["ot_a3_pkg"],
        "instantiates": ["ot_a3_view_resolver"],
    },
    {
        "top": "ot_a3_microsequencer",
        "packages": ["ot_a3_pkg"],
        "instantiates": [
            "ot_a3_event_scoreboard",
            "ot_a3_instruction_decoder",
            "ot_a3_shared_divider",
            "ot_a3_symbol_file",
            "ot_a3_loop_stack",
            "ot_a3_state_controller",
            "ot_a3_view_resolver",
            "ot_a3_resolver_bank",
            "ot_a3_issue_record_store",
            "ot_a3_dependence_table",
        ],
    },
    {
        "top": "ot_a3_device_top",
        "packages": ["ot_a3_pkg"],
        "instantiates": [
            "ot_a3_program_header",
            "ot_a3_event_scoreboard",
            "ot_a3_instruction_decoder",
            "ot_a3_shared_divider",
            "ot_a3_symbol_file",
            "ot_a3_loop_stack",
            "ot_a3_state_controller",
            "ot_a3_view_resolver",
            "ot_a3_resolver_bank",
            "ot_a3_issue_record_store",
            "ot_a3_dependence_table",
            "ot_a3_microsequencer",
        ],
    },
    {
        "top": "ot_a3_collective_engine",
        "packages": ["ot_a3_link_pkg", "ot_fp32_rne_pkg"],
        "instantiates": [],
    },
)

ERROR_RE = re.compile(r"\bERROR:")
WARNING_RE = re.compile(r"^Warning:")
CHECK_RE = re.compile(r"Found and reported (\d+) problems")
IMPORT_RE = re.compile(r"^\s*import\s+[A-Za-z_]\w*::", re.M)


def block_sources(block: dict[str, Any]) -> list[str]:
    """Repository-relative sources, packages first, top last."""
    sources = [PACKAGES[name] for name in block["packages"]]
    sources += [f"rtl/abi3/{name}.sv" for name in block["instantiates"]]
    sources.append(f"rtl/abi3/{block['top']}.sv")
    return sources


def yosys_script(block: dict[str, Any]) -> str:
    sources = " ".join(block_sources(block))
    return f"read_verilog -sv {sources}; hierarchy -top {block['top']}; proc; check"


def parse_log(returncode: int, log: str) -> dict[str, Any]:
    errors = [line.strip() for line in log.splitlines() if ERROR_RE.search(line)]
    warnings = [
        re.sub(r"\s+See .*$", "", line.strip())
        for line in log.splitlines()
        if WARNING_RE.match(line)
    ]
    check = CHECK_RE.search(log)
    problems = int(check.group(1)) if check else None
    ok = returncode == 0 and not errors and problems == 0
    return {
        "returncode": returncode,
        "ok": ok,
        "errors": errors,
        "warnings": sorted(set(warnings)),
        "warning_count": len(warnings),
        "check_problems": problems,
    }


def elaborate_local(block: dict[str, Any], tree: Path, yosys: Path = physical.YOSYS,
                    timeout: int = 1800) -> dict[str, Any]:
    """Elaborate one block with the pinned local Yosys from ``tree``."""
    proc = subprocess.run(
        [str(yosys), "-p", yosys_script(block)],
        cwd=str(tree),
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return parse_log(proc.returncode, (proc.stdout or "") + (proc.stderr or ""))


def elaborate_container(block: dict[str, Any], tree: Path, image: str = physical.ORFS_IMAGE,
                        timeout: int = 1800) -> dict[str, Any]:
    """Elaborate one block with the image's Yosys, ``tree`` mounted read-only at /src."""
    proc = subprocess.run(
        [
            "docker", "run", "--rm",
            "-v", f"{tree}:/src:ro",
            image, "bash", "-lc",
            f"cd /src && yosys -p {json.dumps(yosys_script(block))}",
        ],
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    return parse_log(proc.returncode, (proc.stdout or "") + (proc.stderr or ""))


def container_identity(image: str = physical.ORFS_IMAGE) -> dict[str, Any]:
    inspect = physical.run(["docker", "image", "inspect", image, "--format", "{{.Id}}"], timeout=300)
    physical.require_success(inspect, "docker image inspect")
    image_id = (inspect.stdout or "").strip()
    digests = physical.run(
        ["docker", "image", "inspect", image, "--format", "{{json .RepoDigests}}"], timeout=300
    )
    physical.require_success(digests, "docker image inspect digests")
    probe = physical.run(
        [
            "docker", "run", "--rm", image, "bash", "-lc",
            "echo YOSYS $(yosys -V 2>&1 | head -1); echo PATH $(command -v yosys); "
            "sha256sum $(command -v yosys)",
        ],
        timeout=600,
    )
    physical.require_success(probe, "container yosys probe")
    version = path = sha = ""
    for line in (probe.stdout or "").splitlines():
        if line.startswith("YOSYS "):
            version = line[len("YOSYS "):].strip()
        elif line.startswith("PATH "):
            path = line[len("PATH "):].strip()
        elif line.strip().endswith("yosys") and len(line.split()[0]) == 64:
            sha = line.split()[0]
    return {
        "image_reference": image,
        "image_id": image_id,
        "image_id_matches_archived_asap7_lock": image_id == physical.ORFS_EXPECTED_IMAGE_ID,
        "repo_digests": json.loads(digests.stdout or "[]"),
        "yosys": {"path": path, "version": version, "sha256": sha},
        "mount": "<ROOT>:/src:ro",
    }


def wildcard_imports(tree: Path) -> dict[str, list[int]]:
    """Line numbers of any wildcard package import in the eight blocks."""
    found: dict[str, list[int]] = {}
    for block in BLOCKS:
        path = f"rtl/abi3/{block['top']}.sv"
        lines = (tree / path).read_text(encoding="utf-8").splitlines()
        hits = [
            number
            for number, line in enumerate(lines, start=1)
            if not line.lstrip().startswith("//") and IMPORT_RE.match(line)
        ]
        if hits:
            found[path] = hits
    return found


def archive_tree(commit: str, into: Path) -> str:
    """``git archive`` of ``rtl/`` at ``commit``; returns the resolved SHA."""
    resolved = physical.run(["git", "rev-parse", "--verify", f"{commit}^{{commit}}"])
    physical.require_success(resolved, f"git rev-parse {commit}")
    sha = (resolved.stdout or "").strip()
    tar_path = into / "rtl.tar"
    with tar_path.open("wb") as handle:
        proc = subprocess.run(
            ["git", "archive", sha, "rtl"], cwd=str(ROOT), stdout=handle, check=False
        )
    if proc.returncode != 0:
        raise physical.FlowError(f"git archive {sha} failed")
    with tarfile.open(tar_path) as archive:
        archive.extractall(into)
    return sha


def run_front_ends(tree: Path, *, container: bool, blocks=BLOCKS) -> dict[str, Any]:
    results: dict[str, dict[str, Any]] = {"pinned_local": {}}
    if container:
        results["orfs_container"] = {}
    for block in blocks:
        top = block["top"]
        results["pinned_local"][top] = elaborate_local(block, tree)
        print(f"  pinned_local   {top}: {'ok' if results['pinned_local'][top]['ok'] else 'FAIL'}",
              file=sys.stderr)
        if container:
            results["orfs_container"][top] = elaborate_container(block, tree)
            print(f"  orfs_container {top}: {'ok' if results['orfs_container'][top]['ok'] else 'FAIL'}",
                  file=sys.stderr)
    return results


def build(baseline_commit: str | None, *, container: bool) -> dict[str, Any]:
    if not physical.YOSYS.exists():
        raise physical.FlowError(f"pinned yosys absent: {physical.YOSYS}")
    if container and shutil.which("docker") is None:
        raise physical.FlowError("docker is required for the container front end")

    sources = sorted({path for block in BLOCKS for path in block_sources(block)})
    front_ends: dict[str, Any] = {
        "pinned_local": {
            "role": "tools/run_abi3_physical.py YOSYS (sky130hd synthesis path)",
            "yosys": {
                **physical.tool_identity(physical.YOSYS, ["-V"]),
                "path": str(physical.YOSYS).replace(str(Path.home()), "<HOME>"),
            },
        }
    }
    if container:
        front_ends["orfs_container"] = {
            "role": "tools/run_abi3_physical.py ORFS image (asap7 place-and-route path)",
            **container_identity(),
        }
    else:
        front_ends["orfs_container"] = {"skipped": "--no-container"}

    print("current tree", file=sys.stderr)
    current = run_front_ends(ROOT, container=container)
    current_imports = wildcard_imports(ROOT)

    baseline: dict[str, Any] | None = None
    if baseline_commit:
        with tempfile.TemporaryDirectory(prefix="oi43-baseline-") as raw:
            tree = Path(raw)
            sha = archive_tree(baseline_commit, tree)
            print(f"baseline {baseline_commit} = {sha[:12]}", file=sys.stderr)
            baseline = {
                "requested": baseline_commit,
                "commit": sha,
                "wildcard_imports": wildcard_imports(tree),
                "results": run_front_ends(tree, container=container),
            }
            baseline["blocks_failing"] = {
                front_end: sorted(top for top, record in per_block.items() if not record["ok"])
                for front_end, per_block in baseline["results"].items()
            }

    ran = [name for name in current if current[name]]
    all_ok = all(record["ok"] for per_block in current.values() for record in per_block.values())
    status = "pass" if all_ok and not current_imports else "fail"

    return {
        "schema": SCHEMA,
        "campaign": "abi3_control_plane_yosys_elaboration",
        "issue": "OI-43 (docs/UNIFIED_EXECUTION_CHECKLIST.md)",
        "evidence_class": "public_open_tool_synthesis_frontend_elaboration",
        "canonical_timestamp_policy": "no timestamp in canonical artifact",
        "claim": (
            "each named block elaborates standalone (hierarchy -top, proc, check) under "
            "every front end listed in front_ends_run; nothing about mapping, timing or area"
        ),
        "git": physical.git_identity(),
        "blocks": [
            {
                "top": block["top"],
                "sources": block_sources(block),
                "yosys_script": yosys_script(block),
            }
            for block in BLOCKS
        ],
        "source_sha256": {path: physical.sha256_file(ROOT / path) for path in sources},
        "front_ends": front_ends,
        "front_ends_run": ran,
        "wildcard_imports": current_imports,
        "results": current,
        "baseline": baseline,
        "status": status,
        "limitations": [
            "Elaboration only: read_verilog -sv, hierarchy -top, proc, check. No synth, "
            "no technology mapping, no timing, no area, no place-and-route.",
            "The container Yosys and the pinned local Yosys are different releases; each is "
            "recorded as itself and neither stands in for the other.",
            "Yosys 'Replacing memory ... with list of registers' notes are recorded under "
            "warnings; they are structural observations, not waivers and not failures.",
            "The blocks are elaborated with their default parameters.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true", help="overwrite an existing artifact")
    parser.add_argument(
        "--baseline-commit",
        default=None,
        help="also elaborate git-archive of this commit and record its failures",
    )
    parser.add_argument(
        "--no-container",
        action="store_true",
        help="skip the OpenROAD-flow-scripts image front end (recorded as skipped)",
    )
    args = parser.parse_args(argv)

    if args.output.exists() and not args.force:
        print(f"refusing to overwrite {args.output}; pass --force to replace it", file=sys.stderr)
        return 2

    summary = build(args.baseline_commit, container=not args.no_container)
    physical.canonical_dump(summary, args.output)
    print(f"{args.output}: {summary['status']}", file=sys.stderr)
    return 0 if summary["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
