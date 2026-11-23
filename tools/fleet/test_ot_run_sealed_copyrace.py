"""COPYBACK-RACE-1122 (COORD 22:3x): a copy-back whose pull tar reports 'file changed as we read it' (rc 1) is retried (the copy, not the
stage); other failures return at once; the race on every try returns the tar rc (the wave files 97 as before)."""
import importlib.machinery
import importlib.util
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load():
    loader = importlib.machinery.SourceFileLoader("ot_run_sealed_cr", str(HERE / "ot-run-sealed"))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    m = importlib.util.module_from_spec(spec)
    loader.exec_module(m)
    return m


def setup(tmp_path, monkeypatch, races, other_rc=0):
    m = load()
    src_root, dst_root = tmp_path / "jobhost", tmp_path / "wave"
    (src_root / "kit").mkdir(parents=True)
    (src_root / "kit" / "3_place.odb").write_text("odb")
    dst_root.mkdir()
    K = str(dst_root / "kit")
    cnt = tmp_path / "n"
    cnt.write_text("0")

    def on(host, sh, n=True, timeout_flag=True):
        if sh.startswith("tar -C") and "-cf -" in sh:
            # the job host side: race on the first `races` pulls, then a clean archive
            sh = (f"n=$(cat {cnt}); echo $((n+1)) > {cnt}; tar -C {src_root} -cf - kit; "
                  f"if [ $n -lt {races} ]; then echo 'tar: kit/gen/macros: file changed as we read it' >&2; exit 1; fi; exit {other_rc}")
        elif sh.startswith("rm -rf"):
            sh = "true"
        elif sh.startswith("test -d"):
            sh = "true"
        return ["bash", "-c", sh]
    monkeypatch.setattr(m, "on", on)
    monkeypatch.setattr(m, "COPYBACK_BACKOFF_S", (0,))
    return m, K, cnt, dst_root


def test_race_then_clean_copy_succeeds(tmp_path, monkeypatch, capsys):
    m, K, cnt, dst = setup(tmp_path, monkeypatch, races=2)
    assert m.copy_back("epyc7", "epyc7", K) == 0
    assert cnt.read_text().strip() == "3" and (dst / "kit" / "3_place.odb").read_text() == "odb"
    assert capsys.readouterr().err.count("COPY-BACK RACE") == 2


def test_race_every_try_returns_the_tar_rc(tmp_path, monkeypatch):
    monkeypatch.setenv("OT_COPYBACK_TRIES", "3")
    m, K, cnt, _ = setup(tmp_path, monkeypatch, races=99)
    assert m.copy_back("epyc7", "epyc7", K) == 1 and cnt.read_text().strip() == "3"


def test_other_failure_is_not_retried(tmp_path, monkeypatch):
    m, K, cnt, _ = setup(tmp_path, monkeypatch, races=0, other_rc=2)
    assert m.copy_back("epyc7", "epyc7", K) == 2 and cnt.read_text().strip() == "1"
