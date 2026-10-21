"""D512 KV adapter source row contract; no fixture arithmetic or token claim.

The shared adapter is being implemented by S81-DIE source integration. These
functions encode its existing production KVT/KVQ storage ABI. Programme dates,
the real a_proj producer transfer, and service OWN_ROW handoff remain required.
"""
from __future__ import annotations

PARAM_BASE = 672
OPERAND_BASE = 692
ENGINE_OUTPUT_BASE = 168
SLICE = 'u_s_3N'
LEAF = 0


def descriptor(eps_bits, output_base=ENGINE_OUTPUT_BASE, norm_base=0):
    if not (0 <= eps_bits < 2**32 and 0 <= output_base < 2**14 and 0 <= norm_base < 2**14):
        raise ValueError('KV descriptor field outside actual KVT width')
    return output_base | (norm_base << 64) | (eps_bits << 96)


def split_spine_rows(words, base):
    """512-bit spine rows -> four consecutive native 128-bit leaf rows.

    Values must come from the actual producer/weight store. This function only
    serializes words; it never computes normalized, rotated or quantized values.
    """
    if base % 4 or base < 0 or base + 4 * len(words) > 1024:
        raise ValueError('Unaligned or out-of-range leaf row allocation')
    rows = []
    for index, word in enumerate(words):
        if not 0 <= word < 2**512:
            raise ValueError('Spine row exceeds 512 bits')
        rows.extend(dict(row=base + 4 * index + quarter, mask=15,
                         word128=f'{(word >> (128 * quarter)) & (2**128 - 1):032x}')
                    for quarter in range(4))
    return rows


def contract():
    outputs = [dict(kind='codes', engine_row=ENGINE_OUTPUT_BASE + i,
                    local_rows=[PARAM_BASE + 4 * i, PARAM_BASE + 4 * i + 3], mask16=65535)
               for i in range(8)]
    outputs.extend(dict(kind='exponents', engine_row=ENGINE_OUTPUT_BASE + 8,
                        local_rows=[704, 707], mask16=mask) for mask in (15, 240))
    outputs.extend(dict(kind='qdq_bf16', engine_row=ENGINE_OUTPUT_BASE + 9 + i,
                        local_rows=[708 + 4 * i, 711 + 4 * i], mask16=65535) for i in range(16))
    return dict(schema='opentallas.s81.kv_bank_row_contract.v1', slice=SLICE, leaf=LEAF,
                source='rtl/dsrom_sys/s81_suhc/hier/ot_s81_su_kv.sv',
                parameter_rows=[672, 691], operand_rows=[692, 819],
                input_spine_rows=37, input_leaf_rows=148, input_pair_reads=74,
                gain_load=dict(parameter_rows=1, operand_rows=32, input_leaf_rows=132, pair_reads=66),
                outputs=outputs, output_write_events=26, distinct_output_spine_rows=25,
                output_leaf_rows=[672, 771],
                lifetime='Every input read must complete before the first overlapping output write; '
                         'the scratch epoch is exclusive through final capture and consumer transfer.',
                completion='Two exponent writes share one address; both masks must be preserved.',
                qualification='ROW ABI ONLY; dispatch RTL, cycle dates, producer transfer, service OWN_ROW '
                              'handoff, and whole-calendar lifetimes are not qualified.')
