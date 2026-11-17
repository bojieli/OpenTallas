"""Native t43's actual 595/668-bit transport: resolve only bit-preserving source paths."""
import gzip
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parent))
import kit_bus_bitgroups as BG

CORES = ['u_lf.u_vs', 'u_lf.u_vq', 'u_lf.u_vn.u_b']

def source():
    return gzip.decompress((Path(__file__).parent / 'fixtures/kit_bus_t43_native.sv.gz').read_bytes()).decode()

def bits(owners, core):
    return {b for b, cs in (owners or {}).items() if core in cs}

def test_actual_native_t43_full_width_bus_owners():
    txt = source()
    incoming = BG.in_bit_owners(txt, 'leafdn_i0', CORES)
    outgoing = BG.out_bit_owners(txt, 'leafup_o0', 668, CORES)
    assert bits(incoming, CORES[0]) == set(range(35)) | {594}
    assert bits(incoming, CORES[2]) == set(range(35, 68)) | {594}
    assert bits(outgoing, CORES[0]) == set(range(569, 668))
    assert bits(outgoing, CORES[1]) == set(range(291, 569))
    assert bits(outgoing, CORES[2]) == set(range(1, 34))
    assert len(incoming) == 69 and len(outgoing) == 410
    assert not any(b in outgoing for b in range(34, 291))  # actual VP glue remains unresolved
    assert 0 not in outgoing  # actual control glue remains unresolved

def test_actual_native_t43_wrong_slice_control_changes_exact_bit_ownership():
    txt = source()
    original = 'assign w_24_Y = leafdn_i0_q[593:0];'
    assert original in txt
    mutant = txt.replace(original, 'assign w_24_Y = leafdn_i0_q[594:1];')
    got = bits(BG.in_bit_owners(mutant, 'leafdn_i0', CORES), CORES[0])
    assert got == set(range(1, 36)) | {594}
    assert got != set(range(35)) | {594}

def test_actual_native_wrong_alias_control_does_not_invent_owner():
    txt = source().replace('u_lf1_u_vs', 'foreign_u_vs')
    assert not bits(BG.in_bit_owners(txt, 'leafdn_i0', CORES), CORES[0])
    assert not bits(BG.out_bit_owners(txt, 'leafup_o0', 668, CORES), CORES[0])

def test_ambiguous_image_prefix_refuses_and_exact_name_wins():
    with pytest.raises(ValueError, match='ambiguous native leaf'):
        BG.native_core_aliases('u_u_lf1_u_vs (\nu_u_lf2_u_vs (', ['u_lf.u_vs'])
    assert BG.native_core_aliases('u_u_lf_u_vs (\nu_u_lf1_u_vs (', ['u_lf.u_vs']) == {'u_lf.u_vs': 'u_lf.u_vs'}
    with pytest.raises(ValueError, match='same native instance'):
        BG.native_core_aliases('u_u_lf1_u_vs (', ['u_lf.u_vs', 'u_lf1.u_vs'])
    assert BG.native_core_aliases('u_u_lf1_u_vs (', ['u_lf0.u_vs']) == {'u_lf0.u_vs': 'u_lf0.u_vs'}

@pytest.mark.parametrize('rhs', ['a + b', "{a[3:0], 4'b0000}", 'a[8:1]', '{a[3:0], b[2:0]}'])
def test_unknown_or_non_preserving_assign_is_not_a_driver(rhs):
    nl = BG.Netlist('wire [7:0] a;\nwire [7:0] b;\nwire [7:0] q;\nassign q = '+rhs+';\n')
    assert nl.back('q', 0, lambda name, bit: bit if name == 'a' else None) is None

def test_known_width_alias_slice_and_concat_preserve_bit_order():
    txt = 'wire [7:0] a;\nwire [7:0] q;\nwire [3:0] z;\nassign q = {a[3:0], a[7:4]};\nassign z = q[7:4];\n'
    nl = BG.Netlist(txt)
    assert [nl.back('z', i, lambda name, bit: bit if name == 'a' else None) for i in range(4)] == list(range(4))
