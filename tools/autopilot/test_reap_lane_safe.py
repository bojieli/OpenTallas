"""LANE-SAFE-REAP-1122 (FLOW-OPS-R2): the CANCELLED-row reap (wave_jobs.STOP_KIT) never stops a lane's scope inside a wave kit dir
(FAM-QC-FEFW-R3 eco_r3_residual/i1 rc 143 mid sign-off STA)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import wave_jobs as WJ  # noqa: E402

SRC = WJ.STOP_KIT.split("# >>> lane_owner", 1)[1].split("# <<< lane_owner", 1)[0]
NS = {}
exec(SRC, NS)
own = NS["lane_owner"]


def test_lane_env_or_foreign_client_is_kept():
    envs = {1: {"OT_LANE": "FAM-QC-FEFW-R3", "OT_HEAVY_TAG": "otrun-tolerant-swine-5-6"},
            2: {"OT_HEAVY_TAG": "otrun-ubuntu-1136858-318478175"},
            3: {"OT_HEAVY_TAG": "otrun-tolerant-swine-2729674-318478175"},
            4: {}}
    r = lambda p: envs[p]
    assert own([1], "tolerant-swine", r).startswith("OT_LANE=")
    assert own([2], "tolerant-swine", r) == "ot-run client on ubuntu"      # the killed ECO: client on another host
    assert own([3], "tolerant-swine", r) == ""                             # a wave job (hub client) is still reaped
    assert own([4], "tolerant-swine", r) == ""
    assert own([2], "", r) == ""                                           # no hub name: old behaviour


def test_stop_kit_drops_kept_scopes_and_their_containers():
    s = WJ.STOP_KIT
    assert "scopes -= set(kept)" in s and "cscope.get(n) not in kept" in s and "'kept_lane'" in s
    assert s.index("scopes -= set(kept)") < s.index("subprocess.run(['systemctl', '--user', 'stop', u]")
