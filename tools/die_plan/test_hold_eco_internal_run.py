"""hold_eco_internal_run.py: the one-command post-route internal-endpoint hold ECO (QC-TYPES-R3 11-17): its pure helpers and the
properties that removed the three hand-run restarts (libs from the receipt, Tcl read-only from the checkout, containers as the
calling user)."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hold_eco_internal_run as H  # noqa: E402

SRC = (HERE / "hold_eco_internal_run.py").read_text()


def test_libs_come_from_the_signoff_receipt_and_std_cells_split_off(tmp_path):
    p = tmp_path / "libraries.json"
    p.write_text(json.dumps({"libraries": [
        {"path": "/OpenROAD-flow-scripts/flow/platforms/asap7/lib/NLDM/asap7sc7p5t_AO_RVT_TT_nldm_211120.lib.gz", "sha256": "x"},
        {"path": "/work/macros/ot_phy_tt.lib", "sha256": "y"}]}))
    allp, std = H.libs_from_receipt(p)
    assert len(allp) == 2 and std == [allp[0]]


def test_session_patch_adds_the_dump_once_per_corner_and_refuses_a_foreign_session():
    s = "a\n" + H.MARK + "\nb\n"
    ff, tt = H.patch_session(s, "ff"), H.patch_session(s, "tt")
    assert "ep_ff.tsv" in ff and "ep_tt.tsv" not in ff and ff.count(H.MARK) == 1
    assert "ep_tt.tsv" in tt and "ep_ff.tsv" not in tt
    try:
        H.patch_session("no marker", "ff")
        raise AssertionError("must refuse")
    except SystemExit:
        pass


def test_cmd_is_retargeted_to_the_dump_copy_with_a_fresh_container_name():
    cmd = "docker run --rm --name so_1_ff_2 -v /o/ff:/out -v /k:/work:ro img run"
    out = H.retarget_cmd(cmd, "/o/ff", "/o/dump/ff", "hei_dump_ff_9")
    assert "-v /o/dump/ff:/out" in out and "--name hei_dump_ff_9" in out and "so_1_ff_2" not in out
    try:
        H.retarget_cmd("docker run -v /x:/out", "/o/ff", "/n", "t")
        raise AssertionError("must refuse")
    except SystemExit:
        pass


def test_endpoints_merge_ff_hold_with_tt_setup_in_ps(tmp_path):
    (tmp_path / "ff").mkdir()
    (tmp_path / "tt").mkdir()
    (tmp_path / "ff" / "ep_ff.tsv").write_text("endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps\n"
                                               "u/rbs[0]/RESETN\tu/rrl/q\treg\treg\t-1.55e12\n")
    (tmp_path / "tt" / "ep_tt.tsv").write_text("endpoint\ttt_setup_slack_ps\nu/rbs[0]/RESETN\t120e12\n")
    out = tmp_path / "hold_endpoints.tsv"
    assert H.merge_endpoints(tmp_path, out) == 1
    row = out.read_text().splitlines()[1].split("\t")
    assert row[0] == "u/rbs[0]/RESETN" and abs(float(row[4]) - (-1.55)) < 1e-9 and abs(float(row[5]) - 120.0) < 1e-9


def test_no_hand_copied_inputs_and_containers_run_as_the_caller():
    assert "libraries.json" in SRC and 'ro = rt / "tools/die_plan/post_route_drv"' in SRC
    assert '"-v", "%s:/ro:ro" % ro' in SRC                       # Tcl mounted read-only, never copied (the chmod restarts)
    assert 'user = ["-u", "%d:%d" % (os.getuid(), os.getgid())]' in SRC   # no root-owned outputs
    assert "(a previous ECO)" not in SRC and "never overwrite a previous ECO" in SRC


# --- limits (FABLE-CLOSURE-STRATEGY 11-17 lever 8) ---------------------------------------------------------------------------------
HDR = "endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps\ttt_setup_slack_ps\n"


def _limits(tmp_path, ends, plan, **kw):
    e, p = tmp_path / "e.tsv", tmp_path / "p.tsv"
    e.write_text(HDR + "".join("%s\t%s\t%s\t%s\t%s\t%s\n" % t for t in ends))
    p.write_text("# hold_eco_internal plan\n" + "".join("%s\t%d\n" % t for t in plan)
                 + '# summary {"partial": 0, "skipped": 0, "nets_left_unpadded": 0}\n')
    return H.check_limits(e, p, hb4_tt_ps=132.8, **kw)


def test_inside_the_limits_has_no_violation(tmp_path):
    assert _limits(tmp_path, [("a/D", "s", "reg", "reg", -1.55, 300.0)], [("a/D", 1)]) == []


def test_worst_internal_end_below_minus_15_is_refused_but_port_ends_never_count(tmp_path):
    bad = _limits(tmp_path, [("a/D", "s", "reg", "reg", -15.5, 300.0)], [("a/D", 1)])
    assert any(v.startswith("worst_internal_ff_hold") for v in bad)
    ok = _limits(tmp_path, [("a/D", "s", "reg", "reg", -3.0, 300.0), ("po", "s", "reg", "port", -170.0, 300.0),
                            ("b/D", "pi", "port", "reg", -173.9, 300.0)], [("a/D", 1)])
    assert ok == []                                                    # the parent's port holds are advisory


def test_more_than_100_ends_is_refused(tmp_path):
    ends = [("p%d/D" % i, "s", "reg", "reg", -2.0, 400.0) for i in range(101)]
    assert any(v.startswith("padded_ends 101") for v in _limits(tmp_path, ends, [(e[0], 1) for e in ends]))
    assert _limits(tmp_path, ends[:100], [(e[0], 1) for e in ends[:100]]) == []


def test_setup_room_after_the_pad_is_required_on_every_end(tmp_path):
    v = _limits(tmp_path, [("a/D", "s", "reg", "reg", -20.0, 150.0)], [("a/D", 2)])          # 150 - 2 x 132.8 < 0
    assert any(x.startswith("setup_room a/D") for x in v)
    assert _limits(tmp_path, [("a/D", "s", "reg", "reg", -5.0, 150.0)], [("a/D", 1)]) == []


def test_a_partial_or_skipped_plan_is_refused(tmp_path):
    e, p = tmp_path / "e.tsv", tmp_path / "p.tsv"
    e.write_text(HDR + "a/D\ts\treg\treg\t-3.0\t500.0\n")
    p.write_text('a/D\t1\n# summary {"partial": 1, "skipped": 0, "nets_left_unpadded": 0}\n')
    assert any(v.startswith("plan could not pad") for v in H.check_limits(e, p, hb4_tt_ps=132.8))


def test_net_and_obstruction_checks_are_wired_in_and_refuse_with_exit_4():
    assert "source /out/netcheck.tcl" in SRC and "OT_LIMIT port net" in SRC and "OT_LIMIT non-data net" in SRC
    assert "getObstructions" in SRC and "obs_in != obs_out" in SRC
    assert SRC.count("return finish(4,") >= 3


def test_skipped_port_ends_never_count_but_a_skipped_internal_end_does(tmp_path):
    """S81 col_pg3: 110 input-port ends (the parent's, advisory, never padded) made the plan summary say skipped=110 and the run exit 4.
    Port ends plus a few internal ends must pass; an internal end the plan could not pad must still refuse."""
    ends = [("a/D", "s", "reg", "reg", -3.0, 400.0), ("b/D", "s", "reg", "reg", -2.0, 400.0)] \
        + [("pi%d/D" % i, "arst_n", "port", "reg", -173.9, 400.0) for i in range(110)]
    e, p = tmp_path / "e.tsv", tmp_path / "p.tsv"
    e.write_text(HDR + "".join("%s\t%s\t%s\t%s\t%s\t%s\n" % t for t in ends))
    skips = "".join("# skipped pi%d/D: port path: the parent's, no cell\n" % i for i in range(110))
    p.write_text("a/D\t1\nb/D\t1\n" + skips + '# summary {"partial": 0, "skipped": 110, "nets_left_unpadded": 0, "endpoints": 2}\n')
    assert H.check_limits(e, p, hb4_tt_ps=132.8) == []
    p.write_text("a/D\t1\n" + skips + "# skipped b/D: TT slack 100 - 1 x 132.8 < -42\n"
                 + '# summary {"partial": 0, "skipped": 111, "nets_left_unpadded": 0, "endpoints": 1}\n')
    v = H.check_limits(e, p, hb4_tt_ps=132.8)
    assert len(v) == 1 and v[0].startswith("internal end not padded: b/D")


def test_only_internal_ends_count_toward_max_ends_and_setup_room(tmp_path):
    ends = [("p%d/D" % i, "pi", "port", "reg", -170.0, 10.0) for i in range(150)] + [("a/D", "s", "reg", "reg", -3.0, 400.0)]
    e, p = tmp_path / "e.tsv", tmp_path / "p.tsv"
    e.write_text(HDR + "".join("%s\t%s\t%s\t%s\t%s\t%s\n" % t for t in ends))
    p.write_text("a/D\t1\n" + "".join("# skipped p%d/D: port path: the parent's, no cell\n" % i for i in range(150))
                 + '# summary {"partial": 0, "skipped": 150, "nets_left_unpadded": 0}\n')
    assert H.check_limits(e, p, max_ends=100, hb4_tt_ps=132.8) == []      # 150 port ends, 10 ps of TT setup: none of it counts


def test_ep_tables_are_real_ps_and_legacy_x1e12_tables_still_merge(tmp_path):
    """EP-PS-UNIT 11-19: the dump prints get_property <path end> slack as is (already ps; so_ps converted it a second time, x1e12:
    serdes__t13 H19 ep_tt.tsv read -155709000622182.47 for -155.71 ps).  merge_endpoints reads both table forms the same."""
    import shutil
    import subprocess
    import signoff
    for block in (H.FF_BLOCK, H.TT_BLOCK, signoff.EP_FF_TCL, signoff.EP_TT_TCL):
        assert "[so_ep_ps [get_property $pe slack]]" in block and "so_ps [get_property $pe slack]" not in block
    tclsh = shutil.which("tclsh")
    if tclsh:
        proc = signoff.EP_FF_TCL.split("\n", 1)[0]
        script = proc + '\nputs [so_ep_ps -155.709000622]\nputs [so_ep_ps 12]\nputs [so_ep_ps INF]\n'
        out = subprocess.run([tclsh], input=script, text=True, capture_output=True).stdout.split()
        assert out == ["-155.71", "12.00", "nan"]
    for scale in (1.0, 1e12):
        d = tmp_path / str(int(scale))
        (d / "ff").mkdir(parents=True)
        (d / "tt").mkdir()
        (d / "ff" / "ep_ff.tsv").write_text("endpoint\tstartpoint\tstart_kind\tend_kind\tff_hold_slack_ps\n"
                                            "u/a/D\tu/b/QN\treg\treg\t%r\nu/c/D\tu/d/QN\treg\treg\t%r\n" % (-17.56 * scale, -0.0 * scale))
        (d / "tt" / "ep_tt.tsv").write_text("endpoint\ttt_setup_slack_ps\nu/a/D\t%r\nu/c/D\t%r\n" % (-34.35 * scale, 0.5 * scale))
        assert H.merge_endpoints(d, d / "m.tsv") == 2
        rows = [ln.split("\t") for ln in (d / "m.tsv").read_text().splitlines()[1:]]
        assert [(r[0], round(float(r[4]), 2), round(float(r[5]), 2)) for r in rows] == [("u/a/D", -17.56, -34.35), ("u/c/D", 0.0, 0.5)]
