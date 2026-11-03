#!/usr/bin/env python3
"""DIE-KV-64 11-03 RF-KV1 view bind for the 16 kv3_pv* types (form of hgclk_1030/mk_hgclk.py, DIE-KV-49-HG).

kit_wave prelint flags a hard core without a lef as PLANNED (WAIT-DEP), so the kv3_pv* types waited although both
cores are signed off.  This script, for every partition type holding kv3_pv_pair / ot_qwen_tp8_pv_join_t:
  1. pv_join_t instances on the fMX table move to the R0 table with orient composed with MX (fMX table = exact
     MX mirror of the R0 table, 4621/4621 pins), so every R0/fMX join instance shares the ONE signed R0 view;
  2. binds hard_cores[].lef/lib to pvview_1103/views/<module>/ for kv3_pv_pair (fMX table, all 256) and
     pv_join_t on the R0 table.  pv_join_t on the fR180 table (20 inst in 10 types) stays PLANNED: its table is
     R180 of R0 with 18 nm M3 track snaps (1027/4621 pins), not an exact transform, and a second view of the same
     master cannot coexist in one type kit (one LEF MACRO per name);
  3. core_pg_connect true (views carry VDD/VSS on M5 only);
  4. every kind=core tap of a bound instance: insertion_ps / insertion_ff_ps = the record's TT / FF pin-register
     means (core_clock_contract.load), budget_owner = SIGNED:<views/<module>/signoff.json>.
Fail-closed: SHA256SUMS, SIGNED verdict, one liberty clock pin = the tap pin, LEF SIZE == outline, every plan pin
in the LEF at the table position (first RECT centre, 5 nm), tap xy reproduced before/after the orient change, and
nothing outside those keys changes.
Usage (repo root): python3 physical/die_plan/qwen_kvsys/pvview_1103/mk_pvview.py
"""
import copy, hashlib, json, os, re, sys

sys.path.insert(0, "tools/die_plan")
import core_clock_contract as CC  # noqa: E402

POR = "physical/die_plan/qwen_kvsys/plan_of_record"
VIEWS = "physical/die_plan/qwen_kvsys/pvview_1103/views"
TAG = "DIE-KV-64 RF-KV1 11-03"
PAIR, JOIN = "kv3_pv_pair", "ot_qwen_tp8_pv_join_t"
JR0, JFMX = "pins/pv_join_pins_r26q5c.json", "pins/pv_join_pins_fMX_r26q5c.json"
BIND = {PAIR: {"pins/kv3_pv_pair_pins_fMX_r26c_lc.json"}, JOIN: {JR0}}
COMP_MX = {"R0": "MX", "MX": "R0", "MY": "R180", "R180": "MY"}


def sha_ok(d):
    for line in open(os.path.join(d, "SHA256SUMS")):
        h, f = line.split()
        assert hashlib.sha256(open(os.path.join(d, f), "rb").read()).hexdigest() == h, (d, f)


def lef_pins(lef):
    txt = open(lef).read()
    out, cur, first = {}, None, False
    for ln in txt.splitlines():
        m = re.match(r"\s*PIN\s+(\S+)", ln)
        if m:
            cur, first = m.group(1), True
            continue
        if cur and first:
            m = re.match(r"\s*RECT\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)", ln)
            if m:
                a = list(map(float, m.groups()))
                out[cur] = ((a[0] + a[2]) / 2, (a[1] + a[3]) / 2)
                first = False
        if re.match(r"\s*END\s+(\S+)", ln) and cur and ln.strip() == f"END {cur}":
            cur = None
    sx, sy = map(float, re.search(r"SIZE\s+([\d.]+)\s+BY\s+([\d.]+)", txt).groups())
    assert re.search(r"MACRO\s+(\S+)", txt).group(1) == os.path.basename(lef)[:-4]
    return out, (sx, sy)


def view_check(mod, pins_file, outline):
    lp, size = lef_pins(f"{VIEWS}/{mod}/{mod}.lef")
    assert abs(size[0] - outline[0]) < 1e-3 and abs(size[1] - outline[1]) < 1e-3, (mod, size, outline)
    pp = json.load(open(os.path.join(POR, pins_file)))["pins"]
    bad = [p["name"] for p in pp if p["name"] not in lp or
           abs(lp[p["name"]][0] - p["x"]) > 0.005 or abs(lp[p["name"]][1] - p["y"]) > 0.005]
    assert not bad, (mod, pins_file, len(bad), bad[:5])
    return len(pp)


def tf(o, x, y, w, h):
    return {"R0": (x, y), "MX": (x, h - y), "MY": (w - x, y), "R180": (w - x, h - y)}[o]


def tap_xy(h, pin):
    p = {q["name"]: (q["x"], q["y"]) for q in json.load(open(os.path.join(POR, h["pins_file"])))["pins"]}[pin]
    dx, dy = tf(h["orient"], p[0], p[1], *h["outline_um"])
    to = h.get("track_offset_um", [0, 0])
    return [round(h["origin_um"][0] + to[0] + dx, 3), round(h["origin_um"][1] + to[1] + dy, 3)]


def main():
    path = os.path.join(POR, "plan_c.json")
    raw = open(path).read()
    plan = json.loads(raw)
    ref = copy.deepcopy(plan)
    contracts, checked, n = {}, set(), dict(moved=0, bound=0, taps=0, planned=0)
    for mod in (PAIR, JOIN):
        d = os.path.join(VIEWS, mod)
        sha_ok(d)
        assert json.load(open(os.path.join(d, "signoff.json"))).get("verdict") == "SIGNED", mod
    touched = []
    for tn, t in sorted(plan["partition_types"].items()):
        hs = [h for h in t.get("hard_cores", []) if h["module"] in (PAIR, JOIN)]
        if not hs:
            continue
        touched.append(tn)
        assert t["clock"]["core_taps"] == "internal"
        taps = {tp["name"].split(".")[0]: tp for tp in t["clock"]["taps"] if tp.get("kind") == "core"}
        for h in hs:
            tp = taps[h["inst"]]
            pin = tp["name"].split(".", 1)[1]
            assert tap_xy(h, pin) == tp["xy"], (tn, tp["name"], tap_xy(h, pin), tp["xy"])
            if h["module"] == JOIN and h["pins_file"] == JFMX:
                h["pins_file"], h["orient"] = JR0, COMP_MX[h["orient"]]
                assert tap_xy(h, pin) == tp["xy"], (tn, tp["name"], "moved", tap_xy(h, pin), tp["xy"])
                n["moved"] += 1
            if h["pins_file"] not in BIND[h["module"]]:
                n["planned"] += 1
                continue
            mod = h["module"]
            d = os.path.join(VIEWS, mod)
            if mod not in contracts:
                c = CC.load(dict(inst=h["inst"], module=mod, lib=f"{d}/{mod}_tt.lib", lef=f"{d}/{mod}.lef"))
                assert len(c) == 1, (mod, sorted(c))
                (cp, v), = c.items()
                assert v["signed"] is True
                contracts[mod] = dict(pin=cp, tt=v["corners"]["tt"]["mean_ps"], ff=v["corners"]["ff"]["mean_ps"],
                                      origin=open(os.path.join(d, "RECORD.txt")).read().strip())
            if (mod, h["pins_file"]) not in checked:
                view_check(mod, h["pins_file"], h["outline_um"])
                checked.add((mod, h["pins_file"]))
            c = contracts[mod]
            assert pin == c["pin"], (tn, tp["name"], c["pin"])
            assert not h.get("lef") and not h.get("lib"), (tn, h["inst"])
            h["lef"], h["lib"] = f"{d}/{mod}.lef", f"{d}/{mod}_tt.lib"
            old = (tp.get("insertion_ps"), tp.get("insertion_ff_ps"), tp.get("budget_owner"))
            tp["insertion_ps"], tp["insertion_ff_ps"] = round(c["tt"], 2), round(c["ff"], 2)
            tp["budget_owner"] = f"SIGNED:{d}/signoff.json"
            tp["note"] = (f"{TAG}: SIGNED pin-register means TT/FF {tp['insertion_ps']}/{tp['insertion_ff_ps']} ps on "
                          f"{pin} (record {c['origin'].split(' ')[0]}; was {old[0]}/{old[1]} owner {old[2]}) | "
                          + tp.get("note", ""))
            n["bound"] += 1
            n["taps"] += 1
        if not t.get("core_pg_connect"):
            t["core_pg_connect"] = True
    a, b = copy.deepcopy(ref), copy.deepcopy(plan)
    for x in (a, b):
        for tn in touched:
            tt = x["partition_types"][tn]
            tt.pop("core_pg_connect", None)
            for h in tt["hard_cores"]:
                for k in ("lef", "lib", "pins_file", "orient"):
                    h.pop(k, None)
            for tp in tt["clock"]["taps"]:
                for k in ("insertion_ps", "insertion_ff_ps", "budget_owner", "note"):
                    tp.pop(k, None)
    assert a == b
    out = json.dumps(plan, indent=1) + "\n"
    if raw != json.dumps(ref, indent=1) + "\n":   # keep the file's own formatting outside the changed objects
        print("NOTE plan_c.json is not indent=1 canonical; writing canonical form")
    open(path, "w").write(out)
    print(json.dumps(dict(types=len(touched), **n, contracts={m: {k: (round(v, 2) if isinstance(v, float) else v)
                                                               for k, v in c.items() if k != "origin"}
                                                           for m, c in contracts.items()})))


if __name__ == "__main__":
    main()
