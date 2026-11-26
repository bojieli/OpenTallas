import csv
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import class_track as ct  # noqa: E402


def _w(path, rows, cols):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t", lineterminator="\n")
        w.writerow(cols)
        w.writerows(rows)


def _pre(d, die, lines):
    with open(os.path.join(d, die + ".json"), "w") as fh:
        json.dump({"advisories": lines}, fh)


def _setup(tmp_path):
    base = tmp_path / "base.tsv"
    _w(base, [["S81", "C-STREET", 10, "exact", "s"], ["S81", "C-TAP-LOAD", 5, "lead", "s"], ["QC", "C-STREET", 3, "exact", "s"]],
       ["die", "class_id", "count", "basis", "source"])
    trend = tmp_path / "trend.tsv"
    assert ct.main(["seed", "--label", "c0", "--baseline", str(base), "--trend", str(trend)]) == 0
    return trend


def test_line_types_skip_summary_and_not_checked():
    assert ct._line_type("WARN ADV-FP-STREET kv3_hg: lane demand 9", "ADV-FP-STREET") == "kv3_hg"
    assert ct._line_type("WARN ADV-TAP-LOAD summary 2 of 16", "ADV-TAP-LOAD") is None
    assert ct._line_type("WARN ADV-LAND-REACH not checked: no cores", "ADV-LAND-REACH") is None
    assert ct._line_type("WARN ADV-FP-STREET a: x", "ADV-LEG405-ZERO") is None


def test_fall_flat_new_and_first_exact(tmp_path, capsys):
    trend = _setup(tmp_path)
    pre = tmp_path / "pre"
    pre.mkdir()
    _pre(pre, "s81", [f"WARN ADV-FP-STREET t{i}: x" for i in range(8)] + ["WARN ADV-FP-STREET summary 8"] +
        ["WARN ADV-TAP-LOAD a: x", "WARN ADV-RELAY-SEAT r1 3 finding(s)"])
    _pre(pre, "qc", [f"WARN ADV-FP-STREET t{i}: x" for i in range(3)])
    assert ct.main(["cut", "--label", "c1", "--pre-dir", str(pre), "--trend", str(trend)]) == 0
    out = capsys.readouterr().out
    s81 = [ln for ln in out.splitlines() if ln.startswith("S81")][0]
    assert "total=9 (last 15, -6)" in s81       # tracked classes: street 8 + tap-load 1 vs 10 + 5
    assert "comparable classes 10->8 (-2)" in s81  # tap-load was a lead baseline -> first exact, excluded
    assert "C-RELAY-SEAT" in s81 and "first exact C-TAP-LOAD" in s81
    qc = [ln for ln in out.splitlines() if ln.startswith("QC")][0]
    assert "no-fall streak 1" in qc and "LOOP: none" in out


def test_two_flat_cuts_make_loop(tmp_path, capsys):
    trend = _setup(tmp_path)
    pre = tmp_path / "pre"
    pre.mkdir()
    _pre(pre, "qc", [f"WARN ADV-FP-STREET t{i}: x" for i in range(3)])
    for lab in ("c1", "c2"):
        assert ct.main(["cut", "--label", lab, "--pre-dir", str(pre), "--trend", str(trend), "--write"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert any(ln.startswith("LOOP: ") and "QC" in ln and "KV" not in ln for ln in out)


def test_scan_finds_unknown_tags(tmp_path):
    posts = tmp_path / "posts"
    posts.mkdir()
    (posts / "A.md").write_text("- 2026-11-25 20:00 PST x P-OLD-ONE\n- 2026-11-26 08:10 PST ruling class P-LEC-WIDTH, C-STREET\n"
                                "continuation P-NOT-A-POST-LINE\n")
    got = ct.scan_posts(str(posts), "2026-11-25 21:00", {"C-STREET"})
    assert got == [("A", "2026-11-26 08:10", "P-LEC-WIDTH")]


def test_known_class_on_new_die_starts_from_zero(tmp_path, capsys):
    trend = _setup(tmp_path)
    carry = tmp_path / "carry.tsv"
    _w(carry, [["HEAD", "C-STREET", 2, "exact", "x"]], ["die", "class_id", "count", "basis", "source"])
    pre = tmp_path / "pre"
    pre.mkdir()
    assert ct.main(["cut", "--label", "c1", "--pre-dir", str(pre), "--carry", str(carry), "--trend", str(trend)]) == 0
    head = [ln for ln in capsys.readouterr().out.splitlines() if ln.startswith("HEAD")][0]
    assert "NEW=0" in head and "comparable classes 0->2 (+2)" in head


def test_lane_sha_row_is_kept_and_carry_sha_wins(tmp_path):
    cls = tmp_path / "CLASSES.tsv"
    cols = ["class_id", "die", "kind", "static_check", "owner", "cut_local", "mapped_count", "status", "owner_measurement"]
    _w(cls, [["C-A", "S81", "DESIGN", "x", "o", "c0", "6", "s", "LEG405-STAGED 6 tool 5632156a860"],
             ["C-B", "S81", "DESIGN", "x", "o", "c0", "9", "s", "census pending"]], cols)
    rows = [{"cut_local": "c1", "die": "S81", "class_id": "C-A", "count": 277, "basis": "exact", "source": "PRE legacy",
             "prev_count": 273, "prev_basis": "exact", "move": "UP"},
            {"cut_local": "c1", "die": "S81", "class_id": "C-B", "count": 4, "basis": "exact", "source": "PRE", "prev_count": "", "prev_basis": "",
             "move": "NEW"}]
    ct.update_classes(str(cls), rows, "c1")
    got = {r["class_id"]: r for r in ct.read_tsv(str(cls))}
    assert got["C-A"]["mapped_count"] == "6" and "5632156a860" in got["C-A"]["owner_measurement"]
    assert got["C-B"]["mapped_count"] == "4"
    ct.OWNER_OVERRIDE[("S81", "C-A")] = "KV-INT-R2"
    rows[0].update(count=2, source="KV-INT-R2 dafa157")
    ct.update_classes(str(cls), rows, "c2")
    got = {r["class_id"]: r for r in ct.read_tsv(str(cls))}
    assert got["C-A"]["mapped_count"] == "2" and got["C-A"]["owner"] == "KV-INT-R2"


def test_carried_rows_never_count_and_loop_breakdown(tmp_path, capsys):
    trend = _setup(tmp_path)
    carry = tmp_path / "carry.tsv"
    _w(carry, [["QC", "C-STREET", 3, "exact", "lane sha 0123456", "", "1"]], ["die", "class_id", "count", "basis", "source", "owner", "carried"])
    pre = tmp_path / "pre"
    pre.mkdir()
    for lab in ("c1", "c2"):
        ct.CARRIED.clear()
        assert ct.main(["cut", "--label", lab, "--pre-dir", str(pre), "--carry", str(carry), "--trend", str(trend), "--write"]) == 0
    out = capsys.readouterr().out
    assert "LOOP: QC" in out and "comparable classes 0->0 (+0)" in out
    assert "LOOP-BREAKDOWN QC" in out and "C-STREET 3->3 CARRIED" in out
