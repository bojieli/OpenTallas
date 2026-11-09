"""DIE-HBM-92-Q3VM: delta_q3vm_e_1108 (P-Q3VM-2 rd_il N -> E, clock entry move) on a small synthetic plan dir."""
import importlib.util
import json
import os
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("delta_q3vm_e_1108", HERE / "delta_q3vm_e_1108.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)

W, H = 328.32, 717.12
PF = "cores/ot_hfd_coll_q3_vm_core__328.32x717.12__canon__fr15__codex_g21__centry.json"


def _pins(n=8):
    pins = [dict(name="clk", layer="M5", x=164.184, y=358.56, w=0.048, h=0.48)]
    for i in range(n):
        pins.append(dict(name=f"vmasm_as_il[{i}]", layer="M4", x=0.096, y=round(100.0 + 7.3 * i, 3)))
        pins.append(dict(name=f"vmasm_rd_il[{i}]", layer="M5", x=round(10.0 + 2 * i, 3), y=717.024, w=0.048, h=0.48))
    pins.append(dict(name="writer_tkw_d[0]", layer="M4", x=328.224, y=100.032))   # E-face pin already there
    pins.append(dict(name="writer_kq0[0]", layer="M5", x=50.0, y=717.024))
    return pins


def _plan_dir(d):
    (d / "cores").mkdir(parents=True)
    (d / PF).write_text(json.dumps(_pins()) + "\n")
    hc = dict(inst=D.INST, module=D.MOD, origin_um=[1054.08, 34.56], outline_um=[W, H], track_offset_um=[0.0, 0.0],
              pins_file=PF)
    other = dict(inst=D.INST, module="ot_hfd_coll_q2n2_vm_core", origin_um=[2445.12, 129.6], outline_um=[924.48, 509.76],
                 pins_file="cores/other.json")
    P = dict(schema="opentallas.die_plan.v1", note="prev", die=dict(layers=[dict(name="M5", offset_um=0.024,
                                                                                    pitch_um=0.048)]),
             partition_types={D.TYPE: dict(hard_cores=[hc], internal_stations=[dict(conn="x", regs_um=[[1, 2]])],
                                           clock=dict(taps=[dict(name=D.INST, kind="core", xy=[1218.24, 393.12])])),
                              "q_hub_ne": dict(hard_cores=[other], clock=dict(taps=[dict(name=D.INST, xy=[2907.36, 384.48])]))})
    (d / "die_plan.json").write_text(json.dumps(P))
    ce = {D.TYPE: {D.CE_TAP: dict(xy_um=[164.16, 358.56], island_um=[159.84, 354.24, 168.48, 362.88], port="clk",
                                  merged_clock_ports=[], module=D.MOD, source="s")},
          "q_hub_ne": {D.CE_TAP: dict(xy_um=[462.24, 254.88], port="clk", module="ot_hfd_coll_q2n2_vm_core")}}
    (d / "clock_entries.json").write_text(json.dumps(ce) + "\n")
    (d / "core_conns.json").write_text("{}\n")
    (d / "SHA256SUMS").write_text("00  die_plan.json\n11  core_conns.json\n")
    return d


def test_event(tmp_path):
    base = _plan_dir(tmp_path / "base")
    before = {p: p.read_bytes() for p in base.rglob("*") if p.is_file()}
    rc = D.run(base, tmp_path / "out")
    out = tmp_path / "out"
    # the base dir is never written (hard links are unlinked before writing)
    assert {p: p.read_bytes() for p in base.rglob("*") if p.is_file()} == before
    assert os.stat(out / "core_conns.json").st_ino == os.stat(base / "core_conns.json").st_ino
    assert os.stat(out / "die_plan.json").st_ino != os.stat(base / "die_plan.json").st_ino
    pins = {p["name"]: p for p in json.loads((out / rc["new_pins_file"]).read_text())}
    asy = {i: pins[f"vmasm_as_il[{i}]"]["y"] for i in range(8)}
    ys = []
    for i in range(8):
        p = pins[f"vmasm_rd_il[{i}]"]
        assert (p["layer"], p["x"]) == ("M4", D.E_X) and "w" not in p
        assert abs(p["y"] - asy[i]) <= 0.2
        ys.append(round((p["y"] - D.OFF) / D.PITCH))
    ys.append(round((100.032 - D.OFF) / D.PITCH))
    ys.sort()
    assert all(b - a >= 2 for a, b in zip(ys, ys[1:]))        # no two E-face M4 pins on adjacent tracks
    assert pins["clk"]["y"] == 501.12 and pins["writer_kq0[0]"]["y"] == 717.024
    assert rc["pins_changed_by_bus"] == {"clk": 1, "vmasm_rd_il": 8}
    P = json.loads((out / "die_plan.json").read_text())
    t = P["partition_types"][D.TYPE]
    assert t["hard_cores"][0]["pins_file"].endswith("__q3vmE.json")
    assert t["clock"]["taps"][0]["xy"] == [1218.24, 535.68]
    assert t["internal_stations"] == [dict(conn="x", regs_um=[[1, 2]])]
    ne = P["partition_types"]["q_hub_ne"]                     # the same inst name in another type is untouched
    assert ne["hard_cores"][0]["pins_file"] == "cores/other.json" and ne["clock"]["taps"][0]["xy"] == [2907.36, 384.48]
    ce = json.loads((out / "clock_entries.json").read_text())
    assert ce[D.TYPE][D.CE_TAP]["xy_um"] == [164.16, 501.12]
    assert ce[D.TYPE][D.CE_TAP]["island_um"] == [159.84, 496.8, 168.48, 505.44]
    assert ce["q_hub_ne"][D.CE_TAP]["xy_um"] == [462.24, 254.88]
    sums = (out / "SHA256SUMS").read_text().splitlines()
    assert "11  core_conns.json" in sums and not any(ln == "00  die_plan.json" for ln in sums)
    assert json.loads((out / "q3vmE_1108_event.json").read_text())["pin_cycles_added"] == 0


def test_refuses_existing_out_and_wrong_entry(tmp_path):
    base = _plan_dir(tmp_path / "base")
    (tmp_path / "out").mkdir()
    with pytest.raises(SystemExit):
        D.run(base, tmp_path / "out")
    ce = json.loads((base / "clock_entries.json").read_text())
    ce[D.TYPE][D.CE_TAP]["xy_um"] = [1.0, 2.0]
    (base / "clock_entries.json").write_text(json.dumps(ce))
    with pytest.raises(SystemExit):
        D.run(base, tmp_path / "out2")


def test_expect_sha_mismatch(tmp_path):
    base = _plan_dir(tmp_path / "base")
    with pytest.raises(SystemExit):
        D.run(base, tmp_path / "out", expect_rd_sha="deadbeef")
