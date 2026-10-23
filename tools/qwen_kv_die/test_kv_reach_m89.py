"""FT-KV-DIE 10-23: OT_KV_REACH_M89 lets OT_KV_REACH raise the planned die hop (REACH-M89 1.2 mm); default unchanged."""
import os, subprocess, sys
from pathlib import Path
HERE = Path(__file__).resolve().parent
Q = ("import sys; sys.path[:0]=[%r,%r]; import kv_die as K, inspect; "
     "print(K.PIN_REACH, K.REACH_TARGET, K.RELAY_TARGET, K.HOP_REACH, K.PIN_HOP_GATE, "
     "inspect.signature(K.pin_reach).parameters['reach'].default)") % (str(HERE.parent), str(HERE))


def _probe(**env):
    e = {k: v for k, v in os.environ.items() if not k.startswith('OT_KV_REACH')}
    e.update(env)
    return subprocess.run([sys.executable, '-c', Q], env=e, capture_output=True, text=True, check=True).stdout.split()


def test_default_clamp_unchanged():
    assert _probe() == ['450.0', '470.0', '320.0', '445.0', '500.0', 'None']
    assert _probe(OT_KV_REACH='400') == ['400.0', '400.0', '288.0', '400.0', '500.0', 'None']
    # the knob alone (or with a smaller reach) never changes the legacy clamp below 500
    assert _probe(OT_KV_REACH='1200') == ['450.0', '470.0', '320.0', '445.0', '500.0', 'None']
    assert _probe(OT_KV_REACH_M89='1') == ['450.0', '470.0', '320.0', '445.0', '500.0', 'None']


def test_m89_raises_hop():
    assert _probe(OT_KV_REACH='1200', OT_KV_REACH_M89='1') == ['1200.0', '1200.0', '864.0', '1200.0', '1200.0', 'None']
    assert _probe(OT_KV_REACH='400', OT_KV_REACH_M89='1') == ['400.0', '400.0', '288.0', '400.0', '500.0', 'None']


if __name__ == '__main__':
    test_default_clamp_unchanged(); test_m89_raises_hop(); print('PASS')
