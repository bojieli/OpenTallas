"""WIDE-FLOAT-1: wide face-bus station chains on the outline float (plan event + kit_istations + route_supply)."""
import copy
import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


EV = _load("wide_chain_float_event")
KI = _load("kit_istations")
RS = _load("route_supply")


def _plan():
    t = {"outline_um": [1442.88, 1226.88],
         "buses": [{"name": "frame_int_i0", "width": 1167, "dir": "in", "face": "S"},
                   {"name": "ret_o0", "width": 70, "dir": "out", "face": "E"},
                   {"name": "mid_i0", "width": 512, "dir": "in", "face": "W"}],
         "internal_stations": [
             {"conn": "bus:frame_int_i0", "from_um": [133, 0], "regs_um": [[477, 0], [821, 0], [1165, 0], [1295, 213.7]],
              "to_um": [1295, 557], "capture": "u_r2.u_bn10.rs"},
             {"conn": "bus:ret_o0", "from_um": [1200, 30], "regs_um": [[1442.88, 300]], "to_um": [1442.88, 320]},
             {"conn": "bus:mid_i0", "from_um": [0, 600], "regs_um": [[300, 600]], "to_um": [600, 600]}]}
    return {"partition_types": {"col_x__t1": t}}


def test_event_marks_only_wide_chains_on_the_outline():
    P = _plan()
    rows = EV.mark(P)
    st = P["partition_types"]["col_x__t1"]["internal_stations"]
    assert [r[1] for r in rows] == ["bus:frame_int_i0"]
    assert st[0]["sites"] == "float" and "WIDE-FLOAT-1" in st[0]["note"]
    assert "sites" not in st[1]          # 70 b: below --min-bits
    assert "sites" not in st[2]          # 512 b but no site on the outline


def test_event_all_wide_and_idempotent():
    P = _plan()
    EV.mark(P, all_wide=True)
    st = P["partition_types"]["col_x__t1"]["internal_stations"]
    assert st[2]["sites"] == "float"
    assert EV.mark(P, all_wide=True) == []


def test_kit_chain_floats_needs_every_entry():
    t = copy.deepcopy(_plan()["partition_types"]["col_x__t1"])
    t["internal_stations"].append(dict(t["internal_stations"][0], regs_um=[[500, 0]]))
    t["internal_stations"][0]["sites"] = "float"
    assert not KI.chain_floats(t, "bus:frame_int_i0")
    t["internal_stations"][-1]["sites"] = "float"
    assert KI.chain_floats(t, "bus:frame_int_i0")
    assert not KI.chain_floats(t, "bus:ret_o0")


def test_route_supply_skips_float_chain_polyline():
    import inspect
    src = inspect.getsource(RS)
    assert 'if s.get("sites") == "float":' in src
    assert 'or s_.get("sites") == "float"' in src


def test_kit_float_chain_inserts_stages_without_firm_sites(tmp_path):
    import json
    import subprocess
    import test_kit_istations as TK
    for floating in (False, True):
        kd = tmp_path / ("kit_f" if floating else "kit_p")
        kd.mkdir()
        (kd / "t_part_bound.sv").write_text(TK.BOUND)
        (kd / "kit_rtl.json").write_text(json.dumps(dict(bound_module="t_part_bound", files=[str(kd / "t_part_bound.sv")])))
        st = dict(conn="bus:i_a", from_um=[0, 0], to_um=[10, 20], regs_um=[[3, 0], [6, 0]])
        if floating:
            st["sites"] = "float"
        plan = dict(partition_types=dict(t=dict(buses=[dict(name="i_a", dir="in", width=1, kind="data")], contents=[],
                                                 internal_stations=[st])))
        pf = kd / "plan.json"
        pf.write_text(json.dumps(plan))
        r = subprocess.run([sys.executable, str(HERE / "kit_istations.py"), str(pf), "t", str(kd)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        sv = (kd / "t_part_bound.sv").read_text()
        assert "u_ist_i_a_1 (.clk(clk), .rst_n(rst_n), .d(i_a_is0_q)" in sv        # cycles unchanged either way
        tcl = (kd / "istations.tcl").read_text()
        assert ("is_place {*u_ist_i_a_0[./]*} 3 0 ist:i_a" in tcl) is (not floating)
        if floating:
            assert "sites=float" in r.stdout
