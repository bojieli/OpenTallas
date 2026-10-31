#!/usr/bin/env python3
"""DIE-KV-49-HG one-block clock-metadata fix for kv3_hg_v1 in the KV plan of record (event28w_c, owner 12.20).

KIT-WAVE-2 20:51: kv3_hg_v1 hard cores are all SIGNED, but the wave skips the type because gen_phys needs
explicit SIGNED TT/FF mean core-tap metadata for core_taps "internal" (signed_mean_core_taps), and the
contract reader (core_clock_contract.load) needs each hard core's selected liberty with its signoff.json beside it.

This script, for partition type kv3_hg_v1 only:
  0. core_pg_connect: true (view PG pins are M5 only; lands them on the tile M6 straps, PG-CORECONN-1);
  1. binds every hard_cores[] entry to the signed view in hgclk_1030/views/<module>/ (lef + TT lib; FF lib sibling;
     signoff.json = the counted SIGNED record, origin in RECORD.txt);
  2. sets every kind=core clock tap to the record's measured pin-register means:
     insertion_ps = TT insertion_pinflops mean, insertion_ff_ps = FF mean, budget_owner = SIGNED:<record copy>.
Fail-closed: every view loads through core_clock_contract.load (SIGNED, one clock pin), LEF outline == plan outline,
LEF pin set covers the plan pins_file, file hashes match SHA256SUMS, and no byte of plan_c outside
partition_types.kv3_hg_v1.{core_pg_connect, hard_cores[].lef/lib, clock.taps[].insertion_ps/insertion_ff_ps/budget_owner/note} changes.
Usage (repo root): python3 physical/die_plan/qwen_kvsys/hgclk_1030/mk_hgclk.py
"""
import copy, hashlib, json, os, re, sys

sys.path.insert(0, "tools/die_plan")
import core_clock_contract as CC  # noqa: E402

POR = "physical/die_plan/qwen_kvsys/plan_of_record"
VIEWS = "physical/die_plan/qwen_kvsys/hgclk_1030/views"
TN = "kv3_hg_v1"
TAG = "DIE-KV-49-HG 10-30"


def sha_ok(d):
    for line in open(os.path.join(d, "SHA256SUMS")):
        h, f = line.split()
        assert hashlib.sha256(open(os.path.join(d, f), "rb").read()).hexdigest() == h, (d, f)


def lef_check(lef, mod, outline, pins_file):
    txt = open(lef).read()
    m = re.search(r"MACRO\s+(\S+)", txt)
    assert m and m.group(1) == mod, (lef, m and m.group(1))
    sx, sy = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", txt).groups())
    assert abs(sx - outline[0]) < 1e-3 and abs(sy - outline[1]) < 1e-3, (mod, (sx, sy), outline)
    lp = set(re.findall(r"^\s*PIN\s+(\S+)", txt, re.M))
    pp = json.load(open(os.path.join(POR, pins_file)))
    names = {p["name"] for p in pp["pins"]}
    miss = sorted(names - lp)
    assert not miss, (mod, pins_file, len(miss), miss[:5])
    return len(names), len(lp)


def main():
    path = os.path.join(POR, "plan_c.json")
    raw = open(path).read()
    plan = json.loads(raw)
    assert json.dumps(plan, indent=1) + "\n" == raw
    ref = copy.deepcopy(plan)
    t = plan["partition_types"][TN]
    ck = t["clock"]
    assert ck["core_taps"] == "internal"
    contracts = {}
    for h in t["hard_cores"]:
        mod = h["module"]
        assert not h.get("lef") and not h.get("lib"), (h["inst"], "already bound")
        d = os.path.join(VIEWS, mod)
        if mod not in contracts:
            sha_ok(d)
            rec = json.load(open(os.path.join(d, "signoff.json")))
            assert rec.get("verdict") == "SIGNED", (mod, rec.get("verdict"))
            c = CC.load(dict(inst=h["inst"], module=mod, lib=f"{d}/{mod}_tt.lib", lef=f"{d}/{mod}.lef"))
            assert len(c) == 1, (mod, sorted(c))
            (pin, v), = c.items()
            assert v["signed"] is True
            contracts[mod] = dict(pin=pin, tt=v["corners"]["tt"]["mean_ps"], ff=v["corners"]["ff"]["mean_ps"],
                                  origin=open(os.path.join(d, "RECORD.txt")).read().strip())
        lef_check(f"{d}/{mod}.lef", mod, h["outline_um"], h["pins_file"])
        h["lef"] = f"{d}/{mod}.lef"
        h["lib"] = f"{d}/{mod}_tt.lib"
    # PG-CORECONN-1: the signed views carry VDD/VSS on M5 only; the default M4->M5 core grid lands no via on them
    assert "core_pg_connect" not in t
    t["core_pg_connect"] = True
    insts = {h["inst"]: h["module"] for h in t["hard_cores"]}
    seen = set()
    for tp in ck["taps"]:
        if tp.get("kind") != "core":
            continue
        inst = max((i for i in insts if tp["name"] == i or tp["name"].startswith(i + ".")), key=len)
        mod = insts[inst]
        c = contracts[mod]
        if tp["name"] != inst:
            assert tp["name"] == f"{inst}.{c['pin']}", (tp["name"], c["pin"])
        old = (tp.get("insertion_ps"), tp.get("insertion_ff_ps"), tp.get("budget_owner"))
        tp["insertion_ps"] = round(c["tt"], 2)
        tp["insertion_ff_ps"] = round(c["ff"], 2)
        tp["budget_owner"] = f"SIGNED:{VIEWS}/{mod}/signoff.json"
        tp["note"] = (f"{TAG}: SIGNED pin-register means TT/FF {tp['insertion_ps']}/{tp['insertion_ff_ps']} ps on "
                      f"{c['pin']} (record {c['origin']}; was {old[0]}/{old[1]} owner {old[2]}) | " + tp.get("note", ""))
        seen.add(inst)
    assert seen == set(insts), sorted(set(insts) - seen)
    # fail-closed diff: only kv3_hg_v1 hard_cores lef/lib and core tap metadata
    a, b = copy.deepcopy(ref), copy.deepcopy(plan)
    for x in (a, b):
        tt = x["partition_types"][TN]
        tt.pop("core_pg_connect", None)
        for h in tt["hard_cores"]:
            h.pop("lef", None); h.pop("lib", None)
        for tp in tt["clock"]["taps"]:
            for k in ("insertion_ps", "insertion_ff_ps", "budget_owner", "note"):
                tp.pop(k, None)
    assert a == b
    open(path, "w").write(json.dumps(plan, indent=1) + "\n")
    for mod, c in sorted(contracts.items()):
        print(f"{mod} {c['pin']} TT {c['tt']:.2f} FF {c['ff']:.2f} <- {c['origin']}")


if __name__ == "__main__":
    main()
