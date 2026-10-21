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


def dispatch(kind, gain_set, job_id, drain_age, parameter_base=PARAM_BASE, operand_base=None):
    """Encode the source adapter opcode; drain_age must be measured, never guessed.

    The command is meaningful only on KV_ENABLE=1 s_3N leaf0. Its dispatch
    does not establish ownership or transport the a_proj result into the SRAM.
    """
    from layer_prog.lower_vs import vp_cmd
    if kind not in (1, 7) or gain_set not in range(4) or job_id not in range(256):
        raise ValueError('Unsupported production KV/GK job field')
    if type(drain_age) is not int or not 128 <= drain_age < 2**16:
        raise ValueError('Measured fixed drain edge must satisfy the source minimum of 128')
    if operand_base is None:
        operand_base = parameter_base + (4 if kind == 7 else 20)
    if parameter_base % 4 or operand_base % 4 or not (0 <= parameter_base < 1024 and
                                                    0 <= operand_base <= 1024 - 128):
        raise ValueError('Adapter source rows outside native leaf store')
    immediate = kind | (gain_set << 4) | (job_id << 6) | (drain_age << 16)
    return vp_cmd(15, a0=parameter_base, a1=operand_base, n=32, imm=immediate)


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
                adapter_ref='codex/s81-kvq-bind-1021@19170913b',
                adapter='ot_s81sl_kv_leaf / ot_s81sl_kv_bank; requires KV_ENABLE=1',
                dispatch_abi=dict(op=15, a0=672, a1_kv=692, a1_gain=676, n=32,
                    immediate='kind[3:0], gain_set[5:4], jid[13:6], measured_fixed_drain_age[31:16]',
                    reserved_zero='imm[15:14], imm[127:32]'),
                parameter_rows=[672, 691], operand_rows=[692, 819],
                input_spine_rows=37, input_leaf_rows=148, input_pair_reads=74,
                gain_load=dict(parameter_rows=1, operand_rows=32, input_leaf_rows=132, pair_reads=66),
                outputs=outputs, output_write_events=26, distinct_output_spine_rows=25,
                output_leaf_rows=[672, 771],
                lifetime='Every input read must complete before the first overlapping output write; '
                         'the scratch epoch is exclusive through final capture and consumer transfer.',
                completion='Two exponent writes share one address; both masks must be preserved.',
                output_drain_pair_writes=52,
                output_drain_cycles=104, minimum_fixed_drain_age=128,
                measured_fixed_drain_age=None,
                qualification='ROW ABI ONLY; dispatch RTL, cycle dates, producer transfer, service OWN_ROW '
                              'handoff, and whole-calendar lifetimes are not qualified.')
