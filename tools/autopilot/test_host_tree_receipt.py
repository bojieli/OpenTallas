"""HOST-RECEIPT-1120 (FLEET-WATCH-1015): a host runs gen on a source tree only while its OWN file-hash receipt matches the die's pinned manifest hash."""
import json, os, sys, types
from pathlib import Path
sys.path.insert(0, os.path.dirname(__file__))
import kit_wave as KW

H = "a" * 64
TREE = "/srv/opentallas-scratch2/claude/t/src_new"
MISS = (1, "", "SRC_MANIFEST CACHE MISS /x: no manifest\n")


class AP:
    HUB_NAME = "intel2"

    def __init__(self, tmp, answers):
        self.AP_DIR, self.answers, self.calls, self.logs = Path(tmp), answers, [], []

    def sh(self, argv, timeout=60, input=None):
        host = argv[-2] if argv[0] == "ssh" else "intel2"
        self.calls.append(host)
        return self.answers.get(host, (0, "{}", ""))

    def log(self, m):
        self.logs.append(m)


def setup(monkeypatch, tmp_path, answers, started=None):
    ap = AP(tmp_path, answers)
    monkeypatch.delenv("OT_KW_HOST_RECEIPT", raising=False)
    monkeypatch.setattr(KW, "tree_on_host", lambda *a, **k: True)
    monkeypatch.setattr(KW, "gen_hosts", lambda cfg, die, item=None: ["epyc9", "intel1", "epyc2"])
    monkeypatch.setattr(KW, "_receipt_start_verify", lambda AP_, host, tree, expect, script, hub: (started if started is not None else []).append(host))
    return ap


def sp(host="epyc9"):
    return {"src": TREE, "gen_host": host, "src_manifest_hash": H.upper()}


def test_no_pinned_hash_or_off_switch_never_probes(monkeypatch, tmp_path):
    ap = setup(monkeypatch, tmp_path, {"epyc9": MISS})
    assert KW.host_tree_receipt(ap, {}, "epyc9", TREE, "") and KW.host_tree_receipt(ap, {}, "epyc9", TREE, "short")
    monkeypatch.setenv("OT_KW_HOST_RECEIPT", "0")
    assert KW.host_tree_receipt(ap, {}, "epyc9", TREE, H) and ap.calls == []


def test_a_host_without_its_receipt_is_skipped_and_starts_its_own_verification(monkeypatch, tmp_path):
    started = []
    ap = setup(monkeypatch, tmp_path, {"epyc9": MISS, "intel1": MISS}, started)
    cfg = {"dies": {"qc": {}}}
    assert KW.tree_host_for(ap, cfg, "qc", sp("epyc9"), "t1") == "epyc2"             # epyc9 and intel1 lack the files (the 09:38 QC A4 case); epyc2 has its receipt
    assert started == ["epyc9", "intel1"] and any("HOST-RECEIPT-MISS epyc9" in l for l in ap.logs)
    n = len(ap.calls)
    assert KW.tree_host_for(ap, cfg, "qc", sp("epyc9"), "t2") == "epyc2" and len(ap.calls) == n       # one probe per host and tree per pass


def test_no_host_with_a_receipt_means_no_launch(monkeypatch, tmp_path):
    ap = setup(monkeypatch, tmp_path, {"epyc9": MISS, "intel1": MISS, "epyc2": MISS})
    assert KW.tree_host_for(ap, {"dies": {"qc": {}}}, "qc", sp("epyc9"), "t1") == ""


def test_a_pass_is_remembered_across_passes_and_a_probe_failure_is_unknown_not_a_refusal(monkeypatch, tmp_path):
    ap = setup(monkeypatch, tmp_path, {"epyc9": (0, "{}", "")})
    assert KW.host_tree_receipt(ap, {}, "epyc9", TREE, H) and ap.calls == ["epyc9"]
    ap2 = AP(tmp_path, {"epyc9": MISS})                                              # a new pass: the disk record answers, no ssh
    assert KW.host_tree_receipt(ap2, {}, "epyc9", TREE, H) and ap2.calls == []
    ap3 = AP(tmp_path / "other", {"intel1": (255, "", "ssh: connect timed out"), "epyc2": (1, "", "Traceback ... ImportError")})
    assert KW.host_tree_receipt(ap3, {}, "intel1", TREE, H) and KW.host_tree_receipt(ap3, {}, "epyc2", TREE, H)


def test_die_option_host_receipt_false_keeps_the_old_rule(monkeypatch, tmp_path):
    ap = setup(monkeypatch, tmp_path, {"epyc9": MISS})
    assert KW.tree_host_for(ap, {"dies": {"qc": {"host_receipt": False}}}, "qc", sp("epyc9"), "t1") == "epyc9" and ap.calls == []


def test_the_probe_is_the_hosts_own_cached_receipt_with_the_pinned_hash(monkeypatch, tmp_path):
    seen = []
    ap = setup(monkeypatch, tmp_path, {})
    ap.sh = lambda argv, timeout=60, input=None: (seen.append(argv), (0, "{}", ""))[1]
    assert KW.host_tree_receipt(ap, {}, "epyc9", TREE, H)
    assert seen[0][:2] == ["ssh", "-o"] and seen[0][-2] == "epyc9" and f"receipt {TREE} --expect {H}" in seen[0][-1] and not seen[0][-1].endswith("cached-receipt " + TREE + " --expect " + H)


def test_a_miss_is_not_reprobed_every_tick_and_a_pass_is_kept_an_hour(monkeypatch, tmp_path):
    ap = setup(monkeypatch, tmp_path, {"epyc9": MISS})
    assert not KW.host_tree_receipt(ap, {}, "epyc9", TREE, H) and ap.calls == ["epyc9"]
    ap2 = AP(tmp_path, {"epyc9": (0, "{}", "")})
    assert not KW.host_tree_receipt(ap2, {}, "epyc9", TREE, H) and ap2.calls == []          # next tick: the recorded miss answers (120 s)
    assert KW.HOST_RECEIPT_TTL_S >= 3600 and KW.HOST_RECEIPT_MISS_TTL_S <= 300


def test_the_host_receipt_accepts_a_hardlinked_complete_tree_and_rejects_a_missing_file(tmp_path, monkeypatch):
    import src_manifest as SM
    monkeypatch.setattr(SM, "CACHE_DIR", str(tmp_path / "cache"))
    t = tmp_path / "tree"; (t / "a").mkdir(parents=True)
    (t / "a/f.sv").write_text("x"); os.link(t / "a/f.sv", tmp_path / "other_link")        # shared inode, nlink 2 (the live _work trees)
    files = {"a/f.sv": SM.sha256_file(t / "a/f.sv")}
    m = {"main_sha": "m", "scope": ["a"], "overlay": {}, "files": files}
    m["manifest_hash"] = SM.manifest_hash(m)
    (t / SM.MANIFEST).write_text(json.dumps(m)); (t / SM.HASHFILE).write_text(m["manifest_hash"])
    errs, _ = SM.host_receipt(str(t), m["manifest_hash"])
    assert errs and "no completed verification" in errs[0]                                  # nothing verified on this host yet
    assert SM.verify(str(t), m["manifest_hash"])[0] == []                                   # the host's own full verification (not --ro)
    assert SM.host_receipt(str(t), m["manifest_hash"])[0] == []                             # PASS although the inode is shared
    assert SM.cached_receipt(str(t), m["manifest_hash"])[0]                                 # the old strict receipt would have refused it
    os.unlink(t / "a/f.sv")
    errs, _ = SM.host_receipt(str(t), m["manifest_hash"])
    assert errs and "no longer matches" in errs[0]
    assert SM.host_receipt(str(t), "0" * 64)[0]
