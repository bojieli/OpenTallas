"""OWNER DECISION 8 (2026-10-24): constant output pins are DROPPED from the S81 plan (no face_guard constant class).
inputs/const_pins_dropped.json lists, per hard-core module, the pins that are not pins of the core any more (constant
outputs, and the inputs that only received them); the RTL ports were narrowed to match (hcpl lane o[31:16], rxsb
o_r[30:0], vs ra_ri[30:0]).  drop(table) removes them from one plan pin table (pins + pinhash); core_pins_gen.py and
cores/leaf/repin.py call it before writing; run standalone to apply it to the committed tables (idempotent):
    python3 physical/die_plan/s81/drop_const_pins.py            (cwd = repo root)"""
import glob, hashlib, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
LIST = os.path.join(HERE, "inputs", "const_pins_dropped.json")


def dropped(module):
    d = json.load(open(LIST))["modules"]
    return set(d.get(module, {}).get("pins", ()))


def drop(j, lef_stub=None):
    """remove the listed pins of j['module'] from the table dict j (in place); returns the number removed.  lef_stub:
    a generated stub LEF (repin _lfp) whose PIN blocks of those pins are removed as well."""
    gone = dropped(j["module"])
    if not gone:
        return 0
    n0 = len(j["pins"])
    j["pins"] = [p for p in j["pins"] if p["name"] not in gone]
    n = n0 - len(j["pins"])
    if n:
        j["pinhash"] = hashlib.sha256(json.dumps(j["pins"], sort_keys=True).encode()).hexdigest()[:12]
        if "OWNER DECISION 8" not in j["source"]:
            j["source"] += "; OWNER DECISION 8 10-24: %d constant pins dropped (inputs/const_pins_dropped.json)" % n
    if lef_stub and os.path.exists(lef_stub):
        s = open(lef_stub).read()
        for nm in gone:
            s = re.sub(r"  PIN %s\n.*?  END %s\n" % (re.escape(nm), re.escape(nm)), "", s, flags=re.S)
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
