"""Project planned SRAM instance names through the exact Yosys elaboration."""

from collections import defaultdict
import json
from pathlib import Path
import re
import tempfile

EXPECTED = "native_sram_expected.json"
RECEIPT = "native_sram_paths.json"
SCRIPTS = ("macro_place.tcl", "pdn.tcl")
BODY = "# BEGIN PLANNED SCRIPT FOR STATIC PREFLIGHT\n"
_GENERATED = re.compile(r"genblk[0-9]+")
_PLACE = re.compile(r"(?m)^([ \t]*place_macro[ \t]+-macro_name[ \t]+\{)([^}\n]+)(\})")


def normal(name):
    return name.lstrip("\\").replace(r"\[", "[").replace(r"\]", "]")


def _parts(path):
    return tuple(p for p in path.split(".") if not _GENERATED.fullmatch(p))


def _instance_names(modules, top, expected):
    names = {_parts(p) for p in expected}
    prefixes = {path[:i] for path in names for i in range(1, len(path))}
    hits = defaultdict(dict)

    def visit(module, prefix, active):
        if module in active:
            raise ValueError(f"recursive native hierarchy at {module}")
        for inst, cell in modules[module].get("cells", {}).items():
            path = prefix + normal(inst)
            key = _parts(path)
            master = cell["type"]
            definition = modules.get(master, {})
            if key in names:
                if path in hits[key]:
                    raise ValueError(f"ambiguous native path spelling {path}")
                original = definition.get("attributes", {}).get("hdlname", master).split()
                hits[key][path] = (master, original[0].lstrip("\\") if original else master)
            if key in prefixes and definition.get("cells"):
                visit(master, path + ".", active | {module})

    if top not in modules:
        raise ValueError(f"native elaboration has no top {top}")
    visit(top, "", set())
    return hits


def resolve(design, top, declarations):
    expected = {normal(row["inst"]): row["master"] for row in declarations}
    if not expected or len(expected) != len(declarations):
        raise ValueError("planned macro inventory is empty or has duplicate names")
    hits = _instance_names(design["modules"], top, expected)
    selected = {}
    for inst, master in expected.items():
        key = _parts(inst)
        group = hits[key]
        if inst in group:
            if master not in group[inst]:
                raise ValueError(f"{inst} has native master {group[inst][0]}, expected {master}")
            selected[inst] = inst
            continue
        if not master.startswith("ot_sram_") or tuple(inst.split(".")) != key:
            raise ValueError(f"{inst} ({master}) has no exact native path")
        matches = [p for p, actual in group.items() if master in actual]
        if len(matches) != 1:
            raise ValueError(f"{inst} ({master}) needs exactly one native auto-generate match, found {len(matches)}")
        selected[inst] = matches[0]
    if len(set(selected.values())) != len(selected):
        raise ValueError("multiple planned macro keys resolve to the same native instance")
    return selected


def _odb(name):
    return name.replace("[", r"\[").replace("]", r"\]")


def _pg_pattern(name):
    return "{^" + re.sub(r"([.\[\]()*+?^$|\\])", r"\\\1", _odb(name)) + "$}"


def wrapper(name, body):
    native = name.removesuffix(".tcl") + "_native.tcl"
    return (f'if {{![file exists /work/{RECEIPT}]}} {{ error "Missing native SRAM macro projection" }}\n'
            f"source /work/{native}\nreturn\n{BODY}{body}")


def project(placement, pdn, selected):
    keys = [normal(m.group(2)) for m in _PLACE.finditer(placement)]
    if len(keys) != len(selected) or set(keys) != selected.keys():
        raise ValueError("native projection does not cover the exact generated placement inventory")
    aliases = {a: b for a, b in selected.items() if a != b}

    def place(m):
        old = normal(m[2])
        return m[1] + _odb(aliases[old]) + m[3] if old in aliases else m[0]

    placement = _PLACE.sub(place, placement)
    for old, new in aliases.items():
        pdn = pdn.replace(_pg_pattern(old), _pg_pattern(new))
    for label, text in zip(SCRIPTS, (placement, pdn)):
        plain = text.replace("\\", "")
        if any(old in plain for old in aliases):
            raise ValueError(f"unsupported stale macro reference in {label}")
    return placement, pdn


def _write(path, text):
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False) as output:
        output.write(text)
    partial = Path(output.name)
    partial.chmod(0o644)
    partial.replace(path)


def apply(kit, design, top):
    declarations = json.loads((kit / EXPECTED).read_text())
    selected = resolve(design, top, declarations)
    body = []
    for name in SCRIPTS:
        _, separator, text = (kit / name).read_text().partition(BODY)
        if not separator:
            raise ValueError(f"{name} lacks its native SRAM projection wrapper")
        body.append(text)
    aliases = {a: b for a, b in selected.items() if a != b}
    if aliases:
        supported = set(SCRIPTS) | {n.removesuffix(".tcl") + "_native.tcl" for n in SCRIPTS}
        for path in kit.iterdir():
            if path.name not in supported and path.suffix in {".tcl", ".sdc"}:
                if path.is_file() and any(a in path.read_text().replace("\\", "") for a in aliases):
                    raise ValueError(f"unsupported native macro consumer {path.name}")
    scripts = project(*body, selected)
    report = {"top": top, "expected": len(declarations), "matched": len(selected), "aliases": aliases}
    for name, text in zip(SCRIPTS, scripts):
        _write(kit / (name.removesuffix(".tcl") + "_native.tcl"), text)
    _write(kit / RECEIPT, json.dumps(report, indent=1) + "\n")
    return report
