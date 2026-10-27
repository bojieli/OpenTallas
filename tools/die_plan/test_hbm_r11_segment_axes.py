"""Reject the observed VM-only hub false PASS: segment x=0.617 with whole/segment y under0.6."""
import hbm_r11_delta as R

def test_segment_x_is_a_gate():
    r=dict(cut={"x":{"max_use":.55},"y":{"max_use":.4}},
           segs=[dict(cut_x=.617,cut_y=.5),dict(cut_x=.55,cut_y=.5)])
    assert not R._full(r)
    r["segs"][0]["cut_x"]=.599
    assert R._full(r)
    r["segs"][1]["cut_y"]=.601
    assert not R._full(r)
