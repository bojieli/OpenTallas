#!/usr/bin/env python3
"""QC-S28-BIND (b): parent_id_straps of the HF-1c cbx_q10 row-variant types (*_h), OWNER 10-25 rule B (ID-only straps
tied at the parent, per instance).  The plan value of a type is its REPRESENTATIVE instance literal (bind.emit_type:
first member = sorted partition name; parent_id_straps.validate_bound_id_bits).  HF-1c split the bn/tn rows
(c16_*_1/_2, far=0) out of the cbx_q10 types into *_h but copied the bf representative values (far=1, cid of c16_*_0).

Derived from the event elaboration (asbuilt.json), not guessed; for each *_h type:
  rep = sorted(partitions of T)[0] -> asbuilt instance c16_<col>_<row> (asbuilt_map_p6 rules: bf 0, bn 1, tn 2, tf 3)
  tile_id literal bits = cid << 4  (qfd_c_b16_dv u_t_*.tile_id = {cid[11:0], 4 non-literal tie bits})
  sidx literal bits    = qfd_c_b16_dv_fabric u_x_r_c.sidx bits: far / ~far ($not) / constants, at the rep's far
Self-check: the same derivation must reproduce the plan values of the unsplit cbx_q10 types (exit 5 otherwise).
Guarded: an entry whose current value is not the copied base-type value is a CONFLICT (exit 3); idempotent.
  fix_h_straps.py PLAN_IN PLAN_OUT ASBUILT_JSON REPORT.json
"""
import json
import re
import sys


def main(pin, pout, asb, rep):
    txt = open(pin).read()
    P = json.loads(txt)
    T = P["partition_types"]
    M = json.load(open(asb))["modules"]
    top = M["qfd_die"]["cells"]
    fab = M["qfd_c_b16_dv_fabric"]["cells"]
    dv = M["qfd_c_b16_dv"]
    farbit = dv["ports"]["far"]["bits"][0]
    # sidx bits are far, ~far ($not cell on far) or constants (qfd_c_b16_dv_fabric)
    notfar = {c["connections"]["Y"][0] for c in M["qfd_c_b16_dv_fabric"]["cells"].values()
              if c["type"] == "$not" and c["connections"]["A"] == [farbit]}

    def bitval(b, far):
        if b == farbit:
            return far
        if b in notfar:
            return 1 - far
        if b in ("0", "1"):
            return int(b)
        raise SystemExit(f"sidx bit {b} is neither far, ~far nor a constant")
    row = {"bf": 0, "bn": 1, "tn": 2, "tf": 3}
    R = {"types": {}, "edits": [], "kept": []}
    for tn in sorted(T):
        if not tn.startswith("cbx_q10__"):
            continue
        is_h = tn.endswith("_h")
        base = tn[:-2] if is_h else tn
        parts = sorted(p["name"] for p in P["partitions"] if p["type"] == tn)
        m = re.fullmatch(r"c_([WE]\d)_(bf|bn|tn|tf)_\d\d", parts[0])
        inst = "c16_%s_%d" % (m.group(1), row[m.group(2)])
        c = top[inst]["connections"]
        cid = int("".join(reversed(c["cid"])), 2)
        far = int(c["far"][0])
        R["types"][tn] = dict(rep_partition=parts[0], asbuilt=inst, cid=cid, far=far, partitions=len(parts))
        bdesc = {x.get("inst"): x for x in T[base].get("contents", []) + T[base].get("hard_cores", [])
                 if x.get("parent_id_straps")}
        for d in T[tn].get("contents", []) + T[tn].get("hard_cores", []):
            ids = d.get("parent_id_straps") or {}
            leaf = d.get("parent_id_leaf", d.get("inst"))
            for port, e in ids.items():
                if port == "tile_id":
                    new = cid << 4
                elif port == "sidx":
                    bits = fab[leaf.split(".")[-1]]["connections"]["sidx"]
                    new = sum(v << i for i, b in enumerate(bits) for v in [bitval(b, far)] if v)
                else:
                    raise SystemExit(f"unknown ID port {tn} {leaf}.{port}")
                if e["value"] == new:
                    R["kept"].append([tn, leaf, port, new])
                    continue
                if not is_h:   # the derivation must reproduce every unsplit type's plan value (self-check)
                    print(f"DERIVE MISMATCH {tn} {leaf}.{port}: plan {e['value']} derived {new}")
                    sys.exit(5)
                if e["value"] != bdesc[d.get("inst")]["parent_id_straps"][port]["value"]:
                    print(f"CONFLICT {tn} {leaf}.{port}: {e['value']} is neither the copied base value nor {new}")
                    sys.exit(3)
                R["edits"].append([tn, leaf, port, e["value"], new])
                e["value"] = new
    open(pout, "w").write(json.dumps(P, indent=1) + "\n")
    json.dump(R, open(rep, "w"), indent=1)
    print(json.dumps(R["types"]))
    print("edits", len(R["edits"]), "kept", len(R["kept"]))


if __name__ == "__main__":
    main(*sys.argv[1:5])
