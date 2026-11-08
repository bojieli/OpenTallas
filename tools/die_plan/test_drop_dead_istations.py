"""DIE-HBM-90-ISTA 11-07: drop_dead_istations.py drops type internal_stations whose bus the type, its die ports and
its bound RTL no longer have (the d44v class that stopped 25 HBM types in kit_istations: 'internal station on
unknown bus'), keeps every other entry byte for byte, and fails closed on a stale entry that is still live."""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import drop_dead_istations as D  # noqa: E402

RTL = """module hbm_arch_q_t (input wire clk, input wire [128:0] L5_i, output wire [8:0] L9_o);
    ot_dp_st #(.W(128)) u_bin_L5_i (.clk(clk), .d(L5_i[127:0]), .q(L5_i_q));
endmodule
"""


def st(conn, n=2, cap="u_c.p"):
    return dict(conn=conn, from_um=[0.0, 100.0], to_um=[50.0, 0.0], regs_um=[[10.0, 50.0 + j] for j in range(n)],
                bits=8, launch="face bus " + conn[4:], capture=cap, note="x")


def plan():
    t = dict(module="hbm_arch_q_t", outline_um=[100, 100],
             buses=[dict(name="L5_i", dir="in", width=128, face="N"), dict(name="L9_o", dir="out", width=8, face="S")],
             ft_slots=[dict(name="L7x1", width=4)],
             internal_stations=[st("bus:L5_i", 3), st("bus:L105_i", 7), st("u_a.x|u_b"), st("bus:L39_o", 4),
                                st("bus:L7x1_i", 1), st("bus:L105_i", 2, "u_d.p")])
    other = dict(module="hbm_arch_q_o", buses=[dict(name="L74_o", dir="out", width=1, face="E")])
    return dict(partition_types=dict(q_t=t, q_o=other),
                partitions=[dict(name="NE_t", type="q_t"), dict(name="NE_o", type="q_o")],
                ports=[dict(id="L5_0", src=dict(part="NE_o", bus="L5_o"), dst=dict(part="NE_t", bus="L5_i")),
                       dict(id="L74_0", src=dict(part="NE_o", bus="L74_o"), dst=dict(part="NE_x", bus="L74_i"))],
                note="base")


def rtl_dir(tmp_path, txt=RTL):
    (tmp_path / "hbm_arch_q_t.sv").write_text(txt)
    return tmp_path


def test_kit_istations_stops_on_the_stale_entry_shape():
    """The base failure this event removes: kit_istations' bus lookup has no row for the stale bus."""
    t = plan()["partition_types"]["q_t"]
    names = {b["name"] for b in t["buses"]}
    assert [e["conn"] for e in t["internal_stations"] if e["conn"].startswith("bus:") and e["conn"][4:] not in names] \
        == ["bus:L105_i", "bus:L39_o", "bus:L7x1_i", "bus:L105_i"]


def test_drops_only_dead_entries_and_keeps_the_rest_byte_for_byte(tmp_path):
    raw = plan()
    keep = [copy.deepcopy(e) for e in raw["partition_types"]["q_t"]["internal_stations"]
            if e["conn"] in ("bus:L5_i", "u_a.x|u_b", "bus:L7x1_i")]
    other = copy.deepcopy(raw["partition_types"]["q_o"])
    new, led = D.apply(raw, rtl_dir(tmp_path))
    assert new["partition_types"]["q_t"]["internal_stations"] == keep
    assert new["partition_types"]["q_o"] == other
    assert led["entries"] == 3 and led["buses"] == 2
    lt = led["types"]["q_t"]
    assert (lt["before"], lt["dropped"], lt["after"]) == (6, 3, 3)
    assert [x["stages"] for x in lt["buses"]["L105_i"]] == [7, 2]
    # nothing else in the type changed
    a, b = plan()["partition_types"]["q_t"], new["partition_types"]["q_t"]
    assert {k: v for k, v in a.items() if k != "internal_stations"} == \
        {k: v for k, v in b.items() if k != "internal_stations"}


def test_after_the_event_every_bus_entry_has_a_bus():
    raw = plan()
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        new, _ = D.apply(raw, rtl_dir(Path(d)))
    assert D.stale_entries(new, "q_t") == []


def test_fail_closed_when_the_bound_rtl_still_has_the_bus(tmp_path):
    raw = plan()
    before = copy.deepcopy(raw)
    with pytest.raises(SystemExit, match="L39_o is not in the type but is live \\(bound RTL\\)"):
        D.apply(raw, rtl_dir(tmp_path, RTL.replace("endmodule", "    wire [3:0] L39_o_q;\nendmodule")))
    assert raw == before


def test_fail_closed_when_a_die_port_of_the_type_names_it(tmp_path):
    raw = plan()
    raw["ports"].append(dict(id="L105_0", src=dict(part="NE_o", bus="L105_o"), dst=dict(part="NE_t", bus="L105_i")))
    with pytest.raises(SystemExit, match="L105_i is not in the type but is live \\(die port\\)"):
        D.apply(raw, rtl_dir(tmp_path))


def test_fail_closed_without_bound_rtl(tmp_path):
    with pytest.raises(SystemExit, match="no bound RTL"):
        D.apply(plan(), tmp_path)


def test_a_die_port_of_another_type_does_not_keep_it(tmp_path):
    raw = plan()
    raw["partition_types"]["q_t"]["internal_stations"].append(st("bus:L74_o", 2))
    new, led = D.apply(raw, rtl_dir(tmp_path))
    assert "L74_o" in led["types"]["q_t"]["buses"]


def test_rtl_match_is_whole_identifier():
    assert D.rtl_mentions("wire L105_io; wire xL105_i;", "L105_i") == 0
    assert D.rtl_mentions("u_bout_L105_i_pad3 x; L105_i_is2_q", "L105_i") == 2


def test_cli_writes_plan_and_ledger(tmp_path):
    p = tmp_path / "in.json"
    p.write_text(json.dumps(plan()))
    r = rtl_dir(tmp_path / "rtl") if (tmp_path / "rtl").mkdir() is None else None
    out, led = tmp_path / "out.json", tmp_path / "led.json"
    res = subprocess.run([sys.executable, "-I", str(HERE / "drop_dead_istations.py"), str(p), str(out), str(led),
                          "--bound-rtl", str(r)], capture_output=True, text=True)
    assert res.returncode == 0, res.stderr
    new = json.loads(out.read_text())
    assert new["note"].startswith("DIE-HBM-90-ISTA drop_dead_istations (3 dead entries on 2 type buses, 1 types)")
    assert json.loads(led.read_text())["entries"] == 3
