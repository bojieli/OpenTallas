"""S81-SVCRS-3 11-11: plan pin tables inputs/core_pins/<module>.json of the 6 svc_prov v5 provider boxes, from their
SIGNED routed DBs' abstract LEFs (CORE-KS rule of physical/die_plan/s81/core_pins_gen.py).  Checks per module:
  * LEF sha256 = the durable signed view; SIZE = the routed 6_final.def DIEAREA;
  * every table pin (name, layer, centre) lies inside a RECT of that pin on that layer in the signed LEF;
  * the counter's own pin_compare (tools/fleet/release_tree_plan.py) of the record pins (routed 6_final.def, the
    re-sign record's routed_db) against this table: no moved / extra / missing pin.
usage (cwd = main tools root): svc_pins_gen.py OUTDIR REPORT.json"""
import hashlib
import json
import os
import subprocess
import sys

sys.path[:0] = ["physical/die_plan/s81", "tools/die_plan", "tools/fleet"]
import types  # noqa: E402
# core_pins_gen imports gen_plan_v4 only for CORE_TRACK_OFFSET (= the plan rows' track_offset_um [0.108, 0.012]);
# gen_plan_v4 itself reads plan inputs at import, so this check stands it in with that one constant (asserted below)
sys.modules["gen_plan_v4"] = types.SimpleNamespace(CORE_TRACK_OFFSET=[0.108, 0.012])
import core_pins_gen as CG  # noqa: E402
import release_tree_plan as RT  # noqa: E402

W = "/srv/opentallas-scratch2/claude/s81-svcrs-3"
BOX = [  # key, module, durable dir, kit stage
    ("smc", "ot_s81_su_smc", "s81svc_smc_p4_215554", "p4"),
    ("h4", "ot_s81_svc_merge_h4", "s81svc_h4_p4_221525", "p4"),
    ("sml", "ot_s81_su_sml_fold2", "s81svc_sml_p4_011710", "p4"),
    ("smr", "ot_s81_su_smr", "s81svc_smr_eco_011515", "eco"),
    ("smd", "ot_s81_su_smd_fold2", "s81svc_smd_eco_011509", "eco"),
    ("irg", "ot_s81_svc_idx_hslice_fp", "s81svc_irg_p4_021652", "p4"),
]
PLAN_LEF = "physical/die_plan/s81/cores/svc/prov_1109/%s.lef"


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    out_dir, rep_path = sys.argv[1], sys.argv[2]
    os.makedirs(out_dir, exist_ok=True)
    rep = {}
    for k, mod, dur, st in BOX:
        lef = f"{W}/durable/{dur}/views/{mod}.lef"
        prov = json.load(open(f"{W}/resign/{k}_kd/PROVENANCE.json"))
        odb = prov["routed_db"]
        dfn = os.path.splitext(odb)[0] + ".def"
        j, size = CG.table(mod, lef)
        # LEF centre picks must sit on a RECT of the same pin and layer (they are rect centres by construction)
        _, pins, _ = CG.parse(open(lef).read(), mod)
        for p in j["pins"]:
            rs = [r for r in pins[p["name"]][1] if r[0] == p["layer"]]
            assert any(r[1] - 1e-6 <= p["x"] <= r[3] + 1e-6 and r[2] - 1e-6 <= p["y"] <= r[4] + 1e-6 for r in rs), (mod, p)
        da = [l for l in open(dfn) if l.startswith("DIEAREA")][0].split()
        die = (int(da[6]) / 1000, int(da[7]) / 1000)
        assert tuple(size) == die, (mod, size, die)
        j["lef"] = PLAN_LEF % mod
        j["source"] = (f"S81-SVCRS-3 11-11 from the SIGNED view LEF of {mod} (write_abstract_lef of the routed DB, "
                       f"re-sign record flow-20261110-kd-s81 src {prov['src_commit'][:12]}); CORE-KS rule "
                       f"(physical/die_plan/s81/core_pins_gen.py table(): largest non-M1 rect centre)")
        j["signed"] = dict(lef_sha256=sha(lef), routed_db_sha256=prov["routed_db_sha256"], outline_um=list(size),
                           flow_tag=prov["flow_tag"], src_commit=prov["src_commit"],
                           build_commit=prov["build_commit"], record=f"epyc8:{W}/resign/{k}_kd/PROVENANCE.json")
        f = os.path.join(out_dir, mod + ".json")
        json.dump(j, open(f, "w"), indent=0)
        # the counter's record read (REC_PINS_PY: routed DEF via PROVENANCE routed_db) + its pin_compare vs this table
        sp = f"{W}/resign/{k}_kd/signoff/signoff.json"
        r = subprocess.run(["python3", "-c", RT.REC_PINS_PY], input=json.dumps([[sp, sp]]), capture_output=True, text=True)
        x = json.loads(r.stdout.strip().splitlines()[-1])[sp]
        got = RT.canon_pin_rows(x["doc"])
        shapes = {a: [tuple(q) for q in b] for a, b in (x.get("shapes") or {}).items()}
        c = RT.pin_compare(got, RT.canon_pin_rows(j), shapes or None, None)
        da = x["die_area"]
        cmp_ = {kk: len(v) for kk, v in c.items()}
        rep[mod] = dict(pins=len(j["pins"]), pinhash=j["pinhash"], outline_um=list(size), lef_sha256=j["signed"]["lef_sha256"],
                        def_path=dfn, record_read=x["read"], record_source=x["source"],
                        record_outline_um=[da[2] - da[0], da[3] - da[1]], pin_compare=cmp_, table_sha256=sha(f))
        assert x["source"] == "routed_def" and not (c["moved"] or c["extra"] or c["missing"]), (mod, cmp_)
        print(mod, len(j["pins"]), size, j["pinhash"], cmp_)
    json.dump(rep, open(rep_path, "w"), indent=1)


if __name__ == "__main__":
    main()
