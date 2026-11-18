"""WF-1 11-14: ENQUEUED members of a kit-identity group are cancelled by exact queue unit, the kept one stays."""
import time
from unittest import mock

import kit_wave as K

# S81-COL-FLOW-1118: dedup is off by default (r703 / r705); these tests opt S81 col types in explicitly
DEDUP_ON = {"dies": {"s81": {"kit_dedup": ["col_h*"]}}}


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
        n = K.dedup_enqueued(ap, DEDUP_ON, st, notes, {}, lambda r: hashes[r["item"]])
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
        n = K.dedup_enqueued(AP(), DEDUP_ON, st, {}, {}, lambda r: r["item"].ljust(64, "x"))
    assert n == 0 and all(r["status"] == "ENQUEUED" for r in a)


def test_registry_owner_is_kept_even_when_queued(tmp_path):
    import json
    now = time.time()
    a = [row(f"col_h9_r0_p6__t1__pv{i:08x}", f"job{i}", "QUEUED", now + i) for i in range(1, 4)]
    (tmp_path / "ident.json").write_text(json.dumps({"s81|col_h9_r0_p6__t1|" + "h" * 64: {"owner": a[2]["item"]}}))
    st = {"items": {r["item"]: r for r in a}}
    with mock.patch.object(K, "IDENT_FILE", str(tmp_path / "ident.json")), mock.patch.object(K.WJ, "stop_on_fleet", lambda *x, **k: {}):
        K.dedup_enqueued(AP(), DEDUP_ON, st, {}, {}, lambda r: "h" * 64)
    assert [r["item"] for r in a if r["status"] == "ENQUEUED"] == [a[2]["item"]]


def test_dedup_off_by_default():
    assert K.dedup_group({"dies": {"s81": {}}}, "s81", "col_h9_r0_p6__t1__pv00000001") == ""
    assert K.dedup_group(DEDUP_ON, "s81", "col_h9_r0_p6__t1__pv00000001") == "s81|col_h9_r0_p6__t1"


def _dstate(owner_status):
    return {"items": {
        "o": {"die": "s81", "item": "col_h9_r2__t1__pv000000aa", "status": owner_status, "updated": 1},
        "w": {"die": "s81", "item": "col_h9_r2__t1__pv000000bb", "status": "DEDUP-WAIT", "dedup_owner": "col_h9_r2__t1__pv000000aa",
              "dedup_hash": "h" * 64, "updated": 2},
        "d": {"die": "s81", "item": "col_h9_r2__t1__pv000000cc", "status": "DEDUP", "dedup_owner": "col_h9_r2__t1__pv000000aa",
              "dedup_hash": "h" * 64, "updated": 2}}, "dedup_released": {"s81|col_h9_r2__t1__pv000000bb": {"sig": "x"}}}


def test_dedup_off_releases_wait_and_held_members(tmp_path):
    ap = AP(); ap.AP_DIR = str(tmp_path)
    st = _dstate("FAIL")
    with mock.patch.object(K, "IDENT_FILE", str(tmp_path / "ident.json")):
        K.dedup_step(ap, {"dies": {"s81": {}}}, st, {}, str(tmp_path))
    assert set(st["items"]) == {"o"}
    assert sum("DEDUP OFF RELEASE" in m for m in ap.logs) == 2
    assert "s81|col_h9_r2__t1__pv000000bb" not in st["dedup_released"]


def test_dedup_on_keeps_wait_member_behind_failed_owner(tmp_path):
    ap = AP(); ap.AP_DIR = str(tmp_path)
    st = _dstate("RUNNING")
    with mock.patch.object(K, "IDENT_FILE", str(tmp_path / "ident.json")):
        K.dedup_step(ap, DEDUP_ON, st, {}, str(tmp_path))
    assert set(st["items"]) == {"o", "w", "d"} and not any("DEDUP OFF" in m for m in ap.logs)
