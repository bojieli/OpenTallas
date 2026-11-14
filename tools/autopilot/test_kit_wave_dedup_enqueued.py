"""WF-1 11-14: ENQUEUED members of a kit-identity group are cancelled by exact queue unit, the kept one stays."""
import time
from unittest import mock

import kit_wave as K


class AP:
    DRY = False
    HUB_NAME = "intel2"

    def __init__(self):
        self.cmds, self.logs = [], []

    def sh(self, argv, timeout=0, input=None):
        self.cmds.append(argv)
        return 0, "", ""

    def log(self, m):
        self.logs.append(m)


def row(item, q_id, q_status, started, h=None):
    return {"die": "s81", "item": item, "status": "ENQUEUED", "q_id": q_id, "q_status": q_status, "started": started,
            "kit": f"epyc7:/k/{item}", "dir": f"/nonexistent/{item}", "attempt": 1}


def test_enqueued_duplicates_are_stopped_by_exact_unit_and_keeper_stays(tmp_path):
    now = time.time()
    a = [row(f"col_h9_r0_p6__t1__pv{i:08x}", f"job{i}", "QUEUED", now + i) for i in range(1, 5)]
    a[2]["q_status"] = "RUNNING"                                   # the running one is kept
    other = row("col_h9_r0_p5__t1__pv000000aa", "jobx", "QUEUED", now)   # a different group stays alone
    st = {"items": {r["item"]: r for r in a + [other]}}
    hashes = {r["item"]: "h" * 64 for r in a}
    hashes[other["item"]] = "o" * 64
    ap, notes = AP(), {}
    with mock.patch.object(K, "IDENT_FILE", str(tmp_path / "ident.json")), \
            mock.patch.object(K.WJ, "stop_on_fleet", lambda *x, **k: {}):
        n = K.dedup_enqueued(ap, {"dies": {}}, st, notes, {}, lambda r: hashes[r["item"]])
    assert n == 3
    kept = [r for r in a if r["status"] == "ENQUEUED"]
    assert [r["item"] for r in kept] == [a[2]["item"]]
    stopped = [c for c in ap.cmds if c[:3] == ["systemctl", "--user", "stop"]]
    assert sorted(c[3] for c in stopped) == ["ap-job1-a1", "ap-job2-a1", "ap-job4-a1"]
    assert all(r["status"] == "DEDUP" and r["dedup_owner"] == a[2]["item"] for r in a if r is not a[2])
    assert other["status"] == "ENQUEUED"


def test_different_identities_are_all_kept(tmp_path):
    now = time.time()
    a = [row(f"col_h9_r0_p6__t1__pv{i:08x}", f"job{i}", "QUEUED", now + i) for i in range(1, 4)]
    st = {"items": {r["item"]: r for r in a}}
    with mock.patch.object(K, "IDENT_FILE", str(tmp_path / "ident.json")):
        n = K.dedup_enqueued(AP(), {"dies": {}}, st, {}, {}, lambda r: r["item"].ljust(64, "x"))
    assert n == 0 and all(r["status"] == "ENQUEUED" for r in a)


def test_registry_owner_is_kept_even_when_queued(tmp_path):
    import json
    now = time.time()
    a = [row(f"col_h9_r0_p6__t1__pv{i:08x}", f"job{i}", "QUEUED", now + i) for i in range(1, 4)]
    (tmp_path / "ident.json").write_text(json.dumps({"s81|col_h9_r0_p6__t1|" + "h" * 64: {"owner": a[2]["item"]}}))
    st = {"items": {r["item"]: r for r in a}}
    with mock.patch.object(K, "IDENT_FILE", str(tmp_path / "ident.json")), mock.patch.object(K.WJ, "stop_on_fleet", lambda *x, **k: {}):
        K.dedup_enqueued(AP(), {"dies": {}}, st, {}, {}, lambda r: "h" * 64)
    assert [r["item"] for r in a if r["status"] == "ENQUEUED"] == [a[2]["item"]]
