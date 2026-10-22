import collections
import pytest
from dv_bind import copied_lane_expression

def test_actual_pv_copy_crosses_body_stamp_boundary_and_pads_only_spares():
    out = {('entry','pv_d'): [(0,513,'w_pv_src',1)], ('entry','pv_x'): [(0,48,'w_pv_src',514)]}
    copies = [('entry','pv_d',275,0,238),('entry','pv_x',0,238,38)]
    assert copied_lane_expression('peer_l1',276,copies,out) == '{w_pv_src[551:514], w_pv_src[513:276]}'
    assert copied_lane_expression('peer_l2',276,[('entry','pv_x',38,0,10)],out,10) == "{266'd0, w_pv_src[561:552]}"

def test_broadcast_rejects_missing_ambiguous_and_overlapping_source_slices():
    out=collections.defaultdict(list,{('e','p'):[(0,16,'a',0)]})
    with pytest.raises(ValueError):copied_lane_expression('n',16,[('e','missing',0,0,16)],out)
    out[('e','p')].append((0,16,'b',0))
    with pytest.raises(ValueError):copied_lane_expression('n',16,[('e','p',0,0,16)],out)
    out[('e','p')].pop()
    with pytest.raises(ValueError):copied_lane_expression('n',16,[('e','p',0,0,8),('e','p',8,4,8)],out)
