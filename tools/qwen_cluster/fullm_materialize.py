"""QW-CB16A0 10-20: materialise the qfd_c_b16_fullm(b) kit inputs from the PROVEN joint solutions.

  hard children  <- grid43/<name>_joint_solution.json  (all origins on 43.2; data replay PASS)
  ring bays      <- the same joint solution (7-column bay lines -> EXCLUSIVE legal regions, fabric_sites_place_m.tcl)
  scalar FF sites <- grid43/<name>_control_solution.json (fullm_control_ac.py; independent replay ctl_replay.py PASS)
Writes physical/qcluster/<name>_sites.tsv and updates the children 'at' of tools/ref_tile/specs_qcluster/<name>.json.
Refuses unless the data replay and the control replay are PASS for exactly these solution files.
"""
import json, sys, hashlib, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]; G = ROOT / "results/arch/qw_cb16_legal_bays_1020/grid43"
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
for name in sys.argv[1:]:
    js = G / f"{name}_joint_solution.json"; cs = G / f"{name}_control_solution.json"
    dr = json.loads((G / f"{name}_data_replay.json").read_text()); cr = json.loads((G / f"{name}_control_replay.json").read_text())
    assert dr["status"] == "PASS" and dr["solution_sha256"] == sha(js), "data replay not PASS for this joint solution"
    assert cr["status"] == "PASS" and cr["solution_sha256"] == sha(cs), "control replay not PASS for this control solution"
    sol = json.loads(js.read_text()); pos = json.loads(cs.read_text())["pos"]
    raw = (G / f"{name}_joint_raw_sites.tsv").read_text().splitlines()
    spec_p = ROOT / "tools/ref_tile/specs_qcluster" / f"{name}.json"; spec = json.loads(spec_p.read_text())
    W = spec["outline"]["w"]
    out = ["# prefix\tx\ty\txlo\txhi[\tylo\tyhi]  (fullm_materialize.py: joint 43.2 hard + bay solution, control_ac scalar sites)"]
    done = set(); nb = 0; dup = 0
    for l in raw:
        if not l or l.startswith("#"): continue
        f = l.split("\t")
        if len(f) == 7:
            assert f[0] in sol["bays"], f[0]; x, y, w, h = sol["bays"][f[0]]
            assert abs(float(f[3]) - x) < 1e-3 and abs(float(f[5]) - y) < 1e-3, ("bay line differs from joint solution", f[0])
            out.append(l); nb += 1; continue
        if f[0] in sol["bays"]:
            dup += 1; continue          # stale diag compact-block line of a pad ring half that HAS a bay: the bay region owns it
        if f[0] in pos:
            x, y = pos[f[0]]; done.add(f[0])
            out.append(f"{f[0]}\t{x:.3f}\t{y:.3f}\t{max(0.0, x - 15):.3f}\t{min(W, x + 15):.3f}")
        else:
            raise SystemExit(f"site line {f[0]} is neither a joint bay nor a solved scalar FF")
    for n in sorted(set(pos) - done):
        x, y = pos[n]; out.append(f"{n}\t{x:.3f}\t{y:.3f}\t{max(0.0, x - 15):.3f}\t{min(W, x + 15):.3f}")
    (ROOT / f"physical/qcluster/{name}_sites.tsv").write_text("\n".join(out) + "\n")
    moved = 0
    for c in spec["children"]:
        hx, hy = sol["hard"][c["inst"]][:2]
        if abs(c["at"][0] - hx) > 1e-6 or abs(c["at"][1] - hy) > 1e-6: moved += 1
        c["at"] = [hx, hy]; c["at_exact"] = True
    assert len(spec["children"]) == len(sol["hard"])
    spec["structural_change"] = spec["structural_change"].split(" | QW-CB16A0")[0] + (
        " | QW-CB16A0 10-20 fullm: hard origins = CP-SAT joint station/bay solution on 43.2 (all-bit hard/soft/bank data <=405, "
        "independent replay PASS), ring bays = EXCLUSIVE legal regions (GPL owns ring cells, no FIRM ring blocks), every scalar "
        "reset/control FF at an arc-consistent legal site (all control edges <=385 planned, replay PASS); no data multicycle.")
    spec_p.write_text(json.dumps(spec, indent=1) + "\n")
    print("MATERIALIZE", name, "bays", nb, "dropped stale pad-half block lines", dup, "scalar", len(pos), "children moved", moved)
