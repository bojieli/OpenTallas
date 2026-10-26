import pytest
from mix_clock_spef import mix


def spef(r1,r2):
    return f'*SPEF "IEEE 1481-1998"\n*NAME_MAP\n*1 clockwide\n*2 other\n*D_NET *1 3\n*RES\n1 a b {r1}\n2 b c 0.0123\n*END\n*D_NET *2 7\n*RES\n1 a b {r2}\n2 b c 0.0456\n*END\n'


def test_selects_whole_net_without_scaling_vias(tmp_path):
    a,b,o=[tmp_path/n for n in ['4.spef','8.spef','mix.spef']]
    a.write_text(spef(4,40));b.write_text(spef(8,80))
    assert mix(a,b,{'clockwide'},o)['nets8w']==1
    assert o.read_text()==spef(8,40)
    b.write_text(spef(8,80).replace('*1 clockwide','*1 alien'))
    with pytest.raises(ValueError):mix(a,b,{'clockwide'},o)
