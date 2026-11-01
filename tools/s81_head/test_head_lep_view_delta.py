import copy
import pytest
from head_lep_view_delta import apply, MODULE, VIEW


def fixture():
    return dict(die=dict(name='s81_head'), partition_types=dict(hd_lep0N=dict(
        hard_cores=[dict(inst=f'u_core.u.g_pp[{i}].u_pair', module=MODULE,
                        outline_um=[777.6, 492.48], origin_um=[i, 17.28],
                        pins_file='core_pins/lep_pair_pins_777.json') for i in range(4)])))


def test_only_four_view_references_change_and_input_is_untouched():
    before = fixture()
    result = apply(before)
    expected = copy.deepcopy(before)
    for core in expected['partition_types']['hd_lep0N']['hard_cores']:
        core.update(lef=VIEW+'.lef', lib=VIEW+'_tt.lib')
    assert result == expected
    assert before == fixture()
    assert apply(result) == result


@pytest.mark.parametrize('mutation', ['outline', 'pins', 'missing_child', 'other_view'])
def test_wrong_child_variant_is_rejected(mutation):
    plan = fixture()
    core = plan['partition_types']['hd_lep0N']['hard_cores'][0]
    if mutation == 'outline': core['outline_um'][0] = 388.8
    if mutation == 'pins': core['pins_file'] = 'cores/lep_pair_pins.json'
    if mutation == 'missing_child': plan['partition_types']['hd_lep0N']['hard_cores'].pop()
    if mutation == 'other_view': core['lib'] = 'different_tt.lib'
    with pytest.raises(ValueError): apply(plan)
