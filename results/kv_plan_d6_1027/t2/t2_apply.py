"""KV-PLAN-DELTA-6 task 2 (D-KV-ECTLK-NARROW-D6 + D-KV-PVPAIR-SPLIT-D6) on hm_r26q5c39.

  python3 t2_apply.py TOOLS_DIE_PLAN PLAN_DIR PLAN.json OUT_PLAN.json OUT_DIR

(a) qkd_ectlk_q0 / qkd_ectlk_q2: outline 216.0 x 172.8 -> 155.52 x 172.8, anchored SW (origin, W channel, both
    SRAMs and the 12.2a1 in-core island at (102.168, 8.64) stay put).  Pins re-made with the kv_core_slice
    --outline rule (E: x' = W2-(W-x); S/N: x scaled; W: unchanged; re-snap to the native 0.048 phase, unique per
    layer+face coordinate); ft_ck pins + island_ft stay; die clock/reset pins move to the 12.8a centre entry
    (outline centre on the 4.32 lattice, 0.384 spacing, same M5 phase).  Partition clock taps (kind core) follow.
(b) kv3_pv_pair: 12.8b W/E split core tree record (kv_core_slice form, like ingest_eng_slice_42.json); not a plan
    field (core lane applies with core_infra_htree --hb-axes).
"""
import copy, hashlib, json, sys
from pathlib import Path

TOOLS, PD, PLAN, OUTP, OUT = sys.argv[1:6]
sys.path.insert(0, TOOLS)
import master_plan as MP  # noqa: E402

PD, OUT = Path(PD), Path(OUT)
PITCH = 0.048
W2 = 155.52
NARROW = {"qkd_ectlk_q0": "cores/qkd_ectlk_q0_pins_r25.json", "qkd_ectlk_q2": "cores/qkd_ectlk_q2_pins_r26q2.json"}
TAG = "KV-PLAN-DELTA-6 t2 10-27 (D-KV-ECTLK-NARROW-D6): outline 216.0x172.8 -> 155.52x172.8 anchored SW (GEOM-31 E half empty)"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def face(p, w, h, tol=0.5):
    x, y = p["x"], p["y"]
    if x <= tol: return "W"
    if x >= w - tol: return "E"
    if y <= tol: return "S"
    if y >= h - tol: return "N"
    return None


def narrow_pins(J, ow, oh, w, h):
    J2 = copy.deepcopy(J)
    sx = w / ow
    for p in J2["pins"]:
        f = face(p, ow, oh)
        if f == "E":
            p["x"] = round(w - (ow - p["x"]), 4)
        elif f == "N":
            p["x"], p["y"] = round(p["x"] * sx, 4), round(h - (oh - p["y"]), 4)
        elif f == "S":
            p["x"] = round(p["x"] * sx, 4)
        # W face: unchanged (SW anchor, same height); interior pins handled below
    used = set()
    for p, q in zip(J2["pins"], J["pins"]):
        if face(q, ow, oh) is None:
            continue
        ax = "x" if p["layer"] in ("M5", "M7") else "y"
        ph = round(q[ax] % PITCH, 4)
        v = round(round((p[ax] - ph) / PITCH) * PITCH + ph, 4)
        other = "y" if ax == "x" else "x"
        step = 0
        while (p["layer"], ax, v, round(p[other], 3)) in used:
            step += 1
            v = round(v + (step if step % 2 else -step) * PITCH, 4)
        used.add((p["layer"], ax, v, round(p[other], 3)))
        p[ax] = v
    # 12.8a centre entry: die clock first ON the entry, then reset, 0.384 apart, native M5 phase of the old entry pin
    ex, ey = MP.snap(w / 2), MP.snap(h / 2)
    isl = MP.entry_island((ex, ey))
    mv = [p for p in J2["pins"] if p["name"] == "ck[0]"] + [p for p in J2["pins"] if p["name"] == "rst_n[0]"]
    assert len(mv) == 2, [p["name"] for p in mv]
    phase = round(next(q for q in J["pins"] if q["name"] == "ck[0]")["x"] % PITCH, 4)
    moved = []
    for k, p in enumerate(mv):
        off = (k + 1) // 2 * (1 if k % 2 else -1) * 8 * PITCH
        old = [p["layer"], p["x"], p["y"]]
        p["layer"], p["x"], p["y"] = "M5", round(round((ex + off - phase) / PITCH) * PITCH + phase, 4), round(ey, 4)
        assert isl[0] < p["x"] < isl[2] and isl[1] < p["y"] < isl[3], (p, isl)
        moved.append(dict(pin=p["name"], from_=old, to=[p["layer"], p["x"], p["y"]]))
    # keep everything else interior (ft_ck_* of the 12.2a1 island) exactly where it was
    for p, q in zip(J2["pins"], J["pins"]):
        if face(q, ow, oh) is None and p["name"] not in ("ck[0]", "rst_n[0]"):
            assert (p["x"], p["y"]) == (q["x"], q["y"])
            for a_ in J2.get("island_ft", {}).get("arcs", []):
                r = a_["rect_um"]
                assert r[2] < w, (r, w)
    # uniqueness + inside-outline checks
    keys = [(p["layer"], round(p["x"], 4), round(p["y"], 4)) for p in J2["pins"]]
    assert len(set(keys)) == len(keys), "duplicate pin position"
    assert all(-1e-6 <= p["x"] <= w + 1e-6 and -1e-6 <= p["y"] <= h + 1e-6 for p in J2["pins"])
    J2["frame"] = f"core R0, origin (0,0), outline {w} x {h}"
    J2["source"] = J2.get("source", "") + " | " + TAG + "; pins kv_core_slice --outline rule, die clock/reset -> 12.8a centre entry"
    fc = {}
    for p in J2["pins"]:
        f = face(p, w, h)
        if f:
            fc.setdefault(f, dict(pins=0, layers=set()))
            fc[f]["pins"] += 1
            fc[f]["layers"].add(p["layer"])
    J2["faces"] = {f: dict(pins=v["pins"], layers=sorted(v["layers"])) for f, v in sorted(fc.items())}
    return J2, dict(entry_xy_um=[ex, ey], entry_island_um=isl, moved=moved)


def main():
    plan_path = PD / PLAN
    P = json.loads(plan_path.read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "cores").mkdir(exist_ok=True)
    rep = dict(schema="opentallas.kv_plan_d6.t2.v1", base_plan=str(plan_path), base_plan_sha256=sha(plan_path), ectlk={}, taps=[])
    newpf = {}
    for mod, pf in NARROW.items():
        J = json.loads((PD / pf).read_text())
        ow, oh = 216.0, 172.8
        assert J["frame"].endswith(f"outline {ow} x {oh}"), J["frame"]
        J2, info = narrow_pins(J, ow, oh, W2, oh)
        npf = pf.rsplit("_pins", 1)[0] + "_pins_r26d6.json"
        (OUT / npf).write_text(json.dumps(J2, indent=1) + "\n")
        (PD / npf).write_text(json.dumps(J2, indent=1) + "\n")
        newpf[mod] = npf
        far_old = max(abs(cx - 108.0) + abs(cy - 86.4) for cx in (0, ow) for cy in (0, oh))
        ex, ey = info["entry_xy_um"]
        far_new = max(abs(cx - ex) + abs(cy - ey) for cx in (0, W2) for cy in (0, oh))
        isl = P["clock"]["mesh"]["core_islands"][mod]["rects_um"]
        assert all(r[2] <= W2 for r in isl), isl
        e_faces = {f: v["pins"] for f, v in J2["faces"].items()}
        rep["ectlk"][mod] = dict(pins_file_old=pf, pins_file_new=npf, pins_sha256=sha(OUT / npf),
                                 outline_old_um=[ow, oh], outline_new_um=[W2, oh], anchor="SW",
                                 core_islands_kept=isl, faces=e_faces,
                                 face_density_pins_per_um={f: round(n / (W2 if f in "SN" else oh), 2) for f, n in e_faces.items()},
                                 area_ratio=round(W2 / ow, 4), fill_est=f"{0.1475 * ow / W2:.3f} (GEOM-31 0.1475 x 216/155.52, UNCHECKED)",
                                 single_tree=dict(far_old_um=far_old, pred_old=MP.core_insertion(far_old),
                                                  far_new_um=MP.r3(far_new), pred_new=MP.core_insertion(far_new),
                                                  note="master_plan.core_insertion (TT, FF), PLAN MODEL UNCHECKED; far <= 200 -> no 12.8b split"),
                                 **info)
        # 12.8c fixed trunk (kv_core_slice rule) when the narrowed single tree drops below 250-20 TT
        tt, ff = MP.core_insertion(far_new)
        n = max(0, round((250.0 - tt) / 23.9)) if tt < 230.0 else 0
        rep["ectlk"][mod]["trunk_12_8c"] = dict(cell="BUFx4_ASAP7_75t_R", n=n, pred_after_ps=dict(TT=round(tt + n * 23.9, 1), FF=round(ff + n * 17.6, 1)),
                                                place="in the entry island ahead of the CTS root, dont_touch, identical in every instance",
                                                note="kv_core_slice BUF_STAGE_PS TT 23.9 / FF 17.6; PLAN MODEL UNCHECKED")
    nhc = 0
    for tn, t in P["partition_types"].items():
        for hc in t.get("hard_cores", []):
            if hc["module"] in NARROW:
                assert hc["outline_um"] == [216.0, 172.8] and hc.get("orient", "R0") == "R0", (tn, hc)
                hc["outline_um"] = [W2, 172.8]
                hc["pins_file"] = newpf[hc["module"]]
                hc["note"] = hc.get("note", "") + " | " + TAG
                nhc += 1
                ox, oy = hc["origin_um"]
                ex, ey = rep["ectlk"][hc["module"]]["moved"][0]["to"][1:]
                for tp in (t.get("clock") or {}).get("taps", []):
                    if tp.get("name") == f"{hc['inst']}.ck[0]" or (tp.get("core") == hc["inst"]) or (tp.get("inst") == hc["inst"]):
                        old = list(tp["xy"])
                        tp["xy"] = [MP.r3(ox + ex), MP.r3(oy + ey)]
                        rep["taps"].append(dict(type=tn, tap={k: v for k, v in tp.items() if k != "xy"}, old=old, new=tp["xy"]))
                # outline must stay inside the type and clear of every other hard core of the type
                W, H = t["outline_um"]
                assert ox + W2 <= W and oy + 172.8 <= H
                for o in t["hard_cores"]:
                    if o is hc: continue
                    a0, b0 = o["origin_um"]; a1, b1 = a0 + o["outline_um"][0], b0 + o["outline_um"][1]
                    assert not (ox < a1 and a0 < ox + W2 and oy < b1 and b0 < oy + 172.8), (tn, hc["inst"], o["inst"])
    rep["hard_cores_changed"] = nhc
    # ---- (b) pv_pair W/E split tree record
    hc = next(h for t in P["partition_types"].values() for h in t.get("hard_cores", []) if h["module"] == "kv3_pv_pair")
    w, h = hc["outline_um"]
    ex, ey = MP.snap(w / 2), MP.snap(h / 2)
    tree = MP.restructure_islands(w, h, 220.0)
    ltt, lff = MP.core_insertion(tree["leaf_reach_um"])
    trunks = [MP.r3(abs(q["centre_um"][0] - ex) + abs(q["centre_um"][1] - ey)) for q in tree["islands"]]
    tr = max(trunks)
    far1 = max(abs(cx - ex) + abs(cy - ey) for cx in (0, w) for cy in (0, h))
    isl_entry = MP.entry_island((ex, ey))
    die_isl = P["clock"]["mesh"]["core_islands"]["kv3_pv_pair"]["rects_um"]
    ov = lambda a, b: a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]
    clash = [(q["rect_um"], r) for q in tree["islands"] for r in die_isl + [isl_entry] if ov(q["rect_um"], r)]
    n_inst = sum(1 for t in P["partition_types"].values() for h_ in t.get("hard_cores", []) if h_["module"] == "kv3_pv_pair")
    parts = P.get("partitions") or {}
    parts = parts.values() if isinstance(parts, dict) else parts
    n_die = sum(1 for p_ in parts for h_ in P["partition_types"][p_["type"]].get("hard_cores", []) if h_["module"] == "kv3_pv_pair")
    rec = dict(module="kv3_pv_pair",
               delta_id="D-KV-PVPAIR-SPLIT-D6 (KV-PLAN-DELTA-6 task 2, 10-27; single centre-entry reach over the 220 limit)",
               outline_um=[w, h], instances_type_frame=n_inst, instances_die=n_die,
               entry=dict(xy_um=[ex, ey], island_um=isl_entry),
               core_tree=dict(form="internal H-tree from the entry (12.8b), balanced binary (core_infra_htree --hb-axes); W/E split",
                              grid=tree["grid"], leaf_reach_limit_um=220.0, leaf_reach_um=tree["leaf_reach_um"],
                              islands=tree["islands"], trunk_um=trunks,
                              pred_TT_ps=round(ltt + tr * 0.20, 1), pred_FF_ps=round(lff + tr * 0.20 * MP.FF_RATIO, 1),
                              pred_note="plan model kv_core_slice (core_insertion(leaf reach) + 0.20 ps/um trunk = ~2.5x optimistic per COORD; PLAN MODEL, UNCHECKED)"),
               frame="core R0 frame; identical on every instance and orient (islands mirror with the core, 12.8b)",
               die_core_islands_12_2a1=die_isl, island_overlaps=clash,
               replaces=dict(grid=[1, 1], far_um=MP.r3(far1), pred_TT_ps=MP.core_insertion(far1)[0],
                             source="single centre entry (KV-CORE-SLICE-1 r25 pins, entry (190.08, 95.04))"),
               in_plan_json="slice record (kv_core_slice form); core lane applies with core_infra_htree --hb-axes; pins unchanged")
    assert not clash, clash
    (OUT / "pv_pair_slice_split.json").write_text(json.dumps(rec, indent=1) + "\n")
    rep["pv_pair"] = dict(grid=rec["core_tree"]["grid"], leaf_reach_um=tree["leaf_reach_um"], pred_TT_ps=rec["core_tree"]["pred_TT_ps"],
                          pred_FF_ps=rec["core_tree"]["pred_FF_ps"], single_far_um=MP.r3(far1), single_pred=MP.core_insertion(far1))
    out_plan = PD / OUTP
    out_plan.write_text(json.dumps(P) + "\n")
    rep["out_plan"] = str(out_plan)
    rep["out_plan_sha256"] = sha(out_plan)
    (OUT / "t2_apply_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "ectlk"}, indent=1)[:3000])
    for m, r in rep["ectlk"].items():
        print(m, r["faces"], r["face_density_pins_per_um"], r["entry_xy_um"], r["moved"], r["single_tree"])


main()
