#!/usr/bin/env python3
"""Export a physical master and the exact current elaborated module closure.

Instance names: the cut netlists are flattened, so instances of retained (keep_hierarchy) leaf modules carry
generate-scope names such as `g_lvl[1].g_n[0].u_a`.  write_verilog emits them as escaped identifiers, and
yosys-slang --keep-hierarchy (the LEC gold frontend) then builds an illegal RTLIL module name from the escaped
form (`...$top.\\g_lvl[1].g_n[0].u_a `, trailing space) and stops.  COORD ruling 5 (2026-10-26): the generator emits
legal plain identifiers.  Every instance of a non-blackbox closure module whose name is not a plain Verilog
identifier is renamed deterministically (`[`, `]`, `.` and any other illegal character -> `_`, e.g.
`g_lvl_1__g_n_0__u_a`), unique against every cell and net name of its parent; the map is in the receipt.
Blackbox (SRAM macro) instances keep their names: slang accepts them and macro placement keys on them.
Renaming instances changes no logic, only hierarchical names (so a synthesis checkpoint of the old SV no longer
matches by register name: resynthesise from the new SV).
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path

PLAIN = re.compile(r"[A-Za-z_][A-Za-z0-9_$]*\Z")


def plain_name(name):
    s = re.sub(r"[^A-Za-z0-9_]", "_", name.lstrip("\\"))
    return s if re.match(r"[A-Za-z_]", s) else "i_" + s


def is_blackbox(mod):
    return bool(mod.get("attributes", {}).get("blackbox")) or not (mod.get("cells") or mod.get("netnames"))


def plain_instances(mods, closure):
    """Rename escaped instances of non-blackbox closure modules in place; returns {module: {old: new}}."""
    renames = {}
    for n in sorted(closure):
        cells = mods[n].get("cells", {})
        bad = sorted(c for c, cd in cells.items() if not PLAIN.match(c) and not cd["type"].startswith("$")
                     and cd["type"] in mods and not is_blackbox(mods[cd["type"]]))
        if not bad:
            continue
        taken = (set(cells) - set(bad)) | set(mods[n].get("netnames", {})) | set(mods[n].get("ports", {}))
        m = {}
        for c in bad:
            base = new = plain_name(c)
            k = 1
            while new in taken:
                new, k = f"{base}_{k}", k + 1
            taken.add(new)
            m[c] = new
        mods[n]["cells"] = {m.get(c, c): cd for c, cd in cells.items()}
        renames[n] = m
    return renames


def closure_of(mods, master):
    seen, todo = set(), [master]
    while todo:
        n = todo.pop()
        if n in seen:
            continue
        assert n in mods, n
        seen.add(n)
        todo.extend(c["type"] for c in mods[n].get("cells", {}).values()
                    if not c["type"].startswith("$") and c["type"] not in seen)
    return seen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--netlist", type=Path, required=True); ap.add_argument("--master", required=True)
    ap.add_argument("--out", type=Path, required=True); ap.add_argument("--source-commit", required=True)
    ap.add_argument("--blackbox", action="append", default=[])
    a = ap.parse_args(); a.out.mkdir(parents=True, exist_ok=True)
    j = json.loads(a.netlist.read_text()); mods = j["modules"]
    for n in a.blackbox:
        m = mods[n]; m["attributes"] = {"blackbox": "1"}; m["cells"] = {}; m["netnames"] = {}; m.pop("memories", None)
    seen = closure_of(mods, a.master)
    renames = plain_instances(mods, seen)
    pruned = {**j, "modules": {n: mods[n] for n in sorted(seen)}}
    jp = a.out / (a.master + ".json"); jp.write_text(json.dumps(pruned))
    sv = a.out / (a.master + ".sv"); ys = a.out / (a.master + ".ys")
    ys.write_text(f"read_json {jp.resolve()}\nwrite_verilog -noattr {sv.resolve()}\n")
    subprocess.run([str(Path.home() / ".local/opentallas-tools/bin/yosys"), "-ql", str(a.out / (a.master + ".log")),
                    "-s", str(ys)], check=True)
    escaped = [l.strip() for l in sv.read_text().splitlines()
               if re.match(r"\s+\S+\s+\\\S+\s+\($", l) and not l.lstrip().startswith(("wire", "reg", "input", "output"))]
    bbs = {n for n in seen if is_blackbox(mods[n])}
    bad = [l for l in escaped if l.split()[0].lstrip("\\") not in bbs]
    assert not bad, f"escaped non-blackbox instances remain: {bad[:5]}"
    receipt = dict(source_commit=a.source_commit, input_sha256=hashlib.sha256(a.netlist.read_bytes()).hexdigest(),
                   master=a.master, ports={n: (p["direction"], len(p["bits"])) for n, p in mods[a.master]["ports"].items()},
                   closure_modules=sorted(seen), verilog_sha256=hashlib.sha256(sv.read_bytes()).hexdigest(),
                   qualification="EXACT_CUT_NOT_ROUTED", added_cycles=0, boundary_masters=a.blackbox,
                   instance_names="PLAIN_IDENTIFIERS", instance_renames=renames)
    (a.out / (a.master + "_receipt.json")).write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k not in ("closure_modules", "instance_renames")}
                     | {"instance_renames": sum(map(len, renames.values()))}))


if __name__ == "__main__":
    main()
