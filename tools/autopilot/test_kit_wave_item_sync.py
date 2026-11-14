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
