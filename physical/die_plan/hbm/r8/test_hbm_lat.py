"""DIE-HBM-92-LAT: HBM latency event (hbm_lat_pads.py loop equalisation + hbm_param_regen.py absolute laws)."""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "tools" / "die_plan"))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "bind"))
import r8  # noqa: E402
import hbm_lat_pads as LP  # noqa: E402
import hbm_param_regen as HR  # noqa: E402

RAW = {"die": {"name": "t"}, "partitions": [
    {"name": "ctl", "type": "tctl"}, {"name": "hub", "type": "thub"},
    {"name": "t0", "type": "tt0"}, {"name": "t1", "type": "tt1"}]}


def mem(port, src, asb, bound):
    return dict(sink_port=port, sink_bits=[[0, 7]], source=src, source_bits=[[0, 7]], asbuilt_stages=asb,
                bound_stages=bound, landed_stages=bound, lane="L")


def grp(sink, part, src_part, *ms):
    return dict(sink=sink, sink_part=part, src_part=src_part, members=list(ms))


def die(rq0=2, rr0=2, rq1=5, rr1=3):
    """ctl -> tap k (rq) -> ctl (rr): two LG round trips 4 / 8 sharing one ctl parameter"""
    return dict(die="t", replica=[], landing=[
        grp("tap0", "t0", "ctl", mem("c_rq", "ctl.q", 0, rq0)), grp("ctl", "ctl", "t0", mem("rr0", "tap0.r", 0, rr0)),
        grp("tap1", "t1", "ctl", mem("c_rq", "ctl.q", 0, rq1)), grp("ctl", "ctl", "t1", mem("rr1", "tap1.r", 0, rr1)),
        grp("tap0", "t0", "hub", mem("local_read", "cal.s", 0, 1)),
        grp("tap1", "t1", "hub", mem("local_read", "cal.s", 0, 1))])


CONTRACT = {"name": "t", "legs": [
    {"for": {"k": [0, 1]}, "name": "Q{k}", "sel": {"sink": "tap{k}", "port": "c_rq", "src": "ctl"}},
    {"for": {"k": [0, 1]}, "name": "R{k}", "sel": {"sink": "ctl", "port": "rr{k}", "src": "tap{k}"}},
    {"name": "CAL", "sel": {"sink": "tap[01]", "port": "local_read", "src": "cal"}}],
    "joins": [{"name": "REQ", "members": ["CAL", "Q0", "Q1"]}],
    "families": [{"name": "F", "loops_for": {"k": [0, 1]}, "loop": {"name": "LG{k}", "legs": ["Q{k}", "R{k}"],
                                                                     "pad": "R{k}"}}]}


def test_expand_templates_keep_regex_braces():
    legs, joins, fams = LP.expand({"legs": [{"for": {"k": [1]}, "name": "N{k}",
                                             "sel": {"sink": "vmb({b0}|{b1})", "port": "x\\d{2}"}}]})
    assert legs["N1"]["sel"] == {"sink": "vmb(2|3)", "port": "x\\d{2}"}


def test_loops_equalised_and_joined():
    mem_, used, rep, legrep, errors, rounds, _ = LP.solve(die(), RAW, CONTRACT, r8)
    assert not errors
    # join: calendar + both requests land at one added delay (max 5) -> Q0 padded 3
    assert legrep["CAL"] == legrep["Q0"] == legrep["Q1"] == 5
    # loop: LG0 = 5 + 2 short of LG1 = 5 + 3 -> R0 padded +1
    assert rep[0]["rt_added"] == [8] and legrep["R0"] == 3
    land = {(m["sink"], m["sink_port"]): m["landed"] for m in mem_}
    assert land[("tap0", "c_rq")] == land[("tap0", "local_read")] == 5 and land[("ctl", "rr0")] == 3


def test_table_passes_r8_check(tmp_path):
    bg = die()
    mem_, used, rep, legrep, errors, rounds, _ = LP.solve(bg, RAW, CONTRACT, r8, "type", "part")
    p = tmp_path / "t_r8_landing.json"
    p.write_text(json.dumps(dict(schema=r8.SCHEMA, die="t", members=[
        {k: v for k, v in m.items() if k != "cls"} for m in mem_])))
    msgs, st = r8.check(bg, RAW, r8.load_landing(p)[0], replica="type", bus="part")
    assert not msgs and st["groups_unequal"] == 0


def test_split_separates_calendar_bus():
    bg = dict(die="t", replica=[], landing=[grp("tap0", "t0", "hub", mem("local_read", "cal.s", 0, 1),
                                                mem("near_rr", "vmb.r", 0, 4))])
    sp, n = LP.apply_splits(bg, {"splits": [{"name": "cal", "sel": {"sink": ".*", "src": "cal"}}]})
    assert n == {"cal": 1}
    N, uf, _ = r8.classes(sp, RAW, "type", "part")
    assert uf.find(0) != uf.find(1)


def full_rows(n=(2, 2), h=(1, 1), c=(3, 3), idx=(1, 1, 1, 1, 1, 1), x=(1, 1)):
    rows = []
    for q in HR.QS:
        for k in HR.KS:
            rows += [(f"vmb_{q}{2 * k}", "rq0", f"su_{q}{k}.g_tap_r8b.u_tap", n[0]),
                     (f"su_{q}{k}.g_tap_r8b.u_tap", "near_rr", f"vmb_{q}{2 * k}", n[1]),
                     (f"hc_{q}{k}", "c_rq", f"hc_{q}.u_q", h[0]), (f"hc_{q}.u_q", "lg_rr", f"hc_{q}{k}", h[1]),
                     (f"sfu_{q}{k}", "c_rq", f"sfucore_{q}.__cut_ctl", c[0]),
                     (f"sfucore_{q}.__cut_ctl", "u_core_procdff_66926__D", f"sfu_{q}{k}", c[1])]
    rows += [("vmb_SW0", "rq4", "hb_idx__ctl", idx[0]), ("hb_idx__ctl", "vm_rr", "vmb_SW0", idx[1]),
             ("hb_vms_SW", "cq", "hb_idx__ctl", idx[2]), ("hb_idx__ctl", "cr", "hb_vms_SW", idx[3]),
             ("hb_idx__ctl", "index_rq", "hb_idx__op_SW", idx[4]), ("hb_idx__op_SW", "vm_rr", "hb_idx__ctl", idx[5]),
             ("hc_NW.u_cen.qd_0", "D", "hc_eng", x[0]), ("hc_eng", "qps", "hc_NE.u_cen.qi_0", x[1])]
    return rows


def contract():
    return json.loads((HERE / "hbm_lat_contract.json").read_text())


def test_absolute_laws_reproduce_asbuilt_lg1():
    """N = 2 + 2 (today's LG1/LG3 near legs) reproduces the as-built 15/19/23 tap READ_RETURN; header zero-lane
    references: hc_q capture 23 / done 19 at the 18/15 term tap; rootctl am_pin 1"""
    params, rec, err = HR.derive(HR.Landed(full_rows(h=(0, 0))), HR.legs_of(contract()))
    assert not err
    assert params["su_NW1.g_tap_r8b.u_tap"] == dict(READ_RETURN=15, WRITE_RETURN=12)
    assert params["su_NW1.u_slice.g_leaf[0].u_leaf"]["READ_RETURN"] == 15
    assert params["sfu_NE1"]["READ_RETURN"] == 19 and params["hc_NE1"] == dict(READ_RETURN=23, WRITE_RETURN=20)
    assert params["hc_NW.u_q"] == dict(RD_CAPTURE=28, GATHER_PHASE=28, DONE_LAT=24)
    assert params["hb_idx__ctl"] == dict(VM_RT=3, CR_RT=3) and params["hb_idx__op_SW"] == dict(VM_RT_EXTRA=7)
    assert params["hc_eng"] == dict(XRD=1, XRU=1)


def test_bridge_law_and_unequal_loops_are_errors():
    legs = HR.legs_of(contract())
    params, rec, err = HR.derive(HR.Landed(full_rows()), legs, {"read_k": 10, "write_k": 7})
    assert not err and rec["variant_values"]["sfucore_NW.__cut_ctl"]["READ_RETURN"] == 10 + 19 + 6
    rows = [r if r[:2] != ("hc_NE.u_q", "lg_rr") or r[2] != "hc_NE2" else r[:3] + (5,) for r in full_rows()]
    params, rec, err = HR.derive(HR.Landed(rows), legs)
    assert any("hc_NE.u_q RD_CAPTURE" in e for e in err)
    rows = full_rows() + [("vmb_NW1", "rq0", "su_NW0.g_tap_r8b.u_tap", 3)]
    params, rec, err = HR.derive(HR.Landed(rows), legs)
    assert any(re.match(r"leg N_rq_NW0: landed depths \[2, 3\]", e) for e in err)


def test_event_dir_is_a_new_hardlinked_copy(tmp_path):
    """hbm_lat_event.py: cp -al of the base, only new files + README / SHA256SUMS rewritten (never in place)"""
    import subprocess
    base = tmp_path / "plan_a"
    base.mkdir()
    (base / "die_plan.json").write_text(json.dumps(RAW))
    (base / "README.md").write_text("# base\n")
    subprocess.run("sha256sum die_plan.json README.md > SHA256SUMS", shell=True, cwd=base, check=True)
    bg = tmp_path / "bus_groups.json"
    bg.write_text(json.dumps(die()))
    ab = tmp_path / "ab.json"
    ab.write_text(json.dumps({"base": "/x"}))
    ct = tmp_path / "c.json"
    ct.write_text(json.dumps(CONTRACT))
    out = tmp_path / "plan_b"
    r = subprocess.run([sys.executable, "-I", str(HERE / "hbm_lat_event.py"), str(base), str(bg), str(ab), str(out),
                        "--tools", str(REPO / "tools" / "die_plan"), "--contract", str(ct)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert (out / "die_plan.json").stat().st_ino == (base / "die_plan.json").stat().st_ino     # hardlink, unchanged
    assert (base / "README.md").read_text() == "# base\n"                                       # base untouched
    assert (out / "README.md").stat().st_ino != (base / "README.md").stat().st_ino
    abl = json.loads((out / "asbuilt_lat.json").read_text())
    assert abl["land_align"] == "r8" and abl["land_r8"].endswith("r8/t_r8_landing.json")
    assert Path(abl["param_regen"]["file"]).is_file()
    rec = json.loads((out / "lat_1108_event.json").read_text())
    assert rec["die_plan_changed"] is False and not rec["errors"]
    assert subprocess.run(["sha256sum", "-c", "--quiet", "SHA256SUMS"], cwd=out).returncode == 0
    assert subprocess.run([sys.executable, "-I", str(HERE / "hbm_lat_event.py"), str(base), str(bg), str(ab), str(out),
                           "--tools", str(REPO / "tools" / "die_plan")], capture_output=True).returncode != 0  # exists
