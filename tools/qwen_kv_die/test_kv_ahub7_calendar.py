"""The die's CLOSED a7 hub needs publication 75 edges after reciprocal issue."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kv_static_programme as KP


def test_closed_hub_publication_and_export():
    pr = KP.profile('die', json.loads((KP.ROOT / KP.AGES).read_text()))
    for t in (1, 128, 300, 1000, 4096, 5000, 8192):
        c = KP.attention_calendar(t, dict(pr, fr_ofs=-7))
        assert c['HUB_PUB'] == c['HUB_RECIP'] + 75
        assert c['PV_START'] + c['R'] - 7 >= c['HUB_PUB'] + 3
        assert c['R'] >= max(c['P0'], c['P1'])


def test_native_reference_keeps_original_loop():
    _, _, recip, pub = KP.AC.hub(100, 50)
    assert pub == recip + 73


def test_fixed_link_slot_preserved_or_refused():
    pr = KP.profile('die', json.loads((KP.ROOT / KP.AGES).read_text()))
    pr = dict(pr, fr_ofs=-7)
    c = KP.attention_calendar(8192, pr)
    end = c['PV_START'] + c['R'] + 49
    assert KP.attention_calendar(8192, pr, end)['R'] == c['R']
    try:
        KP.attention_calendar(8192, pr, end - 1)
    except ValueError:
        pass
    else:
        raise AssertionError('an insufficient fixed link slot was accepted')
