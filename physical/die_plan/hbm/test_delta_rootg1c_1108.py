"""DIE-HBM-92-OPEN/ROOTG1C: delta_rootg1c_1108 (ot_wbq_root_g1 payload width split) on a small synthetic plan dir."""
import importlib.util
import json
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("delta_rootg1c_1108", HERE / "delta_rootg1c_1108.py")
D = importlib.util.module_from_spec(spec)
spec.loader.exec_module(D)


def _entry():
    rects = [[12.96, 51.84, 104.76, 79.416], [119.88, 51.84, 211.68, 79.416], [12.96, 90.72, 104.76, 118.296],
             [119.88, 90.72, 211.68, 118.296]]
    return dict(status="KNOWN", outline_um=[216.0, 129.6], channel_rule_um=10.8, basis="b",
                macros=[dict(name=f"u_fcore.u_grp.g_lane[{i}].u_payload", master=D.OLD_MASTER, orient="R0", rect_um=r)
                        for i, r in enumerate(rects)])


def _plan_dir(d):
    d.mkdir(parents=True)
    (d / "cores").mkdir()
    (d / "cores" / "p.json").write_text("[]")
    cm = dict(schema="opentallas.core_macros.v1", note="n", cores={"ot_wbq_root_g0": _entry(), D.MOD: _entry()})
    (d / "core_macros.json").write_text(json.dumps(cm))
    hc = lambda i, m: dict(inst=i, module=m, origin_um=[0, 0], outline_um=[216.0, 129.6], pins_file="cores/p.json")
    P = dict(schema="opentallas.die_plan.v1", partition_types={
        "q_hub_nw": dict(hard_cores=[hc("a__g0", "ot_wbq_root_g0"), hc("a__g1", D.MOD)]),
        "q_hub_ne": dict(hard_cores=[hc("b__g1", D.MOD)])})
    (d / "die_plan.json").write_text(json.dumps(P))
    (d / "SHA256SUMS").write_text("00  die_plan.json\n11  core_macros.json\n")
    return d


def test_event(tmp_path):
    base = _plan_dir(tmp_path / "base")
    base_cm = (base / "core_macros.json").read_text()
    rc = D.run(base, tmp_path / "out")
    out = tmp_path / "out"
    assert (base / "core_macros.json").read_text() == base_cm            # base never written through
    assert (out / "die_plan.json").stat().st_ino == (base / "die_plan.json").stat().st_ino
    assert (out / "cores" / "p.json").stat().st_ino == (base / "cores" / "p.json").stat().st_ino
    cm = json.loads((out / "core_macros.json").read_text())
    assert cm["cores"]["ot_wbq_root_g0"] == json.loads(base_cm)["cores"]["ot_wbq_root_g0"]   # g0 untouched
    g1 = cm["cores"][D.MOD]
    assert g1["outline_um"] == [216.0, 129.6] and g1["status"] == "KNOWN"
    assert len(g1["macros"]) == 8 and {m["master"] for m in g1["macros"]} == {D.NEW_MASTER}
    assert sorted(m["orient"] for m in g1["macros"]) == ["MY"] * 4 + ["R0"] * 4
    names = {m["name"] for m in g1["macros"]}
    assert names == {f"u_fcore.u_grp.g_lane[{i}].u_payload.u_{h}" for i in range(4) for h in ("lo", "hi")}
    assert rc["plan_rows"] == 2 and rc["plan_types"] == ["q_hub_ne", "q_hub_nw"]
    assert rc["pin_changes"] == 0 and rc["pin_cycles"] == 0 and rc["channel_um"] == pytest.approx(29.976)
    sums = (out / "SHA256SUMS").read_text().splitlines()
    assert "00  die_plan.json" in sums
    assert f"{D.sha_file(out / 'core_macros.json')}  core_macros.json" in sums
    assert any(l.endswith(D.RECEIPT) for l in sums)
    rc2 = D.run(base, out)                                                # re-runnable, deterministic
    assert rc2["out_sha256"] == rc["out_sha256"]


def test_geometry_rules():
    ms = D.new_macros()
    assert D.check_geometry(ms) == pytest.approx(29.976)
    for m in ms:                                                          # every M4 edge pin on a track
        for v in m["rect_um"][:2]:
            assert abs(((v - 0.012) / 0.048) - round((v - 0.012) / 0.048)) < 1e-6
    bad = [dict(ms[0], orient="R90")]
    with pytest.raises(SystemExit):
        D.check_geometry(bad)
    over = [ms[0], dict(ms[1], rect_um=[60.0, 14.892, 113.16, 42.468])]
    with pytest.raises(SystemExit):
        D.check_geometry(over)


def test_refuses(tmp_path):
    base = _plan_dir(tmp_path / "base")
    (tmp_path / "busy").mkdir()
    with pytest.raises(SystemExit):
        D.run(base, tmp_path / "busy")                                    # a foreign OUT_DIR is never rebuilt
    cm = json.loads((base / "core_macros.json").read_text())
    cm["cores"][D.MOD]["macros"] = cm["cores"][D.MOD]["macros"][:2]
    (base / "core_macros.json").write_text(json.dumps(cm))
    with pytest.raises(SystemExit):
        D.run(base, tmp_path / "o2")                                      # wrong base -> refuse
