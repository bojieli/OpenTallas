#!/usr/bin/env python3
"""Authoritative measured scoreboard (regenerable).

Reads ONLY committed records named in results/arch/measured_scoreboard/spec.json
and writes results/arch/measured_scoreboard/scoreboard.json + README.md.

Every number in the output is read from a record at generation time; the spec
holds only (path, pointer) citations, never values.  A citation that no longer
resolves is reported as MISSING (and fails --check) instead of being filled in.
Derived ratios are computed only from resolved figures, and inherit the weakest
status of their inputs.

Pointer forms:
  "a.b[0].c"          dotted JSON path (keys containing dots: use a.["x.y"])
  "regex:<pattern>"   first capture group of the first match in a text file
  "sum:<list>|<field>" sum of <field> over the JSON list at pointer <list>
  "len:<list>"        length of the JSON list/object at pointer <list>

Usage:
  python3 tools/measured_scoreboard.py            # regenerate
  python3 tools/measured_scoreboard.py --check    # regenerate, exit 1 if any citation fails
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "results/arch/measured_scoreboard"
SPEC = OUT_DIR / "spec.json"

STATUS_RANK = {"measured": 0, "published": 0, "composed_from_measured": 1,
               "partial": 2, "off_target_context": 2, "modelled": 3, "unvalidated": 4}
TARGET_TITLES = {
    "qwen_rom": "Qwen3-8B ROM accelerator (8K context, P8191)",
    "ds_rom": "DeepSeek-V4.1 ROM accelerator (1M context, P1048575)",
    "hbm_qwen": "HBM accelerator - Qwen3-8B (8K context)",
    "hbm_ds": "HBM accelerator - DeepSeek-V4.1 (1M context)",
    "gpu_qwen": "GPU baseline - Qwen3-8B",
    "gpu_ds": "GPU baseline - DeepSeek-V4.1",
}
SECTION_TITLES = {
    "rate": "Per-user rate at target context",
    "terms": "Measured component terms",
    "collective": "Collectives",
    "physical": "Physical figures",
    "energy": "Energy / silicon",
    "ratios": "Ratios",
    "levers": "Lever figures",
}


class CiteError(Exception):
    pass


def _git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                              text=True, check=True).stdout.strip()
    except subprocess.CalledProcessError:
        return ""


_TOKEN = re.compile(r'\.?(?:\["((?:[^"\\]|\\.)*)"\]|\[(-?\d+)\]|([^.\[\]]+))')


def resolve_json(obj, pointer: str):
    pos = 0
    cur = obj
    while pos < len(pointer):
        m = _TOKEN.match(pointer, pos)
        if not m or m.end() == pos:
            raise CiteError(f"bad pointer syntax at {pointer[pos:]!r}")
        pos = m.end()
        key, idx, name = m.groups()
        try:
            if idx is not None:
                cur = cur[int(idx)]
            else:
                k = key if key is not None else name
                if isinstance(cur, list) and k.lstrip("-").isdigit():
                    cur = cur[int(k)]
                else:
                    cur = cur[k]
        except (KeyError, IndexError, TypeError) as exc:
            raise CiteError(f"pointer {pointer!r} fails at {m.group(0)!r}: {exc!r}")
    return cur


_cache: dict[str, object] = {}


def load(path: str):
    if path in _cache:
        return _cache[path]
    p = ROOT / path
    if not p.is_file():
        raise CiteError(f"record missing: {path}")
    text = p.read_text(errors="replace")
    data = text
    if p.suffix == ".json":
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise CiteError(f"unparseable JSON {path}: {exc}")
    _cache[path] = data
    return data


def _num(s):
    try:
        t = s.replace(",", "")
        return int(t) if re.fullmatch(r"-?\d+", t) else float(t)
    except (ValueError, AttributeError):
        return s


def cite(path: str, pointer: str):
    data = load(path)
    if pointer.startswith("regex:"):
        text = data if isinstance(data, str) else (ROOT / path).read_text()
        m = re.search(pointer[6:], text, re.M)
        if not m:
            raise CiteError(f"regex not found in {path}: {pointer[6:]!r}")
        return _num(m.group(1))
    if isinstance(data, str):
        raise CiteError(f"JSON pointer on non-JSON file {path}")
    if pointer.startswith("sum:"):
        lst, field = pointer[4:].rsplit("|", 1)
        items = resolve_json(data, lst)
        try:
            return round(sum(float(x[field]) for x in items), 6)
        except (KeyError, TypeError, ValueError) as exc:
            raise CiteError(f"sum {pointer!r} failed: {exc!r}")
    if pointer.startswith("len:"):
        return len(resolve_json(data, pointer[4:]))
    return resolve_json(data, pointer)


_provenance: dict[str, dict] = {}


def provenance(path: str) -> dict:
    if path not in _provenance:
        _provenance[path] = {
            "blob": _git("hash-object", path) if (ROOT / path).is_file() else None,
            "last_commit": _git("log", "-1", "--format=%h %cs", "--", path) or None,
        }
    return _provenance[path]


def weakest(statuses):
    return max(statuses, key=lambda s: STATUS_RANK.get(s, 9))


def build(spec: dict) -> dict:
    figures: dict[str, dict] = {}
    failures: list[dict] = []
    for e in spec["figures"]:
        fid = f'{e["target"]}.{e["key"]}'
        rec = {k: e[k] for k in ("target", "section", "key", "label", "unit",
                                 "status", "path", "pointer") if k in e}
        if e.get("note"):
            rec["note"] = e["note"]
        try:
            rec["value"] = cite(e["path"], e["pointer"])
            rec["resolved"] = True
            rec.update(provenance(e["path"]))
        except CiteError as exc:
            rec["value"] = None
            rec["resolved"] = False
            rec["error"] = str(exc)
            failures.append({"id": fid, "error": str(exc)})
        figures[fid] = rec

    for d in spec.get("derived", []):
        fid = f'{d["target"]}.{d["key"]}'
        ins = [figures.get(i) for i in d["inputs"]]
        rec = {"target": d["target"], "section": d.get("section", "ratios"),
               "key": d["key"], "label": d["label"], "unit": d.get("unit", "x"),
               "inputs": d["inputs"], "expr": d["expr"], "derived": True}
        if d.get("note"):
            rec["note"] = d["note"]
        if any(i is None or not i["resolved"] for i in ins):
            rec.update(value=None, resolved=False, status="unvalidated",
                       error="input figure missing or unresolved")
            failures.append({"id": fid, "error": rec["error"]})
        else:
            env = {f"x{n}": float(i["value"]) for n, i in enumerate(ins)}
            rec["value"] = round(eval(d["expr"], {"__builtins__": {}}, env), 4)
            rec["resolved"] = True
            rec["status"] = weakest([i["status"] for i in ins])
        figures[fid] = rec

    # qualitative lists: each item carries its own citation path; verify the path exists
    lists = {}
    for name in ("modelled_terms", "physical_blocks", "levers", "open_items",
                 "missing_baselines"):
        items = []
        for it in spec.get(name, []):
            it = dict(it)
            src = it.get("path")
            if src and not src.startswith("/"):
                it["path_exists"] = (ROOT / src).exists()
                if not it["path_exists"]:
                    failures.append({"id": f"{name}:{it.get('item') or it.get('block') or it.get('lever')}",
                                     "error": f"cited path missing: {src}"})
            elif src:
                it["path_exists"] = Path(src).exists()
            for fk in ("figures",):
                if fk in it:
                    it["figure_values"] = {f: figures.get(f, {}).get("value") for f in it[fk]}
            items.append(it)
        lists[name] = items

    return {
        "schema": "opentallas.measured_scoreboard.v1",
        "generated_from_commit": _git("rev-parse", "--short", "HEAD"),
        "rule": spec.get("rule"),
        "targets": {t: TARGET_TITLES.get(t, t) for t in spec.get("target_order", TARGET_TITLES)},
        "figures": figures,
        **lists,
        "citation_failures": failures,
    }


def fmt(v, unit="", resolved=False):
    if v is None:
        return "null (record holds no value)" if resolved else "**MISSING**"
    if isinstance(v, bool):
        return str(v)
    if isinstance(v, float):
        s = f"{v:,.4g}" if abs(v) < 1000 else f"{v:,.1f}"
    elif isinstance(v, int):
        s = f"{v:,}"
    else:
        s = str(v)
    return f"{s} {unit}".strip() if unit and unit != "-" else s


def render_md(sb: dict, spec: dict) -> str:
    L = []
    L.append("# Authoritative measured scoreboard")
    L.append("")
    L.append(f"Generated by `tools/measured_scoreboard.py` at source commit `{sb['generated_from_commit']}` "
             "from committed records only. Regenerate with `python3 tools/measured_scoreboard.py` "
             "(`--check` fails if any citation stops resolving). Citations live in `spec.json`; "
             "values are read from the records at generation time and are never stored in the spec.")
    L.append("")
    if sb.get("rule"):
        L.append(f"> {sb['rule']}")
        L.append("")
    L.append("Status legend: **measured** = RTL/hardware measurement at the target context; "
             "**composed_from_measured** = analytic composition whose every term is measured; "
             "**partial** = composition that still contains modelled terms (listed per target under "
             "'Still modelled'); **off_target_context** = measured, but not at the target context; "
             "**published** = vendor/third-party published figure; **modelled** / **unvalidated** = "
             "not yet backed by a measurement (listed, not a headline).")
    L.append("")
    if sb["citation_failures"]:
        L.append("## Citation failures")
        L.append("")
        for f in sb["citation_failures"]:
            L.append(f"- `{f['id']}`: {f['error']}")
        L.append("")

    # headline table
    L.append("## Headline (per-user decode, single token at target context)")
    L.append("")
    L.append("| Target | Figure | Value | Status | Record |")
    L.append("|---|---|---|---|---|")
    for fid in spec.get("headline", []):
        f = sb["figures"].get(fid)
        if not f:
            continue
        src = f.get("path") or " / ".join(f.get("inputs", []))
        L.append(f"| {f['target']} | {f['label']} | {fmt(f['value'], f.get('unit'), f.get('resolved'))} | {f['status']} | `{src}` |")
    L.append("")

    for t, title in sb["targets"].items():
        L.append(f"## {title}")
        L.append("")
        figs = [f for f in sb["figures"].values() if f["target"] == t]
        for sec, stitle in SECTION_TITLES.items():
            rows = [f for f in figs if f["section"] == sec]
            if not rows:
                continue
            L.append(f"### {stitle}")
            L.append("")
            L.append("| Figure | Value | Status | Record (pointer) |")
            L.append("|---|---|---|---|")
            for f in rows:
                if f.get("derived"):
                    src = f"= {f['expr']} over " + ", ".join(f"`{i}`" for i in f["inputs"])
                else:
                    src = f"`{f['path']}` (`{f['pointer']}`)"
                note = f" - {f['note']}" if f.get("note") else ""
                L.append(f"| {f['label']}{note} | {fmt(f['value'], f.get('unit'), f.get('resolved'))} | {f['status']} | {src} |")
            L.append("")
        mt = [m for m in sb["modelled_terms"] if m["target"] == t]
        if mt:
            L.append("### Still modelled / unvalidated terms (why a figure is `partial`)")
            L.append("")
            for m in mt:
                L.append(f"- {m['item']} (`{m['path']}`)")
            L.append("")
        pb = [b for b in sb["physical_blocks"] if b["target"] == t]
        if pb:
            L.append("### Physical status per block")
            L.append("")
            L.append("| Block | Area | Route | IR | SS setup | FF hold | Verdict | Record |")
            L.append("|---|---|---|---|---|---|---|---|")
            for b in pb:
                L.append(f"| {b['block']} | {b.get('area','-')} | {b.get('route','-')} | {b.get('ir','-')} | "
                         f"{b.get('ss','-')} | {b.get('ff','-')} | **{b.get('verdict','open')}** | `{b['path']}` |")
            L.append("")
        lv = [x for x in sb["levers"] if x["target"] == t]
        if lv:
            L.append("### Levers (adopted / rejected)")
            L.append("")
            L.append("| Lever | Verdict | Numbers | Record |")
            L.append("|---|---|---|---|")
            for x in lv:
                nums = x.get("numbers", "")
                if x.get("figure_values"):
                    nums += ("; " if nums else "") + "; ".join(f"{k.split('.',1)[1]}={fmt(v)}" for k, v in x["figure_values"].items())
                L.append(f"| {x['lever']} | **{x['verdict']}** | {nums.strip()} | `{x['path']}` |")
            L.append("")
        oi = [x for x in sb["open_items"] if x["target"] == t]
        if oi:
            L.append("### Open items")
            L.append("")
            L.append("| Item | Owner | Source |")
            L.append("|---|---|---|")
            for x in oi:
                L.append(f"| {x['item']} | {x['owner']} | `{x['path']}` |")
            L.append("")
        mb = [x for x in sb["missing_baselines"] if x["target"] == t]
        if mb:
            L.append("### Missing baselines")
            L.append("")
            for x in mb:
                L.append(f"- {x['item']} (`{x['path']}`)")
            L.append("")
    return "\n".join(L) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", type=Path, default=SPEC)
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--check", action="store_true", help="exit 1 if any citation fails")
    a = ap.parse_args()
    spec = json.loads(a.spec.read_text())
    sb = build(spec)
    a.out.mkdir(parents=True, exist_ok=True)
    (a.out / "scoreboard.json").write_text(json.dumps(sb, indent=1, sort_keys=False) + "\n")
    (a.out / "README.md").write_text(render_md(sb, spec))
    n = len(sb["figures"])
    nf = len(sb["citation_failures"])
    print(f"scoreboard: {n} figures, {nf} citation failures -> {a.out}")
    for f in sb["citation_failures"]:
        print(f"  FAIL {f['id']}: {f['error']}", file=sys.stderr)
    return 1 if (a.check and nf) else 0


if __name__ == "__main__":
    sys.exit(main())
