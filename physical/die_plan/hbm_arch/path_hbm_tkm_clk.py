"""PATH-HBM TKM chain clock pins (GEOM-REVIEW-2 11:35 R1 rule (3)): every TKM chain hop must have its launch and
capture clock taps <= ~400 um apart.  The 4x8 snake mirrors cols 1/3 (MX, y flips), so a clock pin on the N face (tiles)
or the S-W corner (root) puts the turn pairs 673.9 um and root->tile0 853.4 um apart, whatever the partition tap does.
Structural fix (pin placement, 0 cycles): put the core clock pins on the E face at mid-height (M6), which is invariant
under MX.  The root cell sits at the col0 foot with the tile outline, so it gets the same E-mid clock pin.  Every
column hop is then one row pitch (354.24 um) and every turn one column pitch (328.32 um).  The tile/root E faces carry
no other pins.  Also regenerates the die clock H-tree for the R1 outline (root moves to the new die centre)."""
import argparse, copy, json, shutil, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "tools/die_plan"))
import path_hbm_b2p as PB  # noqa: E402
import schema as S  # noqa: E402
import check as C  # noqa: E402

M6_Y0, M6_P = 2.208, 0.256        # root W-face M6 track lattice (pins af59c2f2/e77bfa9c)
EDGE = 0.019


def e_mid(w, h, k=0):
    i = round((h / 2 - M6_Y0) / M6_P) + 2 * k
    return round(w - EDGE, 3), round(M6_Y0 + M6_P * i, 3)


def repin(out, rel, names, w, h, log):
    p = out / rel
    pins = json.loads(p.read_text())
    taken = {(q["layer"], round(q["x"], 3), round(q["y"], 3)) for q in pins if q["name"] not in names}
    east = [q for q in pins if q["x"] > w - 1.0 and q["name"] not in names]
    if east:
        raise ValueError(f"{rel}: E face not empty ({len(east)} pins) -- clock pin move needs a new plan")
    got = []
    for k, nm in enumerate(names):
        q = next(q for q in pins if q["name"] == nm)
        old = dict(q)
        x, y = e_mid(w, h, k)
        if ("M6", x, y) in taken:
            raise ValueError(f"{rel}: {nm} target occupied")
        q.update(layer="M6", x=x, y=y)
        got.append(dict(pin=nm, old=[old["layer"], old["x"], old["y"]], new=["M6", x, y]))
    p.write_text(json.dumps(pins) + "\n")
    log[rel] = dict(moved=got, sha256=PB.sha(p))


def hop_table(T, pinsets):
    HC = {c["inst"]: c for c in T["hard_cores"]}
    tapxy = {}
    for inst, c in HC.items():
        if not inst.startswith("u_tkm_SW_"):
            continue
        clk = pinsets[c["module"]]
        tapxy[inst] = PB.xform(clk, c["origin_um"], c.get("orient", "R0"), *c["outline_um"])
    ptap = T["clock"]["tap_um"]
    pairs = [("u_tkm_SW_root", "u_tkm_SW_tile0")] + [(f"u_tkm_SW_tile{k}", f"u_tkm_SW_tile{k + 1}") for k in range(31)]
    rows = []
    for a, b in pairs:
        same = round(HC[a]["origin_um"][0], 2) == round(HC[b]["origin_um"][0], 2)
        d = abs(tapxy[a][0] - tapxy[b][0]) + abs(tapxy[a][1] - tapxy[b][1])
        da = abs(tapxy[a][0] - ptap[0]) + abs(tapxy[a][1] - ptap[1])
        db = abs(tapxy[b][0] - ptap[0]) + abs(tapxy[b][1] - ptap[1])
        rows.append(dict(launch=a, capture=b, kind="column" if same else "turn", tap_launch=tapxy[a],
                         tap_capture=tapxy[b], tap_dist_um=round(d, 2), root_dist_um=[round(da, 1), round(db, 1)],
                         root_dist_delta_um=round(db - da, 1), both_dirs=True))
    return tapxy, dict(partition_tap_um=ptap, pairs=rows, worst_tap_dist_um=max(r["tap_dist_um"] for r in rows),
                       worst_turn_um=max(r["tap_dist_um"] for r in rows if r["kind"] == "turn"),
                       worst_column_um=max(r["tap_dist_um"] for r in rows if r["kind"] == "column"),
                       rule="GEOM-REVIEW-2 11:35 R1 (3): every chain hop launch/capture taps <= ~400 um; related-pair "
                            "skew <= 20 ps after CPPR (decision 5); hops are face flop -> face flop in both directions")


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--src", required=True)
    a.add_argument("--out", required=True)
    a.add_argument("--no-clock", action="store_true", help="skip the die H-tree regeneration")
    x = a.parse_args()
    src, out = Path(x.src), Path(x.out)
    if out.exists():
        raise ValueError("new output directory required")
    out.mkdir(parents=True)
    for p in src.iterdir():
        if p.name.startswith("g0") or p.name in ("gates", "die_plan.json") or p.suffix in (".log", ".exit"):
            continue
        (shutil.copytree if p.is_dir() else shutil.copy2)(p, out / p.name)
    plan = json.loads((src / "die_plan.json").read_text())
    T = plan["partition_types"]["root"]
    HC = {c["inst"]: c for c in T["hard_cores"]}
    w, h = HC["u_tkm_SW_tile0"]["outline_um"]
    assert HC["u_tkm_SW_root"]["outline_um"] == [w, h], "root cell must share the tile outline"
    log = dict(src=str(src), src_plan_sha256=PB.sha(src / "die_plan.json"), pins={})
    _, before = hop_table(T, {PB.TILE_M: (159.84, 345.581), PB.TERM_M: (159.84, 345.581), PB.ROOT_M: (6.264, 0.019)})
    repin(out, HC["u_tkm_SW_tile0"]["pins_file"], ["tile_clk"], w, h, log["pins"])
    repin(out, HC["u_tkm_SW_tile31"]["pins_file"], ["tile_clk"], w, h, log["pins"])
    repin(out, HC["u_tkm_SW_root"]["pins_file"], ["clk", "buffer_clk"], w, h, log["pins"])
    clk = e_mid(w, h)
    tapxy, after = hop_table(T, {PB.TILE_M: clk, PB.TERM_M: clk, PB.ROOT_M: clk})
    n = 0
    for tp in T["clock"]["taps"]:
        if tp["name"] in tapxy:
            tp["xy"] = tapxy[tp["name"]]
            tp["note"] = (tp.get("note", "") + " | PATH-HBM TKMCLK: E-face mid clock pin (M6), MX-invariant").lstrip(" |")
            n += 1
    if n != 33:
        raise ValueError(f"expected 33 TKM core taps, updated {n}")
    log["cts_hop_table_before"] = dict(worst_tap_dist_um=before["worst_tap_dist_um"], worst_turn_um=before["worst_turn_um"])
    log["cts_hop_table"] = after
    if not x.no_clock:
        import b2m
        clog = []
        b2m.clock(plan, out, clog)
        ch = json.loads((out / "clock_htree.json").read_text())
        log["htree"] = dict(root_um=ch["root_um"], die_centre_x=plan["die"]["outline_um"][0] / 2,
                            summary={k: v for k, v in ch["summary"].items() if not isinstance(v, list)})
    P = S.Plan(plan, out / "die_plan.json")
    R = C.Report()
    log["station_sites"] = C.check_station_sites(P, R)
    log["lane_cycle_delta"] = {}
    plan["note"] = plan.get("note", "") + " | PATH-HBM TKMCLK: TKM core clock pins E-mid M6 (chain hop taps <= 354.24 um)"
    (out / "die_plan.json").write_text(json.dumps(plan, indent=1) + "\n")
    log["out_plan_sha256"] = PB.sha(out / "die_plan.json")
    (out / "tkm_clk_report.json").write_text(json.dumps(log, indent=1) + "\n")
    print(json.dumps(dict(before=log["cts_hop_table_before"],
                          after=dict(worst=after["worst_tap_dist_um"], turn=after["worst_turn_um"], col=after["worst_column_um"]),
                          pins=log["pins"], htree=log.get("htree"), plan=log["out_plan_sha256"][:12]), indent=1, default=str))


if __name__ == "__main__":
    main()
