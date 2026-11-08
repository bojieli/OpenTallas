#!/usr/bin/env python3
"""DIE-HBM-90-PEV 11-07: plan event that drops core input pins the kit face shell dropped as unread top bits.

face_shell.py (kit generation) narrows an input port when the core reads none of its top bits: the shell port is
declared [keep-1:0] and the core port is fed {N'd0, <bus>__fq}; the dropped names are listed in face_shell.json
'dropped'.  The routed DB then has no pin for them, so the signed form misses those plan pins and does not count
until the plan table drops them too (face_shell.py: "dropped_in_bits leave the pin table as a plan change for the
lane owner").  This tool is that plan change.  It drops a pin only when all of these hold (else it fails closed,
exit 1, nothing written):
  1. face_shell.json is schema opentallas.hbm_arch.core_face_shell.v1 for the module and lists the pin in 'dropped';
  2. the pin's bus is an input in face_shell.json, and bus[bit] has bit >= keep[bus] (a top bit the shell cut);
  3. the kit shell RTL declares 'input wire [keep-1:0] <bus>' and feeds the core port with '{<n>'d0, <bus>__fq}'
     where n = width - keep (the core sees constant 0 on the dropped bits);
  4. the pin is in the old plan table; with --kit-pins, the kit pins.json names equal the new table names.
Every other pin row is kept byte for byte (same order, same sites).  Every hard core of the module whose pins_file is
the old table is repointed to the new table; nothing else in the plan changes.

    drop_face_shell_pins.py PLAN_DIR --module M --old-table cores/X.json --new-table cores/Y.json
        --face-shell KIT/face_shell.json --shell-rtl KIT/rtl/M__fshell.sv [--kit-pins KIT/pins.json]
        --event NAME --by LANE --ruling TEXT [--note-file F.json]
PLAN_DIR holds die_plan.json(.gz), the tables (.json or .json.gz) and SHA256SUMS as on main (sha256 of the
uncompressed bytes, '.gz' left out of the name); .gz files are written with mtime 0.  Writes <EVENT>_event.json.
"""
import argparse
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

SCHEMA = "opentallas.hbm_arch.core_face_shell.v1"


def split_pin(name):
    m = re.fullmatch(r"(.+)\[(\d+)\]", name)
    return (m.group(1), int(m.group(2))) if m else (name, None)


def check_drops(module, shell, shell_rtl, old_rows):
    """-> sorted drop names; raises SystemExit (fail closed) when a dropped pin is not a proven unread top bit."""
    bad = []
    if shell.get("schema") != SCHEMA or shell.get("module") != module:
        raise SystemExit(f"drop_face_shell_pins: face_shell.json is not {SCHEMA} for {module}")
    drops = sorted(shell.get("dropped") or [])
    if not drops:
        raise SystemExit("drop_face_shell_pins: face_shell.json drops no pin; nothing to do")
    names = {r["name"] for r in old_rows}
    widths, keep, dirs = shell.get("widths") or {}, shell.get("keep") or {}, shell.get("dirs") or {}
    if isinstance(dirs, str):
        dirs = {}
    for n in drops:
        bus, bit = split_pin(n)
        if n not in names:
            bad.append(f"{n}: not in the old plan table")
        if bit is None or bus not in widths or bus not in keep:
            bad.append(f"{n}: no bus width / keep width in face_shell.json")
            continue
        w, k = int(widths[bus]), int(keep[bus])
        if dirs and dirs.get(bus) != "input":
            bad.append(f"{n}: {bus} is not an input")
        if not (k <= bit < w):
            bad.append(f"{n}: bit {bit} is not a cut top bit (keep {k}, width {w})")
        b = re.escape(bus)
        if not re.search(rf"input\s+wire\s+\[{k - 1}:0\]\s+{b}\s*[,)]", shell_rtl):
            bad.append(f"{n}: shell RTL does not declare input [{k - 1}:0] {bus}")
        if not re.search(rf"\.{b}\s*\(\s*\{{\s*{w - k}'d0\s*,\s*{b}__fq\s*\}}\s*\)", shell_rtl):
            bad.append(f"{n}: shell RTL does not feed .{bus}({{{w - k}'d0, {bus}__fq}})")
    if bad:
        raise SystemExit("drop_face_shell_pins: fail closed, nothing written:\n  " + "\n  ".join(bad))
    return drops


def apply(raw, module, old_pf, new_pf, drops, old_rows, kit_pins=None):
    """-> (raw with the module's old-table cores repointed, new rows, [type.inst]); raises SystemExit on a mismatch."""
    d = set(drops)
    new_rows = [r for r in old_rows if r["name"] not in d]
    if kit_pins is not None:
        kn = {(p["bus"] if p.get("bit") is None else f"{p['bus']}[{p['bit']}]") if "bus" in p else p["name"] for p in kit_pins}
        tn = {r["name"] for r in new_rows}
        if kn != tn:
            raise SystemExit(f"drop_face_shell_pins: kit pins != new table (kit only {sorted(kn - tn)[:5]}, "
                             f"table only {sorted(tn - kn)[:5]}); nothing written")
    inst = []
    for tname, t in sorted(raw["partition_types"].items()):
        for h in t.get("hard_cores") or []:
            if h.get("module") == module and h.get("pins_file") == old_pf:
                h["pins_file"] = new_pf
                inst.append(f"{tname}.{h['inst']}")
    if not inst:
        raise SystemExit(f"drop_face_shell_pins: no hard core of {module} uses {old_pf}; nothing written")
    return raw, new_rows, inst


def _read(path):
    """(object, gz?, text format) of PATH or PATH.gz; format 'compact' = json.dumps(obj) (+ newline flag)."""
    p = Path(path)
    gz = not p.exists() and Path(str(p) + ".gz").exists()
    data = gzip.decompress(Path(str(p) + ".gz").read_bytes()) if gz else p.read_bytes()
    obj = json.loads(data)
    txt = data.decode()
    fmt = ("indent1" if txt.rstrip("\n") == json.dumps(obj, indent=1) else "compact", txt.endswith("\n"))
    return obj, gz, fmt


def _write(path, obj, gz, fmt):
    txt = json.dumps(obj, indent=1) if fmt[0] == "indent1" else json.dumps(obj)
    raw = (txt + ("\n" if fmt[1] else "")).encode()
    p = Path(str(path) + ".gz") if gz else Path(path)
    if gz:
        with open(p, "wb") as f, gzip.GzipFile(fileobj=f, mode="wb", mtime=0, filename="") as g:
            g.write(raw)
    else:
        p.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def update_sums(plan_dir, changed):
    """SHA256SUMS: replace the sums of changed names, append new names (sha256 of the uncompressed bytes)."""
    f = Path(plan_dir) / "SHA256SUMS"
    lines = f.read_text().splitlines() if f.exists() else []
    seen, out = set(), []
    for line in lines:
        if not line.strip():
            continue
        h, n = line.split(None, 1)
        n = n.strip()
        if n in changed:
            h = changed[n]
            seen.add(n)
        out.append(f"{h}  {n}")
    out += [f"{changed[n]}  {n}" for n in changed if n not in seen]
    f.write_text("\n".join(out) + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("plan_dir")
    for k in ("--module", "--old-table", "--new-table", "--face-shell", "--shell-rtl", "--event", "--by", "--ruling"):
        ap.add_argument(k, required=True)
    ap.add_argument("--kit-pins")
    ap.add_argument("--note-file", help="JSON object merged into the event (evidence fields)")
    a = ap.parse_args(argv)
    pd = Path(a.plan_dir)
    if a.new_table == a.old_table:
        raise SystemExit("drop_face_shell_pins: --new-table must differ from --old-table")
    old_rows, tgz, tfmt = _read(pd / a.old_table)
    shell = json.loads(Path(a.face_shell).read_text())
    drops = check_drops(a.module, shell, Path(a.shell_rtl).read_text(), old_rows)
    raw, pgz, pfmt = _read(pd / "die_plan.json")
    kit = json.loads(Path(a.kit_pins).read_text()) if a.kit_pins else None
    raw, new_rows, inst = apply(raw, a.module, a.old_table, a.new_table, drops, old_rows, kit)
    if (pd / a.new_table).exists() or Path(str(pd / a.new_table) + ".gz").exists():
        raise SystemExit(f"drop_face_shell_pins: {a.new_table} exists; nothing written")
    note = f"{a.by} {a.event}: {a.module} table drops {len(drops)} face-shell-dropped input pin(s) {drops}"
    raw["note"] = note + " <- " + raw.get("note", "")[:200] if raw.get("note") else note
    ts = _write(pd / a.new_table, new_rows, tgz, tfmt)
    ps = _write(pd / "die_plan.json", raw, pgz, pfmt)
    ev = dict(schema="opentallas.plan_drop_face_shell_pins.v1", event=a.event, by=a.by, ruling=a.ruling, module=a.module,
              instances=inst, pins_removed=drops, old_table=a.old_table, new_table=a.new_table,
              table_pins=[len(old_rows), len(new_rows)], new_table_sha256=ts, die_plan_sha256=ps,
              kit_pins_equal=kit is not None, pin_sites_moved=0, pin_cycles=0, macros_outline_clock="unchanged",
              face_shell=dict(path=a.face_shell, dropped=shell.get("dropped"), unread_kept=shell.get("unread_kept")),
              shell_rtl=a.shell_rtl)
    if a.note_file:
        ev.update(json.loads(Path(a.note_file).read_text()))
    evn = f"{a.event}_event.json"
    (pd / evn).write_text(json.dumps(ev, indent=1) + "\n")
    update_sums(pd, {"die_plan.json": ps, a.new_table: ts,
                     evn: hashlib.sha256((pd / evn).read_bytes()).hexdigest()})
    print(note, "| instances", inst, "| table", len(old_rows), "->", len(new_rows), ts[:12], "| die_plan", ps[:12])
    return 0


if __name__ == "__main__":
    sys.exit(main())
