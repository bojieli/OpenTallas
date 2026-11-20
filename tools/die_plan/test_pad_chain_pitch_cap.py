"""PAD-PITCH-CAP (FABLE-CBC-QK-0130 section 3, QC V1): plan key budgets.pad_chain_pitch_cap_um caps the hop of a landing-pad chain.

"A pad chain spreads its D stages at span / (D + 1); cap the pitch at 380 um and put the surplus stages at the consumer end.  0 cycles
where D allows it.  Where it does not, +1 pad stage on the whole latency group."  Evidence: cb legs u_lpad_nb_i12.r[0] -> r[1]
417.6 um, r[1] -> q 417.1 um.  Absent key = kits byte-identical; a chain the cap cannot hold keeps its sites and is reported.
"""

import pytest

import gen_phys as G
import schema as S
from test_pad_chain_site import SRC, TCS, needs_tclsh, tcl

CAP = 380.0


def test_key_is_declared_in_the_budgets_schema():
    b = S.SCHEMA["properties"]["budgets"]["properties"]["pad_chain_pitch_cap_um"]
    assert b == {"type": "number", "exclusiveMinimum": 0}
    assert G.pad_chain_pitch_cap_um({}) is None and G.pad_chain_pitch_cap_um({"pad_chain_pitch_cap_um": 380}) == 380.0
    with pytest.raises(ValueError):
        G.pad_chain_pitch_cap_um({"pad_chain_pitch_cap_um": 0})


@pytest.mark.parametrize("length,n,rb", [(900, 2, 0), (600, 3, 400), (1500, 4, 120), (1670, 3, 0), (300, 6, 50)])
def test_key_absent_gives_the_sites_of_today(length, n, rb):
    today = G.pad_chain_stage_points(length, n, rb)
    d = (length + rb) / (n + 1)
    assert today == [min(float(length), j * d) for j in range(1, n + 1)]
    # the cap never moves a site: a feasible chain already holds it, an infeasible one is kept (fail-open)
    assert G.pad_chain_stage_points(length, n, rb, cap=CAP) == today


@pytest.mark.parametrize("length,n,rb", [(1500, 4, 120), (1100, 3, 0), (300, 6, 50), (600, 3, 300), (1520, 3, 0)])
def test_key_set_feasible_chain_holds_the_cap_with_surplus_at_the_consumer_end(length, n, rb):
    assert G.pad_chain_cap_ok(length, n, rb, CAP)
    pts = G.pad_chain_stage_points(length, n, rb, cap=CAP)
    hops = G.pad_chain_hops(length, pts, rb)
    assert max(hops) <= CAP + 1e-9 and pts == sorted(pts) and abs(sum(hops) - (length + rb)) < 1e-6
    # stages past the even pitch wait at the tail: every zero hop sits after the last moving stage (consumer end)
    moving = [i for i, h in enumerate(hops[:-1]) if h > 1e-9]
    assert all(h <= 1e-9 for h in hops[(moving[-1] + 1 if moving else 0):-1])
    assert G.pad_chain_cap_rows("cbn_q01", [(f"u_pd{n}_x_i_0", length, rb, n)], CAP) == []


def test_surplus_stages_pack_at_the_tail_when_the_fan_is_long():
    pts = G.pad_chain_stage_points(600, 3, 300, cap=CAP)        # d = 225: stage 3 would sit at 675 > 600, it waits at the tail
    assert pts == [225.0, 450.0, 600.0] and G.pad_chain_hops(600, pts, 300) == [225.0, 225.0, 150.0, 300.0]


def test_infeasible_chain_is_reported_and_its_sites_unchanged():
    """the cb evidence: 3 stages at 417 um (span ~1670 um) cannot hold 380 um; 4 stages can (1670 / 5 = 334)."""
    length, n = 1670.0, 3
    assert not G.pad_chain_cap_ok(length, n, 0, CAP)
    assert G.pad_chain_stage_points(length, n, 0, cap=CAP) == G.pad_chain_stage_points(length, n, 0)
    rows = G.pad_chain_cap_rows("cbn_q01__cld9ff4c40", [("u_pd3_nb_i12_7", length, 0.0, n), ("u_pd3_nb_i12_8", 1100.0, 0.0, n),
                                                        ("u_pd2_b_tw_i_0", 300.0, 420.0, 2)], CAP)
    assert rows == [dict(type="cbn_q01__cld9ff4c40", chain="u_pd3_nb_i12_7", bus="nb_i12", span_um=1670.0, fan_um=0.0, D=3,
                         stages_needed=4),
                    dict(type="cbn_q01__cld9ff4c40", chain="u_pd2_b_tw_i_0", bus="b_tw_i", span_um=720.0, fan_um=420.0, D=2,
                         stages_needed=1)]                       # fan beyond the reach: listed though D covers the span
    assert G.pad_chain_cap_rows("t", [("u_pd3_nb_i12_7", length, 0.0, n)], None) == []


def test_report_reader_round_trips_the_kit_tsv(tmp_path):
    f = tmp_path / "ot_pad_chain_cap.tsv"
    f.write_text("# type\tchain\tbus\tspan_um\tfan_um\tD\tstages_needed\tcap_um\n"
                 "cbn_q01\tu_pd3_nb_i12_7\tnb_i12\t1670.0\t0.0\t3\t4\t380\n")
    assert G.read_pad_chain_cap_report(f) == [dict(type="cbn_q01", chain="u_pd3_nb_i12_7", bus="nb_i12", span_um=1670.0,
                                                   fan_um=0.0, D=3, stages_needed=4, cap_um=380.0)]


@needs_tclsh
def test_tcl_cap_check_matches_the_python(tmp_path):
    cases = [(1670, 0, 3), (1100, 0, 3), (300, 420, 2), (600, 300, 3), (1520, 0, 3), (1521, 0, 3), (0, 0, 1)]
    body = "".join(f"puts \"[pcs_cap_need {L} {rb} 380000] [pcs_cap_ok {L} {rb} {n} 380000]\"\n"
                   for L, rb, n in [(a * 1000, b * 1000, c) for a, b, c in cases])
    out = tcl(tmp_path, ["pcs_cap_need", "pcs_cap_ok"], body)
    want = []
    for L, rb, n in cases:
        want += [str(G.pad_chain_cap_need(L, rb, CAP)), str(int(G.pad_chain_cap_ok(L, n, rb, CAP)))]
    assert out == want


def test_hook_exports_the_cap_only_when_the_key_is_set(tmp_path):
    for cap, tail in ((None, "export OT_PAD_CHAIN_SITE = auto\n"),
                      (380.0, "export OT_PAD_CHAIN_SITE = auto\nexport OT_PAD_CHAIN_PITCH_CAP_UM = 380\n")):
        kd = tmp_path / f"kit{cap}"
        kd.mkdir()
        (kd / "face_flops.tcl").write_text("# face flops\n")
        (kd / "config.mk").write_text("export A = 1\n")
        assert G.pad_chain_site_place(kd, env={"OT_PAD_CHAIN_SITE": "auto"}, cap_um=cap) == "auto"
        assert (kd / "config.mk").read_text() == "export A = 1\n" + tail
        assert (kd / "pad_chain_site.tcl").read_text() == SRC and (kd / "tail_copy_anchor.tcl").read_text() == TCS
    kd = tmp_path / "off"
    kd.mkdir()
    (kd / "face_flops.tcl").write_text("# face flops\n")
    (kd / "config.mk").write_text("export A = 1\n")
    assert G.pad_chain_site_place(kd, env={}, cap_um=380.0) is None
    assert (kd / "config.mk").read_text() == "export A = 1\n" and not (kd / "pad_chain_site.tcl").exists()


def test_tcl_cap_is_report_only_and_off_without_the_env():
    assert 'set cap_um [expr {[info exists ::env(OT_PAD_CHAIN_PITCH_CAP_UM)]' in SRC
    assert "if {$cap_um > 0 && ![pcs_cap_ok [lindex $route 0] $rb $k [expr {$cap_um * $dbu}]]}" in SRC
    assert "set tg [pcs_stage_points $route $k $rb]\n" in SRC          # the stage targets never read the cap
