#!/usr/bin/env python3
"""HA9 area sensitivities; no timing, route, or macro-selection qualification.

HA2 supplies replacement fabric inventory; HA8 supplies bank/port selection.
Existing comparator files and the unified model remain unchanged.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = 'physical/asap7_memory_macros/index.json'
STUDY = 'results/uarch/hbm_accelerator_study_20261003/ladder_model.py'
COMPARATOR = 'tools/hbm_gpu_floorplan.py'
MACROS = ('ot_sram_1r1w_128x256_m1_r2c2',
          'ot_sram_1r1w_1024x256_m2_r2c2')


def positive(value):
    if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
        raise ValueError('finite positive source quantity required')
    return value


def sram_tile(macro, total_bytes, dies, packing):
    positive(total_bytes); positive(dies); positive(packing)
    if type(total_bytes) is not int or type(dies) is not int or packing < 1:
        raise ValueError('integer die count and packing >= 1 required')
    bits = macro['capacity_bits']
    count = math.ceil(total_bytes * 8 / dies / bits)
    w, h = macro['width_um'], macro['height_um']
    # A rectangular hierarchical tile envelope, with unused last-row slots.
    cols = max(1, math.ceil(math.sqrt(count*h/w)))
    rows = math.ceil(count/cols)
    raw = count*w*h/1e6
    scale = math.sqrt(packing)
    return dict(macros_per_die=count, capacity_bytes_per_die=count*bits//8,
                raw_macro_mm2_per_die=raw, packed_area_mm2_per_die=raw*packing,
                abstract_width_um=cols*w*scale, abstract_height_um=rows*h*scale,
                abstract_area_mm2_per_die=cols*rows*w*h*packing/1e6,
                columns=cols, rows=rows, packing_factor_assumed=packing,
                macro_ports=macro['spec']['ports'],
                macro_SS_clk_to_q_ps=macro['clk_to_q_ps']['ss'],
                TT_read_energy_fJ_per_macro_access=macro['read_energy_fj_tt'],
                qualification=False)


def replacement_die(ports, per_port_mm2, additional_service_mm2):
    if type(ports) is not int: raise ValueError('literal port count required')
    positive(ports); positive(per_port_mm2)
    if not math.isfinite(additional_service_mm2) or additional_service_mm2 < 0:
        raise ValueError('nonnegative incremental service area required')
    # 340.5 contains the historical 18 mm2 fabric allocation. Replace it once.
    return 340.5 - 18 + ports*per_port_mm2 + additional_service_mm2


def report(root=ROOT, ha2=None):
    catalog = json.loads((root/INDEX).read_text())['macros']
    inputs = {p: hashlib.sha256((root/p).read_bytes()).hexdigest()
              for p in (INDEX, STUDY, COMPARATOR)}
    for name in MACROS:
        view = f'physical/asap7_memory_macros/{name}/{name}.lef'
        digest = hashlib.sha256((root/view).read_bytes()).hexdigest()
        if digest != catalog[name]['views'][name+'.lef']:
            raise ValueError('selected macro LEF differs from catalog')
        inputs[view] = digest
    qwen = []
    for dies, mib, stacks in ((2,842,8),(4,1684,16)):
        alternatives = []
        for name in MACROS:
            for factor in (1,1.31):
                tile = sram_tile(catalog[name], mib*(1<<20), dies, factor)
                tile.update(macro=name, dies=dies, total_residency_MiB=mib,
                            logic_area_mm2=265.8*dies+tile['abstract_area_mm2_per_die']*dies)
                # DRAM range is the study's assumption, not a measured HBM die.
                tile['total_silicon_mm2_assumed_DRAM_range'] = [
                    tile['logic_area_mm2']+stacks*x for x in (900,1450)]
                alternatives.append(tile)
        qwen.append(dict(dies=dies, stacks=stacks, alternatives=alternatives,
                         selected_macro=None, port_fit=None))
    ds = dict(planned_die_mm2=340.5, planned_ports=20,
              historical_fabric_reservation_mm2=18,
              existing_HBM_service_band_mm2=48*0.63072,
              HBM_service_band_basis='Comparator 48mm total frontage x 630.72um; already in base, not incremental',
              service_geometry_fit=None, replacement_die_mm2=None)
    if ha2 is not None:
        ds['HA2_inventory'] = ha2
        ds['replacement_die_mm2'] = replacement_die(
            ha2['ports'],ha2['per_port_mm2'],ha2['additional_service_mm2'])
        ds['logic_area_mm2'] = 96*ds['replacement_die_mm2']
        ds['total_silicon_mm2_assumed_DRAM_range'] = [
            ds['logic_area_mm2']+384*x for x in (900,1450)]
    return dict(schema='HA9_ABSTRACT_SIZING_V1',status='MODEL_ONLY_NOT_QUALIFIED',
                input_sha256=inputs,DS=ds,Qwen=qwen,
                physical_launch_allowed=False,
                missing_owner_inputs=['HA2 lanes/frontage/wires/power and physical abstract',
                                     'HA8 bank/port/concurrency selection and channel/halo budget'],
                service_area_note='No controller area shrink or fabric latency gain claimed from this area calculation',
                abstract_note='SRAM rectangular envelopes only; 1.31 is study packing sensitivity, not routed halo or channel closure',
                latency_cycles_added=0,
                latency_note='Area alternatives only; no pipeline or model-rate change',
                SS_FF_qualified=False, PDN_qualified=False, fulltoken_qualified=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--ha2',type=Path)
    args=parser.parse_args()
    result=report(ha2=json.loads(args.ha2.read_text()) if args.ha2 else None)
    if args.ha2:
        result['input_sha256'][str(args.ha2)] = hashlib.sha256(args.ha2.read_bytes()).hexdigest()
    with args.out.open('x') as stream:
        json.dump(result,stream,indent=2,sort_keys=True); stream.write('\n')


if __name__=='__main__': main()
