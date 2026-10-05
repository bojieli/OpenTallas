#!/usr/bin/env python3
"""Execute all 36 layers and head with reduced deterministic parameter fixtures.

This is software control/dataflow evidence, not full-shape checkpoint or RTL.
"""
import argparse
import json
from pathlib import Path
from qwen_hbm_complete_program import compile_program, coverage
from qwen_hbm_complete_executor import SoftwareGPUProvider, execute

def smoke():
    config = dict(hidden_size=8, head_dim=4, num_attention_heads=2,
                  num_key_value_heads=2, intermediate_size=16, vocab_size=16,
                  num_hidden_layers=36, rms_norm_eps=1e-6, rope_theta=1000000)
    program = compile_program(config, context=32, groups=16)
    provider = SoftwareGPUProvider(program)
    first = execute(program, provider, 3, 0)
    second = execute(program, provider, first['next_token'], 1)
    assert first['instructions_retired'] == second['instructions_retired'] == len(program['instructions'])
    assert len(provider.memory.published) == 144
    assert not provider.memory.pending
    return dict(scope='reduced-geometry 36-layer plus head two-token software execution',
                config=config, tokens=[first['next_token'], second['next_token']],
                instructions_per_token=len(program['instructions']),
                coverage=coverage(program), persistent_publications=144,
                fixture_weights=True, golden_intermediate_injection=False,
                actual_RTL_executed=False, fullshape_checkpoint_executed=False,
                token_cycles=None, token_rate=None)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = smoke()
    with args.out.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('instructions_per_token', 'persistent_publications', 'tokens')}))
