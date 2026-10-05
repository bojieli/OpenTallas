#!/usr/bin/env python3
"""Emit the owner-selected nearHBM baseline; no builds, goldens or runs."""
import argparse
import hashlib
import json
from pathlib import Path
import qwen_rom_combined_sources as predecessor

ROOT = Path(__file__).resolve().parents[1]


def selected(output, *, hbm_layers=36):
    output = Path(output)
    if output.exists():
        raise ValueError('use a fresh source output')
    combined = ROOT / 'rtl/qwen_sys/combined'
    pin = json.loads((combined / 'nearbaseline_source_pin.json').read_text())
    for name, expected in pin['sources'].items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise ValueError('selected pipelined engine source changed: ' + name)
    rec = predecessor.selected(output, near_hbm=True, hbm_layers=hbm_layers)
    omit = {'ot_qwen_rom_combined_die.sv', 'ot_qwen_nearhbm_sys_tb_fenced.sv',
            'ot_qwen_nearhbm_attn_hub.sv', 'ot_qwen_nearhbm_attn_stack.sv',
            'ot_qwen_nearhbm_sfu_p.sv'}
    die = [Path(p) for p in rec['die'] if Path(p).name not in omit]
    die += [combined / 'ot_qwen_rom_combined_nearbaseline_die.sv',
            combined / 'ot_qwen_combined_nearbaseline_subsystem.sv',
            *(ROOT / p for p in pin['sources'])]
    die = list(dict.fromkeys(die))
    rec['die'] = list(map(str, die))
    rec['top'] = 'ot_qwen_rom_combined_nearbaseline_die'
    rec['parameters']['NEAR_HBM'] = 1
    rec['mandatory_baseline'] = {'near_hbm': True, 'layer_start_fence': 1,
                                 'pipelined_hub_row_engine': pin['engine_commit'],
                                 'collective': 'one-stream AR256',
                                 'preload_fix': pin['preload_fix']}
    rec['optional_candidates']['near_hbm'] = False
    rec['source_sha256'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest()
                           for p in dict.fromkeys(die + list(map(Path, rec['tile']))
                                                 + list(map(Path, rec['collective'])))}
    rec['context_limit'] = {'maximum_position': 8191, 'target_context': 8192}
    rec['runtime_contract'] = 'initialized model eval BEFORE first preload; descriptor3 layer images; per-layer runs then composition'
    (output / 'sources.json').write_text(json.dumps(rec, indent=2) + '\n')
    (output / 'die_sources.f').write_text('\n'.join(map(str, die)) + '\n')
    return rec


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--hbm-layers', type=int, default=36)
    args = ap.parse_args()
    rec = selected(args.output, hbm_layers=args.hbm_layers)
    print(json.dumps({'top': rec['top'], 'NEAR_HBM': 1,
                      'HBM_LAYERS': rec['parameters']['HBM_LAYERS']}))
