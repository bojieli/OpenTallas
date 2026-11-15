"""KIT-OPS-5 11-14: a job whose runner / kit dir is gone on the hub is "kit lost", never resubmitted (rc 127 loop)."""
import autopilot as A


def test_present_kit_is_not_lost(tmp_path):
    k = tmp_path / "k"
    k.mkdir()
    (k / "run_kit.sh").write_text("")
    assert A.kit_lost({"runner": str(k / "run_kit.sh"), "path": str(k)}) == ""


def test_missing_runner_is_lost(tmp_path):
    k = tmp_path / "k"
    k.mkdir()
    assert "missing on the hub" in A.kit_lost({"runner": str(k / "run_kit.sh"), "path": str(k)})


def test_missing_dir_is_lost(tmp_path):
    assert "missing on the hub" in A.kit_lost({"runner": "", "path": str(tmp_path / "gone")})
