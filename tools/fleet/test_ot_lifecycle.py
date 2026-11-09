#!/usr/bin/env python3
"""Fixture test for ot-lifecycle plan/apply: positive controls (retained paths stay KEEP) and negative controls (a row added
after the plan stops the apply); hold expiry; cited older attempts; report-only signed trim."""
import json, os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
LC, TOOL = os.path.join(HERE, "ot-lifecycle.py"), os.path.join(HERE, "ot-autoclean.py")
OLD = time.time() - 72 * 3600


def write(p, n=4096, old=True):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write(os.urandom(n))
    if old:
        os.utime(p, (OLD, OLD))


def kit(d):
    b = f"{d}/run/results/asap7/d/base"
    for n in ("2_1_floorplan.odb", "2_floorplan.odb", "3_3_place_gp.odb", "3_place.odb", "4_1_cts.odb", "4_cts.odb",
              "5_route.odb", "6_final.odb", "6_final.spef"):
        write(f"{b}/{n}", 8192)
    write(f"{d}/run/objects/lib.lib", 8192)
    write(f"{d}/run/logs/asap7/d/base/1.log", 4096)
    write(f"{d}/config.mk", 200)


def run_fixture(W):
    global ROOT
    ROOT = os.path.join(W, "x/claude")
    os.makedirs(ROOT)
    kit(f"{ROOT}/dead-aa/kit1")
    write(f"{ROOT}/dead-aa/.keep", 0)
    os.utime(f"{ROOT}/dead-aa/.keep", (OLD, OLD))
    kit(f"{ROOT}/dead-bb/kit2")
    write(f"{ROOT}/dead-bb/.keep", 0, old=False)
    kit(f"{ROOT}/dead-cc/kit3")
    kit(f"{ROOT}/dead-dd/kit4")
    kit(f"{ROOT}/dead-ee/kit5")
    write(f"{ROOT}/dead-ee/kit5/signoff/signoff.json", 10)
    with open(f"{ROOT}/dead-ee/kit5/signoff/signoff.json", "w") as fh:
        json.dump({"verdict": "SIGNED", "inputs": {"odb": f"{ROOT}/dead-ee/kit5/run/results/asap7/d/base/6_final.odb"}}, fh)
    write(f"{ROOT}/dead-ee/kit5/ARCHIVED.json", 10)
    kit(f"{ROOT}/dead-ff/kit6")
    write(f"{ROOT}/dead-ff/kit6/run/logs/young.log", 10, old=False)
    kit(f"{ROOT}/die-s81-81/kit7")
    with open(f"{ROOT}/die-s81-81/kit7/config.mk", "w") as fh:      # a live lane file names a dead lane's kit
        fh.write(f"export X = {ROOT}/dead-ll/kit10/run\n")
    os.utime(f"{ROOT}/die-s81-81/kit7/config.mk", (OLD, OLD))
    kit(f"{ROOT}/dead-ll/kit10")
    kit(f"{ROOT}/dead-mm.old-kw37-1/kit11")          # a renamed tree is skipped whole (holds are keyed by path)
    kit(f"{ROOT}/dead-gg/kit-wave/s81/p/items/it/attempt_1/gen/it")
    write(f"{ROOT}/dead-hh/loose/file.bin", 4096)
    # older attempt cited by a signed record elsewhere: whole attempt stays even though it is not the latest
    kit(f"{ROOT}/dead-jj/kit-wave/s81/p/items/it2/attempt_1/gen/it2")
    kit(f"{ROOT}/dead-jj/kit-wave/s81/p/items/it2/attempt_3/gen/it2")
    write(f"{ROOT}/dead-kk/rec/signoff/signoff.json", 10)
    with open(f"{ROOT}/dead-kk/rec/signoff/signoff.json", "w") as fh:
        json.dump({"verdict": "SIGNED", "inputs": {"odb": f"{ROOT}/dead-jj/kit-wave/s81/p/items/it2/attempt_1/gen/it2/run/results/asap7/d/base/6_final.odb"}}, fh)
    write(f"{ROOT}/dead-ii/kit9/keepme.txt", 20)
    kit(f"{ROOT}/dead-nn/kit12")                     # read-only dir inside: rm -rf would stop half way, so the folder is not started
    os.chmod(f"{ROOT}/dead-nn/kit12/run/objects", 0o555)
    kit(f"{ROOT}/dead-oo/kit13")                     # lane goes live between plan and apply: recheck must skip the row
    # snapshot
    snap = os.path.join(W, "snap")
    os.makedirs(snap)
    with open(f"{snap}/protected.tsv", "w") as fh:
        fh.write(f"{ROOT}/dead-cc/kit3\tfixture\n")
        for i in range(120):
            fh.write(f"/srv/none/claude/lane/x{i}\tpad\n")
    json.dump({"created": time.time(), "created_h": "now"}, open(f"{snap}/meta.json", "w"))
    json.dump({"paths": [], "words": []}, open(f"{snap}/queue.json", "w"))
    json.dump({"attempts": {}, "latest": {f"fix:{ROOT}/dead-jj/kit-wave/s81/p/items/it2": 3}, "keep": [], "current_di": {}, "created": time.time(), "source": "fix"},
              open(f"{snap}/kitwave.json", "w"))
    life = {"created": time.time(), "live": ["DIE-S81-81"], "lane_last": {},
            "paths48": [f"{ROOT}/dead-dd/kit4"], "words48": [],
            "protected_full": [["fix", f"{ROOT}/dead-cc/kit3", "fixture"]]}
    json.dump(life, open(f"{W}/life.json", "w"))
    out = f"{W}/out"
    r = subprocess.run([sys.executable, "-I", LC, "plan", "--tool", TOOL, "--host", "fix", "--lifesnap", f"{W}/life.json", "--out", out,
                        "--state", f"{W}/state", "--snapshot", snap, "--docker", "", "--roots", ROOT], capture_output=True, text=True, timeout=600)
    print(r.stdout[-1500:], r.stderr[-1500:])
    assert r.returncode == 0
    mf = sorted(f for f in os.listdir(out) if f.startswith("PLAN-"))[-1]
    rows = {}
    for ln in open(f"{out}/{mf}").read().splitlines()[1:]:
        c = ln.split("\t")
        rows[c[0].replace(ROOT + "/", "")] = (c[1], c[2])
    for k, v in sorted(rows.items()):
        print(f"{k:50s} {v[0]:26s} {v[1]}")
    expect = {
        "dead-mm.old-kw37-1": ("KEEP-excluded", "KEEP"),
        "dead-nn/kit12": ("KEEP-not-deletable", "KEEP"),
        "dead-oo/kit13": ("DEL-L4-KIT", "DELETE"),
        "dead-ll/kit10": ("KEEP-referenced", "KEEP"),      # positive control of the reference scan
        "dead-jj/kit-wave/s81/p/items/it2/attempt_1": ("KEEP-cited-unit", "KEEP"),   # older attempt cited by a signed record
        "dead-aa/kit1": ("DEL-L4-KIT", "DELETE"),          # expired .keep (72 h, dead lane) released
        "dead-bb": ("KEEP-dotkeep", "KEEP"),               # young .keep at the lane root holds its tree
        "dead-cc/kit3": ("KEEP-protected", "KEEP"),
        "dead-dd/kit4": ("KEEP-queue48", "KEEP"),
        "dead-ff/kit6": ("KEEP-kit-livelane", "KEEP"),      # a file written within 24 h keeps the kit
        "die-s81-81": ("KEEP-livelane-tree", "KEEP"),
        "dead-gg/kit-wave/s81/p/items/it/attempt_1": ("DEL-L4-ATTEMPT-UNKNOWN", "DELETE"),
    }
    bad = 0
    for k, v in expect.items():
        if rows.get(k) != v:
            print("MISMATCH", k, rows.get(k), "expected", v)
            bad += 1
    sg = [k for k in rows if k.startswith("dead-ee/kit5/") and rows[k][1] == "DELETE"]
    print("signed trim rows:", sg)
    if sg:                      # signed trim is report-only until the stub is defined by readers and tested
        print("MISMATCH signed trim must be report-only", sg)
        bad += 1
    print("CONTROLS", "PASS" if not bad else f"FAIL {bad}")
    # apply on the fixture: only DEL-L4-KIT; negative control: a row added to protected after plan must ALERT
    with open(f"{snap}/protected.tsv", "a") as fh:
        fh.write(f"{ROOT}/dead-aa/kit1\tadded after plan (must ALERT)\n")
    json.dump({"created": time.time(), "created_h": "now"}, open(f"{snap}/meta.json", "w"))
    r = subprocess.run([sys.executable, "-I", LC, "apply", "--tool", TOOL, "--host", "fix", "--lifesnap", f"{W}/life.json", "--out", out,
                        "--state", f"{W}/state2", "--snapshot", snap, "--docker", "", "--roots", ROOT, "--manifest", f"{out}/{mf}", "--cats", "DEL-L4-KIT",
                        "--coord-ref", "fixture"], capture_output=True, text=True, timeout=600)
    print(r.stdout[-800:], r.stderr[-800:], "rc", r.returncode)
    assert r.returncode == 3, "added-protected must ALERT and stop"
    assert os.path.exists(f"{ROOT}/dead-aa/kit1/config.mk"), "alerted row must not be deleted"
    life2 = json.load(open(f"{W}/life.json"))           # dead-oo has a live owner after the plan
    life2["live"] = life2["live"] + ["DEAD-OO"]
    json.dump(life2, open(f"{W}/life.json", "w"))
    # remove the fake row, apply really
    lines = open(f"{snap}/protected.tsv").read().splitlines()
    open(f"{snap}/protected.tsv", "w").write("\n".join(lines[:-1]) + "\n")
    r = subprocess.run([sys.executable, "-I", LC, "apply", "--tool", TOOL, "--host", "fix", "--lifesnap", f"{W}/life.json", "--out", out,
                        "--state", f"{W}/state3", "--snapshot", snap, "--docker", "", "--roots", ROOT, "--manifest", f"{out}/{mf}", "--cats", "DEL-L4-KIT",
                        "--coord-ref", "fixture"], capture_output=True, text=True, timeout=600)
    print(r.stdout[-400:], r.stderr[-800:], "rc", r.returncode)
    assert r.returncode == 0 and not os.path.exists(f"{ROOT}/dead-aa/kit1"), "apply must delete the row"
    assert os.path.exists(f"{ROOT}/dead-cc/kit3") and os.path.exists(f"{ROOT}/dead-bb/kit2"), "protected/.keep untouched"
    assert os.path.exists(f"{ROOT}/dead-oo/kit13/config.mk"), "lane live at apply time: row skipped"
    os.chmod(f"{ROOT}/dead-nn/kit12/run/objects", 0o755)     # so pytest can clean up
    print("APPLY CONTROLS PASS")
    assert not bad


def test_lifecycle_fixture(tmp_path):
    run_fixture(str(tmp_path))


def test_count_check_lost(tmp_path):
    import importlib.util
    sp = importlib.util.spec_from_file_location("lc", LC)
    lc = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(lc)
    sp2 = importlib.util.spec_from_file_location("ac", TOOL)
    ac = importlib.util.module_from_spec(sp2)
    sp2.loader.exec_module(ac)
    ap = lc.Apply.__new__(lc.Apply)
    ap.m = ac
    root = str(tmp_path)
    kept, ours, theirs = f"{root}/a/keep", f"{root}/b/sub/rec", f"{root}/c/rec"
    assert ap.lost({kept}, {f"{root}/b"}) == []                          # still there
    assert ap.lost({ours}, {f"{root}/b"}) == [ours]                      # gone under a removed path: loss
    assert ap.lost({theirs}, {f"{root}/b"}) == []                        # gone but not under anything this run removed
