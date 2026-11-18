import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import autopilot as AP


def test_enospc_is_an_infra_crash_that_resubmits():
    cls, kind, why = AP.classify({"runlog_tail": "write error\nmkdir: cannot create directory: No space left on device\n", "goal": "route"}, {"exit": 1})
    assert (cls, kind) == ("CRASH", "infra-disk") and "No space left" in why
    assert "infra-disk" in AP.INFRA_KINDS
    cls2, kind2, _ = AP.classify({"runlog_tail": "segfault in drt", "goal": "route"}, {"exit": 1})
    assert kind2 != "infra-disk"
