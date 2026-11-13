import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("nrev", Path(__file__).with_name("stage_gunit_bf_nrev.py"))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

W, H = 432.0, 172.8


def site(b, port):
    # lane i = b // 41 at a 48.624-um lane pitch, bits interleaved a / b on M5 tracks (as plan_Aor3: origin x 207.36 + offset 0.108)
    i, k = divmod(b, 41)
    return round(0.012 + 0.048 * (460 + 1013 * i + 2 * k + (1 if port.endswith("b") else 0)), 4)


def tables():
    bf = [dict(name=f"{p}[{b}]", layer="M5", x=site(b, p), y=172.758) for p in ("s1a", "s1b") for b in range(328)]
    bf += [dict(name=f"s0a[{b}]", layer="M5", x=site(b, "s1a"), y=0.042) for b in range(328)]
    bf += [dict(name="clk", layer="M4", x=0.042, y=86.412)]
    ahi = [dict(name=f"{q}[{b}]", layer="M5", x=site(b, p), y=0.042) for p, q in (("s1a", "qa"), ("s1b", "qb")) for b in range(328)]
    ahi += [dict(name="re", layer="M4", x=0.042, y=50.412)]
    return bf, ahi


def lef(pins):
    out = ["MACRO dsdv_gunit_l1f_bf", "  SIZE 432.000 BY 172.800 ;"]
    for p in pins:
        out += [f"  PIN {p['name']}", "    DIRECTION INPUT ;", "    PORT", f"      LAYER {p['layer']} ;",
                f"        RECT {p['x'] - 0.012:.4f} {p['y'] - 0.042:.4f} {p['x'] + 0.012:.4f} {p['y'] + 0.042:.4f} ;",
                "    END", f"  END {p['name']}"]
    out += ["  OBS", "    LAYER M5 ;", "      RECT 0.0000 0.0000 432.0000 172.8000 ;", "  END", "END dsdv_gunit_l1f_bf", ""]
    return "\n".join(out)


def hc(inst, mod, y, h, pins, lef_):
    return dict(inst=inst, module=mod, origin_um=[207.36, y], outline_um=[W, h], orient="R0", track_offset_um=[0.108, 0.012],
                pins_file=pins, lef=lef_)


@pytest.fixture
def repo(tmp_path):
    bf, ahi = tables()
    d = tmp_path / "physical/die_plan/s81/inputs/core_pins"
    d.mkdir(parents=True)
    (d / "bf.json").write_text(json.dumps(dict(module="dsdv_gunit_l1f_bf", source="gen", pinhash="x", pins=bf)))
    (d / "ahi.json").write_text(json.dumps(dict(module="dsdv_gunit_l1f_ba1", pins=ahi)))
    (tmp_path / "bf.lef").write_text(lef(bf))
    cores = []
    for f in range(2):
        cores += [hc(f"u.g[{f}].u_l1f.u_f", "dsdv_gunit_l1f_bf", 201.6 + 600 * f, H, "inputs/core_pins/bf.json", "bf.lef"),
                  hc(f"u.g[{f}].u_l1f.u_ahi", "dsdv_gunit_l1f_ba1", 374.4 + 600 * f, 151.2, "inputs/core_pins/ahi.json", "a.lef")]
    plan = dict(partition_types=dict(gunit__t1=dict(outline_um=[2000, 2000], hard_cores=cores)))
    (tmp_path / "plan.json").write_text(json.dumps(plan, indent=1))
    return tmp_path


def run(repo, mode="lanes", out="out.json"):
    return m.stage(repo / "plan.json", repo / out, "inputs/core_pins/nrev/bf.json", "nrev/bf.lef", mode, repo)


def test_lanes_reverse_permutes_own_sites_on_track(repo):
    rep = run(repo)
    old = {p["name"]: p for p in tables()[0]}
    new = {p["name"]: p for p in json.loads((repo / "physical/die_plan/s81/inputs/core_pins/nrev/bf.json").read_text())["pins"]}
    assert rep["moved_pins"] == 656
    for port in ("s1a", "s1b"):
        for b in range(328):
            i, k = divmod(b, 41)
            assert new[f"{port}[{b}]"]["x"] == old[f"{port}[{41 * (7 - i) + k}]"]["x"]
            assert new[f"{port}[{b}]"]["y"] == old[f"{port}[{b}]"]["y"]
    assert all(new[n] == old[n] for n in old if not n.startswith(("s1a", "s1b")))
    assert sorted((p["x"], p["y"]) for p in new.values()) == sorted((p["x"], p["y"]) for p in old.values())
    assert all(r["offtrack_before"] == 0 and r["offtrack_after"] == 0 for r in rep["instances"])
    # parent: abutted bf / ahi -> every B net is unaligned, a full reversal crosses all of them at mid-face
    for p in rep["parent"]:
        assert p["bf_top_to_ahi_gap_um"] == 0.0 and p["unaligned_nets"] == 656 and p["peak_crossing_tracks"] == 656


def test_plan_only_repoints_bf_and_lef_shifts_rects(repo):
    run(repo)
    a = json.loads((repo / "plan.json").read_text())["partition_types"]["gunit__t1"]["hard_cores"]
    b = json.loads((repo / "out.json").read_text())["partition_types"]["gunit__t1"]["hard_cores"]
    for x, y in zip(a, b):
        diff = {k for k in x if x[k] != y[k]}
        assert diff == ({"pins_file", "lef"} if x["module"] == "dsdv_gunit_l1f_bf" else set())
    old, new = (repo / "bf.lef").read_text(), (repo / "nrev/bf.lef").read_text()
    ol, nl = old.splitlines(), new.splitlines()
    assert len(ol) == len(nl) and old.count("RECT") == new.count("RECT")
    changed = [i for i in range(len(ol)) if ol[i] != nl[i]]
    assert len(changed) == 656 and all("RECT" in ol[i] for i in changed)
    assert "PIN s1a[0]" in new and "OBS" in new


def test_deterministic_and_second_run_refused(repo):
    run(repo, out="o1.json")
    t1 = (repo / "o1.json").read_bytes(), (repo / "nrev/bf.lef").read_bytes()
    run(repo, out="o2.json")
    assert ((repo / "o2.json").read_bytes(), (repo / "nrev/bf.lef").read_bytes()) == t1
    with pytest.raises(AssertionError, match="second run"):
        m.stage(repo / "o1.json", repo / "o3.json", "inputs/core_pins/nrev2/bf.json", "nrev2/bf.lef", "lanes", repo)


def test_mirror_refuses_half_pitch_off_track(repo):
    # 432 / 0.048 is whole, so x -> W - x lands every M5 pin half a pitch off its track: fail closed, nothing written
    with pytest.raises(AssertionError):
        run(repo, mode="mirror", out="om.json")
    assert not (repo / "om.json").exists()
