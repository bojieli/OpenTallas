"""DIE-HBM-92-RESTJ: delta_restj_c_1108 (RESTJ form C outline + kit pin table) on a small synthetic plan dir."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("delta_restj_c_1108", HERE / "delta_restj_c_1108.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)

PF = "cores/ot_hgi_sfu_split3_ctl_rest_1c__427.68x453.6__d44v_split.json"
INST = "u_sfucore_Q_ctl__rest"


def _old_pins():
    return [dict(name="clk", layer="M5", x=215.976, y=224.64, w=0.048, h=0.48),
            dict(name="rst_n", layer="M4", x=427.584, y=164.568),
            dict(name="fault", layer="M5", x=200.04, y=0.096),
            dict(name="d[0]", layer="M4", x=0.096, y=33.96)]


def _kit_pins():
    pins = [dict(name="clk", layer="M5", x=133.896, y=133.824), dict(name="rst_n", layer="M4", x=267.744, y=86.76),
            dict(name="fault", layer="M5", x=120.024, y=0.096), dict(name="d[0]", layer="M4", x=0.096, y=40.008)]
    return json.dumps(dict(schema="opentallas.hbm_arch.core_plan_pins.v1", module=D.MOD, pins=pins), indent=1) + "\n"


def _plan_dir(d):
    (d / "cores").mkdir(parents=True)
    (d / PF).write_text(json.dumps(_old_pins(), indent=1))
    hc = dict(inst=INST, module=D.MOD, origin_um=[509.76, 1010.88], outline_um=[427.68, 453.6],
              track_offset_um=[-0.096, 0.0], pins_file=PF, orient="MY", note="n")
    other = dict(inst="u_other", module="m_other", origin_um=[0.0, 0.0], outline_um=[10.0, 10.0], pins_file="cores/o.json")
    ist = [dict(conn=f"{INST}.fault|u_lane", from_um=[721.4, 1010.88], regs_um=[[756.0, 915.84]], to_um=[1400, 500])]
    types = {}
    for tk in ("q_b113", "q_b113__physical_v1"):
        types[tk] = dict(outline_um=[1857.6, 1572.48], hard_cores=[copy_(hc), copy_(other)], internal_stations=ist,
                         clock=dict(taps=[dict(name=INST, kind="core", xy=[721.344, 1235.52]),
                                          dict(name="u_other", xy=[5.0, 5.0])]))
    P = dict(schema="opentallas.die_plan.v1", note="prev",
             die=dict(grid_um=8.64, layers=[dict(name="M5", offset_um=0.024, pitch_um=0.048)]), partition_types=types)
    (d / "die_plan.json").write_text(json.dumps(P))
    e = dict(xy_um=[216.0, 224.64], island_um=[211.68, 220.32, 220.32, 228.96], port=None,
             merged_clock_ports=["clk"], tap=INST, module=D.MOD, source="s")
    (d / "clock_entries.json").write_text(json.dumps({tk: {INST: dict(e)} for tk in types}) + "\n")
    (d / "core_macros.json").write_text(json.dumps(dict(cores={D.MOD: dict(status="NONE", outline_um=[427.68, 453.6],
                                                                            macros=[], note="x")})))
    (d / "core_conns.json").write_text("{}\n")
    (d / "SHA256SUMS").write_text("00  die_plan.json\n11  core_conns.json\n")
    kit = d.parent / "kit_plan_pins.json"
    kit.write_text(_kit_pins())
    return d, kit


def copy_(x):
    return json.loads(json.dumps(x))


def test_event(tmp_path):
    base, kit = _plan_dir(tmp_path / "base")
    before = {p: p.read_bytes() for p in base.rglob("*") if p.is_file()}
    rc = D.run(base, tmp_path / "out", kit)
    out = tmp_path / "out"
    assert {p: p.read_bytes() for p in base.rglob("*") if p.is_file()} == before
    assert os.stat(out / "core_conns.json").st_ino == os.stat(base / "core_conns.json").st_ino
    assert (out / rc["new_pins_file"]).read_bytes() == kit.read_bytes()          # byte-equal kit table
    assert rc["new_pins_file"] == "cores/ot_hgi_sfu_split3_ctl_rest_1c__267.84x267.84__restjC.json"
    P = json.loads((out / "die_plan.json").read_text())
    for tk in ("q_b113", "q_b113__physical_v1"):
        t = P["partition_types"][tk]
        hc = t["hard_cores"][0]
        assert hc["outline_um"] == [267.84, 267.84] and hc["pins_file"] == rc["new_pins_file"]
        assert hc["origin_um"] == [587.52, 1105.92] and hc["track_offset_um"] == [-0.096, -2.112]
        assert t["clock"]["taps"][0]["xy"] == [721.344, 1237.632]                # x exact, y +2.112 (lattice)
        assert t["hard_cores"][1]["pins_file"] == "cores/o.json" and t["clock"]["taps"][1]["xy"] == [5.0, 5.0]
        assert t["internal_stations"][0]["from_um"] == [721.4, 1010.88]
        pl = rc["placements"][tk]
        nb, sb = pl["new_box"], pl["slot_box"]
        assert sb[0] <= nb[0] and nb[2] <= sb[2] and sb[1] <= nb[1] and nb[3] <= sb[3]
    ce = json.loads((out / "clock_entries.json").read_text())
    assert all(ce[tk][INST]["xy_um"] == [133.92, 133.824] for tk in ce)
    assert json.loads((out / "core_macros.json").read_text())["cores"][D.MOD]["outline_um"] == [267.84, 267.84]
    sums = (out / "SHA256SUMS").read_text().splitlines()
    assert "11  core_conns.json" in sums and not any(ln == "00  die_plan.json" for ln in sums)
    assert rc["changed_types"] == ["q_b113", "q_b113__physical_v1"] and rc["pin_cycles_added"] == 0
    assert len(rc["station_hops"]) == 2


def test_solve_axis_keeps_track_grain():
    o, off, res = D.solve_axis(1101.696, 8.64, 0.0)
    assert (o, off) == (1105.92, -2.112) and abs(res - 2.112) < 1e-9
    assert D.solve_axis(587.424, 8.64, -0.096) == (587.52, -0.096, 0.0)


def test_refuses(tmp_path):
    base, kit = _plan_dir(tmp_path / "base")
    (tmp_path / "out").mkdir()
    with pytest.raises(SystemExit):
        D.run(base, tmp_path / "out", kit)
    with pytest.raises(SystemExit):
        D.run(base, tmp_path / "out2", kit, expect_kit_sha="deadbeef")
    bad = json.loads(kit.read_text())
    bad["pins"] = bad["pins"][::-1]
    kit.write_text(json.dumps(bad))
    with pytest.raises(SystemExit):                                              # pin order must match
        D.run(base, tmp_path / "out3", kit)
