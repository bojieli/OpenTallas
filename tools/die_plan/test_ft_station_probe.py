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
