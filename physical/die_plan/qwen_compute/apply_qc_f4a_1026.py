#!/usr/bin/env python3
"""QC PLAN-DELTA F4A (COORD RULING QC-SU-F4-2 2026-10-26 14:49 (1)+(3); lane QC-PLAN-F4A; plan owner INFRA-FIRST).

On the QC master-plan input plan (candidate_oneqc0733.json, sha checked) change ONLY the vmr / rp1 hard cores of the six
su_c partition types:
  * outline 259.2 x 276.48 -> F4A 250.56 x 216 (column SRAM ot_sram_1r1w_1024x256_m1b2_r2c2_ns, results/qc_su_f4/f4.py);
    origin (SW corner) unchanged, so the S face stays on the same parent line and S-face pins keep their parent x;
  * ONE pin table per module (template, all instances): names / layers / order / pitch = the closed view LEF port table
    (no port added or removed); S face (M5): x kept; W face (M4): the block is shifted as a whole to the centre of the
    F4A W read window [156.68, 210.68] (shift snapped to the 0.048 M4 track); ck = interior M5 pin at the F4A centre clock
    entry (12.8a; die M9->M5 stack, 12.2a1), x snapped onto the M5 track (125.292);
  * track_offset_um [0.012, 0.012] (as D-QC-SU1713 prog/btab): every M4/M5 pin on the parent 0.048/0.024 lattice, asserted;
  * the core ck tap moves to origin + ck; tap insertion = the 12.3 common target 250 TT / 202.5 FF (built to it, no
    per-core budget); the old 395.7/349 measured budgets are retired with the old outline;
  * companion master-plan inputs: entries and core islands (F4A g4c L1 islands incl. the re-sited NW island, trees on
    the track-snapped geo results/qc_plan_f4a/geo/*_f4s.geo, COORD RULING QC-PLAN-F4A (1)) -- every other module record
    byte-identical.  RULING (3): the entry = the centre of the CURRENT outline (125.28, 108), recorded bound to that
    outline (entries[mod].outline_um, master_plan.core_entry refuses a record bound to another outline); the physical ck
    pin / tap sits on the nearest M5 track (125.292, 0.012 from the entry, inside the 0.5-um entry check).
Partition outlines / buses / ft / partition clock entry / all other types and top-level keys asserted unchanged.
usage: apply_qc_f4a_1026.py PLAN_IN PLAN_OUT ENTRIES_IN ENTRIES_OUT ISLANDS_IN ISLANDS_OUT VMR_G4C.json RP1_G4C.json
"""
import copy, hashlib, json, re, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE / "cores/legacy"))
import gen_core_kit_qc as G  # noqa: E402  (lef_contract / face_of: the kit generator's own pin reader)

PLAN_SHA = "e4829ce26d222eac5fb51ab34454e28d0174585995bc0e837fc7e29d660f48d2"
OLD, NEW = [259.2, 276.48], [250.56, 216.0]
WWIN = (156.68, 210.68)                      # f4.py: wy1 = core top - 1.0 = 210.68, window = top 54 um
CK = (125.292, 108.0)                        # ck pin: F4A entry (125.28, 108) on the M5 track (0.012 + 0.048 k)
ENTRY = (125.28, 108.0)                      # RULING (3): entry = centre of the current outline NEW (4.32 lattice)
assert ENTRY == (round(round(NEW[0] / 2 / 4.32) * 4.32, 4), round(round(NEW[1] / 2 / 4.32) * 4.32, 4))
TOFF = [0.012, 0.012]
MODS = {"qfd_dv_s8x_vmr": "physical/ref_tile/qfd_dv_s5_vmr/views/qfd_dv_s8x_vmr/qfd_dv_s8x_vmr.lef",
        "qfd_dv_s8_crh_rp1": "physical/ref_tile/qfd_dv_s8_crh_rp1/views/qfd_dv_s8_crh_rp1/qfd_dv_s8_crh_rp1.lef"}
TAG = {"qfd_dv_s8x_vmr": "vmr", "qfd_dv_s8_crh_rp1": "rp1"}


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def on(v, o, p):
    k = (v - o) / p
    return abs(k - round(k)) < 1e-6


def pin_table(mod, lef):
    (w, h), pins = G.lef_contract(REPO / lef, mod)
    assert [w, h] == OLD, (mod, w, h)
    W_ = [p for p in pins if G.face_of(p["x"], p["y"], w, h) == "W"]
    S_ = [p for p in pins if G.face_of(p["x"], p["y"], w, h) == "S"]
    assert len(W_) + len(S_) == len(pins), "only W / S faces expected"
    assert all(p["layer"] == "M4" for p in W_) and all(p["layer"] == "M5" for p in S_)
    ys = [p["y"] for p in W_]
    shift = round(round(((WWIN[0] + WWIN[1]) / 2 - (min(ys) + max(ys)) / 2) / 0.048) * 0.048, 3)
    out = []
    for p in pins:
        f = G.face_of(p["x"], p["y"], w, h)
        q = dict(name=p["name"], layer=p["layer"], x=p["x"], y=p["y"], face=f)
        if p["name"] == "ck":
            q.update(layer="M5", x=CK[0], y=CK[1], face="island", note="12.8a centre clock entry, die M9->M5 stack (12.2a1)")
        elif f == "W":
            q["y"] = round(p["y"] + shift, 4)
            assert WWIN[0] <= q["y"] <= WWIN[1], q
        else:
            assert 4.32 <= p["x"] <= NEW[0] - 4.32, q
        out.append(q)
    for q in out:                              # kit tracks (core frame) and parent lattice (origin + TOFF)
        c = q["y"] if q["layer"] == "M4" else q["x"]
        assert on(c, 0.012, 0.048), q
    return out, dict(w_shift_um=shift, w_span_um=[round(min(ys) + shift, 4), round(max(ys) + shift, 4)],
                     n_w=len(W_), n_s=len(S_) - 1, n=len(out))


def main(pin_, pout, ein, eout, iin, iout, gvmr, grp1):
    assert sha(pin_) == PLAN_SHA, "not the QC master-plan input plan e4829ce2"
    raw = json.loads(Path(pin_).read_text())
    base = copy.deepcopy(raw)
    pdir = Path(pout).parent
    rep = dict(schema="opentallas.qc-plan-delta.v1", delta="QC-PLAN-F4A", ruling="COORD RULING QC-SU-F4-2 14:49",
               plan_in=str(pin_), plan_in_sha256=PLAN_SHA, tables={}, changed=[])
    files = {}
    for mod, lef in MODS.items():
        pins, st = pin_table(mod, lef)
        rel = f"cores/su/f4a/{mod}_f4a_pins.json"
        doc = dict(schema="opentallas.core_pins.v1", core=mod, frame="core R0, origin (0,0)", outline_um=NEW,
                   source=f"QC-PLAN-F4A top-down F4A table from the closed LEF port list {lef} (sha {sha(REPO / lef)[:12]}): "
                          f"S x kept, W block shifted {st['w_shift_um']} um to the F4A W window, ck at the F4A centre entry; "
                          "NOT SIGNED; must match the final LEF", pins=pins)
        (pdir / rel).parent.mkdir(parents=True, exist_ok=True)
        (pdir / rel).write_text(json.dumps(doc, indent=1) + "\n")
        files[mod] = rel
        rep["tables"][mod] = dict(file=rel, sha256=sha(pdir / rel), **st)
    for tn, t in raw["partition_types"].items():
        hcs = [h for h in t.get("hard_cores", []) if h["module"] in MODS]
        if not hcs:
            continue
        cont = {c["inst"]: c for c in t["contents"]}
        for h in hcs:
            assert h["outline_um"] == OLD and h.get("orient", "R0") == "R0", (tn, h["inst"])
            o = h["origin_um"]
            h["outline_um"] = list(NEW)
            h["track_offset_um"] = list(TOFF)
            h["pins_file"] = files[h["module"]]
            h["note"] = h.get("note", "") + "; QC-PLAN-F4A: F4A 250.56x216 column-SRAM outline, SW anchored, centre ck entry"
            if "outline_um" in cont.get(h["inst"], {}):
                cont[h["inst"]]["outline_um"] = list(NEW)
            for q in json.loads((pdir / files[h["module"]]).read_text())["pins"]:
                c = (q["y"] + o[1] if q["layer"] == "M4" else q["x"] + o[0]) + 0.012
                assert on(c, 0.024, 0.048), (tn, h["inst"], q)
            n = 0
            for tp in t["clock"]["taps"]:
                if tp.get("name") == h["inst"] + ".ck":
                    tp["xy"] = [round(o[0] + TOFF[0] + CK[0], 4), round(o[1] + TOFF[1] + CK[1], 4)]
                    tp["insertion_ps"], tp["insertion_ff_ps"] = 250.0, 202.5
                    tp["budget_owner"] = ("12.3 common target (F4A core built to it; plan prediction results/qc_plan_f4a/"
                                          f"{TAG[h['module']]}_f4s_g4c.json, UNCHECKED)")
                    n += 1
            assert n == 1, (tn, h["inst"])
            rep["changed"].append(dict(type=tn, inst=h["inst"], module=h["module"], origin_um=o, old_outline_um=OLD,
                                       new_outline_um=NEW))
    assert len(rep["changed"]) == 24, len(rep["changed"])        # 6 su_c x 3 vmr + 3 slw_su_c x 2 rp1 (sle u_cl/u_ch = qfd_dv_s8x_crh, not in F4A)
    def iface(t):
        c = t.get("clock", {})
        return json.dumps(dict(o=t["outline_um"], b=t["buses"], f=t.get("ft_slots"), r=t.get("reset"),
                               tap=c.get("tap_um"), l=c.get("layer"), i=c.get("insertion_ps")), sort_keys=True)
    for tn, t in raw["partition_types"].items():
        assert iface(t) == iface(base["partition_types"][tn]), tn
        if not any(h["module"] in MODS for h in t.get("hard_cores", [])):
            assert t == base["partition_types"][tn], tn
    for k in raw:
        if k != "partition_types":
            assert raw[k] == base[k], k
    Path(pout).write_text(json.dumps(raw, indent=1) + "\n")
    rep["plan_out_sha256"] = sha(pout)
    # entries + islands
    ent = json.loads(Path(ein).read_text())
    isl = json.loads(Path(iin).read_text())
    e0, i0 = copy.deepcopy(ent), copy.deepcopy(isl)
    for mod, gj in (("qfd_dv_s8x_vmr", gvmr), ("qfd_dv_s8_crh_rp1", grp1)):
        g = json.loads(Path(gj).read_text())
        assert g["verdict"] == "PASS" and g["clear_route"]["verdict"] == "PASS" and g["band"]["in_band_12_3"], gj
        ent[mod] = dict(xy=list(ENTRY), outline_um=list(NEW), ck_pin_um=list(CK),
                        source=f"QC-PLAN-F4A RULING (3): centre of the current outline {NEW}; {Path(gj).name}")
        leaves = list(g["leaf_avg_with_trunk"]["TT"])
        T = g["levels"]["T_um"]
        isl[mod] = dict(method=f"QC-PLAN-F4A f4_g4c G4-strict L1 islands ({Path(gj).name} sha {sha(gj)[:12]})",
                        k=g["k"], max_entry_um=T["T1"], entry_um=list(ENTRY), sinks=g["n_sinks"], sampled=g["n_sinks"],
                        entry_maze_um=dict(min=T["T1"], max=T["T1"]),
                        leaf_reach_um=round(T["T1"] + T["T2"] + T["T3"], 2),
                        equal_path_um=round(T["T1"] + T["T2"] + T["T3"], 2), verdict="PASS",
                        islands=[dict(centre_um=[round((i["rect_um"][0] + i["rect_um"][2]) / 2, 3),
                                                 round((i["rect_um"][1] + i["rect_um"][3]) / 2, 3)],
                                      rect_um=i["rect_um"], entry_maze_um=T["T1"],
                                      load_frac=round(sum(1 for l in leaves if l.startswith(i["island"] + "B")) / len(leaves), 4))
                                 for i in g["gates"]["G2_island_rows"]["islands"]])
    for k in e0:
        if k not in MODS:
            assert ent[k] == e0[k]
    for k in i0:
        if k not in MODS:
            assert isl[k] == i0[k]
    Path(eout).write_text(json.dumps(ent, indent=1) + "\n")
    Path(iout).write_text(json.dumps(isl, indent=1) + "\n")
    rep.update(entries_out_sha256=sha(eout), islands_out_sha256=sha(iout), cycles_added=0, ports_added=0)
    (pdir / "qc_f4a_1026_report.json").write_text(json.dumps(rep, indent=1) + "\n")
    print(json.dumps({k: v for k, v in rep.items() if k != "changed"}, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:9])
