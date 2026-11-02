#!/usr/bin/env python3
"""HBM-CORES-KITS-41/COMPACT: apply one per-block compact plan event to a die plan dir (default c11G).
usage: k41_compact.py BLOCK BASE_DIR OUT_DIR EVENT_DIR
BLOCK = tnode | vms | bfqg.  EVENT_DIR holds the Codex PREP inputs for that block (read-only copies).
Writes OUT_DIR as BASE_DIR with symlinks for untouched files; rewrites die_plan.json, core_macros.json,
clock_entries.json and adds one new pins file under cores/.  Report -> OUT_DIR/k41_event_report.json."""
import json, os, sys, shutil, hashlib, copy
BLOCK, BASE, OUT, EV = sys.argv[1:5]
os.makedirs(OUT, exist_ok=True); os.makedirs(OUT + "/cores", exist_ok=True)
REWRITE = {"die_plan.json", "core_macros.json", "clock_entries.json"}
for f in os.listdir(BASE):
    if f in REWRITE or f == "cores" or f.startswith("k41_"): continue
    dst = os.path.join(OUT, f)
    if not os.path.lexists(dst): os.symlink(os.path.realpath(os.path.join(BASE, f)), dst)
for f in os.listdir(BASE + "/cores"):
    dst = os.path.join(OUT, "cores", f)
    if not os.path.lexists(dst): os.symlink(os.path.realpath(os.path.join(BASE, "cores", f)), dst)
J = lambda p: json.load(open(p))
plan = J(BASE + "/die_plan.json"); cm = J(BASE + "/core_macros.json"); ce = J(BASE + "/clock_entries.json")
r6 = lambda v: round(v + 0.0, 6)
rep = {"block": BLOCK, "base": BASE, "base_die_plan_sha256": hashlib.sha256(open(BASE + "/die_plan.json", "rb").read()).hexdigest(),
       "changed_instances": []}

def write_pins(name, pins):
    p = OUT + "/cores/" + name
    if os.path.lexists(p): os.remove(p)
    json.dump(pins, open(p, "w"), indent=0); rep["pins_file"] = "cores/" + name
    rep["pins_sha256"] = hashlib.sha256(open(p, "rb").read()).hexdigest(); rep["pins_n"] = len(pins)
    return "cores/" + name

def place(origin, orient, outline, xy):
    W, H = outline; x, y = xy; ox, oy = origin
    if orient in (None, "R0"): return [r6(ox + x), r6(oy + y)]
    if orient == "MX": return [r6(ox + x), r6(oy + H - y)]
    if orient == "MY": return [r6(ox + W - x), r6(oy + y)]
    if orient == "R180": return [r6(ox + W - x), r6(oy + H - y)]
    raise SystemExit("orient " + str(orient))

GRID = 8.64
def snap(want, old, outline):
    """G0C: hard-core origins sit on the 8.64-um lattice (track_offset only < 2.16). Snap each axis of the
    Codex origin to the lattice, picking the side that keeps the new core inside the old slot (nearest first)."""
    out = []
    for a in (0, 1):
        k = want[a] / GRID; lo, hi = r6(int(k // 1) * GRID), r6((int(k // 1) + 1) * GRID)
        if abs(k - round(k)) < 1e-6: out.append(r6(round(k) * GRID)); continue
        o0, o1 = old["origin_um"][a], old["origin_um"][a] + old["outline_um"][a]
        fits = [c for c in (lo, hi) if c >= o0 - 1e-6 and c + outline[a] <= o1 + 1e-6]
        cands = sorted(fits or (lo, hi), key=lambda c: (abs(c - want[a]), c))
        out.append(cands[0])
    rep.setdefault("lattice_snaps", []).append({"want": want, "snapped": out})
    return out

def apply(module, outline, new_origin_fn, pins_fn, macros, clock_xy, island, note):
    """new_origin_fn(ptype, hc) -> new origin (type-local); pins_fn(hc) -> new pins_file."""
    n = 0
    for pt, v in plan["partition_types"].items():
        taps = {t["name"]: t for t in v.get("clock", {}).get("taps", [])}
        for hc in v.get("hard_cores", []):
            if hc.get("module") != module: continue
            old = copy.deepcopy(hc)
            want = [r6(c) for c in new_origin_fn(pt, hc)]
            hc["origin_um"] = snap(want, old, outline)
            hc["outline_um"] = list(outline); hc["pins_file"] = pins_fn(hc)
            hc["note"] = (hc.get("note", "") + " | " + note).strip(" |")
            ent = ce.get(pt, {}).get(hc["inst"]); tap = taps.get(hc["inst"]); tapd = None
            if ent is not None:
                old_entry_parent = place(old["origin_um"], old.get("orient"), old["outline_um"], ent["xy_um"])
                ent["xy_um"] = list(clock_xy); ent["island_um"] = list(island)
                ent["source"] = ent.get("source", "") + " | " + note
                new_entry_parent = place(hc["origin_um"], hc.get("orient"), hc["outline_um"], clock_xy)
                if tap is not None:
                    tap_old = list(tap["xy"]); tap["xy"] = new_entry_parent
                    tap["note"] = tap.get("note", "") + " | " + note
                    tapd = [r6(tap["xy"][0] - tap_old[0]), r6(tap["xy"][1] - tap_old[1]), r6(tap_old[0] - old_entry_parent[0]), r6(tap_old[1] - old_entry_parent[1])]
            rep["changed_instances"].append({"type": pt, "inst": hc["inst"], "orient": hc.get("orient", "R0"),
                                             "old_origin": old["origin_um"], "new_origin": hc["origin_um"],
                                             "old_outline": old["outline_um"], "new_outline": hc["outline_um"],
                                             "old_pins_file": old["pins_file"], "new_pins_file": hc["pins_file"],
                                             "clock_entry": ent is not None, "tap_delta_and_old_tap_minus_entry": tapd})
            n += 1
    c = cm["cores"][module]
    c["previous_k41"] = {"outline_um": c["outline_um"], "macros": c["macros"]}
    c["outline_um"] = list(outline); c["macros"] = macros; c["basis"] = note
    rep["n_instances"] = n

if BLOCK == "tnode":
    cand = J(EV + "/candidate.json"); pe = J(EV + "/parent_event.json"); pp = J(EV + "/candidate_plan_pins.json")["pins"]
    pins = [{"name": p["name"], "layer": p["layer"], "x": p["x"], "y": p["y"]} for p in pp]
    pf = write_pins("ot_hnx_fused_tnode__125.28x95.04__k41c.json", pins)
    deltas = {(r["part"], r["instance"]): r["origin_delta_in_parent_um"] for r in pe["rows"]}
    tmap = {p["type"]: p["name"] for p in plan["partitions"]}
    macros = [{"name": "u_fcore." + m["instance"], "master": m["master"], "orient": m["orient"],
               "rect_um": [r6(x) for x in m["rect"]]} for m in cand["macros"]]
    note = ("HBM-CORES-KITS-41 compact event k41c-tnode: 172.8x172.8 -> 125.28x95.04 (Codex PREP tnode_compact_1548 / "
            "hbm-tnode-native-look-1131 parent_event: child R0 origin +21.6,+21.6 keeps world clk+PG; native fill FAIL 6.57% -> est 22.4%)")
    apply("ot_hnx_fused_tnode", cand["outline_um"],
          lambda pt, hc: [hc["origin_um"][0] + deltas[(tmap.get(pt, pt), hc["inst"])][0], hc["origin_um"][1] + deltas[(tmap.get(pt, pt), hc["inst"])][1]],
          lambda hc: pf, macros,
          cand["clock"]["new_M5_pin_um"], cand["clock"]["island_rect"], note)
elif BLOCK == "vms":
    mod = "hnx_vms_bank_q0_faces__vecd4ae"
    cmod = J(EV + "/compact_model.json"); pp = J(EV + "/parent_pose_proofs.json"); cep = J(EV + "/clock_entries_proposed.json")["model"]["u_vms"]
    pmap = {}
    rep["pins_files"] = {}
    for t in cmod["typed_profiles"]:
        pins = J(EV + "/" + t["proposed_pins_file"])
        name = "hnx_vms_bank_q0_faces__vecd4ae__224.64x272.16__k41c_" + t["old_pin_sha256"][:12] + ".json"
        pf = write_pins(name, pins); pmap[t["old_pins_file"]] = pf; rep["pins_files"][t["old_pins_file"]] = [pf, rep["pins_sha256"]]
    poses = {(p["parent_type"], p["inst"]): p for p in pp}
    macros = [{"name": "u_fcore." + m["name"], "master": m["master"], "orient": m["orient"], "rect_um": m["rect_um"]} for m in cmod["macro_placement"]]
    note = ("HBM-CORES-KITS-41 compact event k41c-vms: base 3-SRAM vecd4ae 270x403.92 -> 224.64x272.16 (Codex PREP vms-native-compact-1630@4e21d56ad; "
            "per-pose origins from parent_pose_proofs; main clk entry 111.96,177.12; _mu1 vec6293 4-SRAM unchanged per COORD Q8)")
    def org(pt, hc):
        p = poses[(pt, hc["inst"])]
        assert [round(a, 3) for a in p["old_origin_um"]] == [round(a, 3) for a in hc["origin_um"]], (pt, hc["inst"])
        assert p["orient"] == hc.get("orient", "R0"), (pt, hc["inst"])
        return p["new_origin_um"]
    apply(mod, cmod["outline_um"], org, lambda hc: pmap[hc["pins_file"]], macros, cep["xy_um"], cep["island_um"], note)
elif BLOCK == "bfqg":
    mod = "ot_hgi_sm_xload_cl2_bfqg"
    cmod = J(EV + "/compact_model.json"); pw = J(EV + "/actual_parent_world_deltas.json"); pins = J(EV + "/proposed_pins.json")
    pf = write_pins("ot_hgi_sm_xload_cl2_bfqg__259.2x220.32__k41c.json", pins)
    tmap = {p["type"]: p["name"] for p in plan["partitions"]}
    inst = {(a["part"], a["inst"]): a for a in pw["actual_instances"]}
    S = (94.824, 41.064)
    macros = [{"name": "u_fcore." + m["inst"], "master": m["master"], "orient": m["orient"],
               "rect_um": [m["x"], m["y"], r6(m["x"] + S[0]), r6(m["y"] + S[1])]} for m in cmod["macro_placement"]]
    clk = [p for p in pins if p["name"] == "clk"][0]; cx, cy = clk["x"], clk["y"]
    isl = [r6(4.32 * round((cx - 4.32) / 4.32)), r6(4.32 * round((cy - 4.32) / 4.32))]; isl += [r6(isl[0] + 8.64), r6(isl[1] + 8.64)]
    note = ("HBM-CORES-KITS-41 compact event k41c-bfqg: 302.4x298.08 -> 259.2x220.32 (Codex PREP bfqg-native-compact-1745, uncommitted WT "
            "codex-bfqg-native-1520 re-created; incl bfqg-native-spacing-1710 4 clock +-0.048 moves; main clk world fixed)")
    def org(pt, hc):
        a = inst[(tmap.get(pt, pt), hc["inst"])]
        assert [round(x, 3) for x in a["old_origin_um"]] == [round(x, 3) for x in hc["origin_um"]], (pt, hc["inst"])
        return [hc["origin_um"][0] + a["origin_delta_um"][0], hc["origin_um"][1] + a["origin_delta_um"][1]]
    apply(mod, cmod["outline_um"], org, lambda hc: pf, macros, [cx, cy], isl, note)
else:
    sys.exit("block not implemented: " + BLOCK)

json.dump(plan, open(OUT + "/die_plan.json", "w"))
json.dump(cm, open(OUT + "/core_macros.json", "w"), indent=1)
json.dump(ce, open(OUT + "/clock_entries.json", "w"), indent=1)
rep["new_die_plan_sha256"] = hashlib.sha256(open(OUT + "/die_plan.json", "rb").read()).hexdigest()
json.dump(rep, open(OUT + "/k41_event_report.json", "w"), indent=1)
print(BLOCK, "instances", rep["n_instances"], "new sha", rep["new_die_plan_sha256"][:12])
