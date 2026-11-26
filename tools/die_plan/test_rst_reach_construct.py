"""RST-REACH-CONSTRUCT (C-RST-RELAY-REACH): seat audit, raw diff, opt-in only."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import rst_reach_construct as C  # noqa: E402


class FakeRT:
    @staticmethod
    def physical_reset_relays(tree):
        return tree["relays"]


def tree():
    return {"root": (0.0, 0.0), "relays": [
        dict(name="u_rrl_1", q="q1", d="rst_root_n", xy=(100.0, 0.0)),
        dict(name="u_rrl_2", q="q2", d="q1", xy=(200.0, 0.0)),
        dict(name="u_rrl_3", q="q3", d="q2", xy=(300.0, 0.0)),
    ]}


def rows(**kw):
    return {n: (f"{n}/q", list(v)) for n, v in kw.items()}


def test_seat_within_reach_kept():
    o, h, k = C.seat_audit(FakeRT, tree(), rows(u_rrl_2=(210.0, 40.0)), 300.0)
    assert (o, h, k) == ([], [], ["u_rrl_2/q"])


def test_stale_seat_far_from_source_and_child_is_harmful():
    # u_rrl_2 seat left from an older solve, 800 um away: D leg 800 and child leg 700, tree site 100/100
    o, h, k = C.seat_audit(FakeRT, tree(), rows(u_rrl_2=(900.0, 0.0)), 300.0)
    assert not o and not k and len(h) == 1 and h[0][0] == "u_rrl_2/q" and h[0][2] > 300 > h[0][3]


def test_orphan_seat_has_no_relay():
    o, h, k = C.seat_audit(FakeRT, tree(), rows(u_rrl_9=(1.0, 1.0)), 300.0)
    assert [x[0] for x in o] == ["u_rrl_9/q"] and not h and not k


def test_seat_already_over_reach_in_tree_is_not_blamed():
    # a tree whose own leg is over reach: the seat is no worse, so it is not the cause and is kept
    t = tree()
    t["relays"][2]["xy"] = (900.0, 0.0)
    o, h, k = C.seat_audit(FakeRT, t, rows(u_rrl_3=(900.0, 0.0)), 300.0)
    assert not h and k == ["u_rrl_3/q"]


def test_seat_rows_only_reset_relay_keys():
    t = {"relay_sites": {"u_rrl_4/q": [1, 2], "u_srl_5/q": [3, 4], "u_x/q[3]": [5, 6], "u_ist_a_0.q[1]": [7, 8]}}
    assert sorted(C.seat_rows(t)) == ["u_rrl_4", "u_srl_5"]


def test_raw_diff_reports_only_changed_stage_raws():
    old = {"clock": {"landing_writer_start": {"branches": {"b": {"stages": [{"raw_reset": "rst_n_t5", "xy_um": [1, 1]}]}}},
                     "landing_local_resets": [{"name": "fstart_0", "raw": "rst_rl_3"}]}}
    new = {"clock": {"landing_writer_start": {"branches": {"b": {"stages": [{"raw_reset": "rst_n_t9", "xy_um": [1, 1]}]}}},
                     "landing_local_resets": [{"name": "fstart_0", "raw": "rst_rl_3"}]}}
    d = C.raw_diff(old, new)
    assert len(d) == 1 and d[0][1:] == ["rst_n_t5", "rst_n_t9"]
    assert C.raw_diff(old, old) == []
