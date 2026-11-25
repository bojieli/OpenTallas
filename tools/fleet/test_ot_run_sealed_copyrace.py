"""COPYBACK-RACE-1122 + SEAL-COPYBACK-1124: a copy-back whose pull tar reports 'file changed as we read it' (rc 1) is retried (the
copy, not the stage); other failures return at once.  The stage files are copied strictly (a race on every try returns the tar rc, the
wave files 97); run/layout_review (advisory renders) is copied apart and a race there on every try is logged, not failed; the copy
first waits for run/layout_review to be quiet."""
import importlib.machinery
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent
RACE = "tar: kit/%s: file changed as we read it"


def load():
    loader = importlib.machinery.SourceFileLoader("ot_run_sealed_cr", str(HERE / "ot-run-sealed"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def setup(tmp_path, monkeypatch, races, other_rc=0, lr_races=0, quiet_after=0):
    """races: pulls of the stage part that race; lr_races: pulls of the layout_review part that race;
    quiet_after: quiet probes that report 'still written' first"""
    m = load()
    src_root, dst_root = tmp_path / "jobhost", tmp_path / "wave"
    (src_root / "kit" / "run" / "layout_review" / "place").mkdir(parents=True)
    (src_root / "kit" / "3_place.odb").write_text("odb")
    (src_root / "kit" / "run" / "layout_review" / "place" / "layout.png").write_text("png")
    dst_root.mkdir()
    K = str(dst_root / "kit")
    cnt, lcnt, qcnt = tmp_path / "n", tmp_path / "l", tmp_path / "q"
    for f in (cnt, lcnt, qcnt):
        f.write_text("0")

    def on(host, sh, n=True, timeout_flag=True):
        if sh.startswith("tar -C") and "-cf -" in sh:
            part = "l" if " kit/run/layout_review" in sh and "--exclude=kit/run/layout_review" not in sh else "s"
            c, lim, w = (lcnt, lr_races, "run/layout_review/place/layout.png") if part == "l" else (cnt, races, "run/macros")
            excl = "--exclude=kit/run/layout_review" if part == "s" else ""
            what = "kit/run/layout_review" if part == "l" else "kit"
            sh = (f"n=$(cat {c}); echo $((n+1)) > {c}; tar -C {src_root} {excl} -cf - {what}; "
                  f"if [ $n -lt {lim} ]; then echo '{RACE % w}' >&2; exit 1; fi; exit {other_rc if part == 's' else 0}")
        elif sh.startswith("rm -rf"):
            sh = "true"
        elif sh.startswith("test ! -d") and "find" in sh:     # wait_quiet probe
            sh = f"n=$(cat {qcnt}); echo $((n+1)) > {qcnt}; [ $n -ge {quiet_after} ]"
        elif sh.startswith("test -d"):
            sh = "true"
        return ["bash", "-c", sh]
    monkeypatch.setattr(m, "on", on)
    monkeypatch.setattr(m, "COPYBACK_BACKOFF_S", (0,))
    monkeypatch.setenv("OT_COPYBACK_QUIET_GAP", "0")
    monkeypatch.setattr(m.time, "sleep", lambda s: None)
    return m, K, cnt, lcnt, qcnt, dst_root


def test_race_then_clean_copy_succeeds(tmp_path, monkeypatch, capsys):
    m, K, cnt, _l, _q, dst = setup(tmp_path, monkeypatch, races=2)
    assert m.copy_back("epyc7", "epyc8", K) == 0
    assert cnt.read_text().strip() == "3" and (dst / "kit" / "3_place.odb").read_text() == "odb"
    assert (dst / "kit" / "run" / "layout_review" / "place" / "layout.png").read_text() == "png"
    assert capsys.readouterr().err.count("COPY-BACK RACE") == 2


def test_stage_race_every_try_returns_the_tar_rc(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_COPYBACK_TRIES", "3")
    m, K, cnt, lcnt, _q, _ = setup(tmp_path, monkeypatch, races=99)
    assert m.copy_back("epyc7", "epyc8", K) == 1 and cnt.read_text().strip() == "3"
    assert lcnt.read_text().strip() == "0"          # stage failed: the review part is never reached


def test_other_failure_is_not_retried(tmp_path, monkeypatch):
    m, K, cnt, _l, _q, _ = setup(tmp_path, monkeypatch, races=0, other_rc=2)
    assert m.copy_back("epyc7", "epyc8", K) == 2 and cnt.read_text().strip() == "1"


def test_layout_review_race_every_try_is_advisory_only(tmp_path, monkeypatch, capsys):
    """the 11-24 col_h9_r2 hit: the render still wrote run/layout_review/place; the stage files are copied strictly and clean"""
    monkeypatch.setenv("OT_COPYBACK_TRIES", "2")
    m, K, cnt, lcnt, _q, dst = setup(tmp_path, monkeypatch, races=0, lr_races=99)
    assert m.copy_back("epyc7", "epyc8", K) == 0
    assert cnt.read_text().strip() == "1" and lcnt.read_text().strip() == "2"      # the stage part is not re-pulled
    assert (dst / "kit" / "3_place.odb").read_text() == "odb"
    assert "COPY-BACK ADVISORY-RACE" in capsys.readouterr().err


def test_stage_files_are_never_excused_by_the_advisory_rule(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("OT_COPYBACK_TRIES", "2")
    m, K, cnt, _l, _q, _ = setup(tmp_path, monkeypatch, races=99, lr_races=99)
    assert m.copy_back("epyc7", "epyc8", K) == 1
    assert "ADVISORY-RACE" not in capsys.readouterr().err


def test_waits_for_layout_review_to_be_quiet(tmp_path, monkeypatch):
    m, K, cnt, _l, qcnt, _ = setup(tmp_path, monkeypatch, races=0, quiet_after=3)
    assert m.copy_back("epyc7", "epyc8", K) == 0
    assert int(qcnt.read_text()) == 4                  # 3 'still written' probes, then quiet; only then the copy


def test_quiet_wait_is_bounded(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("OT_COPYBACK_QUIET_S", "0")
    m, K, cnt, _l, qcnt, _ = setup(tmp_path, monkeypatch, races=0, quiet_after=99)
    assert m.copy_back("epyc7", "epyc8", K) == 0 and int(qcnt.read_text()) == 1
    assert "still being written" in capsys.readouterr().err


def test_self_copy_on_the_holder_is_skipped_and_k_is_kept(tmp_path, monkeypatch, capsys):
    """SEAL-COPYBACK-1124: host == src and no stage = the job returned into K itself: no tar at all, K never removed (it raced on every
    try and would have been rm -rf'd on success)"""
    m, K, cnt, _l, _q, _ = setup(tmp_path, monkeypatch, races=99)
    (tmp_path / "wave" / "kit").mkdir()
    (tmp_path / "wave" / "kit" / "3_place.odb").write_text("keep")
    ran = []
    monkeypatch.setattr(m, "on", lambda *a, **k: ran.append(a) or ["true"])
    assert m.copy_back("epyc9", "epyc9", K) == 0
    assert not ran and (tmp_path / "wave" / "kit" / "3_place.odb").read_text() == "keep"
    assert "nothing to copy" in capsys.readouterr().err


def test_same_host_with_a_stage_dir_still_copies(tmp_path, monkeypatch):
    m, K, cnt, _l, _q, _ = setup(tmp_path, monkeypatch, races=0)
    assert m.copy_back("epyc7", "epyc7", K, stage=str(tmp_path / "jobhost" / "kit")) == 0 and cnt.read_text().strip() == "1"
