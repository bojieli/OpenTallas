"""KIT-OPS-6 11-15: ot-job imports its deps from a clean install dir (the 113 ot_store failures), and the installer stages them."""
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def test_clean_install_dir_imports(tmp_path):
    for f in ("ot-job", "ot_store.py", "signed_store.py"):
        shutil.copy(HERE / f, tmp_path / f)
    code = ("import importlib.machinery as m,importlib.util as u,sys;"
            "l=m.SourceFileLoader('otj','%s/ot-job');mod=u.module_from_spec(u.spec_from_loader(l.name,l));l.exec_module(mod);"
            "assert hasattr(mod,'best_job_root') and hasattr(mod.S,'__name__');print('OK')" % tmp_path)
    r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, cwd=str(tmp_path))
    assert r.stdout.strip() == "OK", r.stderr


def test_ot_job_without_store_module_fails_loudly(tmp_path):
    shutil.copy(HERE / "ot-job", tmp_path / "ot-job")
    r = subprocess.run([sys.executable, "-I", str(tmp_path / "ot-job"), "--help"], capture_output=True, text=True, cwd=str(tmp_path))
    assert r.returncode != 0 and "ot_store" in r.stderr


def test_installer_stages_the_modules_and_repo_has_best_job_root():
    s = (HERE / "install_fleet_host.sh").read_text()
    assert "ot_store.py signed_store.py" in s and ".local/bin" in s
    assert "def best_job_root" in (HERE / "ot-job").read_text()
