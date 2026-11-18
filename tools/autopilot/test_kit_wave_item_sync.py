"""FIX-SELFCONT: an item input held by one gen host is copied to the others (KIT_NOT_SELF_CONTAINED class)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kit_wave as KW

P = "/srv/opentallas-scratch2/claude/kit-ops-1/drt73-aor3/landed_sidecar_aor3.json"


class AP:
    def __init__(self): self.cmds, self.logs = [], []
    def sh(self, argv, timeout=0, input=None): self.cmds.append(argv); return 0, "", ""
    def log(self, m): self.logs.append(m)


def cfg(**kw):
    c = {"dies": {"s81": {"gen_hosts": ["epyc7", "epyc8", "epyc10"]}},
         "_item_incomplete": {"epyc8": {"s81": {"t62": f"{P} missing"}}, "epyc10": {"s81": {"t62": f"{P} missing"}}, "epyc7": {}}}
    c.update(kw); return c


def test_copies_from_holder_to_missing_hosts():
    ap = AP()
    done = KW.sync_item_inputs(ap, cfg())
    assert sorted((h, s) for h, _, s in done) == [("epyc10", "epyc7"), ("epyc8", "epyc7")]
    assert all("tar" in c[-1] and "--keep-old-files" in c[-1] and "epyc7" in c[-1] for c in ap.cmds)


def test_nothing_when_no_holder_or_off_or_unsafe():
    ap = AP()
    c = cfg(); c["_item_incomplete"]["epyc7"] = {"s81": {"t62": f"{P} missing"}}
    assert KW.sync_item_inputs(ap, c) == []
    assert KW.sync_item_inputs(ap, cfg(item_sync=False)) == []
    c = cfg(); c["_item_incomplete"]["epyc8"]["s81"]["t62"] = "/etc/passwd missing"
    assert [d for d in KW.sync_item_inputs(ap, c) if d[0] == "epyc8"] == []


def test_never_targets_a_host_outside_gen_hosts_and_backs_off_a_failed_copy(tmp_path, monkeypatch):
    """FLOW-2200 E: QC items spilled to epyc2 (not a gen host) retried the same failing copy every tick, 5 x sleeps each"""
    monkeypatch.setattr(KW, "_heal_path", lambda: str(tmp_path / "heal.json"))
    calls = []
    run = lambda argv, inp=None: (calls.append(argv), 2)[1]
    c = cfg(); c["_item_incomplete"]["epyc2"] = {"s81": {"t62": f"{P} missing"}}      # epyc2 is not in the die's gen_hosts
    c["_item_incomplete"]["epyc8"] = {}; c["_item_incomplete"]["epyc10"] = {}; c["_item_incomplete"]["epyc7"] = {"s81": {}}
    KW.sync_item_inputs(AP(), c, run=run)
    assert calls == []                                                                 # nothing targets epyc2
    c = cfg()
    monkeypatch.setattr(KW.time, "sleep", lambda s: (_ for _ in ()).throw(AssertionError("a permanent rc must not sleep-retry")))
    KW.sync_item_inputs(AP(), c, run=run)
    first = len(calls)
    assert first == 2                                                                  # one try per (src, dst, path), rc=2 is not retried
    KW.sync_item_inputs(AP(), c, run=run)
    assert len(calls) == first                                                         # backed off for ITEM_SYNC_BACKOFF_S
