#!/usr/bin/env python3
"""Join full mapped enabled cone to Archimedes's source-matched pin/OBS context.

Review only: no new engine, P&R, clock/cycle adoption or numerical promotion.
"""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import uarch_model as U

ROOT=Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def join(mapped,context):
    if Path(U.__file__).resolve()!=ROOT/'tools/uarch_model.py':raise ValueError('Wrong unified model root')
    model=U.qwen_rom_enabled_capture_mapped_review(mapped,enabled=True)
    origin=json.loads((context/'origin.json').read_text())
    for name,digest in origin['sha256'].items():
        if sha(context/name)!=digest:raise ValueError('Context snapshot changed: '+name)
    receipt=json.loads((context/'input_receipt.json').read_text())
    for name,item in receipt['inputs'].items():
        if sha(context/'inputs'/name)!=item['sha256']:raise ValueError('Context input changed: '+name)
    for name in ['tile.sv','ROM.lef','SRAM.lef']:
        item=receipt['inputs'][name]
        if sha(ROOT/item['path'])!=item['sha256']:raise ValueError('Current physical source differs: '+name)
    physical=json.loads((context/'model.json').read_text())
    if physical['enabled_cones']['source_sha256']!=mapped['source_sha256']['rtl/hdc/ot_qwen_rom_tile_w12.sv']:
        raise ValueError('Enabled-cone source mismatch')
    if physical['timing_budget']['period_ps']!=mapped['period_ps'] or physical['timing_budget']['SS_setup_uncertainty_ps']!=60 or physical['timing_budget']['FF_hold_uncertainty_ps']!=25:
        raise ValueError('Physical clock constraints differ')
    rom=physical['enabled_cones']['ROM']
    if rom['capture_bits']!=model['capture_register_bits'] or rom['bank_enable_capture_loads']!=512:
        raise ValueError('Physical capture dimensions differ')
    cfg=physical['target_configuration']
    if (cfg['G'],cfg['CODE_BANKS'],cfg['MEM_EXTRA'])!=(6144,5,1):raise ValueError('Physical target configuration differs')
    placements=json.loads((context/'macro_collar_placement.json').read_text())
    rom_placements=[p for p in placements if p['master']=='ROM']
    net_instances={f'g_col[{p}].g_bank[{b}].u_rom' for p in range(2) for b in range(5)}
    if {p['instance'] for p in rom_placements}!=net_instances:raise ValueError('Physical macro geometry differs')
    shapes=json.loads(gzip.decompress((context/'translated_pin_OBS.json.gz').read_bytes()))
    pg=sum(s['kind']=='pins' and s.get('use') in ['POWER','GROUND'] for s in shapes)
    if pg!=physical['macro_context']['PG_pin_shapes']:raise ValueError('Lost PG shapes')
    # Every current instance keeps signal, PG and OBS shapes. No routing credit.
    for name in net_instances:
        own=[s for s in shapes if s['instance']==name]
        if not any(s['kind']=='OBS' for s in own) or not any(s.get('use')=='POWER' for s in own) or not any(s.get('use')=='GROUND' for s in own):
            raise ValueError('Incomplete physical context: '+name)
    return dict(schema='opentallas.qwen-rom-enabled-capture-joined-review.v1',
        status='BLOCKED_ENABLED_CAPTURE_AND_ROUTED_CONTEXT',unified_model_review=model,
        archimedes_commit=origin['commit'],physical_source_main_pin=physical['source_main_pin'],
        source_matched_macro_collar_context=physical['macro_context'],
        physical_target_configuration=cfg,ROM_placement_instance_names=sorted(net_instances),
        context_origin_sha256=sha(context/'origin.json'),
        pin_load_scope='Mapped SS library input-pin capacitance only; not extracted pin+wire capacitance.',
        skew_scope='Ideal clock. Neither actual relative insertion nor FF contextual hold is available.',
        timing_rejection='Negative SS setup plus capacitance/slew limit violations. Extrapolated delays identify failure; they do not calibrate a slower frequency.',
        no_transfer_from_ideal_capture=True,full_tile_fit=False,PG_connectivity=False,
        model_added_cycles=0,existing_MEM_EXTRA_charged_once=True,successor_55_bridge_adopted=False,
        next_source_decision='Model and exactness review a capture-data/hold-feedback repair and sized control buffers. No replacement RTL is implemented in this packet.',
        owners=dict(Euclid='Source capture repair and source-bound exactness gate preparation.',
                    Maxwell='Whole-program +55 MLAT/tree/MUL and any added-cycle/clock/control-buffer pricing review.',
                    Archimedes='Current full-tile outline/placement, pins/OBS/PG connections, RC and actual clock skew; contextual SS/FF.'),
        physical_build_ready=False,heavy_jobs_launched=0,live_Qwen_job_handle=None,
        second_position_queued=False,adoption=False)


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--mapped',type=Path,required=True);ap.add_argument('--context',type=Path,required=True);ap.add_argument('--output',type=Path,required=True);a=ap.parse_args()
    if a.output.exists():raise ValueError('Refusing to overwrite review')
    record=join(json.loads(a.mapped.read_text()),a.context)
    record['mapped_record_sha256']=sha(a.mapped)
    record['review_tool_sha256']=sha(Path(__file__))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    with a.output.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    print(record['status']);return 0


if __name__=='__main__':raise SystemExit(main())
