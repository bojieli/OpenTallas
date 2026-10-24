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
        # boundary flops for din (64), x_o (277), r_i (71) + one station per bit of fz (65)
        import gen_phys
        nt = len(gen_phys.tap_pins(P, "fa"))                    # R4 clock tap grid + the reset tap
        assert nt == len(schema.tap_grid(P, "fa")) + 1 and nt > 2
        assert meta["flops"] == 64 + 277 + 71 + 65 + nt          # + one tap buffer per clock / reset tap
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
        assert "place_macro -macro_name pfb -location {1434.24 0} -orientation R0 -exact" in tcl and "detailed_route" in tcl
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
        assert "export OT_TAP_WINDOW_PS = 40" in cfg and "export CORNER = TC" in cfg
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
    (tmp_path / "m.lib").write_text("library(m) {}\n")
    t = raw["partition_types"]["src"]
    t.setdefault("contents", []).append(dict(inst="u_sram", module="sram_m", status="planned", lef="m.lef", lib="m.lib",
                                             origin_um=[17.28, 25.92], orient="MX"))
    t["hard_cores"] = [dict(inst="u_core", module="core_m", origin_um=[8.64, 8.64], outline_um=[8.64, 8.64],
                            track_offset_um=[0.0, 0.012], lef="m.lef")]
    P = schema.Plan(raw)
    kd = gen_phys.write_type_kit(P, "src", tmp_path / "k", [], root=tmp_path)
    mp = (kd / "macro_place.tcl").read_text()
    assert "place_macro -macro_name {u_sram} -location {17.2800 25.9200} -orientation MX -exact" in mp
    assert "-macro_name {u_core} -location {8.6400 8.6520} -orientation R0" in mp
    cfg = (kd / "config.mk").read_text()
    assert "ADDITIONAL_LEFS = /work/macros/m.lef" in cfg and "MACRO_PLACEMENT_TCL = /work/macro_place.tcl" in cfg
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
