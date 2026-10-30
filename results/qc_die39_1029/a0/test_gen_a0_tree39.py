"""DIE-QC-39 A0: gen_a0_tree39.py opt-in standard stages.
  * default (no new flag): slice, report and stdout byte-identical to gen_a0_tree21.py (DIE-QC-37) on a synthetic kit
    (the real NL/NK kits were checked on intel2: sha256 equal to the DIE-QC-37 V2 slices, README section 3);
  * --std-leg: equal total stage counts kept, median planned node leg inside the window, measured early-tap stage
    written to core_tree.early_tap_stage_ps, report block std_stage;
  * flag misuse refused.
Run: python3 -I test_gen_a0_tree39.py   (or pytest)"""
import gzip, json, random, subprocess, sys, tempfile, statistics
from pathlib import Path
HERE = Path(__file__).resolve().parent
GEN21 = HERE.parent.parent / "qc_die37_1029" / "a0" / "gen_a0_tree21.py"
GEN39 = HERE / "gen_a0_tree39.py"
LIB = """library(x) { cell(ot_qwen_tile_romleaf) { pin(clk) { timing() { timing_type : min_clock_tree_path;
  cell_rise(scalar) { values("%s"); } cell_fall(scalar) { values("%s"); } }
  timing() { timing_type : max_clock_tree_path;
  cell_rise(scalar) { values("%s"); } cell_fall(scalar) { values("%s"); } } } } }
"""


def kit(root):
    k = Path(root) / "kit"; (k / "macros").mkdir(parents=True)
    (k / "master_slice.json").write_text(json.dumps({"core_clock_port": "ck", "x": 1}))
    (k / "freeze.json").write_text(json.dumps({"hard_children": [
        {"inst": "u_rom/u_leaf", "master": "ot_qwen_tile_romleaf", "at": [300.0, 300.0], "orient": "R0"}]}))
    (k / "macros" / "ot_qwen_tile_romleaf.lef").write_text(
        "MACRO ot_qwen_tile_romleaf\n SIZE 40 BY 40 ;\n PIN clk\n  PORT\n   LAYER M4 ;\n    RECT 19 19 21 21 ;\n END\nEND\n")
    (k / "macros" / "ot_qwen_tile_romleaf_ff.lib").write_text(LIB % (190.35, 199.70, 243.27, 256.77))
    (k / "macros" / "ot_qwen_tile_romleaf_tt.lib").write_text(LIB % (245.10, 263.91, 301.85, 324.14))
    rng = random.Random(7)
    lines = ["die 457.92 1157.76", "port ck 228.948 578.64"]
    S = lambda path, d, inst, pin, m, x, y: "\t".join(["S", path, str(d), inst, pin, m, f"{x:.3f}", f"{y:.3f}", "PLACED"])
    lines.append(S("root", 0, "g_m/u_icg", "CLK", "ICGx8DC_ASAP7_75t_R", 100.0, 900.0))
    lines.append(S("root>g_m/u_icg", 1, "u_rom/u_leaf", "clk", "ot_qwen_tile_romleaf", 320.0, 320.0))
    for g, (cx, cy, n) in {"g_a/u_icg": (100, 200, 60), "g_b/u_icg": (350, 1000, 45)}.items():
        lines.append(S("root", 0, g, "CLK", "ICGx8DC_ASAP7_75t_R", cx + 10, cy - 10))
        for i in range(n):
            lines.append(S("root>" + g, 1, f"{g.split('/')[0]}_r{i}", "CLK", "DFFHQNx1_ASAP7_75t_R",
                           cx + rng.uniform(-40, 40), cy + rng.uniform(-40, 40)))
    for i in range(50):
        lines.append(S("root", 0, f"rr{i}", "CLK", "DFFHQNx1_ASAP7_75t_R", rng.uniform(20, 440), rng.uniform(20, 1140)))
    with gzip.open(Path(root) / "census.tsv.gz", "wt") as f:
        f.write("\n".join(lines) + "\n")
    return k, Path(root) / "census.tsv.gz"


def run(gen, k, census, out, *extra, ok=True):
    p = subprocess.run([sys.executable, "-I", str(gen), "--kit", str(k), "--census", str(census), "--out", str(out) + ".json",
                        "--report", str(out) + "_rep.json", *extra], capture_output=True, text=True)
    assert (p.returncode == 0) == ok, p.stderr[-2000:]
    return p


def test_default_off_byte_identical():
    with tempfile.TemporaryDirectory() as td:
        k, c = kit(td)
        for args in (["--stages", "21", "--leg", "100", "--reg-domains", "planned"],
                     ["--stages", "21", "--leg", "150", "--reg-domains", "open"],
                     ["--stages", "24", "--leg", "100", "--reg-domains", "planned", "--dpl-max", "40"]):
            a = run(GEN21, k, c, Path(td) / "a", *args); b = run(GEN39, k, c, Path(td) / "b", *args)
            assert a.stdout == b.stdout
            for suf in (".json", "_rep.json"):
                assert (Path(td) / ("a" + suf)).read_bytes() == (Path(td) / ("b" + suf)).read_bytes(), (args, suf)


def test_std_stage_mode():
    with tempfile.TemporaryDirectory() as td:
        k, c = kit(td)
        run(GEN39, k, c, Path(td) / "s", "--stages", "22", "--leg", "100", "--reg-domains", "planned", "--std-leg", "50",
            "--std-max", "60", "--leaf-max", "12", "--stage-ff", "25.02", "--stage-tt", "32.10", "--stage-src", "unit")
        sl = json.loads((Path(td) / "s.json").read_text())["core_tree"]
        rep = json.loads((Path(td) / "s_rep.json").read_text())
        assert list(rep["geometry"]["total_stage_counts"]) == ["22"]           # equal total stage count kept
        assert sl["early_tap_stage_ps"] == {"TT": 32.10, "FF": 25.02, "source": "unit"}
        assert rep["early"][0]["k"] == 9                                       # romleaf FF mid 223.56 / 25.02
        st = rep["std_stage"]; assert st["std_leg"] == 50.0 and st["leaf_max"] == 12
        xy = {n["name"]: n["xy_um"] for n in sl["nodes"]}; xy.update({g["inst"]: g["xy_um"] for g in sl["gates"]})
        par = {n["name"]: n["parent"] for n in sl["nodes"]}; par.update({g["inst"]: g["parent"] for g in sl["gates"]})
        legs = [abs(xy[p][0] - xy[n][0]) + abs(xy[p][1] - xy[n][1]) for n, p in par.items() if p != "port:ck"]
        assert 40 <= statistics.median(legs) <= 60
        assert max(len(l["sinks"]) for l in sl["leaves"] if l.get("load_class") != "macro") <= 12
        assert "DIE-QC-39" in sl["note"]


def test_flag_misuse_refused():
    with tempfile.TemporaryDirectory() as td:
        k, c = kit(td)
        base = ["--stages", "21", "--leg", "100", "--reg-domains", "planned"]
        run(GEN39, k, c, Path(td) / "x", *base, "--std-split", "0.5", ok=False)
        run(GEN39, k, c, Path(td) / "x", *base, "--std-fan", "2", ok=False)
        run(GEN39, k, c, Path(td) / "x", *base, "--stage-ff", "25", "--stage-tt", "32", ok=False)


if __name__ == "__main__":
    for f in (test_default_off_byte_identical, test_std_stage_mode, test_flag_misuse_refused):
        f(); print("OK", f.__name__)
