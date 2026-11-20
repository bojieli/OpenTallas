"""RST-FAN-1 (HEAD-CROSSING-1119, COORD ruling on hd_lep0N): R-REACH-6 (b) placed reset relay census.

hd_lep0N r8b place: the wrapper relay u_rrl_657/q (gated tap 116, (930, 643) um) drove 157 core async-reset loads up to
1311 um away, minimax radius 992 um > REACH_UM 405 -> reset_relay_span (needs same-edge copies / a pipelined fan);
a relay whose loads fit within the reach but sits off them -> reset_relay_site (re-site at the minimax point).
    python3 -m pytest -q tools/die_plan/test_reset_relay_span.py"""
import reach_rules as RR


def geom(tmp_path, cells, nets):
    """write a geom_dump.tcl-format file: C id kind master x0 y0 x1 y1 name / N SIGNAL drv sinks..."""
    ln = [f"C\t{i}\t{k}\tX\t{x:.3f}\t{y:.3f}\t{x + 1:.3f}\t{y + 0.27:.3f}\t{n}" for i, (k, x, y, n) in cells.items()]
    ln += ["N\tSIGNAL\t" + "\t".join(["i" + d] + ["i" + s for s in sk]) for d, sk in nets]
    p = tmp_path / "geom.tsv"
    p.write_text("\n".join(ln) + "\n")
    return str(p)


def lep0n_like(tmp_path):
    cells = {
        "1": ("S", 930.0, 643.0, "u_rrl_657/q$_DFF_P_"),                       # the core reset relay (one net)
        "2": ("B", 1300.0, 650.0, "u_rrl_657/_buf_"),                          # a repeater on that net
        "3": ("S", 247.0, 663.0, r"u_core.u.g_kl\[2\].g_rxf.g_s\[0\].u_st.q\[0\]$_DFFE_PN0P_"),
        "4": ("S", 1833.0, 1038.0, r"u_core.u.g_plw.g_s\[2\].u_st.q\[0\]$_DFF_PN0_"),
        "5": ("S", 912.0, 1312.0, r"u_core.u.g_c0i.g_s\[0\].u_st.q\[0\]$_DFF_PN0_"),
        "6": ("S", 1000.0, 600.0, "u_core.u.u_lep.u.g_reset_balanced.u_rstr.root_r$_DFF_PN0_"),   # sited 300 um off
        "7": ("S", 1290.0, 600.0, r"u_core.u.u_lep.u.g_reset_balanced.u_rstr.g_group\[0\].group_r$_DFF_PN0_"),
        "8": ("S", 1350.0, 640.0, r"u_core.u.u_lep.u.g_reset_balanced.u_rstr.g_group\[1\].group_r$_DFF_PN0_"),
        "9": ("S", 100.0, 100.0, "u_core.u.lw_r\\[0\\]$_DFF_PN0_"),            # a data flop with a far load: not a relay
        "10": ("S", 900.0, 900.0, "u_core.u.x_q$_DFF_P_"),
        "11": ("S", 1000.0, 610.0, r"u_core.u.u_lep.u.g_reset_balanced.u_rstr.g_local\[3\].local_r$_DFF_PN0_"),
        "12": ("S", 1010.0, 620.0, "u_core.u.y_q$_DFF_PN0_"),
    }
    nets = [("1", ["3", "5", "6", "2"]), ("2", ["4"]), ("6", ["7", "8"]), ("9", ["10"]), ("11", ["12"])]
    return geom(tmp_path, cells, nets)


def test_core_reset_relay_span_and_site(tmp_path):
    rows, fs = RR.reset_relay_spans(lep0n_like(tmp_path), "hd_lep0N")
    by = {r["relay"]: r for r in rows}
    assert set(by) == {"u_rrl_657/q", "u_core.u.u_lep.u.g_reset_balanced.u_rstr.root_r",
                       "u_core.u.u_lep.u.g_reset_balanced.u_rstr.g_local[3].local_r"}     # lw_r is not a relay
    r = by["u_rrl_657/q"]
    assert r["n"] == 4                                   # through the repeater: g_plw stage 2 counted
    assert r["r_now"] > 1200 and r["r_minimax"] > RR.REACH_UM
    kinds = {(f["kind"], f["msg"].split()[2]) for f in fs}
    assert ("reset_relay_span", "u_rrl_657/q") in kinds
    # root_r: loads 290..390 um away from its site, but both within 40 um of each other -> re-site, no copies
    assert ("reset_relay_site", "u_core.u.u_lep.u.g_reset_balanced.u_rstr.root_r") not in kinds   # 330/390 <= 405
    assert all(f["warn"] and f["rule"] == "6" for f in fs)
    assert len(fs) == 1


def test_relay_site_finding(tmp_path):
    cells = {"1": ("S", 0.0, 0.0, "u_core.u.u_lep.u.g_reset_mapped.u_rstr.g_root\\[1\\].root_r$_DFF_PN0_"),
             "2": ("S", 500.0, 0.0, "a_q$_DFF_PN0_"), "3": ("S", 700.0, 0.0, "b_q$_DFF_PN0_")}
    rows, fs = RR.reset_relay_spans(geom(tmp_path, cells, [("1", ["2", "3"])]), "t")
    assert [f["kind"] for f in fs] == ["reset_relay_site"]
    assert rows[0]["minimax"][0] == 600.5 and rows[0]["r_minimax"] == 100.0


def test_fan_leaves_within_reach_no_finding(tmp_path):
    cells = {"1": ("S", 0.0, 0.0, "u_core.u.g_rfan.u_rfan.g_leaf\\[5\\].leaf_r$_DFF_PN0_"),
             "2": ("S", 100.0, 50.0, "a_q$_DFF_PN0_"), "3": ("S", 300.0, 0.0, "b_q$_DFF_PN0_")}
    rows, fs = RR.reset_relay_spans(geom(tmp_path, cells, [("1", ["2", "3"])]), "t")
    assert len(rows) == 1 and fs == []


def test_cli(tmp_path, capsys):
    g = lep0n_like(tmp_path)
    out = tmp_path / "r.json"
    assert RR.main(["rstspan", f"hd_lep0N={g}", "--json", str(out)]) == 0
    assert "reset_relay_span 1" in capsys.readouterr().out
    assert out.exists()
