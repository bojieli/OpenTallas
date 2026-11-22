"""CLEAN-AGGR-R3: leases (ot_lease.py) keep what a lane / job uses; expired leases protect nothing; the guard honours them; the live-process
check matches whole path components (specA is not kept by a live specA7)."""
import importlib.util, json, os, sys, time

H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H)
import ot_lease as L          # noqa: E402
import ot_delete_guard as g   # noqa: E402


def test_take_renew_release_expire(tmp_path):
    d = str(tmp_path / "leases")
    r = L.take("/srv/opentallas-scratch2/claude/lane/tree", "LANE-A", 2, d=d, now=1000)
    assert r["expires"] == 1000 + 7200
    L.take("/srv/opentallas-scratch2/claude/lane/tree", "LANE-A", 4, d=d, now=2000)        # renew: same file
    assert len(os.listdir(d)) == 1 and L.leases(d, now=2000 + 4 * 3600 - 1)
    assert L.leases(d, now=2000 + 4 * 3600 + 1) == []                                      # expired = nothing
    L.take("/srv/opentallas-scratch2/claude/lane/tree", "LANE-B", 1, d=d, now=2000)
    assert L.release("/srv/opentallas-scratch2/claude/lane/tree", "LANE-B", d=d) and not L.release("/x", "LANE-B", d=d)
    assert L.take("/a", "X", 1000, d=d, now=0)["expires"] == L.MAX_TTL_H * 3600


def test_covering():
    ls = [{"path": "/srv/s/claude/rt/abcdef012345", "owner": "K", "expires": 9e18}]
    assert L.covering("/srv/s/claude/rt/abcdef012345", ls)
    assert L.covering("/srv/s/claude/rt/abcdef012345/tools", ls)
    assert L.covering("/srv/s/claude/rt", ls)                     # contains a leased path
    assert L.covering("/srv/s/claude/rt/abcdef0123456", ls) is None
    assert L.covering("/srv/s/claude/rt/abcdef01234", ls) is None  # a prefix of the NAME is not the path


def test_guard_honours_live_lease_only(tmp_path, monkeypatch):
    d = tmp_path / "leases"
    k = tmp_path / "srv" / "lane" / "kit"; k.mkdir(parents=True)
    monkeypatch.setenv("OT_LEASE_DIR", str(d))
    assert g.refuse(str(k), protected=set(), ptext="", current={}, allow=set()) is None
    L.take(str(k), "LANE-A", 1)
    assert "lease" in g.refuse(str(k), protected=set(), ptext="", current={}, allow=set())
    assert "lease" in g.refuse(str(k.parent), protected=set(), ptext="", current={}, allow=set())
    f = os.path.join(str(d), os.listdir(str(d))[0])
    r = json.load(open(f)); r["expires"] = time.time() - 1; json.dump(r, open(f, "w"))
    assert g.refuse(str(k), protected=set(), ptext="", current={}, allow=set()) is None


def test_live_text_match_is_component_exact(tmp_path):
    a = tmp_path / "fam" / "specA"; a.mkdir(parents=True)
    a7 = str(tmp_path / "fam" / "specA7")
    pt = "python3 run-item %s/spec.json\n" % a7
    assert g.refuse(str(a), protected=set(), ptext=pt, current={}, allow=set()) is None
    assert g.refuse(str(a), protected=set(), ptext="bash %s/go.sh" % a, current={}, allow=set())
    assert g.refuse(str(a), protected=set(), ptext="cd %s && x" % a, current={}, allow=set())
    assert g.refuse(str(a), protected=set(), ptext="x %s\n" % a, current={}, allow=set())


def test_hub_leases_in_protected_list(tmp_path):
    sp = importlib.util.spec_from_file_location("bpl_l", os.path.join(H, "build_protected_live.py")); B = importlib.util.module_from_spec(sp); sp.loader.exec_module(B)
    d = str(tmp_path / "hl")
    L.take("/srv/opentallas-scratch2/claude/lane/tree", "LANE-A", 1, host="epyc7", d=d)
    L.take("/srv/opentallas-scratch2/claude/rt/abcdef012345", "LANE-B", 1, d=d)
    out = set()
    assert B.hub_lease_paths(out, g.canon, d=d) == 2
    assert "@epyc7,intel2 /srv/opentallas-scratch2/claude/lane/tree" in out and "/srv/opentallas-scratch2/claude/rt/abcdef012345" in out



def test_container_lease_protects_only_itself_clean_aggr_r3():
    import ot_lease as L
    ls = [{"path": "/srv/opentallas-scratch2/claude/kw45", "owner": "ot-run/x"}, {"path": "/srv/opentallas-scratch3/claude/ot-jobs", "owner": "ot-run/y"}]
    assert L.covering("/srv/opentallas-scratch2/claude/kw45/snap_s81_head/s81_head_r3c_s0", ls) is None
    assert L.covering("/srv/opentallas-scratch3/claude/ot-jobs/job-1", ls) is None
    assert L.covering("/srv/opentallas-scratch2/claude/kw45", ls) is not None
    assert L.covering("/srv/opentallas-scratch2/claude/lane/x", [{"path": "/srv/opentallas-scratch2/claude/lane", "owner": "o"}]) is not None


def test_hub_container_lease_not_a_list_row_clean_aggr_r3(tmp_path):
    sp = importlib.util.spec_from_file_location("bpl_c", os.path.join(H, "build_protected_live.py")); B = importlib.util.module_from_spec(sp); sp.loader.exec_module(B)
    d = str(tmp_path / "hc")
    L.take("/srv/opentallas-scratch2/claude/kw45", "FLOW-OPS-R2", 1, d=d)
    L.take("/srv/opentallas-scratch2/claude/kw45/src_x_work", "X", 1, d=d)
    out = set()
    assert B.hub_lease_paths(out, g.canon, d=d) == 1
    assert out == {"/srv/opentallas-scratch2/claude/kw45/src_x_work"}
