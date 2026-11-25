"""PVX-PORT-1125 (KV-PV-ESTRIP, COORD FLOW-0930 K-03): pvx_regen.py (recovered from epyc8) maps composite sinks back to as-built bank names and
refuses (exit 3, nothing written) a view with no bank members / a table with 0 members.  Synthetic: one composite core, one bank."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[3] / "tools/die_plan"))
import pvx_regen as X  # noqa: E402


def _compose(path):
    bl = lambda b: [[dict(member="pvw_1__u_s0_b0", port="bc", bit=b)]]     # noqa: E731
    path.write_text(json.dumps(dict(cores=[dict(inst="native_composite_pv_N_0_pvg0_p0",
                                                ports={"s0__bc": dict(dir="input", indices=[0, 1, 2], bits=[bl(0)[0], bl(1)[0], bl(2)[0]])})])))


def _member(sink, port="s0__bc", bits=((0, 2),), source="pvw_1__u_ctl.cmd"):
    return dict(id=f"{sink}.{port}", sink=sink, sink_part="pv_N_0", src_part="pv_N_3", sink_port=port, sink_bits=[list(b) for b in bits],
                source=source, asbuilt=50, bound=53, pad=0, landed=53, lane="L1")


def test_view_maps_composite_back_to_the_as_built_bank(tmp_path):
    _compose(tmp_path / "c.json")
    comp = json.loads((tmp_path / "c.json").read_text())
    V = X.View(dict(members=[_member("native_composite_pv_N_0_pvg0_p0")]), comp, 54, 58)
    assert V.unmapped == 0 and len(V.rows) == 1
    r = V.rows[0]
    assert (r["sink"], r["sink_port"], r["sink_bits"], r["source"]) == ("pvw_1__u_s0_b0", "bc", [[0, 2]], "pvw_1__u_ctl.cmd")
    assert r["id"] == "pvw_1__u_s0_b0.bc[0:2]<-pvw_1__u_ctl.cmd@50"


def test_view_counts_unmapped_composite_bits(tmp_path):
    _compose(tmp_path / "c.json")
    comp = json.loads((tmp_path / "c.json").read_text())
    V = X.View(dict(members=[_member("native_composite_pv_N_0_pvg0_p0", bits=((0, 5),))]), comp, 54, 58)
    assert V.unmapped == 3 and V.rows[0]["sink_bits"] == [[0, 2]]


def _tree(tmp_path, members):
    (tmp_path / "asb.json").write_text(json.dumps(dict(compose="c.json")))
    _compose(tmp_path / "c.json")
    (tmp_path / "r8.json").write_text(json.dumps(dict(members=members)))
    return ["pvx_tree", str(tmp_path / "r8.json"), str(tmp_path / "col.json"), str(tmp_path / "v.json")]


def _run(tmp_path, members, fn=None):
    a = _tree(tmp_path, members)
    a[0] = str(tmp_path)
    return (fn or X.main)(a + ["--asbuilt", "asb.json"])


def test_empty_view_exits_3_and_writes_nothing(tmp_path, capsys):
    assert _run(tmp_path, []) == 3
    assert "EMPTY" in capsys.readouterr().out
    assert not (tmp_path / "col.json").exists() and not (tmp_path / "v.json").exists()


def test_view_without_bank_members_exits_3(tmp_path):
    # composite members that the compose file cannot map back (wrong core) -> no pvw banks -> refuse
    assert _run(tmp_path, [_member("native_composite_pv_S_9_pvg9_p9")]) == 3
    assert not (tmp_path / "v.json").exists()


def test_guard_mutant_is_killed(tmp_path):
    src = Path(X.__file__).read_text()
    a = "    if not banks0 and not a.allow_empty:"
    assert src.count(a) == 1
    ns = {"__name__": "pvx_mut", "__file__": X.__file__}
    exec(compile(src.replace(a, "    if False:"), X.__file__, "exec"), ns)
    try:
        rc = _run(tmp_path, [], ns["main"])
    except BaseException:                  # without the guard the empty view falls into the column law and fails differently, never 3
        rc = None
    assert rc != 3
