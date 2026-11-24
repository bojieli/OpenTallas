"""D512 KV adapter source row contract; no fixture arithmetic or token claim.

The source adapter has a qualified real-VP consumer component. These functions
encode its production KVT/KVQ storage ABI. Absolute programme dates,
the real a_proj producer transfer, and service OWN_ROW handoff remain required.
"""
from __future__ import annotations

PARAM_BASE = 672
OPERAND_BASE = 692
ENGINE_OUTPUT_BASE = 168
SLICE = 'u_s_3N'
LEAF = 0

# ---- SUKV command timing, seen from the A side (the kv_leaf t2 A pins), in sampled edges from the command capture.
# Base: rtlgap_sukv_1021 bench, seam 0, VLAT 4 (finish_edges - 1).
ADAPTER_DONE = dict(KV=1130, GK=1025, CN=1218, IK=1058, CP=390)
FIRST_NATIVE_WRITE = dict(KV=1030, CN=1030, IK=1030, CP=139)
LAST_READ_BOUND = dict(KV=80, CN=80, IK=80, GK=72, CP=378)
# (seam_in, seam_out) of the t2 A|B cut that a bench measured (S81-KVLEAF-T2-ARCH-R2 bench_xq3 / xq4, RTL d97edba9f3a3).
# Only these may be priced: another depth needs its own bench run.
MEASURED_SEAMS = ((0, 0), (2, 2), (3, 3))


def kv_timing(seam_in=0, seam_out=0, vp_sr=0):
    """Done / first-write / last-read dates of the five SUKV jobs for a t2 seam and vp SRAM-register form.

    d = seam_in + seam_out.  GK / CN / IK / KV finish on the fixed drain age, so done moves by d (the command crosses the
    seam in, the done level crosses it out).  The compressor pool finishes on its last VM read return, which crosses the
    seam a second time: CP moves by 2 d.  Writes leave through the same output stages as done, so write-to-done is
    unchanged.  vp_sr (OT_S81SL_VP_SRAMREG: registered leaf-store pins) adds one edge to the VM read loop (CP done) and one
    edge to every store commit and store read; the fixed-drain done dates do not move.
    """
    if (seam_in, seam_out) not in MEASURED_SEAMS:
        raise ValueError(f'kv_leaf t2 seam {seam_in}+{seam_out} has no measured timing; run the seam bench first')
    if vp_sr not in (0, 1):
        raise ValueError('vp SRAM-register form must be 0 or 1')
    d = seam_in + seam_out
    done = {k: v + (2 * d + vp_sr if k == 'CP' else d) for k, v in ADAPTER_DONE.items()}
    first = {k: v + (2 * d + 2 * vp_sr if k == 'CP' else d + vp_sr) for k, v in FIRST_NATIVE_WRITE.items()}
    return dict(seam_in=seam_in, seam_out=seam_out, vp_sr=vp_sr, done=done, first_native_write=first,
                last_read_completion_bound={k: v + d + vp_sr for k, v in LAST_READ_BOUND.items()},
                native_write_commit_after_done=1 + vp_sr, native_read_ready_after_done=2 + vp_sr)


def program_timing(program):
    """The timing a programme was compiled for: kv_seam {in, out, vp_sr}; absent = the uncut leaf at vp SR 0."""
    seam = program.get('kv_seam')
    if seam is None:
        return kv_timing()
    if set(seam) != {'in', 'out', 'vp_sr'} or any(type(v) is not int for v in seam.values()):
        raise ValueError('kv_seam needs exactly the integers in, out and vp_sr')
    return kv_timing(seam['in'], seam['out'], seam['vp_sr'])


def dispatch(kind, gain_set, job_id, drain_age, parameter_base=PARAM_BASE, operand_base=None):
    """Encode the source adapter opcode; drain_age must be measured, never guessed.

    The command is meaningful only on KV_ENABLE=1 s_3N leaf0. Its dispatch
    does not establish ownership or transport the a_proj result into the SRAM.
    """
    from layer_prog.lower_vs import vp_cmd
    if kind not in (1, 7, 12, 13) or gain_set not in range(4) or job_id not in range(256):
        raise ValueError('Unsupported production KV/GK/CN/IK job field')
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
                adapter_ref='codex/s81-kvq-bind-1021@286841a838132f393f3b387f2ecce0e20111c73b',
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
                measured_fixed_drain_age=1024,
                consumer_component=dict(
                    receipt='results/token_pass/s81_kv_real_vp_1021/r3/result.json',
                    boundary='Native VP sw fixture preload; VP command forwarding, real SRAM extension and readback',
                    vp_extension_response_edges=4, gain_finish_adapter_age=1025,
                    kv_finish_adapter_age=1130, first_result_adapter_age=266,
                    last_result_adapter_age=285, input_and_readback_requests=190,
                    input_and_readback_responses=190, exponent_drop_mismatches=8,
                    vp_command_pre_capture_to_done_observation=dict(gain=1028, kv=1133),
                    convention='Command start is benchmark negedge before VP pin capture; elapsed counts '
                               'the following posedges through done observation. Adapter ages are dut.age '
                               'observed at negedge. These are not global programme dates.'),
                qualification='CONSUMER COMPONENT ONLY at the pinned source: real VP dispatch/storage, '
                              'D512 arithmetic and masked output readback. Actual producer transfer, '
                              'absolute issue dates, service OWN_ROW handoff and whole-calendar lifetimes '
                              'remain unqualified. Source minimum 128 is an encoding bound; the measured '
                              'fixed drain age is 1024.')


def pool_dispatch(slot0_base, slot1_base, output_base):
    """Encode CP14. Inputs are actual producer rows, never fixture outputs.

    Each input record contains128 native KV rows then128 native score rows.
    The pool writes128 BF16-widened native rows. Overlap is legal only for
    exact in-place replacement of one input's KV section (RTL's live range).
    """
    from layer_prog.lower_vs import vp_cmd
    if any(type(v) is not int or v % 4 for v in (slot0_base, slot1_base, output_base)):
        raise ValueError('CP record and output bases must be four-row aligned integers')
    if not (0 <= slot0_base <= 768 and 0 <= slot1_base <= 768 and 0 <= output_base <= 896):
        raise ValueError('CP record or output outside native1024-row store')
    if max(slot0_base, slot1_base) < min(slot0_base, slot1_base) + 256:
        raise ValueError('CP slot records overlap')
    for base in (slot0_base, slot1_base):
        if output_base != base and output_base < base + 256 and output_base + 128 > base:
            raise ValueError('CP output overlaps a live input record')
    return vp_cmd(15, a0=slot0_base, a1=slot1_base, n=32, imm=14 | (output_base << 4))


def sukv_contract():
    """Exact source ABI extension. Absolute calendar still consumes measured ages."""
    return dict(schema='opentallas.s81.sukv_bank_contract.v1', slice=SLICE, leaf=LEAF,
        enables=dict(KV_ENABLE=1, KV_CNIK=1, KV_CP=1),
        command_op=15, source='rtl/dsrom_sys/s81_dv/slice/ot_s81sl_kv_leaf.sv',
        norm_jobs={
            'CN':dict(kind=12, gain_set=3, dimension=512, reads=74, events=48,
                      qdq_native_rows=[672,735], raw_native_rows=[736,799], norm_native_rows=[800,863],
                      format='FP4 E2M1 with E4M3 scale, block16; BF16 pre-RoPE norm output'),
            'IK':dict(kind=13, gain_set=0, dimension=128, reads=74, events=8,
                      zero_operand_prefix_rows=96, qdq_native_rows=[672,687], raw_native_rows=[688,703],
                      format='FP4 E2M1 with UE8M0 scale, block32')},
        pool=dict(kind=14, dimension=512, ratio=2, issue_edges=372, pair_reads=256,
                  pair_writes=64, slot_native_rows=256, output_native_rows=128,
                  arithmetic='softmax across2 rows per feature; golden sequential2-term sum then BF16'),
        eng_knorm=dict(instance='each slice.u_eg.u_nh / u_nk', new_hardware=False,
                       divisor=5120, epsilon='1e-20', producer='actual chunk8 sum of h*h and k*k'),
        lifetime='Each job owns the leaf port through busy deassertion, including the final registered pair write; '
                 'gain records precede CN/IK; IK requires zero-prefix plus the real128-dimensional key.',
        calendar_qualified=False,
        schedule='Use actual measured command-to-done ages plus actual XRT/landing transfer ages; '
                 'source issue-edge counts alone are not absolute compiler dates.')
