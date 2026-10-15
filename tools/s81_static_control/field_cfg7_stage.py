"""Emit every pair of one canonical resident FIELD stage into existing CFG7.

Reads only source metadata. Uses the unmodified native phase_cfg function from
its actual source AST, avoiding unrelated compiler checkpoint/tool imports.
This emits storage, not a runtime program or arithmetic qualification.
"""
from pathlib import Path
from array import array
from types import SimpleNamespace
import argparse, ast, gzip, hashlib, json, math
from field_inventory import PINS, file_sha
from field_cfg7_image import emit

ROOT = Path(__file__).resolve().parents[2]


def source_function(path, name, scope):
    nodes = [n for n in ast.parse(path.read_text()).body
             if isinstance(n, ast.FunctionDef) and n.name == name]
    if len(nodes) != 1:
        raise ValueError('missing actual compiler function:' + name)
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), 'exec'), scope)
    return scope[name]


def compile_stage(base, out, stage, rank):
    base, out = Path(base), Path(out)
    for name, pin in PINS.items():
        if file_sha(base / name) != pin:
            raise ValueError('canonical source changed:' + name)
    if stage not in range(81) or rank not in range(4):
        raise ValueError('canonical stage/rank identity required')
    stage_map = json.loads((base / 'stage_map.json').read_text())
    unit_source = ROOT / 'tools/v41_rom_ksplit_bankmap.py'
    cfg_source = ROOT / 'tools/dsrom_full_owner_compiler.py'
    unit = source_function(unit_source, 'unit_range', {})
    cfg = source_function(cfg_source, 'phase_cfg', dict(math=math, S=SimpleNamespace(unit_range=unit)))
    payloads = [array('Q') for _ in range(2417)]
    phase = active_pairs = 0
    phase_sources = []
    with gzip.open(base / 'matrix_map.jsonl.gz', 'rt') as stream:
        for line in stream:
            matrix = json.loads(line)
            if matrix['stage'] != stage:
                continue
            if matrix['compiled_NP'] != 2417:
                raise ValueError('reduced pair allocation refused')
            if phase >= 1 << stage_map['PHW_required_by_stage'][stage]:
                raise ValueError('canonical phase overflow')
            plans = {p[1]: p for p in matrix['plans']}
            if len(plans) != len(matrix['plans']):
                raise ValueError('duplicate per-phase pair allocation')
            owner = rank in matrix.get('physical_owner_ranks', [0, 1, 2, 3])
            for pair in range(2417):
                words = cfg(dict(matrix, plans=[plans[pair]]), pair) if owner and pair in plans else [0] * 25
                if len(words) != 25:
                    raise ValueError('native CFG length changed')
                payloads[pair].extend(words)
            active_pairs += len(plans) if owner else 0
            phase_sources.append(dict(phase=phase, matrix_sha256=hashlib.sha256(line.encode()).hexdigest(),
                                      layer=matrix['layer'], alias=matrix['alias'], rank_owner=owner))
            phase += 1
            if phase % 64 == 0:
                print(json.dumps(dict(stage=stage, source_phases_loaded=phase)), flush=True)
    if phase == 0:
        raise ValueError('provider-only stage has no FIELD CFG image')
    out.mkdir(parents=True, exist_ok=False)
    images = []
    for pair, words in enumerate(payloads):
        source = out / f'e{pair}.cfg.hex'
        source.write_text(''.join(f'{w:012x}\n' for w in words))
        binding = dict(stage=stage, rank=rank, pair=pair, cfg_sha256=file_sha(source),
                       canonical_sources=PINS, native_CFG_function_sha256=file_sha(cfg_source),
                       native_unit_range_source_sha256=file_sha(unit_source))
        record = emit(source, out / f'e{pair}.cfg7', phase_count=phase,
                      PHW=stage_map['PHW_required_by_stage'][stage], source_binding=binding)
        images.append(dict(pair=pair, source_cfg_sha256=binding['cfg_sha256'], images=record['images']))
        if pair % 128 == 0:
            print(json.dumps(dict(stage=stage, rank=rank, pairs_emitted=pair + 1)), flush=True)
    result = dict(stage=stage, rank=rank, phase_count=phase, pairs=2417, macros=16919,
                  all_pair_images=True, all_source_words_read_back=True,
                  source_pins=PINS, active_pair_phases=active_pairs, phase_sources=phase_sources,
                  images=images, arithmetic_qualified=False, calendar_qualified=False,
                  physical_qualified=False, native_execution_qualified=False)
    (out / 'stage_receipt.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(dict(stage=stage, pairs=2417, macros=16919, phase_count=phase)), flush=True)
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--base', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--stage', type=int, required=True)
    p.add_argument('--rank', type=int, required=True)
    a = p.parse_args()
    compile_stage(a.base, a.out, a.stage, a.rank)
