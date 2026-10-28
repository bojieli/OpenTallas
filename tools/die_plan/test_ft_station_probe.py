import pytest
import ft_station_probe as probe


def test_station_terminals_keep_g2_stage_zero_and_epoch(monkeypatch):
    pins=[('ft_i',0,'M5',10.,100.,'N'),('ft_i',1,'M5',11.,100.,'N')]
    monkeypatch.setattr(probe.gen_phys,'type_pins',lambda p,t:pins)
    s=dict(name='ft',width=1,stations=2,bit_site_cell_um=[2.,1.],bit_sites_um=[[[31.,41.],[32.,41.]]])
    rows=probe.station_sites(None,'type',s,2)
    assert rows[0]==[[10.,100.-probe.g2.FLOP_INSET_UM],[11.,100.-probe.g2.FLOP_INSET_UM]]
    assert rows[1]==[[31.,41.],[32.,41.]]
    # Epoch is the last bit in the same physical stage; a missing site fails closed.
    s['bit_sites_um'][0].pop()
    with pytest.raises(ValueError,match='width\\+1'):
        probe.station_sites(None,'type',s,2)


def test_exit_zero_never_overrides_routing_failure(tmp_path):
    import json
    (tmp_path/'station_probe.json').write_text(json.dumps(dict(qualification='ROUTING_DIAGNOSTIC_ONLY')))
    lines=['Final congestion report:']+[f'M{i} 123 100 1.00%             0 /  0 / {17 if i==6 else 0}' for i in range(1,8)]
    lines+=['OT_DONE','ot-run: RAN on localhost (unit test): exit 0']
    (tmp_path/'run.log').write_text('\n'.join(lines))
    assert probe.report(tmp_path)['verdict']=='FAIL'
    (tmp_path/'run.log').write_text('\n'.join(lines).replace('OT_DONE',''))
    assert probe.report(tmp_path)['verdict']=='NOT RUN'


def test_bounded_coupon_rejects_escaping_guides_even_with_zero_overflow(tmp_path):
    import json
    (tmp_path/'grt').mkdir()
    (tmp_path/'station_probe.json').write_text(json.dumps(dict(bounded=True,coupon_canvas_um=[0,0,10.8,10.8],part_bounds_um=[1,1,10,10])))
    rows=['Final congestion report:']+[f'M{i} 123 100 1.00%             0 /  0 / 0' for i in range(1,8)]
    rows+=['OT_DONE','ot-run: RAN on localhost (unit test): exit 0']
    (tmp_path/'run.log').write_text('\n'.join(rows))
    (tmp_path/'grt/route.guide').write_text('ft_p__a_1[0]\n(\n1000 1000 12000 2000 M6\n)\n')
    result=probe.report(tmp_path)
    assert result['verdict']=='FAIL' and result['boundary']['outside_canvas_rectangles']==1


def test_f1_station_layer_follows_face_class_and_direction():
    # KV/HEAD plans alternate [M4,M6] / [M5,M7]: even bits lower class, odd bits upper class
    assert probe.station_layer('M4','E',0)=='M4' and probe.station_layer('M6','W',1)=='M6'
    assert probe.station_layer('M5','N',0)=='M5' and probe.station_layer('M7','S',1)=='M7'
    # S81-style reversed port layer order: the class follows the face pin, not the bit parity
    assert probe.station_layer('M6','E',0)=='M6' and probe.station_layer('M4','E',1)=='M4'
    # a vertical face pin class on an E/W-entering slot maps to the horizontal layer of the same class
    assert probe.station_layer('M7','E',0)=='M6' and probe.station_layer('M5','W',1)=='M4'
    # unknown layer -> parity fallback (even M4, odd M6)
    assert probe.station_layer('M8','E',0)=='M4' and probe.station_layer('M8','E',3)=='M6'


def test_f1_station_layers_and_single_layer_pin(monkeypatch):
    pins=[('ft_i',0,'M4',0.,10.,'W'),('ft_i',1,'M6',0.,11.,'W'),('ft_o',0,'M4',50.,10.,'E'),('ft_o',1,'M6',50.,11.,'E')]
    monkeypatch.setattr(probe.gen_phys,'type_pins',lambda p,t:pins)
    assert probe.station_layers(None,'t',dict(name='ft'),2)==['M4','M6']
    one=probe.pin('ot_s_ft_0_d[1]','INPUT',5.,6.,'M6')
    assert one.count('LAYER ')==1 and 'LAYER M6' in one and 'RECT 4.98400 5.98400 5.01600 6.01600' in one
    legacy=probe.pin('ot_s_ft_0_d[1]','INPUT',5.,6.)
    assert 'LAYER M4' in legacy and 'LAYER M5' in legacy


def test_f1_station_pins_is_opt_in():
    # KV-PLAN-DELTA-8 canary: F1 regressed the S81 coupon (M7-scarce die), so the default stays the stacked M4+M5 square
    import inspect
    assert inspect.signature(probe.build).parameters["f1_station_pins"].default is False
