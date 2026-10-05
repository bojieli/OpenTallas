#!/usr/bin/env python3
"""Default-preserving arithmetic propagation contract; preparation never builds RTL."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = dict(ACC_LAT=5, TREE_LAT=3, MUL_LAT=5, FAST_ISSUE=0, KV_PREP=0)
TARGET = dict(ACC_LAT=7, TREE_LAT=7, MUL_LAT=6, FAST_ISSUE=1, KV_PREP=3)


def flags(enabled=False):
    # Omit flags on the default path, preserving the existing command contract.
    return [f'-G{name}={value}' for name, value in TARGET.items()] if enabled else []


def prepare():
    import uarch_model as U
    if Path(U.__file__).resolve() != (ROOT/'tools/uarch_model.py').resolve():
        raise ValueError('Model source belongs to another root')
    names = ['tools/uarch_model.py', 'tools/qwen_rom_rt_token_w12.py',
             'tools/qwen_rom_rt_core_emit_w12.py', 'tools/qwen_rom_arithmetic_contract_w12.py',
             'rtl/test/qwen_rom_runtime/ot_qwen_rom_rt_die_w12.sv',
             'rtl/hdc/ot_qwen_me_array_w12.sv', 'rtl/hdc/ot_qwen_rom_tile_w12.sv']
    pins = {n: hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in names}
    successor = U.qwen_rom_physical_successor(enabled=True) if hasattr(U, 'qwen_rom_physical_successor') else None
    model_joined = bool(successor and successor['model_price_joined'] and successor['selected_arithmetic_extra']==55)
    return dict(schema='opentallas.qwen-rom-arithmetic-contract.v1',
                at=datetime.datetime.now(datetime.timezone.utc).isoformat(), status='blocked',
                defaults=DEFAULTS, target=TARGET, default_flags=flags(), die_target_flags=flags(True), tile_target_flags=flags(True),
                source_sha256=pins, model_successor=successor, model_price_joined=model_joined,
                model_bridge_ref='f6507ec19f3016ebfa3e802af72b3ef1a83b98fc',
                preserved_fail_ref='65ffc747f28ae4a485b5ad3a94470240eddeaddf',
                blockers=['Source-current +55 model bridge and publisher re-pin required' if not model_joined else 'Analytical bridge ready; actual connected latency not qualified',
                          'Unified hub/fill track capacity, replica mux/fanout, slot fit, macro SS clk-to-q and service latency missing',
                          'Macro-local KV and complete current-source numerical token gate missing',
                          'SS setup/FF hold and contextual physical/routing/power closure missing'],
                physical_build_ready=False, adoption=False, heavy_jobs_launched=0,
                claim_boundary='Parameter propagation preparation only. Legacy commands/defaults retained; candidate execution deliberately blocked pending model/physical prerequisites.')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--result',type=Path,required=True)
    a=ap.parse_args()
    if a.result.exists():ap.error('Refusing to overwrite evidence')
    r=prepare();a.result.parent.mkdir(parents=True,exist_ok=True)
    with a.result.open('x') as f:json.dump(r,f,indent=2,sort_keys=True);f.write('\n')
    print(json.dumps(dict(status=r['status'],model_price_joined=r['model_price_joined'],physical_build_ready=False)))
    return 1


if __name__=='__main__':raise SystemExit(main())
