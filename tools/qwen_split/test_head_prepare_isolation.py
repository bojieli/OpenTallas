"""RM176 isolation: importing head_prepare_age (test_head_prepare_export does, for export_result) must not switch the
process into HEAD_PREP mode.  It used to set OT_QWEN_HEAD_PREP=1 and import record_bundles at module import, and the
rest of the pytest session then built other view pin geometry (test_closed_view_frames, test_die_params,
test_record_bundles failed after it)."""
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

PROBE = """
import json, os, sys
sys.path.insert(0, sys.argv[1])
import head_prepare_age
{call}
print(json.dumps(dict(env=os.environ.get('OT_QWEN_HEAD_PREP'),
                      leaked=sorted(m for m in ('record_bundles', 'die_params', 'static_link_bind', 'dv_case')
                                    if m in sys.modules))))
"""


def _probe(call=""):
    env = {k: v for k, v in os.environ.items() if k != "OT_QWEN_HEAD_PREP"}
    r = subprocess.run([sys.executable, "-c", PROBE.format(call=call), str(HERE)], env=env, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout.strip().splitlines()[-1])


def test_import_does_not_enter_head_prepare_mode():
    assert _probe() == dict(env=None, leaked=[])


def test_export_result_needs_no_head_prepare_mode():
    call = ("head_prepare_age.export_result(dict(die_sha256='x', filler_head_prepare_edges=14, "
            "user0_prepare_only_min_edges=15))")
    assert _probe(call) == dict(env=None, leaked=[])
