import pytest
from qwen_tp8.frame_pin_directions import apply_frame_directions


def lef(master='frame', direction='INOUT'):
    return f'MACRO {master}\n  PIN data[7]\n    DIRECTION {direction} ;\n  END data[7]\n  PIN VDD\n    DIRECTION INOUT ;\n  END VDD\nEND {master}\n'


def test_vector_direction_and_preserved_unconnected_power():
    source = lef()
    result, audit = apply_frame_directions(source, {'frame': {'data': 'output'}})
    assert result == source.replace('DIRECTION INOUT', 'DIRECTION OUTPUT', 1)
    assert audit == dict(fixed=1, checked=1, unresolved_inout=1)
    assert apply_frame_directions(result, {'frame': {'data': 'output'}})[0] == result


def test_macros_and_exact_bit_override_are_scoped():
    result, audit = apply_frame_directions(lef() + lef('other'), {'frame': {'data': 'input', 'data[7]': 'output'}})
    assert result.count('DIRECTION OUTPUT') == 1
    assert audit['fixed'] == 1
    assert result.endswith(lef('other'))


def test_typed_view_disagreement_fails_closed():
    with pytest.raises(ValueError, match='direction conflict frame.data'):
        apply_frame_directions(lef(direction='INPUT'), {'frame': {'data': 'output'}})


def test_invalid_map_direction_fails_closed():
    with pytest.raises(ValueError, match='Invalid direction'):
        apply_frame_directions(lef(), {'frame': {'data': 'outpt'}})
