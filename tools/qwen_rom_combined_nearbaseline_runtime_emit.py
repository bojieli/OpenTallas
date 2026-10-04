#!/usr/bin/env python3
"""Initialized, single-layer host for the mandatory fenced nearHBM baseline.

All numerical execution, row responses and visibility fences remain in the
selected RTL. This host reuses raw images/history and the original transport.
"""
import argparse
import hashlib
import importlib.util
from pathlib import Path
import qwen_rom_combined_runtime_emit_initialized as initialized

ROOT = Path(__file__).resolve().parents[1]
ABI = 'combined-nearbaseline-layer-v1'
TOP = 'ot_qwen_rom_combined_nearbaseline_die'
FIXED_BASE_SHA = 'abc8a5cbb19e11664a1704d99a9e4480e92c88349c2bdbaf51ccb89defcc9632'


def emit(root=ROOT):
    # Main adopted 15778679a in the BASE host. Load an isolated copy of the
    # unchanged transform, pin the new BASE explicitly, then initialize all
    # added HBM models too. No canonical module/global guard is weakened.
    base = root/initialized.predecessor.BASE
    if hashlib.sha256(base.read_bytes()).hexdigest() != FIXED_BASE_SHA:
        raise ValueError('source-fixed 157 preload host changed')
    spec = importlib.util.spec_from_file_location('_nearbaseline_combined_transform',
                                                root/'tools/qwen_rom_combined_runtime_emit.py')
    transform = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(transform)
    transform.BASE_SHA = FIXED_BASE_SHA
    src = initialized.initialize_source(transform.emit(root))
    def replace(old, new):
        nonlocal src
        if src.count(old) != 1:
            raise ValueError('near runtime anchor missing/ambiguous: ' + old[:80])
        src = src.replace(old, new)
    replace('    DieMem mem[D];', '''    // Minimum-layer baseline: no implicit embedding/full-array run.
    if(stages.size()!=1 || stages[0].layer<0)
        fatal("near baseline requires exactly one decoder layer");
    if(POS<0 || POS>=8192 || kv_dir.empty())
        fatal("near baseline requires bounded position and actual KV history");
    DieMem mem[D];''')
    replace('    m.desc = as64(QwenHex::load(p + "/segments.hex", 2));', '''    m.desc = as64(QwenHex::load(p + "/segments.hex", 2));
    if(m.desc.empty() || (m.desc[0]&3)!=3 || (m.desc[0]>>62)!=0)
        fatal("mandatory near baseline requires actual descriptor3 image");''')
    replace('QWEN_ROM_COMBINED PASS stages=%zu', 'QWEN_ROM_NEARBASELINE PASS stages=%zu')
    # Existing layer fences read kv_arm_o, kv_layer_start_o, row_drained_o,
    # kv_drained_o and actual core/near fault aggregation. No host near READY.
    replace('            fflush(stdout);\n        }\n    }', '''            for(int d=0;d<D;++d)
                printf("NEARPORT die=%d active=%d row_drained=%d core_done=%d kv_arm=%d\\n",
                       d,int(die[d]->nhb_active_o),int(die[d]->row_drained_o),
                       int(die[d]->core_done_o),int(die[d]->kv_arm_o));
            fflush(stdout);
        }
    }''')
    return '// NEARBASELINE_ABI '+ABI+'; selected top '+TOP+'\n'+src


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    with args.out.open('x') as stream:
        stream.write(emit())
