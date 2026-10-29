import copy
import pytest
from gen_core_kit_qc import interior_clock_pin


def test_interior_clock_requires_exact_slice_layer_and_position():
    q=dict(name="ck", face="C", layer="M5", x=127.452, y=69.12)
    s=dict(core_clock_port="ck", islands=[dict(clock_pin=dict(layer="M5", xy_um=[127.452,69.12]))])
    assert interior_clock_pin(q,s,"ck")
    assert not interior_clock_pin(dict(q,face="S"),None,"ck")
    for bad in [None, dict(s,core_clock_port="other"), dict(s,islands=[]),dict(s,islands=[dict(clock_pin=dict(layer="M4",xy_um=[127.452,69.12]))])]:
        with pytest.raises(SystemExit):interior_clock_pin(q,bad,"ck")
    with pytest.raises(SystemExit):interior_clock_pin(dict(q,x=127.5),s,"ck")
    with pytest.raises(SystemExit):interior_clock_pin(dict(q,name="data"),s,"ck")
