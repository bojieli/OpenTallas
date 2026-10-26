import json
import pytest
from restore_clock_spef_caps import restore,repair,M1_CLOCK_BUFFERS

# Actual native exporter root net from the admitted ASAP7 three-buffer pair.
NATIVE='''*D_NET root 1.81881
*CONN
*P root I
*I nroot:A I *D BUFx24_ASAP7_75t_R
*CAP
1 root:2 0.547131
2 root:9 0.362275
*RES
1 root:1 root:2 0.0172
2 root:2 root:3 0.0172
3 root:3 root:4 0.0172
4 root:4 root:5 0.0118
5 root:5 root:6 0.0118
6 root:6 root:7 0.0082
7 root:7 root:8 0.0082
8 root:8 root:9 0.0063
9 nroot:A root:2 0.203053
10 root root:9 0.0033375
*END
'''


def test_restores_terminal_wire_caps_and_preserves_native_resistors():
    fixed,stats=restore(NATIVE.splitlines(True),4)
    assert stats['added_caps']==2
    assert stats['cap_ff']==pytest.approx(1.81881-.547131-.362275)
    assert '9 nroot:A root:2 0.203053\n' in fixed
    assert any(' nroot:A 0.547' in line for line in fixed)
    _,second=restore(fixed,4)
    assert second['added_caps']==0


def test_missing_segment_negative_control_is_rejected():
    mutant=NATIVE.replace('4 root:4 root:5 0.0118\n','')
    with pytest.raises(ValueError,match='disconnected'):
        restore(mutant.splitlines(True),4)


@pytest.mark.parametrize('master', sorted(M1_CLOCK_BUFFERS))
def test_checked_m1_buffers_keep_the_native_wire_cap_reconstruction(master):
    fixed, stats = restore(NATIVE.replace('BUFx24_ASAP7_75t_R', master).splitlines(True), 4)
    assert stats['added_caps'] == 2
    assert stats['cap_ff'] == pytest.approx(1.81881-.547131-.362275)
    assert f'*I nroot:A I *D {master}\n' in fixed


def test_other_masters_and_supply_pins_are_rejected():
    for mutant in (NATIVE.replace('BUFx24_ASAP7_75t_R', 'BUFx2_ASAP7_75t_L'), NATIVE.replace('nroot:A', 'nroot:VDD')):
        with pytest.raises(ValueError, match='checked native'):
            restore(mutant.splitlines(True), 4)


def test_clock_coverage_is_required_before_mixed_rc(tmp_path):
    clock=tmp_path/'clock';clock.mkdir()
    (clock/'nets.json').write_text(json.dumps(dict(ports=[['input','root']],nets=[dict(name='root'),dict(name='missing')])) )
    src=tmp_path/'src.spef';src.write_text('*SPEF "test"\n'+NATIVE)
    with pytest.raises(ValueError,match='missing expected clock nets'):
        repair(src,tmp_path/'out.spef',4,clock,prefix='')
