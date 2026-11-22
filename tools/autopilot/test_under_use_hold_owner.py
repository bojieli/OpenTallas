"""HOLD-OWNER-1122 (FABLE-FLOW-0350 U1): a hold key with no term (or no owner) for 24 h becomes an OWNERS row for the die owner lane."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ownership as OWN  # noqa: E402
import under_use as UU  # noqa: E402

NOW = 1_800_000_000.0
CFG = {"dies": {
    "s81": {"die_owner": "DIE-S81-92", "lane": "KIT-WAVE-3", "hold_items": {
        "col_h9_r2*": "col_h9_r2 wait for the seat fix", "gunit__t1": "owner=S81-T51-RECUT eta=2099-01-01 recut",
        "hd_x*": "owner=S81-PLAN wait"}},
    "qwen_compute": {"owner_lane": "QC die owner (DIE-QC-103)", "lane": "KIT-WAVE-12", "hold_items": {"cbf_*": "fresh hold"}},
    "hbm": {"die_owner": "DIE-HBM-102", "parked": {"owner": "COORD"}, "hold_items": {"*": "hbm parked"}}}}


def rows(die, item, n, age_h):
    return {f"{die}|{item}{i}": {"die": die, "item": f"{item}{i}", "status": "ENQUEUED", "updated": NOW - age_h * 3600} for i in range(n)}


def items():
    it = {}
    it.update(rows("s81", "col_h9_r2_", 3, 36.7))       # no owner, no eta, 36.7 h -> row for DIE-S81-92
    it.update(rows("s81", "gunit__t1", 1, 33.0))        # has eta -> no row
    it.update(rows("s81", "hd_x", 2, 30.0))             # named owner, no eta, 30 h -> row for the die owner, names S81-PLAN
    it.update(rows("qwen_compute", "cbf_", 2, 3.0))      # 3 h: too young
    it.update(rows("hbm", "q_", 4, 237.0))              # parked die: left out
    return it


def test_rows_for_unowned_or_termless_holds_older_than_24h():
    det = UU.held_detail(items(), CFG, now=NOW)
    out = UU.hold_owner_rows(det, CFG, dies={d for d, _, _ in OWN.DIES}, now=NOW)
    got = {(r["die"], r["item"]): r for r in out}
    assert set(got) == {("s81", "HOLD SKIP-HELD col_h9_r2*"), ("s81", "HOLD SKIP-HELD hd_x*")}
    a = got[("s81", "HOLD SKIP-HELD col_h9_r2*")]
    assert a["owner"] == a["default_owner"] == "DIE-S81-92" and a["replicas"] == 3 and a["state"] == "FIX" and "no owner" in a["next_step"]
    assert "hold names S81-PLAN" in got[("s81", "HOLD SKIP-HELD hd_x*")]["next_step"]
    tsv = OWN.to_tsv(out, NOW)                                   # rows fit the OWNERS.tsv writer (die order, state order, columns)
    assert tsv.count("\tHOLD SKIP-HELD ") == 2 and "\tDIE-S81-92\t" in tsv


def test_owner_lane_from_owner_lane_text_and_unnamed():
    assert UU.die_owner_lane(CFG, "qwen_compute") == "DIE-QC-103"
    assert UU.die_owner_lane(CFG, "zz") == "zz die owner (unnamed)"


class _AP:
    OT_RUN = "ot-run"

    def __init__(self, d):
        self.AP_DIR, self.posts, self.lines = str(d), [], []

    def sh(self, argv, timeout=0):
        return 1, "", ""

    def log(self, m):
        self.lines.append(m)

    def coord_append(self, rel, line):
        self.posts.append(line)


def test_flag_post_goes_to_die_owner_and_skips_parked(tmp_path, monkeypatch):
    import json
    st = {"items": items()}
    for r in st["items"].values():
        r["updated"] = time.time() - (NOW - r["updated"])
    (tmp_path / "kit_wave_state.json").write_text(json.dumps(st))
    (tmp_path / "kit_wave.json").write_text(json.dumps(CFG))
    ap = _AP(tmp_path)
    UU.step(ap)
    post = [p for p in ap.posts if "HELD rows" in p]
    assert len(post) == 1 and "[AUTOPILOT -> DIE-QC-103, DIE-S81-92, S81-PLAN, COORD]" in post[0] and "hbm/" not in post[0]
