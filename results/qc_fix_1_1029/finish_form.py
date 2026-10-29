"""QC-FIX-1: plan record -> legal planned slice -> kit inputs for one BTAB form (F1 / F2).
Same steps as Codex convert_turn.sh + legalize_turn.py + make_turntree.py (codex-qc-btab-compact), parametrized; main tools.
usage: finish_form.py D T FORM TREE_WORK RECIPE_EXTRA_JSON"""
import json, subprocess, sys
from pathlib import Path

D, T, form, W = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3], Path(sys.argv[4])
extra = json.loads(sys.argv[5])
sys.path[:0] = [str(T / "tools/die_plan"), str(T / "tools/autopilot")]
import core_infra_plan as CP, core_infra as CI, geom_rules as G  # noqa: E402

F = D / form; F.mkdir(exist_ok=True)
IN = D / "in"
planned = F / "planned.json"
r = subprocess.run([sys.executable, str(T / "tools/die_plan/core_plan_to_infra.py"), str(W / "plan.json"), "--sites", str(W / "sites.txt"),
                    "--module", "qfd_dv_s8x_btab", "--clock-port", "ck", "--die", "qwen_compute", "--outline", "293.76,155.52",
                    "--ndr", "none", "--band", "info", "--window-policy", "info", "--out", str(planned)], capture_output=True, text=True)
(F / "convert.log").write_text(r.stdout + r.stderr)
if r.returncode:
    raise SystemExit("convert rc %d: %s" % (r.returncode, (r.stdout + r.stderr)[-800:]))
s = json.load(open(planned)); orig = json.load(open(IN / "turntree_slices/qfd_dv_s8x_btab.json"))
s["pushdown"] = orig["pushdown"]
s["master_plan_sha256"] = "QC-FIX-1 %s BTAB candidate (turntree outline/pins); current QC event unchanged" % form
tech = dict(dbu=1000, rows=[], masters={}, obstacles=[], core=[4320, 4320, 289440, 151200]); sw = .054; rh = .27
for l in open(W / "sites.txt"):
    f = l.split()
    if f[:1] == ["ROW0"]: sw = float(f[4]); rh = float(f[6])
    if f[:1] == ["ROW"]:
        x, y = float(f[1]), float(f[2]); n = int(f[4])
        tech["rows"].append(dict(rect=[round(1000 * x), round(1000 * y), round(1000 * (x + n * sw)), round(1000 * (y + rh))], site=round(sw * 1000), orient=f[3]))
    if f[:1] == ["MASTER"]: tech["masters"][f[1]] = [round(float(v) * 1000) for v in f[2:4]]
    if f[:1] == ["FIXED"]:
        rr = [round(float(v) * 1000) for v in f[3:7]]
        tech["obstacles"].append(dict(name=f[1], kind="macro" if rr[3] - rr[1] > 1.5 * rh * 1000 else "fixed", rect=rr))
geo = G.Design(Path(sys.argv[6]) if len(sys.argv) > 6 else IN / "turntree_geom.tsv")
tech["obstacles"] += json.load(open(IN / "actual_turn_blockages.json"))
for c in geo.cells.values(): tech["masters"].setdefault(c[1], [round(1000 * (c[4] - c[2])), round(1000 * (c[5] - c[3]))])
root0 = next(n for n in s["core_tree"]["nodes"] if n["parent"] == "port:ck")["xy_um"]; entry0 = s["islands"][0]["clock_pin"]["xy_um"]
new, report = CP.legalize_slice(s, tech, macro_halo_um=4.32)
root = next(n for n in new["core_tree"]["nodes"] if n["parent"] == "port:ck")["xy_um"]
snap = lambda z: round(.012 + .048 * round((z - .012) / .048), 6)
new["islands"][0]["clock_pin"]["xy_um"] = [snap(entry0[j] + root[j] - root0[j]) for j in [0, 1]]
viol = []
for n, p in new["cell_placements"].items():
    x, y = p["origin_um"]; w, h = p["size_um"]
    for z in tech["obstacles"]:
        a, b, c, d = [v / 1000 for v in z["rect"]]; halo = 4.32 if z["kind"] == "macro" else 0
        if x < c + halo - 1e-6 and x + w > a - halo + 1e-6 and y < d + halo - 1e-6 and y + h > b - halo + 1e-6: viol.append([n, z["name"]])
assert not viol, viol
comp = CI.compile_slice(new); pg = CI.trunk_pg_clearance(new, comp); assert pg["verdict"] in ["PASS", "NOT APPLICABLE"], pg; CI.emit_tcl(new)
report.update(placement_obstacle_overlaps=0, macro_halo_um=4.32, clock_pin_um=new["islands"][0]["clock_pin"]["xy_um"], root_um=root, pg_clearance=pg["verdict"])
new["plan_conversion"]["actual_placement_obstacles_legalization"] = {k: v for k, v in report.items() if k != "moves"}
(F / "slices").mkdir(exist_ok=True)
(F / "slices/qfd_dv_s8x_btab.json").write_text(json.dumps(new, indent=1) + "\n")
(F / "legalization.json").write_text(json.dumps(report, indent=1) + "\n")
# plan: core clock pin + parent tap follow the legalized clock pin (make_turntree.py form)
ck = new["islands"][0]["clock_pin"]["xy_um"]
p = json.load(open(IN / "plan/turn_clock.json")); pins = json.load(open(IN / "plan/cores/su/qfd_dv_s8x_btab_pins_turntree.json"))
for v in pins["pins"]:
    if v["name"] == "ck": v["x"], v["y"] = ck
pd = F / "plan"; subprocess.run(["rm", "-rf", str(pd)]); subprocess.run(["cp", "-r", str(IN / "plan"), str(pd)], check=True)
pf = "cores/su/qfd_dv_s8x_btab_pins_%s.json" % form
(pd / pf).write_text(json.dumps(pins, indent=1) + "\n")
for t in p["partition_types"].values():
    for c in t.get("hard_cores", []):
        if c["module"] == "qfd_dv_s8x_btab":
            c["pins_file"] = pf
            for tap in t["clock"]["taps"]:
                if tap.get("name") == c["inst"] + ".ck": tap["xy"] = [round(c["origin_um"][j] + ck[j], 6) for j in [0, 1]]
(pd / "turn_clock.json").write_text(json.dumps(p, indent=1) + "\n")
rc = json.load(open(IN / "turntree_recipe.json")); v = dict(next(iter(rc.values())))
v.update(suffix=form, hold_ff_margin=15.0, **extra)
v["_why"] = "QC-FIX-1 %s: turntree outline/pins/macros; tree re-planned by core_family_slice.py from the census placement %s; measured hold + FF hold margin 15. UNADOPTED candidate." % (form, sys.argv[6] if len(sys.argv) > 6 else "")
(F / "recipe.json").write_text(json.dumps({"qfd_dv_s8x_btab__" + form: v}, indent=1) + "\n")
print(json.dumps(dict(form=form, clock_pin=ck, root=root, **{k: v for k, v in report.items() if k not in ("moves",)})))
