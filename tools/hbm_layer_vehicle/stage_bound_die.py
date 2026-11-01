#!/usr/bin/env python3
"""Stage a binder's whole HBM die for simulation; preserve unresolved source obligations.

This is source bring-up, not a token-pass receipt. Failed bind reports and native_required
ports are retained. Missing files or ambiguous module choices are reported explicitly.
"""
import argparse
import collections
import hashlib
import json
from pathlib import Path
import re
import shutil

MOD = re.compile(r"\bmodule\s+(?:automatic\s+)?(\w+)")
INST = re.compile(r"^\s*([A-Za-z_]\w*)\s*(?:#\s*\(.*?\)\s*)?([A-Za-z_]\w*)\s*\(", re.M | re.S)
KW = set("module if else for always assign wire reg input output logic begin end case generate function task initial localparam parameter return while foreach assert property typedef genvar integer bit int string".split())


def stripped(path):
    text = path.read_text(errors="replace")
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def stage(bind, repo, out):
    if out.exists():
        raise ValueError("Use a new output directory; existing builds are preserved")
    out.mkdir(parents=True)
    shutil.copytree(bind / "rtl", out / "bound")
    shutil.copy2(bind / "bind_report.json", out / "bind_report.json")
    report = json.loads((bind / "bind_report.json").read_text())
    selected, missing_files, replacements = [], [], []
    for line in (bind / "bind.f").read_text().splitlines():
        path = Path(line)
        if not line.strip() or line.startswith("+"):
            continue
        if path.is_relative_to(bind / "rtl"):
            selected.append(out / "bound" / path.relative_to(bind / "rtl"))
        elif path.is_file():
            target = out / "external" / (hashlib.sha256(line.encode()).hexdigest()[:12] + "_" + path.name)
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(path, target)
            selected.append(target)
        else:
            # Old source worktrees may have been retired. Make the substitution visible.
            candidates = [repo / root / line.split("/" + root + "/", 1)[1]
                          for root in ("rtl", "physical", "results") if "/" + root + "/" in line]
            candidates = [p for p in candidates if p.is_file()]
            if len(candidates) == 1:
                selected.append(candidates[0])
                replacements.append(dict(old=line, current=str(candidates[0])))
            else:
                missing_files.append(line)
    definitions = collections.defaultdict(list)
    roots = [repo / "rtl", repo / "physical/asap7_memory_macros", repo / "physical/asap7_memory_macros_v2", repo / "physical/die_plan/hbm/bind"]
    for root in roots:
        for path in root.rglob("*"):
            if path.suffix not in (".sv", ".v") or path.name.endswith("_bb.v"):
                continue
            for module in MOD.findall(stripped(path)):
                definitions[module].append(path)
    have, defined, used, users, ambiguous = set(selected), set(), set(), {}, {}
    queue = list(selected)
    while queue:
        path = queue.pop()
        text = stripped(path)
        defined.update(MOD.findall(text))
        for module, instance in INST.findall(text):
            if module not in KW and instance not in KW:
                used.add(module)
                users.setdefault(module, path)
        if queue:
            continue
        for module in sorted(used - defined):
            choices = definitions.get(module, [])
            if not choices:
                continue
            choices = sorted(choices, key=lambda p: ("/test/" in str(p), "/tb_" in str(p), "/pinned/" in str(p), len(str(p)), str(p)))
            choice = choices[0]
            if len(choices) > 1:
                ambiguous[module] = dict(chosen=str(choice), candidates=list(map(str, choices)), user=str(users[module]))
            if choice not in have:
                have.add(choice)
                selected.append(choice)
                queue.append(choice)
    missing_modules = sorted(used - defined)
    selected = list(dict.fromkeys(selected))
    # Files carrying defines precede users; source -v libraries still resolve transitively.
    defines = [p for p in selected if "`define" in p.read_text(errors="replace")]
    filelist = [str(p) for p in defines] + ["-v " + str(p) for p in selected if p not in defines]
    filelist += ["+incdir+" + str(p) for p in sorted({p.parent for p in selected})]
    (out / "sim.f").write_text("\n".join(filelist) + "\n")
    top = next((p for p in (out / "bound").glob("*_bound_top.sv")), None)
    ports = [] if top is None else re.findall(r"input\s+wire\s*(?:\[[^]]+\]\s*)?(native_required_\w+)", top.read_text())
    result = dict(scope="Whole-die source bring-up only; no numeric G5 claim", bind=str(bind), bind_errors=report.get("n_errors"), files=len(selected), missing_files=missing_files, current_source_substitutions=replacements, ambiguous=ambiguous, missing_modules=missing_modules, native_required_ports=ports, top=str(top))
    (out / "staging.json").write_text(json.dumps(result, indent=1) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k not in ("ambiguous", "native_required_ports")}))
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bind", type=Path, required=True)
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    stage(args.bind.resolve(), args.repo.resolve(), args.out.resolve())
