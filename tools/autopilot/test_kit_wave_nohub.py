"""KW-FIX-45 11-12 (COORD ruling 4, TAP-SITE-1): heavy kit-wave stages never run on the hub."""
from pathlib import Path
import kit_wave as KW


def test_heavy_args_exclude_hosts_is_opt_in():
    # the lane-declare / sealed wrappers in front of ot-run reject --exclude-hosts: default off
    assert KW.heavy_args({"hub": "intel2"}) == []
    assert KW.heavy_args({"hub": "intel2", "crit": True}) == ["--priority", "die", "--crit"]
    a = KW.heavy_args({"hub": "intel2", "ot_run_exclude_hosts": True})
    assert a[:2] == ["--exclude-hosts", "intel2,localhost"] and "--crit" not in a
    assert KW.heavy_args({"ot_run_exclude_hosts": True})[:2] == ["--exclude-hosts", "localhost"]

def test_place_async_and_otrun_have_the_guard():
    src = (Path(KW.__file__)).read_text()
    assert 'KW_PLACE_REFUSED: heavy stage place refuses to run on the hub' in src
    assert 'if h not in (hub, "localhost")]       # KW-FIX-45 11-12: a heavy stage never targets the hub' in src


def test_ot_run_accepts_exclude_hosts():
    p = Path(KW.__file__).resolve().parents[1] / "fleet" / "ot-run"
    s = p.read_text()
    assert '"--exclude-hosts"' in s and "HOSTS[:] = [h for h in HOSTS if h not in _ex]" in s
