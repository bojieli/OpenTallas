"""FLOW-21 CANSTALL 11-01: a canary client that ended NOT RUN never blocks its die's next canary."""
import importlib.util
import json
from pathlib import Path
from unittest import mock
spec = importlib.util.spec_from_file_location('trig_dead', Path(__file__).with_name('trigger.py'))
T = importlib.util.module_from_spec(spec)
spec.loader.exec_module(T)

NOTRUN = ("kex_exchange_identification: read: Connection reset by peer\n"
          "ot-run: NOT RUN on localhost: ssh ended with status 255 before the command was admitted\n")


def _run(root, name, log):
    r = root / name
    r.mkdir()
    (r / 'canary_meta.json').write_text(json.dumps({'spec': {'die': 'qwen_compute'}, 'client_unit': 'u-' + name,
                                                    'src': '/srv/x/flow-canary/sources/abc'}))
    if log is not None:
        (r / 'otrun.log').write_text(log)
    return r


def test_dead_notrun_client_is_not_live(tmp_path):
    _run(tmp_path, 'a', NOTRUN)
    with mock.patch.object(T, 'unit_active', return_value=False):
        assert T.live_dies(tmp_path) == set()
    with mock.patch.object(T, 'unit_active', return_value=True):     # client still placing again
        assert T.live_dies(tmp_path) == {'qwen_compute'}


def test_started_or_logless_client_stays_live(tmp_path):
    _run(tmp_path, 'a', NOTRUN + "ot-run: NOT COMPLETED: the command started on intel1\n")
    _run(tmp_path, 'b', None)
    with mock.patch.object(T, 'unit_active', return_value=False):
        assert T.live_dies(tmp_path) == {'qwen_compute'}
        (tmp_path / 'a' / 'canary.json').write_text('{}')
        assert T.live_dies(tmp_path) == {'qwen_compute'}           # b: no evidence, stays live
        (tmp_path / 'b' / 'otrun.log').write_text("ot-run: -> localhost\nCANARY_FLOW_RC 0\nNOT RUN\n")
        assert T.live_dies(tmp_path) == {'qwen_compute'}


def test_canary_launch_uses_crit():
    src = Path(__file__).with_name('canary.py').read_text()
    assert src.count('{OT_RUN} {CRIT}--mem') == 2
