"""OWNER DECISION 8 (2026-10-24): constant output pins are DROPPED from the S81 plan (no face_guard constant class).
inputs/const_pins_dropped.json lists, per hard-core module, the pins that are not pins of the core any more (constant
outputs, and the inputs that only received them); the RTL ports were narrowed to match (hcpl lane o[31:16], rxsb
o_r[30:0], vs ra_ri[30:0]; S81-KITS-RTLA: rxsf o_u / o_u2 [30:0], rxsb i_u / i_u2 [30:0], and the packed BF16 buses
vn y / vq y, ve o_y / vs ve_oy [127:0] whose kept bits are renamed by the 'rename' map, closed-view positions kept).  drop(table) removes them from one plan pin table (pins + pinhash); core_pins_gen.py and
cores/leaf/repin.py call it before writing; run standalone to apply it to the committed tables (idempotent):
    python3 physical/die_plan/s81/drop_const_pins.py            (cwd = repo root)"""
import glob, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIST = os.path.join(HERE, "inputs", "const_pins_dropped.json")


def dropped(module):
    d = json.load(open(LIST))["modules"]
    return set(d.get(module, {}).get("pins", ()))


def renames(module):
    d = json.load(open(LIST))["modules"]
    return dict(d.get(module, {}).get("rename", {}))


def drop(j, lef_stub=None):
    """remove the listed pins of j['module'] from the table dict j (in place) and apply its 'rename' map (packed /
    narrowed buses: old bit name -> new bit name, same position).  Renames apply in map order, each once: the table
    records how many it has applied (j['const_rename'] = N, the first N entries of the module's map; the LEF stub's
    marker line '# OT const_rename N' likewise, a bare marker = the table's count before this call), so entries
    appended to the map later (a second narrowing of the same module) apply on the next run.  Returns the number of
    pins removed + renamed.  lef_stub: a generated stub LEF (repin _lfp) whose PIN blocks are removed / renamed too."""
    gone = dropped(j["module"])
    items = list(renames(j["module"]).items())
    if not gone and not items:
        return 0
    done0 = int(j.get("const_rename") or 0)
    applied, todo = dict(items[:done0]), dict(items[done0:])
    gone = gone - set(applied.values())    # renamed already: a new name may equal a dropped old name (packed bus)
    n0 = len(j["pins"])
    j["pins"] = [p for p in j["pins"] if p["name"] not in gone]
    n = n0 - len(j["pins"])
    if todo:
        assert not (set(todo.values()) - set(todo)) & {p["name"] for p in j["pins"]}, "rename target collides with a kept pin"
        for p in j["pins"]:
            if p["name"] in todo:
                p["name"] = todo[p["name"]]
                n += 1
        j["const_rename"] = len(items)
    if n:
        j["pinhash"] = hashlib.sha256(json.dumps(j["pins"], sort_keys=True).encode()).hexdigest()[:12]
        if "OWNER DECISION 8" not in j["source"]:
            j["source"] += "; OWNER DECISION 8 10-24: %d constant pins dropped (inputs/const_pins_dropped.json)" % n
    if lef_stub and os.path.exists(lef_stub):
        s = open(lef_stub).read()
        m = re.match(r"# OT const_rename(?: (\d+))?[^\n]*\n", s)
        ldone = (int(m.group(1)) if m.group(1) else done0) if m else 0
        lapplied, ltodo = dict(items[:ldone]), dict(items[ldone:])
        lgone = gone | dropped(j["module"])
        lgone = lgone - set(lapplied.values())
        for nm in lgone:
            s = re.sub(r"  PIN %s\n.*?  END %s\n" % (re.escape(nm), re.escape(nm)), "", s, flags=re.S)
        if ltodo:
            s = re.sub(r"^(  (?:PIN|END) )(\S+)$", lambda mm: mm.group(1) + ltodo.get(mm.group(2), mm.group(2)), s, flags=re.M)
        if items:
            if m:
                s = s[m.end():]
            s = "# OT const_rename %d: packed / narrowed buses renamed (physical/die_plan/s81/inputs/const_pins_dropped.json)\n" % len(items) + s
        open(lef_stub, "w").write(s)
    return n


def main():
    for f in sorted(glob.glob(os.path.join(HERE, "inputs", "core_pins", "*.json"))):
        j = json.load(open(f))
        stub = j.get("lef") if j.get("lef", "").startswith("physical/die_plan/s81/cores/") else None
        n = drop(j, stub)
        if n:
            json.dump(j, open(f, "w"), indent=0)
            print("dropped %d pins: %s" % (n, f))


if __name__ == "__main__":
    main()
