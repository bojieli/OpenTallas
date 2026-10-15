#!/usr/bin/env python3
"""Audit frozen W19 units and padding without modifying any performance price."""
import ast
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ['tools/w19_hbm_token_compose.py', 'tools/hgi_sim/calibration.json',
           'tools/hgi_sim/ds_native.py', 'rtl/gpu/ot_gpu_payload_assemble.sv',
           'rtl/chip/ot_chip_v41x_hbm3e_phy.sv']

def run():
    wanted = {'F_FAST', 'N_SM', 'HBM_STACKS', 'HBM_STACK_BYTES_PER_S',
              'HBM_SUSTAINED', 'SM_LINE_BYTES', 'SM_HBM_PEAK_BYTES_PER_CYCLE',
              'SM_HBM_BYTES_PER_CYCLE'}
    values = {}
    for node in ast.parse((ROOT / SOURCES[0]).read_text()).body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in wanted:
                values[target.id] = eval(compile(ast.Expression(node.value), SOURCES[0], 'eval'),
                                         {'__builtins__': {}}, values)
    assert wanted == values.keys()
    peak = values['SM_HBM_PEAK_BYTES_PER_CYCLE']
    sustained = values['SM_HBM_BYTES_PER_CYCLE']
    line = values['SM_LINE_BYTES']
    price = line / sustained
    assert line == 136 and values['N_SM'] == 32
    # Four PCs per SM, each transfers 32 B on the actual 1.024 ns HBM edge.
    stream_ps = 1e12 / values['F_FAST']
    raw_per_hbm_edge = 4 * 32
    assert math.isclose(raw_per_hbm_edge * stream_ps / 1024, peak)
    cases = []
    for lines in (1, 4, 16, 32, 128, 256, 1024, 4096):
        useful = lines * line
        for granule in (32, 128):
            raw = math.ceil(useful / granule) * granule
            cycles = raw / sustained
            cases.append(dict(lines=lines, final_padding_granule_bytes=granule,
                              raw_bytes=raw, padding_bytes=raw-useful,
                              ideal_95pct_stream_edges=cycles,
                              ratio_to_frozen_line_floor=cycles/(lines*price),
                              max_extra_setup_edges_at_110pct=1.1*lines*price-cycles))
    return dict(schema='opentallas.hbm.bandwidth_audit.v1',
        status='STRUCTURAL_REPAIR_REQUIRED_NO_PERFORMANCE_QUALIFICATION',
        source_sha256={p: hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in SOURCES},
        frozen_constants=values,
        clock_units=dict(stream_period_ps=stream_ps, hbm_period_ps=1024,
                         raw_bytes_per_sm_hbm_edge=raw_per_hbm_edge),
        immutable_price=dict(raw_bytes_per_sm_stream_edge_peak=peak,
                            raw_bytes_per_sm_stream_edge_95pct=sustained,
                            stream_edges_per_136byte_line=price,
                            payload=dict(weights_bytes=128, checkpoint_scale_bytes=8)),
        padded_nb5=dict(raw_bytes_per_line=160,
            peak_stream_edges_per_line=160/peak,
            sustained_stream_edges_per_line=160/sustained,
            peak_ratio_to_frozen_price=(160/peak)/price,
            sustained_ratio_to_frozen_price=(160/sustained)/price,
            useful_bytes_per_stream_edge_peak=peak*136/160,
            useful_bytes_per_stream_edge_95pct=sustained*136/160),
        packed_candidate=dict(phase_bytes=[0,8,16,24], sectors_per_four_lines=17,
            bytes_per_four_lines=544,
            existing_reference='rtl/gpu/ot_gpu_payload_assemble.sv is opt-in and handshaken; static production migration required',
            blocks=cases),
        scope_notes=[
            '99 B/cycle is rounded sustained RAW physical bandwidth per SM per streaming edge; the frozen W19 136-byte line includes 8 scale bytes.',
            'Qwen fmt3_transport=1.25 already charges its 160-byte stride per128 INT8 codes. That separate calibration does not charge DS W19 160 bytes.',
            'Final padding and setup must be included once per actual transfer block, not silently amortized over an unbounded stream.',
            'The measured off-chip 77/122 HBM-edge baselines exclude new CDC staging; actual service pipeline has failed its 110-percent timing gate.',
            'No revised bandwidth, SM count, throughput target, or performance waiver is authorized.'],
        required_gates=['actual 136-byte checkpoint image and full 30-bit XOR-PC mapping',
            'actual static formatter and 1099-bit consumer including real scales/tags',
            'compiled 83-bit programme and all setup/padding/drain costs',
            'full production-shape end-to-end run at distinct actual clocks',
            '95-percent sustained throughput and immutable accepted latency gates',
            'physical roots, pins, SRAM, TT setup, FF hold and DRC0'])

if __name__ == '__main__':
    out = ROOT/'results/arch/hbm_die_v15/bandwidth_audit/receipt.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    result = run()
    out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({'output': str(out), 'price': result['immutable_price'],
                      'padded_nb5': result['padded_nb5']}, indent=2))
