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


def test_src_sync_counts_a_batch_only_when_the_files_exist_on_the_target(tmp_path, monkeypatch):
    """FABLE-FLOW-0010 F: tar rc 2 (destination write failed) was counted as copied: 229 files x3, no directory"""
    monkeypatch.setattr(KW, "_heal_path", lambda: str(tmp_path / "heal.json"))
    P1 = "/srv/opentallas-scratch2/claude/x/bind_a/f1.sv"
    cfg = {"dies": {"qwen_compute": {"gen_hosts": ["epyc9", "epyc2"]}}, "_src_incomplete": {"epyc2": {"qwen_compute": P1 + " missing"}, "epyc9": {}}}
    class A2:
        def __init__(self): self.logs = []
        def log(self, m): self.logs.append(m)
    def run_factory(verify_rc):
        def run(argv, inp=None):
            return 2 if "-cf -" in argv[-1] else verify_rc
        return run
    a = A2()
    assert KW.sync_die_inputs(a, cfg, run=run_factory(1)) == []                       # copy rc 2, files not there: not counted
    assert any("NOT on epyc2" in l for l in a.logs)
    a = A2()
    done = KW.sync_die_inputs(a, cfg, run=run_factory(0))                             # rc 2 because the files already existed, verified: counted
    assert done and done[0][:3] == ("epyc2", "qwen_compute", 1)


def test_src_sync_logs_the_first_stderr_line_of_a_failed_copy(tmp_path, monkeypatch):
    """SRCSYNC-ERR-1119: the log names the copy's error, and the 2-try stop is the existing heal_blocked"""
    monkeypatch.setattr(KW, "_heal_path", lambda: str(tmp_path / "heal.json"))
    P1 = "/srv/opentallas-scratch2/claude/x/bind_a/f1.sv"
    cfg = {"dies": {"qwen_compute": {"gen_hosts": ["epyc9", "epyc2"]}}, "_src_incomplete": {"epyc2": {"qwen_compute": P1 + " missing"}, "epyc9": {}}}
    class A2:
        def __init__(self): self.logs = []
        def log(self, m): self.logs.append(m)
    def run(argv, inp=None):
        if "-cf -" in argv[-1]:
            errf = argv[-1].rsplit("2>", 1)[1].strip().strip("'")
            open(errf, "w").write("tar: x: Cannot write: No space left on device\n")
            return 2
        return 1
    a = A2()
    KW.sync_die_inputs(a, cfg, run=run)
    assert any("first error: tar: x: Cannot write: No space left on device" in l for l in a.logs)
    a2 = A2()
    KW.sync_die_inputs(a2, cfg, run=run)
    KW.sync_die_inputs(a2, cfg, run=run)                                              # third call: blocked after 2 tries
    assert any("STOPPED after 2" in l for l in a2.logs)


def test_plan_present_pins_file_missing_copies_the_pins_file(tmp_path, monkeypatch):
    """FLOW-HEALTH-2 11-19: 'plan.json: <pins> missing' (plan exists on the host) copied the PLAN every tick: tar --keep-old-files rc 2, ITEM-SYNC loop 37x"""
    monkeypatch.setattr(KW, "_heal_path", lambda: str(tmp_path / "heal.json"))
    plan = "/srv/opentallas-scratch2/claude/tl-q/por/plan_x.json"
    pins = "/srv/opentallas-scratch2/claude/tl-q/por/cores/pins.json"
    c = {"dies": {"qwen_compute": {"gen_hosts": ["intel1", "epyc2"]}},
         "_item_incomplete": {"epyc2": {"qwen_compute": {"phy": f"{plan}: {pins} missing"}}, "intel1": {}}}
    ap = AP()
    KW.sync_item_inputs(ap, c)
    cmd = ap.cmds[0][-1]
    assert "cores/pins.json" in cmd and "plan_x.json" not in cmd


def test_die_off_line_is_hourly_per_die_and_reason():
    import inspect
    src = inspect.getsource(KW)
    assert 'st.setdefault("die_off_logged"' in src and ">= 3600" in src
