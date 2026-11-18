"""Current819 leaf34: the native top dissolves the leaf prefix (bare u_u_vs / g_u_cst_*); exact name first, one candidate."""
import gzip
import re
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_bus_bitgroups as BG

CORES = ['u_lf.u_vs', 'u_lf.u_vq', 'u_lf.u_vn.u_b', 'u_lf.u_vn.u_a', 'u_lf.u_vp', 'u_lf.u_cst']


def source(name='kit_bus_t34_current819.sv.gz'):
    return gzip.decompress((Path(__file__).parent / 'fixtures' / name).read_bytes()).decode()


def bits(owners, core):
    return {b for b, cs in (owners or {}).items() if core in cs}


def test_actual_leaf34_bare_names_resolve_to_the_one_observed_alias():
    txt = source()
    assert not re.search(r'u_lf\d*_', txt) and ' u_u_vs (' in txt and 'g_u_cst_' in txt
    assert BG.native_core_aliases(txt, CORES) == {c: c[len('u_lf.'):] for c in CORES}


def test_actual_leaf34_595_668_bus_owners():
    txt = source()
    incoming = BG.in_bit_owners(txt, 'leafdn_i0', CORES)
    outgoing = BG.out_bit_owners(txt, 'leafup_o0', 668, CORES)
    assert bits(incoming, 'u_lf.u_vs') == set(range(559, 594))
    assert bits(incoming, 'u_lf.u_vn.u_b') == set(range(33)) == bits(incoming, 'u_lf.u_vn.u_a')
    assert len(incoming) == 68          # soft VP captures (bits 33..558) are not instance ports: unresolved, not guessed
    assert bits(outgoing, 'u_lf.u_vs') == set(range(1, 100))
    assert bits(outgoing, 'u_lf.u_vp') == set(range(100, 357))
    assert bits(outgoing, 'u_lf.u_vn.u_b') == set(range(357, 390))
    assert bits(outgoing, 'u_lf.u_vq') == set(range(390, 668))
    assert len(outgoing) == 667 and 0 not in outgoing   # control glue bit stays unresolved
    assert not bits(incoming, 'u_lf.u_cst') and not bits(outgoing, 'u_lf.u_cst')


def test_bare_and_indexed_together_refuse():
    with pytest.raises(ValueError, match='ambiguous native leaf'):
        BG.native_core_aliases('u_u_vs (\nu_u_lf1_u_vs (', ['u_lf.u_vs'])
    with pytest.raises(ValueError, match='ambiguous native leaf'):
        BG.native_core_aliases(source() + '\n    ot_s81sl_vs u_u_lf1_u_vs (\n', CORES)


def test_exact_name_wins_over_bare_and_indexed_still_resolves():
    assert BG.native_core_aliases('u_u_lf_u_vs (\nu_u_vs (', ['u_lf.u_vs']) == {'u_lf.u_vs': 'u_lf.u_vs'}
    assert BG.native_core_aliases('u_u_lf1_u_vs (', ['u_lf.u_vs']) == {'u_lf.u_vs': 'u_lf1.u_vs'}
    t43 = source('kit_bus_t43_native.sv.gz')
    assert BG.native_core_aliases(t43, ['u_lf.u_vs'])['u_lf.u_vs'] == 'u_lf1.u_vs'


def test_bare_alias_needs_an_observed_name_and_whole_identifier():
    # a longer identifier (u_u_vsw) or an unrelated hierarchy (u_x_u_vs) is not the bare core
    for txt in ('u_u_vsw (', 'u_x_u_vs (', 'w_foreign_u_vs_o', ''):
        assert BG.native_core_aliases(txt, ['u_lf.u_vs']) == {'u_lf.u_vs': 'u_lf.u_vs'}
    assert BG.native_core_aliases('u_u_vs (', ['top.u_vs']) == {'top.u_vs': 'top.u_vs'}   # only u_lf.* plan names
    with pytest.raises(ValueError, match='same native instance'):
        BG.native_core_aliases('u_u_vs (', ['u_lf.u_vs', 'u_vs'])


def test_actual_leaf34_wrong_bare_name_control_does_not_invent_owner():
    txt = source().replace('u_u_vs ', 'u_foreign_vs ').replace('w_u_vs_', 'w_foreign_vs_')
    assert not bits(BG.in_bit_owners(txt, 'leafdn_i0', CORES), 'u_lf.u_vs')
    assert not bits(BG.out_bit_owners(txt, 'leafup_o0', 668, CORES), 'u_lf.u_vs')
