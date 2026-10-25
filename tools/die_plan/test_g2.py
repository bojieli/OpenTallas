"""G2 probe generation tests (no OpenROAD run).   python3 -m pytest -q tools/die_plan/"""
import json
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import g2  # noqa: E402
import schema  # noqa: E402

PAIR = json.loads((HERE / "examples" / "s81_pair" / "s81_pair_plan.json").read_text())

LOG = """
[INFO GRT-0096] Final congestion report:
Layer         Resource        Demand        Usage (%)    Max H / Max V / Total Overflow
---------------------------------------------------------------------------------------
M2              113413          1000            0.88%             0 /  0 /  0
M8               20000          4000           20.00%             1 /  0 /  3
Total           133413          5000            3.75%             1 /  0 /  3
[INFO GRT-0018] Total wirelength: 94217 um
OT_REACH clk max 717.1 p90 717.1 n 2
#stdCellPinNoAp        = 2
[INFO DRT-0166] Complete pin access.
OT_DONE
"""


def test_parse():
    r = g2.parse_grt(LOG)
    assert r["total_overflow"] == 3 and r["layers"]["M8"]["overflow"] == 3 and r["wirelength_um"] == 94217
    assert r["reach"]["clk"]["max_um"] == 717.1 and r["pin_access_no_ap"] == {"stdCell": 0, "stdCellPin": 2} or \
        r["pin_access_no_ap"]["stdCellPin"] == 2
    assert r["done"] and r["pin_access_done"]


def test_die_probe_files():
    P = schema.Plan(PAIR)
    with tempfile.TemporaryDirectory() as d:
        out = g2.die_probe(P, d)
        tcl = (out / "probe.tcl").read_text()
        assert "clk_tap_pfa" in tcl and "rst_tap_pfb" in tcl
        assert tcl.count("create_obstruction") > 2 * 7          # partitions on M1-M7 + PG stripes
        assert "set_routing_layers -signal M8-M9" in tcl
        meta = json.loads((out / "probe.json").read_text())
        grid = sum(len(schema.tap_grid(P, p["type"])) for p in P.parts.values())     # R4 tap grid per partition
        assert meta["taps"] == grid and grid > 2 and meta["pg_stripes"] > 100


def test_part_probe_files_and_worst():
    P = schema.Plan(PAIR)
    R, summ = check.run(PAIR)
    sel = g2.worst_types(P, summ, 1)
    assert len(sel) == 1 and sel[0][0] in ("fa", "fb")
    with tempfile.TemporaryDirectory() as d:
        out = g2.part_probe(P, "fa", d)
        meta = json.loads((out / "probe.json").read_text())
        # boundary flops for din (64), x_o (277), r_i (71) + 4 stations per bit of fz (4 x 65; R3 <= 405 um)
        import gen_phys
        nt = len(gen_phys.tap_pins(P, "fa"))                    # R4 clock tap grid + the reset tap
        assert nt == len(schema.tap_grid(P, "fa")) + 1 and nt > 2
        assert meta["flops"] == 64 + 277 + 71 + 4 * 65 + nt      # + one tap buffer per clock / reset tap
        v = (out / "probe.v").read_text()
        assert "st_fz_64_0" in v and "CLK" not in v
        assert (out / "io.tcl").read_text().count("place_pin") == 64 + 277 + 71 + 64 + 65 + nt  # fz_i from die IO: no epoch


def test_assembly_die_flow():
    import gen_phys
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "views").mkdir()
        kd = gen_phys.write_assembly(PAIR, d, str(Path(d) / "views"))
        kd = Path(d) / "die"
        tcl = (kd / "die_flow.tcl").read_text()
        assert "findInst {pfb}]" in tcl and "setLocation [expr {round(1434.24 * $_d)}] [expr {round(0 * $_d)}]" in tcl and "detailed_route" in tcl
        v = (kd / "die_top_struct.v").read_text()
        assert "endmodule :" not in v and "w_x" in v
        assert (kd / "seams.json").is_file() and (kd / "abut_audit.py").is_file() and (kd / "run_die.sh").is_file()


def test_coincident_taps_split():
    import copy
    import gen_phys
    raw = copy.deepcopy(PAIR)
    t = raw["partition_types"][0] if isinstance(raw["partition_types"], list) else next(iter(raw["partition_types"].values()))
    ck = t.setdefault("clock", {}).setdefault("tap_um", [700.0, 1800.0])
    t.setdefault("reset", {})["tap_um"] = list(ck)
    P = schema.Plan(raw)
    tn = t.get("name") or next(iter(P.types))
    a, b = gen_phys.tap_points(P, tn)
    assert a != b and abs(a[1] - b[1]) > 8


def test_seam_audit_catches_or11810():
    """OR#11810: an M4 pin touching an M5 pin counts as 'abutted' on images without #11814; the seam audit must FAIL it
    and PASS the same-layer seam.  Needs docker + openroad/orfs:asap7lock (skipped otherwise)."""
    import shutil
    import subprocess
    import pytest
    if not shutil.which("docker"):
        pytest.skip("no docker")
    with tempfile.TemporaryDirectory() as d:
        src = HERE / "examples" / "abut_layer_bug"
        for f in ("blk.lef", "t.v", "t.tcl", "seams.json"):
            shutil.copy(src / f, d)
        shutil.copy(HERE / "abut_audit.py", d)
        cmd = ("source /OpenROAD-flow-scripts/env.sh >/dev/null 2>&1; openroad -exit /w/t.tcl >/dev/null 2>&1; "
               "ODB=/w/t.odb SEAMS=/w/seams.json OUT=/w/a.json DRC=/none openroad -python -exit /w/abut_audit.py; "
               "chmod -R a+rwX /w")
        r = subprocess.run(["docker", "run", "--rm", "--memory=4g", "--memory-swap=4g", "-v", f"{d}:/w",
                            "openroad/orfs:asap7lock", "bash", "-lc", cmd], capture_output=True, text=True, timeout=600)
        if r.returncode and "Unable to find image" in r.stderr:
            pytest.skip("image missing")
        a = json.loads((Path(d) / "a.json").read_text())
        assert a["ok"] == 1 and a["fails"] == {"abut_no_same_layer_overlap": 1}


def test_pins_avoid_partition_pg_stripes():
    P = schema.Plan(PAIR)
    n = 0
    for pid in P.ports:
        for bit, ln, c in P.port_pins(pid):
            assert not schema.pg_blocked(ln, c), (pid, bit, ln, c)
            n += 1
    assert n > 500
    # band geometry: M6 VDD 1.968 +- 0.144 / VSS 2.352 +- 0.144 must be blocked, a mid-gap track free
    assert schema.pg_blocked("M6", 1.968) and schema.pg_blocked("M6", 2.352) and not schema.pg_blocked("M6", 4.0)


def test_spread_uniform_at_budget_density():
    """PLAN-HBM 10-23: a window sized at exactly the 6/um budget must pass the G0 face check (the old spreader packed
    pins up to 1.2x the window average)."""
    import copy
    import check
    raw = copy.deepcopy(PAIR)
    pr = next(p for p in raw["ports"] if p["id"] == "x")
    n = pr["width"] + 1                                   # + epoch
    lo = 1800.0
    pr["window_um"] = [lo, lo + n / 6.0]                  # exactly 6 pins/um over 2 layers
    P = schema.Plan(raw)
    pins = sorted(c for _, _, c in P.port_pins("x"))
    assert len(pins) == n
    win = 10.0
    mx = max(sum(1 for c in pins if a <= c < a + win) for a in pins)
    assert mx <= 6 * win + 4, mx                          # check.py allowance: 2 pins per layer
    R, summ = check.run(raw)
    assert not [f for f in R.errors() if f["check"] == "faces"], R.errors()
    # uniform: per layer most gaps are the window average (1/3 um) to within one track; the rest sit at PG bands
    for ln in pr["layers"]:
        cs = sorted(c for _, l, c in P.port_pins("x") if l == ln)
        gaps = [b - a for a, b in zip(cs, cs[1:])]
        near = sum(1 for g in gaps if abs(g - 1 / 3.0) <= 0.065)
        assert near >= 0.6 * len(gaps), (ln, near, len(gaps))


def test_window_for_fits_after_pg_bands():
    L = {x["name"]: x for x in schema.ASAP7_LAYERS}
    for lo in (2.0, 4.1, 100.3):
        for n in (1, 2, 9, 141):
            hi = schema.window_for(lo, n, ["M7", "M5"])
            port = dict(id="t", width=n, window_um=[lo, hi], layers=["M7", "M5"], epoch=False)
            assert len(schema.pin_positions(port, L)) == n


def test_kit_overrides_platform_tracks():
    import gen_phys
    import tempfile
    P = schema.Plan(json.loads((HERE / "examples" / "tiny_plan.json").read_text()))
    with tempfile.TemporaryDirectory() as d:
        kd = gen_phys.write_type_kit(P, "src", d, [])
        cfg = (kd / "config.mk").read_text()
        assert "override export MAKE_TRACKS = /work/make_tracks.tcl" in cfg
        # CP1 10-23: pin registers FIRM at their faces through GPL, released before DPL
        assert "export PRE_GLOBAL_PLACE_TCL = /work/face_flops.tcl" in cfg
        assert "export PRE_DETAIL_PLACE_TCL = /work/face_flops_release.tcl" in cfg
        assert (kd / "face_flops.tcl").is_file() and (kd / "face_flops_release.tcl").is_file()
        # COORD 10-23: tap trees balanced to the plan insertion after CTS
        assert "export POST_CTS_TCL = /work/tap_balance.tcl" in cfg and "export OT_TAP_TARGET_PS = 250" in cfg
        assert "export OT_TAP_WINDOW_PS = 20" in cfg and "export OT_TAP_TOL_PS = 10" in cfg and "export CORNER = TC" in cfg
        assert (kd / "tap_balance.tcl").is_file()


def test_die_sta_flat_in_opensta_etm_with_tech():
    """CP1 10-23: openroad link_design needs a technology (ORD-2010) and flattens the hierarchy, so read_spef -path
    <instance> finds nothing (STA-0276).  FLAT runs in standalone OpenSTA without LEF; ETM reads tech + abstracts."""
    import gen_phys
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "views").mkdir()
        gen_phys.write_assembly(PAIR, d, str(Path(d) / "views"))
        kd = Path(d) / "die"
        sta = (kd / "sta_die.tcl").read_text()
        etm = sta.split('if {$MODE == "etm"} {', 1)[1].split("}", 1)[0]
        assert "asap7_tech_1x" in etm and sta.count("read_lef") == sta.count("read_lef", sta.index('if {$MODE == "etm"}'))
        assert "read_spef -path" in sta
        assert "T='sta -no_splash'" in (kd / "run_die.sh").read_text()


def test_spread_mirror_equivariant_on_ties():
    """PLAN-HBMv2: windows with edges between tracks put targets exactly half-way between two tracks; the pick must
    not depend on floating-point noise (die frame x vs W - x) and the odd middle pin must mirror."""
    L = {l["name"]: l for l in schema.ASAP7_LAYERS}
    W = 20217.6
    for ln, (lo, hi), n in (("M5", (4182.576, 4183.536), 2), ("M7", (4167.936, 4172.544), 13)):
        p = dict(id="t", window_um=[lo, hi], layers=[ln], width=n, epoch=False)
        q = dict(p, window_um=[W - hi, W - lo])
        a = sorted(round(c, 3) for _, _, c in schema.pin_positions(p, L))
        b = sorted(round(W - c, 3) for _, _, c in schema.pin_positions(q, L))
        assert a == b, (ln, a, b)


def test_part_cli_resolves_census_beside_plan(tmp_path, monkeypatch):
    """Worst-type selection must read plan-relative census files from any cwd."""
    import copy
    raw = copy.deepcopy(PAIR)
    plan_dir = tmp_path / "plan"
    plan_dir.mkdir()
    (plan_dir / "census.json").write_text("[]")
    (plan_dir / "map.json").write_text('{"parts": {}}')
    raw["census"] = [{"rows": "census.json", "map": "map.json"}]
    plan = plan_dir / "die_plan.json"
    plan.write_text(json.dumps(raw))
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    out = tmp_path / "probes"
    assert g2.main(["part", str(plan), "--out", str(out), "--worst", "1"]) == 0
    assert len(list(out.glob("part_*/probe.json"))) == 1


def test_die_probe_declared_taps_share_spine_and_transform_once(tmp_path):
    import copy
    raw = copy.deepcopy(PAIR)
    p = next(x for x in raw['partitions'] if x['name'] == 'pfa')
    p['orient'] = 'MY'
    tn = p['type']
    raw['partition_types'][tn]['clock']['taps'] = [
        dict(name='core.ck[0]', kind='core', xy=[10, 20], orient='MY', insertion_ps=250,
             insertion_tol_ps=40, budget_owner='declared core budget'),
        dict(name='glue', kind='glue', xy=[30, 40], insertion_ps=276, insertion_tol_ps=40)]
    out = g2.die_probe(schema.Plan(raw), tmp_path/'extra')
    tcl = (out/'probe.tcl').read_text()
    meta = json.loads((out/'probe.json').read_text())
    assert meta['partition_root_taps'] == 2 and meta['declared_clock_taps'] == 2
    assert meta['taps'] == meta['grid_taps'] + 2
    assert tcl.count('odb::dbNet_create') == 2  # same virtual clock/reset spines, no new regional clock net
    assert 'clk_tap_pfa__declared_0' in tcl and 'clk_tap_pfa' in tcl and 'rst_tap_pfa' in tcl
    tap = meta['declared_taps'][0]
    assert tap['name'] == 'core.ck[0]' and tap['insertion_ps'] == 250 and tap['orient'] == 'MY'
    width = raw['partition_types'][tn]['outline_um'][0]
    assert tap['xy_die_um'] == [width-10, 20]  # core MY was already applied in xy; only partition MY applies here
    assert f'{{{width-10:.3f} 20.000}}' in tcl
    assert 'not measured regional clock-tree' in meta['clock_scope']


def test_die_probe_empty_declared_taps_preserves_outputs(tmp_path):
    import copy
    original = g2.die_probe(schema.Plan(PAIR), tmp_path/'plain')
    raw = copy.deepcopy(PAIR)
    for t in raw['partition_types'].values():
        t.setdefault('clock', {})['taps'] = []
    empty = g2.die_probe(schema.Plan(raw), tmp_path/'empty')
    for name in ('probe.v', 'probe.tcl', 'probe.json', 'run.sh'):
        assert (original/name).read_bytes() == (empty/name).read_bytes()


def test_kit_places_content_macros(tmp_path):
    """COORD 10-23: partition kits place SRAM / ROM / hard cores at their plan sites (lef views)."""
    import copy
    import gen_phys
    import pytest
    raw = copy.deepcopy(json.loads((HERE / "examples" / "tiny_plan.json").read_text()))
    (tmp_path / "m.lef").write_text("VERSION 5.8 ;\n")
    (tmp_path / "m_tt.lib").write_text("library(m) {}\n")
    (tmp_path / "m_ff.lib").write_text("library(m_ff) {}\n")
    t = raw["partition_types"]["src"]
    t.setdefault("contents", []).append(dict(inst="u_sram", module="sram_m", status="planned", lef="m.lef", lib="m_tt.lib",
                                             origin_um=[17.28, 25.92], orient="MX"))
    t["hard_cores"] = [dict(inst="u_core", module="core_m", origin_um=[8.64, 8.64], outline_um=[8.64, 8.64],
                            track_offset_um=[0.0, 0.012], lef="m.lef", lib="m_tt.lib")]
    P = schema.Plan(raw)
    kd = gen_phys.write_type_kit(P, "src", tmp_path / "k", [], root=tmp_path)
    assert (kd / "macros/m_ff.lib").read_text() == "library(m_ff) {}\n"
    assert (kd / "face_keep.tcl").is_file()
    assert (kd / "face_keep_release.tcl").is_file()
    mp = (kd / "macro_place.tcl").read_text()
    assert "place_macro -macro_name {u_sram} -location {17.2800 25.9200} -orientation MX -exact" in mp
    assert "-macro_name {u_core} -location {8.6400 8.6520} -orientation R0" in mp
    cfg = (kd / "config.mk").read_text()
    assert "ADDITIONAL_LEFS = /work/macros/m.lef" in cfg and "MACRO_PLACEMENT_TCL = /work/macro_place.tcl" in cfg
    del t["hard_cores"][0]["lib"]
    with pytest.raises(ValueError, match="LEF but no timing liberty"):
        gen_phys.write_type_kit(schema.Plan(raw), "src", tmp_path / "missing_lib", [], root=tmp_path)
    assert not (tmp_path / "missing_lib").exists()
    t["hard_cores"][0]["lib"] = "m_ss.lib"
    with pytest.raises(ValueError, match="requires TT macro liberty"):
        gen_phys.write_type_kit(schema.Plan(raw), "src", tmp_path / "ss_lib", [], root=tmp_path)
    assert not (tmp_path / "ss_lib").exists()
    t["hard_cores"][0]["lib"] = "m_tt.lib"
    del t["contents"][-1]["origin_um"]
    with pytest.raises(ValueError):
        gen_phys.write_type_kit(schema.Plan(raw), "src", tmp_path / "k2", [], root=tmp_path)


def test_sdc_units_match_liberty():
    """KV-P3b 10-23 12:17: the ASAP7 libs are in ps; an SDC written in ns gave every plan kit a 0.833-ps clock.  Read
    the platform lib time / cap units and check the kit, assembly and die-STA SDCs against them."""
    import gzip
    import re
    import subprocess
    import gen_phys
    import pytest
    lib = "results/rtl/s81_ph_20261006/gather/root_selective_model_20261007/libs/asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz"
    try:
        raw_lib = subprocess.run(["git", "-C", str(HERE), "show", f"HEAD:{lib}"], capture_output=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        pytest.skip("platform liberty not in the repo history")
    head = gzip.decompress(raw_lib)[:20000].decode()
    tu = re.search(r'time_unit\s*:\s*"1(ps|ns)"', head).group(1)
    cu = re.search(r"capacitive_load_unit\s*\(\s*1\s*,\s*(fF|pF|ff|pf)\s*\)", head).group(1).lower()
    assert (tu, cu) == ("ps", "ff") and gen_phys.LIB_TIME_UNIT_PS == 1.0 and gen_phys.LIB_CAP_UNIT_FF == 1.0
    P = schema.Plan(json.loads((HERE / "examples" / "tiny_plan.json").read_text()))
    per = float(P.die["period_ps"])
    sdc = gen_phys.sdc(P, "src", [])
    m = re.search(r"create_clock -name clk -period ([0-9.]+)", sdc)
    assert abs(float(m.group(1)) - per) < 1e-3, sdc
    assert f"set_clock_uncertainty {gen_phys.UNC_SETUP_PS:.4f} -setup" in sdc
    assert abs(float(re.search(r"set_clock_latency -source ([0-9.]+)", sdc).group(1)) - P.clock["insertion_ps"]) < 1e-3
    assert "set_load 2 [all_outputs]" in sdc
    with tempfile.TemporaryDirectory() as d:
        (Path(d) / "views").mkdir()
        gen_phys.write_assembly(PAIR, d, str(Path(d) / "views"))
        Q = schema.Plan(PAIR)
        for f in ("constraint.sdc", "sta_die.tcl"):
            t = (Path(d) / "die" / f).read_text()
            assert abs(float(re.search(r"-period ([0-9.]+)", t).group(1)) - float(Q.die["period_ps"])) < 1e-3, f


def test_per_tap_reset_synchronisers():
    """KV-P5 10-23: a multi-tap type gets one kept synchroniser per tap; every station / boundary flop (and a lane-source
    epoch) takes one of them, never a tap-0-only reset; the kit gets reset_taps.tcl sourced from face_flops.tcl."""
    import copy
    import re
    import shutil
    import subprocess
    import gen_rtl
    P = schema.Plan(PAIR)
    n = len(schema.tap_grid(P, "fa"))
    assert n > 2
    with tempfile.TemporaryDirectory() as d:
        gen_rtl.write_rtl(copy.deepcopy(PAIR), d)
        mod = P.types["fa"]["module"]
        v = (Path(d) / f"{mod}.sv").read_text()
        assert all(f"ot_dp_rsync_s2 u_rsync_t{i} " in v for i in range(n)) and "u_rst_sync" not in v
        rs = re.findall(r"ot_dp_ste? #\(\.W\(\d+\)\) \w+ \(\.clk\(clk\), \.rst_n\((\w+)\)", v)
        assert rs and set(rs) <= {f"rst_n_t{i}" for i in range(n)}
        # S81-P9: each boundary flop takes the synchroniser of the tap nearest its pins
        import gen_phys
        taps = schema.tap_grid(P, "fa")
        pins = {}
        for bn, _b, _l, x, y, _f in gen_phys.type_pins(P, "fa"):
            pins.setdefault(bn, []).append((x, y))
        for kind, bn, r in re.findall(r"ot_dp_ste? #\(\.W\(\d+\)\) u_(bin|bout)_(\w+?) \(\.clk\(clk\), \.rst_n\((\w+)\)", v):
            key = next((k for k in pins if gen_rtl.sv_id(k) == bn), None)
            if key is None:
                continue
            x = sum(p[0] for p in pins[key]) / len(pins[key])
            y = sum(p[1] for p in pins[key]) / len(pins[key])
            i = min(range(n), key=lambda k: abs(taps[k][1] - x) + abs(taps[k][2] - y))
            assert r == f"rst_n_t{i}", (bn, r, i)
        cells = Path(d) / "ot_dp_cells.sv"
        if shutil.which("yosys"):
            top = Path(d) / "t.sv"
            top.write_text("module t(input wire clk, input wire a, output wire y0, output wire y1);\n"
                           "  ot_dp_rsync_s2 u0(.clk(clk), .async_rst_n(a), .sync_rst_n(y0));\n"
                           "  ot_dp_rsync_s2 u1(.clk(clk), .async_rst_n(a), .sync_rst_n(y1));\nendmodule\n")
            r = subprocess.run(["yosys", "-p", f"read_verilog -sv {cells} {top}; synth -flatten -top t; stat"],
                               capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            assert re.search(r"ot_dp_rsync_s2\s+2", r.stdout), r.stdout       # identical copies are NOT merged
    ff = (HERE / "face_flops.tcl").read_text()
    assert "source /work/reset_taps.tcl" in ff and (HERE / "reset_taps.tcl").is_file()


def test_grid_is_default_and_sink_taps_only_add():
    """CP1 r8 RULING (COORD 10-23 21:26): the R4 tap GRID (<= 400 um, covering all sinks) is the default on every die;
    clock.tap_mode 'grid+sinks' / 'sinks' (KV-P6) only ADDS sink-anchored taps after the grid taps, never replaces
    them (CP1 r8: sink taps alone put 4.5-5.7k interior sinks on one tap, face-flop spread 133 ps)."""
    import copy
    import math
    import gen_phys
    import taps
    P0 = schema.Plan(copy.deepcopy(PAIR))
    w, h = PAIR["partition_types"]["fa"]["outline_um"]
    assert P0.budgets["tap_pitch_um"] == 400.0 and schema.tap_pitch(P0, "fa") == 400.0
    grid = schema.tap_grid(P0, "fa")
    assert len(grid) == math.ceil(w / 400.0) * math.ceil(h / 400.0) and grid[0][0] == "clk"
    for mode in ("grid+sinks", "sinks"):
        raw = copy.deepcopy(PAIR)
        raw["partition_types"]["fa"].setdefault("clock", {}).update(tap_mode=mode, tap_radius_um=120.0,
                                                                     tap_max_sinks=40)
        P = schema.Plan(raw)
        tl = schema.tap_grid(P, "fa")
        st = taps.sink_taps(P, "fa")
        assert st and all(t[3] > 0 for t in st)                                 # sink taps carry planned sinks
        assert tl[:len(grid)] == grid                                           # the grid stays, unchanged
        assert len(tl) > len(grid) and len(tl) <= len(grid) + len(st)           # sink taps are additions
        assert [n for n, _, _ in tl] == ["clk"] + [f"clk_t{i}" for i in range(1, len(tl))]
        assert all(0 < x < w and 0 < y < h for _, x, y in tl)
        assert schema.tap_pitch(P, "fa") == 400.0                               # grid pitch, not 2 x radius
        with tempfile.TemporaryDirectory() as d:
            gen_phys.write_type_kit(P, "fa", d, [])
            cfg = (Path(d) / "fa" / "config.mk").read_text()
            assert "OT_TAP_MAX_SINKS = 40" in cfg and "OT_TAP_PITCH_UM = 400" in cfg
            bud = json.loads((Path(d) / "fa" / "budget.json").read_text())["clock"]
            assert bud["grid_taps"] == len(grid) and len(bud["taps"]) == len(tl)
            assert [t["kind"] for t in bud["taps"]] == ["grid"] * len(grid) + ["sinks"] * (len(tl) - len(grid))
    with tempfile.TemporaryDirectory() as d:                                    # default kit: grid only, cap 3000
        gen_phys.write_type_kit(P0, "fa", d, [])
        assert "OT_TAP_MAX_SINKS = 3000" in (Path(d) / "fa" / "config.mk").read_text()
        bud = json.loads((Path(d) / "fa" / "budget.json").read_text())["clock"]
        assert bud["tap_mode"] == "grid" and len(bud["taps"]) == len(grid) and bud["sink_taps"] == []


def test_seam_hold_padding_min_input_delay():
    """CP1 r9 seam-hold padding: every kit input gets min input delay -clock.insertion_tol_ps vs vclk (the neighbour's
    face flop may launch at the fast end of the insertion window, no clk-to-q / wire credit), so the kit hold-pads
    seam inputs (r8: 0 ps padded nothing, seam hold -50 TT)."""
    import gen_phys
    P = schema.Plan(PAIR)
    sdc = gen_phys.sdc(P, "fa", gen_phys.type_pins(P, "fa"))
    tol = P.clock["insertion_tol_ps"]
    assert tol > 0 and f"set_input_delay -min {-tol:.4f} -clock vclk $non_clk_in" in sdc


def test_tap_balance_to_plan_insertion_and_seam_uncertainty_once():
    """KV-P5 17:34: tap trees balance to the plan insertion (OT_TAP_TARGET_PS), not the slowest local tree; COORD 16:58:
    the kit SDC counts the seam uncertainty once (half on the sender clk->vclk, half on the receiver vclk->clk)."""
    import gen_phys
    tb = (HERE / "tap_balance.tcl").read_text()
    assert "set tgt $tb_target" in tb and "empty taps" in tb
    P = schema.Plan(PAIR)
    s = gen_phys.sdc(P, "fa", gen_phys.type_pins(P, "fa"))
    half = gen_phys.t_lib(gen_phys.UNC_SETUP_PS / 2)
    assert f"-from [get_clocks vclk] -to [get_clocks clk] -setup {half:.4f}" in s
    assert f"-from [get_clocks clk] -to [get_clocks vclk] -setup {half:.4f}" in s


def test_reset_epoch_flops_not_merged():
    """S81-P9 10-23: every station whose epoch flop loads a reset net (out buses, non-lane inputs) is an ot_dp_ste with a
    kept ot_dp_ep, so Yosys opt_merge cannot fold the epoch flops of several faces into one (S81 r0: one eq flop drove
    ret_o0[70] 2.27 mm away); lane-epoch stations stay plain ot_dp_st."""
    import copy
    import re
    import shutil
    import subprocess
    import gen_rtl
    P = schema.Plan(PAIR)
    with tempfile.TemporaryDirectory() as d:
        gen_rtl.write_rtl(copy.deepcopy(PAIR), d)
        for tn, t in P.types.items():
            if t.get("hard"):
                continue
            p = Path(d) / f"{t['module']}.sv"
            if not p.is_file():
                continue
            for cell, ea in re.findall(r"(ot_dp_ste?) #\(\.W\(\d+\)\) \w+ \(.*?\.ea\(([^)]*)\)", p.read_text()):
                assert (cell == "ot_dp_ste") == bool(re.fullmatch(r"rst_n(_t\d+)?", ea)), (tn, cell, ea)
        cells = Path(d) / "ot_dp_cells.sv"
        if shutil.which("yosys"):
            top = Path(d) / "t.sv"
            top.write_text("module t(input wire clk, input wire r, input wire [1:0] d, output wire [1:0] q, output wire e0, "
                           "output wire e1);\n"
                           "  ot_dp_ste #(.W(1)) a(.clk(clk), .rst_n(r), .d(d[0]), .ea(r), .q(q[0]), .eq(e0));\n"
                           "  ot_dp_ste #(.W(1)) b(.clk(clk), .rst_n(r), .d(d[1]), .ea(r), .q(q[1]), .eq(e1));\nendmodule\n")
            r = subprocess.run(["yosys", "-p", f"read_verilog -sv {cells} {top}; synth -flatten -top t; stat"],
                               capture_output=True, text=True)
            assert r.returncode == 0, r.stderr
            # one epoch flop per station (ot_dp_ste is itself kept since CP1-R10: count the async epoch flops in the
            # hierarchy totals; older yosys stat printed the flattened ot_dp_ep count)
            assert re.search(r"(ot_dp_ep|\$_DFF_PN0_)\s+2\b", r.stdout), r.stdout


def test_empty_grid_taps_dropped_at_assembly():
    """COORD 10-23 (CP1 r9: 7 of 16 grid taps empty): the kit's clock_taps.tcl reports per-tap sink counts and writes
    the taps without sinks to RESULTS_DIR/ot_clock_taps.json; gen.py assembly leaves those tap ports unconnected in
    the die top (no dead spine drop), keeps every other tap on clk, and never drops all taps of a type."""
    import copy
    import gen_phys
    tcl = (HERE / "clock_taps.tcl").read_text()
    assert "ot_clock_taps.json" in tcl and "per-tap sinks" in tcl
    raw = copy.deepcopy(PAIR)
    P = schema.Plan(raw)
    grid = [n for n, _, _ in schema.tap_grid(P, "fa")]
    assert len(grid) > 2
    with tempfile.TemporaryDirectory() as d:
        v = Path(d) / "views"
        (v / "fa").mkdir(parents=True)
        (v / "fa" / "ot_clock_taps.json").write_text(json.dumps(
            dict(sinks={n: (0 if n in grid[1:3] else 7) for n in grid}, dropped=grid[1:3])))
        if "fb" in raw["partition_types"]:
            nb = [n for n, _, _ in schema.tap_grid(P, "fb")]
            (v / "fb").mkdir()
            (v / "fb" / "ot_clock_taps.json").write_text(json.dumps(dict(sinks={n: 0 for n in nb}, dropped=nb)))
        kd = gen_phys.write_assembly(raw, Path(d) / "a", v)
        top = next((Path(kd) / "rtl").glob("*_top.sv")).read_text()
        fa_parts = [n for n, p in P.parts.items() if p["type"] == "fa"]
        assert fa_parts
        for n in grid[1:3]:
            assert top.count(f".{n}()") == len(fa_parts)
        assert f".{grid[3]}(clk)" in top and ".clk(clk)" in top
        dr = json.loads((Path(kd) / "clock_taps.json").read_text())["dropped"]
        assert dr == {"fa": sorted(grid[1:3])}                  # fb: all empty -> nothing dropped


def test_pair_drops_hard_cores():
    """CP1-R10 (10-24): pair.py's proof leaf replaces every content, so hard_cores[] (S81 v4.7+ frame cores with LEF
    views) are dropped too; kept, the kit would place macros the proof netlist does not instantiate."""
    import copy
    import pair
    raw = copy.deepcopy(PAIR)
    tn = raw["partitions"][0]["type"]
    raw["partition_types"][tn]["hard_cores"] = [dict(inst="u_core", module="m", lef="x.lef", origin_um=[8.64, 8.64],
                                                    outline_um=[100.0, 100.0])]
    out, _ = pair.extract(raw, [p["name"] for p in raw["partitions"][:2]])
    assert all("hard_cores" not in t for t in out["partition_types"].values())
    assert "1 hard_cores dropped" in out["partition_types"][tn]["note"]
    assert not schema.validate(out)


def test_run_die_signoff_corners():
    """CP1-R10: the die STA runs at TT (setup sign-off), FF (hold sign-off) and SS (information only, AGENTS.md 10-24)."""
    import gen_phys
    assert "for c in SS TT FF" in gen_phys.RUN_DIE


def test_die_sta_reports_face_flop_spread():
    """CP1-R10: die STA prints the R4 face-flop spread (rise-edge CK arrival over the u_bin_/u_bout_ pin registers)
    per partition instance and over the die."""
    import gen_phys
    P = schema.Plan(PAIR)
    t = gen_phys.sta_die_tcl(P)
    assert "FFSPREAD" in t and "u_(bin|bout)_" in t and t.index("FFSPREAD") < t.index("close $fh")
