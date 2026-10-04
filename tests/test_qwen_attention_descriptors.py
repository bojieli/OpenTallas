"""Actual decoded control-image checks; not a numerical/RTL verdict."""
from pathlib import Path

import pytest
from tools import hdc_isa as I
from tools.runtime.qwen_combined import attention_descriptors as A

INPUT = Path(__file__).resolve().parents[1] / 'results/uarch/qwen_rom_descriptor_binding_20261003/inputs'


def source():
    return ([int(x, 16) for x in (INPUT / 'program.hex').read_text().split()],
            [int(x, 16) for x in (INPUT / 'segments.hex').read_text().split()])


def patch(word, field, value):
    offset, width = I.LAYOUT[field]
    return (word & ~(((1 << width) - 1) << offset)) | (value << offset)


def test_actual_prefix_suffix_and_normal_collective_identity():
    w, d = source()
    nw, nd, r = A.derive(w, d, enable=True)
    assert r['source_removed_attention_pcs'] == [11, 12, 13, 14, 15]
    assert nw[:11] == w[:11] and nw[11] == w[17]
    assert nw[13:] == w[17:]
    before, after = I.decode(w[16]), I.decode(nw[12])
    assert {k: v for k, v in before.items() if k not in r['projection_control_patch']} == {
        k: v for k, v in after.items() if k not in r['projection_control_patch']}
    assert after['chase'] == after['chase_n'] == 0 and after['barrier'] == 1
    assert A.decode_near(nd[0]) == dict(qr_base=15104, attn_base=88944, prefix_program_base=0)
    mask = ~(0xffff << 32)
    assert all(a & mask == b & mask for a, b in zip(d, nd[1:]))
    assert [(x >> 32) & 0xffff for x in nd[1:]] == [12, 14, 15, 23, 24]
    assert (len(nw), len(nd)) == (27, 6)


@pytest.mark.parametrize('pc,field,value', [
    (11, 'me_d_nout', 0), (13, 'me_wsrc', 0), (15, 'su_nout', 7),
    (16, 'me_xbase', 1), (7, 'd_base', 1), (3, 'dst', I.DST_VM),
])
def test_mutated_attention_contract_refused(pc, field, value):
    w, d = source()
    w[pc] = patch(w[pc], field, value)
    with pytest.raises(ValueError):
        A.derive(w, d, enable=True)


def test_default_off_bad_descriptor_and_missing_drain():
    w, d = source()
    with pytest.raises(ValueError, match='default off'):
        A.derive(w, d)
    with pytest.raises(ValueError, match='normal'):
        A.derive(w, [3] + d[1:], enable=True)
    w[17] = patch(w[17], 'barrier', 0)
    with pytest.raises(ValueError, match='drained'):
        A.derive(w, d, enable=True)


def test_kind3_field_limits_and_reserved_bits():
    x = A.encode_near(0xfffff0, 0xffffe0, 4095)
    assert A.decode_near(x)['prefix_program_base'] == 4095
    for qr, attn, base in ((1, 16, 0), (0, 1 << 24, 0), (0, 0, 4096)):
        with pytest.raises(ValueError):
            A.encode_near(qr, attn, base)
    with pytest.raises(ValueError):
        A.decode_near(x | (1 << 62))


def test_emit_keeps_actual_normal_images_and_links_payloads(tmp_path):
    src = tmp_path / 'source'
    src.mkdir()
    for name in ('program.hex', 'segments.hex'):
        (src / name).write_bytes((INPUT / name).read_bytes())
    for name in ('matrix_int8.hex', 'matrix_scale_bf16.hex', 'crom.hex'):
        (src / name).write_text('explicit raw transport fixture\n')
    pins = {name: A.sha(src / name) for name in ('program.hex', 'segments.hex')}
    result = A.emit(src, tmp_path / 'candidate', program_sha256=pins['program.hex'],
                    descriptors_sha256=pins['segments.hex'], enable=True)
    assert all(A.sha(src / name) == value for name, value in pins.items())
    assert (tmp_path / 'candidate/matrix_int8.hex').resolve() == src / 'matrix_int8.hex'
    assert result['payloads_regenerated'] is False and result['adopt'] is False
    with pytest.raises(ValueError, match='pins'):
        A.emit(src, tmp_path / 'wrong', program_sha256='0' * 64,
               descriptors_sha256=pins['segments.hex'], enable=True)
