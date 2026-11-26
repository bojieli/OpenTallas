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
    assert any(ln.startswith("LOOP: ") and "QC" in ln for ln in out[-3:])


def test_scan_finds_unknown_tags(tmp_path):
    posts = tmp_path / "posts"
    posts.mkdir()
    (posts / "A.md").write_text("- 2026-11-25 20:00 PST x P-OLD-ONE\n- 2026-11-26 08:10 PST ruling class P-LEC-WIDTH, C-STREET\n"
                                "continuation P-NOT-A-POST-LINE\n")
    got = ct.scan_posts(str(posts), "2026-11-25 21:00", {"C-STREET"})
    assert got == [("A", "2026-11-26 08:10", "P-LEC-WIDTH")]
