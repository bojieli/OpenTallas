#!/usr/bin/env python3
"""Source-bound H3 scalar inspection and exact rational witnesses; no HDL execution."""
import argparse
from fractions import Fraction
import hashlib
import json
import re
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
BASE = '400d3d0c0f9caaf5e16392b71da21d6a135d3a6d'
HANDOFF = 'cd9a7781052d2a6b870fcbe781553f50a0baf350'
PINS = ['tools/hdc_golden.py', 'tools/hdc_golden_v41.py',
        'tools/qwen_hbm_complete_program.py', 'tools/h3_distributed_norm_endpoint.py',
        'tools/uarch_model.py', 'rtl/gpu/ot_gpu_full_sm_service.sv',
        'rtl/gpu/ot_gpu_fadd.sv', 'rtl/hdc/ot_hdc_fp32_add_lat.sv',
        'rtl/hdc/ot_hdc_fp32_mul_lat.sv', 'rtl/hdc/ot_hdc_sfu.sv',
        'rtl/hdc/v41/ot_hdc_fdiv.sv', 'rtl/abi3/ot_a3_fp32_div_rne_pipe.sv',
        'results/uarch/h3_distributed_norm_endpoint_20261002/model.json',
        'results/physical_abi3/asap7/primitive_fmax_headroom/routes/hdc_fdiv_base.json']


def finite(code):
    if code & 0x7f800000 == 0x7f800000:
        raise ValueError('nonfinite')
    e, f = (code >> 23) & 255, code & 0x7fffff
    s, p = ((1 << 23) | f, e - 150) if e else (f, -149)
    v = Fraction(s) * Fraction(2) ** p
    return -v if code >> 31 else v


def rne(v):
    """Independent rational -> FP32 bits, canonical zero, IEEE overflow to Inf."""
    if not v:
        return 0
    sign = 0x80000000 if v < 0 else 0
    v = abs(v)
    e = v.numerator.bit_length() - v.denominator.bit_length()
    if v < Fraction(2) ** e:
        e -= 1
    p = max(e - 23, -149)
    t = v / Fraction(2) ** p
    n, rem = divmod(t.numerator, t.denominator)
    n += 2 * rem > t.denominator or (2 * rem == t.denominator and n & 1)
    if not n:
        return 0
    if n >= 1 << 24:
        n >>= 1
        p += 1
    if p == -149 and n < 1 << 23:
        return sign | n
    be = p + 150
    if be >= 255:
        return sign | 0x7f800000
    return sign | (be << 23) | (n & 0x7fffff)


def div_contract(a, b):
    if (a & 0x7f800000 == 0x7f800000 or
            b & 0x7f800000 == 0x7f800000 or not b & 0x7fffffff):
        return 0, 1
    y = rne(finite(a) / finite(b))
    return (0, 2) if y & 0x7f800000 == 0x7f800000 else (y, 0)


def restoring_div31(a, b):
    """Integer transcription of pinned HDC31 stages, distinct from rational oracle.

    Functional static witness only; does not evaluate RTL scheduling/valid/reset.
    """
    bad = (a & 0x7f800000 == 0x7f800000 or b & 0x7f800000 == 0x7f800000 or not b & 0x7fffffff)
    if bad:
        return {'y': 0, 'fault': 1, 'stage': 'decode_argument'}
    if not a & 0x7fffffff:
        return {'y': 0, 'fault': 0, 'stage': 'canonical_zero'}
    def norm(c):
        e, f = (c >> 23) & 255, c & 0x7fffff
        if e:
            return (1 << 23) | f, e - 127
        p = f.bit_length() - 1
        return f << (23 - p), p - 149
    ma, ea = norm(a)
    mb, eb = norm(b)
    rem, q = ma, 0
    for j in range(27):
        if j:
            rem = (rem & 0xffffff) << 1
        take = rem >= mb
        if take:
            rem -= mb
        q = ((q << 1) | take) & 0x7ffffff
    if q & (1 << 26):
        sig, g, st, be = q >> 3, (q >> 2) & 1, bool(q & 3 or rem), ea - eb + 127
    else:
        sig, g, st, be = q >> 2, (q >> 1) & 1, bool(q & 1 or rem), ea - eb + 126
    original_be = be
    shift = 0
    if be < 1:
        shift = min(1 - be, 25)
        ext = (sig << 1) | g
        st |= bool(ext & ((1 << shift) - 1))
        shifted = ext >> shift
        sig, g, field = shifted >> 1, shifted & 1, 0
    else:
        field = be & 255
    up = bool(g and (st or sig & 1))
    code = ((field << 23) | (sig & 0x7fffff)) + up
    fault = be > 254 or code >> 23 == 255
    y = 0 if fault or not code else ((a ^ b) & 0x80000000) | code
    return {'y': y, 'fault': int(fault), 'Q27': q, 'remainder': rem,
            'biased_exponent': original_be, 'subnormal_shift': shift,
            'guard': g, 'sticky': bool(st), 'round_up': up}


def newton(v, kind):
    """Every round is explicit; source constants/loop order retained exactly."""
    trace = []
    def op(name, a, b, multiply):
        y = rne(finite(a) * finite(b) if multiply else finite(a) + finite(b))
        trace.append({'op': name, 'a': f'{a:08x}', 'b': f'{b:08x}', 'y': f'{y:08x}'})
        return y
    if kind == 'rsqrt':
        seed = (0x5f3759df - (v >> 1)) & 0xffffffff
        half = op('half_mul', v, 0x3f000000, True)
        y = seed
        for i in range(3):
            yy = op(f'{i}:y_y', y, y, True)
            hyy = op(f'{i}:half_yy', half, yy, True)
            corr = op(f'{i}:correction_add', 0x3fc00000, hyy ^ 0x80000000, False)
            y = op(f'{i}:next_mul', y, corr, True)
    elif kind == 'reciprocal':
        saturated = not v >> 31 and v & 0x7f800000 != 0x7f800000 and v > 0x7ef311c7
        seed = 0 if saturated else (0x7ef311c7 - v) & 0xffffffff
        y = seed
        for i in range(3):
            dy = op(f'{i}:d_y', v, y, True)
            corr = op(f'{i}:correction_add', 0x40000000, dy ^ 0x80000000, False)
            y = op(f'{i}:next_mul', y, corr, True)
    else:
        raise ValueError('kind')
    return {'input': f'{v:08x}', 'kind': kind, 'seed': f'{seed:08x}',
            'steps': trace, 'result': f'{y:08x}'}


def divider_search_edges(a, b):
    """Exact source bisection steps; E=accept, terminal is E+2*K+3."""
    if div_contract(a, b)[1] == 1 or not a & 0x7fffffff:
        return {'iterations': 0, 'edges_after_accept': 0}
    ea, eb = (a >> 23) & 255, (b >> 23) & 255
    ed = ea - eb
    lo = 0 if not ea or not eb or ed + 126 <= 0 else (0x7f7fffff if ed + 126 >= 255 else (ed + 126) << 23)
    hi = 0x7f7fffff if not ea or not eb or ed + 128 >= 255 or ed + 128 <= 0 else min(((ed + 128) << 23) - 1, 0x7f7fffff)
    q = abs(finite(a) / finite(b))
    k = 0
    while lo <= hi:
        c = lo + ((hi - lo) >> 1)
        k += 1
        if finite(c) <= q:
            if c == 0x7f7fffff:
                lo, hi = c, c - 1
            else:
                lo = c + 1
        else:
            if c == 0:
                lo, hi = 1, 0
            else:
                hi = c - 1
    return {'iterations': k, 'edges_after_accept': 2 * k + 3}


def model():
    pins = {}
    for path in PINS:
        data = subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT)
        if (ROOT / path).read_bytes() != data:
            raise ValueError('source changed: ' + path)
        pins[path] = hashlib.sha256(data).hexdigest()
    external = {}
    for path in ['tools/h3_native_command_cost_contract.py', 'tools/w19_gpu_norm_calendar.py',
                 'rtl/hdc/v41x/ot_hdc_v41x_sfu.sv', 'rtl/gpu/ot_gpu_rf_service.sv']:
        data = subprocess.check_output(['git', 'show', f'{HANDOFF}:{path}'], cwd=ROOT)
        external[path] = hashlib.sha256(data).hexdigest()
    historical = json.loads((ROOT / PINS[-1]).read_text())
    hist_commit = historical['git']['commit']
    for src in historical['design']['sources']:
        old_bytes = subprocess.check_output(['git', 'show', f"{hist_commit}:{src['path']}"], cwd=ROOT)
        if hashlib.sha256(old_bytes).hexdigest() != src['sha256']:
            raise ValueError('historical record pin mismatch: ' + src['path'])
    old_sfu = subprocess.check_output(['git', 'show', f'{hist_commit}:rtl/hdc/ot_hdc_sfu.sv'], cwd=ROOT).decode()
    pat = r'module ot_hdc_vline\b.*?endmodule'
    old_vline = re.search(pat, old_sfu, re.S).group()
    new_vline = re.search(pat, (ROOT / 'rtl/hdc/ot_hdc_sfu.sv').read_text(), re.S).group()
    if old_vline != new_vline:
        raise ValueError('reachable vline module changed')
    if historical['design']['sources'][0]['sha256'] != pins['rtl/hdc/v41/ot_hdc_fdiv.sv']:
        raise ValueError('historical DIV body changed')
    dff = 0.2916
    # Explicit source declaration ledger, no synthesis constant propagation credit.
    pipe_regs = {'decode': 62, 'recurrence_27x90': 2430, 'finish1': 40,
                 'finish2': 38, 'output': 33, 'valid_line': 31}
    fsm_regs = {'control': 4, 'bracket': 93, 'operand_significands': 48,
                'operand_powers': 18, 'product': 49, 'product_power': 10,
                'degenerate': 1, 'candidate': 31, 'round_significand': 25,
                'round_power': 9, 'output': 35}
    witnesses = []
    for a, b in [(0x3f800000, 0x45a00000), (0x3f800000, 0x40400000),
                 (0x00800000, 0x43800000), (0x80000001, 0x40000000),
                 (0x7f7fffff, 0x3f000000), (0, 0x45a00000),
                 (0x3f800000, 0), (0x7f800000, 0x3f800000)]:
        y, err = div_contract(a, b)
        witnesses.append({'a': f'{a:08x}', 'b': f'{b:08x}', 'y': f'{y:08x}',
                          'error': err, **divider_search_edges(a, b)})
    return {'status': 'SOURCE_CONTRACT_MODEL_ONLY_NOT_BUILD_READY', 'base': BASE,
      'source_sha256': pins, 'handoff_commit': HANDOFF, 'handoff_source_sha256': external,
      'RTL_builds': 0, 'physical_runs': 0,
      'historical_physical_price': {'source_record': PINS[-1], 'corner': historical['corner']['name'],
        'DIV31_routed_standard_cell_area_um2': historical['design']['area_um2'],
        'DIV31_routed_core_outline_um2': historical['design']['core_area_um2'],
        'source_body_match': True, 'historical_git_commit': hist_commit,
        'reachable_vline_module_sha256': hashlib.sha256(new_vline.encode()).hexdigest(),
        'full_support_file_identical': False,
        'scope': 'DIV body and reachable vline identical; full SFU file differs in unrelated modules. Retained primitive TT price only, not native GPU SS/FF slot or timing qualification',
        'NS8_one_core_per_SM_cell_um2': 8 * historical['design']['area_um2'],
        'NS8_one_core_per_SM_outline_um2': 8 * historical['design']['core_area_um2'],
        'actual_required_replica_count': None, 'new_capture_mux_tag_control_area_um2': None,
        'actual_native_slot_admission': False},
      'selected_endpoint': {'owner': 'Epicurus explicitly assigned by parent',
        'call': 'DIV(sum,F32(5120))', 'denominator_hex': '45a00000',
        'defaultoff_implementation': 'held until G0 model/slot/clock admission',
        'Qwen_mean_denominator_reciprocal_hex': '39800000',
        'source_full_SM_instance_count_NS': 8,
        'lease': 'sole whole-SM RF lease from command accept through mirrored write ACK and done retirement; no new RF port',
        'root_tree': 'Peirce chunk8 sibling/order unchanged; final collector lane0',
        'proposed_service_cost_edges': {
          'admission': 1, 'RF_read': 2, 'execute_declared_D31': 31,
          'mirrored_write_ACK': 2, 'done_retire': 1, 'total_D31_no_stall': 37,
          'total_D19_no_stall': 25,
          'scope': 'analytical proposed scalar join under ready source RF, no competing host and no output stall; not actual measured GPU service'},
        'proposed_edge_calendar': ['E0 accept, lease lock', 'E1 RF read accepted',
          'E2 registered RF response becomes valid', 'E3 consume/start DIV decode',
          'E(D+2) final DIV valid/result', 'E(D+3) capture result/fault',
          'E(D+4) successful mirrored RF write', 'E(D+5) ACK consumed',
          'E(D+6) successful command retired'],
        'stalls': 'admission/RF read/write/done stalls add explicit edges; no finite service upper bound without ready guarantee',
        'fault_reset': 'invalid argument/overflow captured as failed command, suppress successful scalar publication; no stale result after reset, pipeline valid flushed; RF payload may persist but invalid',
        'context_clock': 'single GPU service clock proposed; scalar result holder bridges backpressure. Different serial clock requires modeled CDC and is not selected',
        'conditional_ns_at_1p2GHz': {'D31_service': 37 / 1.2, 'D19_service': 25 / 1.2},
        'frequency_qualified': False,
        'native_source_join_missing': True,
        'Maxwell_admission_required': ['NS8 source instance and scalar lease hook pins', '12339 RF local tracks and 41 root tracks', 'scalar slot actual area/corridor and SS/FF paths', 'all participant/collector/scale/delivery service costs']},
      'ownership': {'scalar': 'Epicurus explicitly assigned; Peirce compiler and Maxwell composition unchanged',
                    'D2': 'remains primary, clean pinned worktree, no running jobs'},
      'contracts': {
        'DS_RMS': 'chunk8 padded golden tree requires HDC_V41_ARITH=chunk8 or su; DIV(sum,F32(N)); ADD(eps); rsqrt3; HC-pre BF16 rounding retained',
        'Qwen_RMS': 'HDC_SU_WIDTH>=8; chunk8 padded golden tree; MUL(sum,F32(1/N)); ADD(eps); rsqrt3',
        'rsqrt3': {'seed': '0x5f3759df-(bits(v)>>1)', 'FMUL': 10, 'FADD': 3, 'neg_XOR': 3, 'INT_seed': 2},
        'reciprocal3': {'seed': '0x7ef311c7-bits(d), source positive-finite saturation retained', 'FMUL': 6, 'FADD': 3, 'neg_XOR': 3, 'INT_seed': 1,
                        'callers': ['Qwen softmax denominator', 'Qwen attention PV normalization', 'Qwen SILU'], 'not_RMS_rsqrt': True},
        'fault': 'DIV nonfinite/zero-divisor -> +0/argument; overflow -> +0/overflow. Golden IEEE Inf/NaN is not a zero-fault hardware oracle.'},
      'primitive_inventory': {
        'existing_ABI3_exact_DIV': {'state_bits': sum(fsm_regs.values()), 'ledger': fsm_regs,
          'DFF_cell_um2_proxy': sum(fsm_regs.values()) * dff, 'core_max_edges_after_accept': 65,
          'unclamped_normal_window_max_edges': 53, 'zero_argument_edges_after_accept': 0,
          'result_held_until_ready': True, 'II': 'core edges+1+out_ready stall; one in flight',
          'logic': 'one 25x24->49 multiplier, 97-bit alignment/comparator, 31-bit bracket, seed/midpoint logic'},
        'existing_HDC_exact_DIV': {'state_bits': sum(pipe_regs.values()), 'ledger': pipe_regs,
          'DFF_cell_um2_proxy': sum(pipe_regs.values()) * dff, 'source_stages': 31, 'II': 1,
          'result_held_until_ready': False, 'logic': '27 recurrence 25-bit compare/subtract stages, two normalize/shift paths, finish RNE shift/sticky',
          'integration': 'needs tagged result capture/backpressure holder; not connected GPU endpoint; no native GPU timing transfer'},
        'existing_v41x_DIV19': {'source_commit': HANDOFF, 'state_bits': 1904,
          'ledger': {'decode': 62, 'mb3_prep': 88, 'recurrence_14x116': 1624, 'finish1': 40, 'finish2': 38, 'output': 33, 'valid_line': 19},
          'DFF_cell_um2_proxy': 1904 * dff, 'declared_stages': 19, 'declared_II': 1,
          'logic': '13 two-bit radix4 stages and final one-bit; three 28-bit subtract/select paths per stage; normalization and RNE finish',
          'native_GPU_binding': False, 'timing_transfer': False},
        'native_GPU': 'existing 128xADD/MUL LAT7 SIMD; parent has binary mul selector, no DIV command. Reuse arithmetic; scalar endpoint/gather INT lease join remains proposed.'},
      'G0': {'target_applicability': ['Qwen ROM','Qwen HBM','DS ROM','DS HBM'],
        'selected_primitive': None, 'replicas': {'norm_collector_per_rank': 1, 'local_SM_count': 32, 'replica_selection': 'requires Maxwell admission; no 128-lane DIV assumed'},
        'MAC_per_cycle': 0, 'DIV_issue_per_cycle': 'ABI3 worst-case core+reaccept 66 edges, stalls extend it; HDC 1 internal, RF lease serialized',
        'RF_existing_read_bytes_per_accepted_transaction': 1024,
        'RF_existing_write_bytes_per_accepted_transaction': 512,
        'RF_peak_read_bytes_per_cycle': 1024, 'RF_peak_write_bytes_per_cycle': 512,
        'scalar_operand_bits': 64, 'scalar_result_bits': 32, 'tags_ready_fault_bits': None,
        'new_RF_memory_ports': 0, 'local_RF_read_wire_bits': 8192, 'local_RF_write_wire_bits': 4096,
        'Newton_rsqr_FP_rounds': 13, 'Qwen_RMS_scalar_FP_rounds_including_mean_epsilon': 15,
        'DS_RMS_scalar_FP_rounds_excluding_DIV_including_epsilon': 14,
        'reuse_SIMD_naive_rsqr_RF_read_bytes': 13 * 1024,
        'reuse_SIMD_naive_rsqr_RF_write_bytes': 13 * 512,
        'lane_local_fusion': 'must retain exact operand registers/rounding; removes intermediate RF trips only after separate source model, no implemented fusion credit',
        'intensity': 'naive RF rsqrt: 13 scalar rounded ops / 19968 transferred bytes; lane-local scalar capture cost unbound',
        'proposed_context_ledger_bits': {'input_d': 32, 'half': 32, 'y': 32, 'result': 32, 'error': 2, 'valid': 1, 'step': 4, 'kind': 2, 'busy': 1},
        'proposed_context_bits_excluding_tags': 138,
        'proposed_context_DFF_um2_proxy_excluding_tags': 138 * dff,
        'context_service': 'costed proposal only: lane-local rounded results retained; uses existing native ADD/MUL via explicit operand/result routing still to be modeled',
        'proposed_extra_state_bits_with_tags': None, 'extra_mux_fanout_area_um2': None,
        'cell_area_total_um2': None, 'floorplan_slot_fit': None, 'routing_tracks_against_capacity': None,
        'SS_FF_in_context': False, 'clock_policy': 'native streaming 1.2GHz SS/FF60/25ps; serial0.9GHz requires explicit3:4 CDC; neither divider inherits frequency',
        'full_composed_token_latency_ns': None,
        'latency_expression': 'Peirce root service + exact DIV or mean-MUL + epsilon-ADD + 10MUL+3ADD + integer seed/neg + scalar capture + RF mirrored ACK + delivery fence',
        'calibration': 'Peirce H1 19-edge FP driver calibration is functional only, not native GPU time; DIV core edge ledger separate'},
      'gates': ['owner ack and exact compiler source binding', 'native root/RF INT/gather cycle and source lease join',
        'selected existing DIV source qualification and error codes', 'finite capture/tag/reset/drain CDC model',
        'full G0 area/routing/slot/cycle composition before RTL', 'bounded assertion-only source-composed exact gate before SS/FF physical gate'],
      'witnesses': witnesses,
      'selected_DIV5120_static_stage_witnesses': [dict(input=f'{a:08x}', expected_y=f'{div_contract(a, 0x45a00000)[0]:08x}',
          expected_error=div_contract(a, 0x45a00000)[1], source_stages=restoring_div31(a, 0x45a00000))
          for a in [0, 1, 0x00800000, 0x3f800000, 0x7f7fffff, 0x80000001, 0x7f800000]],
      'Newton_traces': [newton(v, k) for k in ['rsqrt','reciprocal'] for v in [0x3f800000,0x40000000,0x40800000,0x3a800000]]}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(model(), indent=2, sort_keys=True) + '\n')
