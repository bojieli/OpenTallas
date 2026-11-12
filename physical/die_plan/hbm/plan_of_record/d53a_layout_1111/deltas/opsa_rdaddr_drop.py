#!/usr/bin/env python3
"""opsa_rdaddr_drop.py PLAN_IN PLAN_OUT CORES_DIR   (HBM-CORES-C 11-12, DIE-HBM-101 approved, precedent opsbpins_1109)

Event opsa_rdaddr375_1112: ot_hgi_sfu_opsa_group0 (and group1 when its table carries the bits) pin tables lose the 9 proven-unread
input pins rd_addr[375..383].  Core side: the kit face shell drops them (face_shell.json dropped), ties the core port .rd_addr({9'd0,
rd_addr__fq}) and declares input [374:0] rd_addr.  Run on the t39w plan AFTER opsa_g0_lattice.py (group0 table
cores_d51/..895.344x270__d51opsaB_lat.json).  Fails closed unless the only changes are pins_file + note.
Writes PLAN_OUT and OUT/cores_d51/<new tables>."""
import json, os, sys, hashlib
src, dst, cores = sys.argv[1:4]
DROP = {"rd_addr[%d]" % i for i in range(375, 384)}
D = json.load(open(src)); T = D["partition_types"]
done = {}
for tn, t in T.items():
    for h in t.get("hard_cores") or []:
        if h["module"] not in ("ot_hgi_sfu_opsa_group0", "ot_hgi_sfu_opsa_group1"): continue
        old = h["pins_file"]
        if old not in done:
            p = os.path.join(os.path.dirname(os.path.abspath(dst)), "cores_d51", os.path.basename(old))
            if not os.path.exists(p): p = os.path.join(cores, os.path.basename(old))
            pins = json.load(open(p))
            names = {q["name"] for q in pins}
            assert DROP <= names, (old, sorted(DROP - names))
            new = [q for q in pins if q["name"] not in DROP]
            assert len(new) == len(pins) - 9
            newname = old.replace(".json", "__rdaddr375.json")
            outp = os.path.join(os.path.dirname(os.path.abspath(dst)), "cores_d51", os.path.basename(newname))
            os.makedirs(os.path.dirname(outp), exist_ok=True); json.dump(new, open(outp, "w"))
            done[old] = (newname, hashlib.sha256(open(outp, "rb").read()).hexdigest(), len(pins), len(new))
        h["pins_file"] = done[old][0]
assert done
open(dst, "w").write(json.dumps(D, indent=1) + "\n")
for k, v in done.items(): print(k, "->", v)
