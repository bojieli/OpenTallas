#!/usr/bin/env python3
"""Capacity and 100us necessary service envelope; no qualified physical ceiling."""
import hashlib
import json
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]


def capacity(area, weight_bytes, density, reserve=.02):
    required = weight_bytes / (density * (1-reserve))
    return {'available_area_mm2': area, 'rom_area_required_mm2': required,
            'area_left_before_compute_sram_fabric_mm2': area-required,
            'capacity_fits_with_all_area_available': required <= area,
            'minimum_devices_if_entire_area_were_rom': math.ceil(required/area)}


def main():
    names = ['configs/models/candidates/deepseek-v4.1-flash.json',
             'configs/models/candidates/deepseek-v4.1-flash-engram_hbm.json',
             'configs/architecture/rom_hbm_review_v3.json',
             'results/architecture/v41_architecture_feasibility.json',
             'tools/audit_v41_physical_envelope.py']
    m,h,c,a = [json.loads((ROOT/p).read_text()) for p in names[:4]]
    density = c['rom_bytes_per_mm2_assumed']
    areas = {'reticle_815mm2':815, 'wafer_300mm_max_inscribed_square':45000,
             'wafer_60000mm2_hypothetical_usable':60000,
             'wafer_300mm_gross_disk_upper_bound':math.pi*150**2}
    screens = {name:{placement:capacity(area,model['checkpoint_bytes'],density)
                    for placement,model in [('all_rom',m),('engram_elsewhere',h)]}
               for name,area in areas.items()}
    active = a['contexts'][1]['weight_bytes']
    routed = m['routed_weight_bytes']*m['experts_per_token']//m['num_experts']
    out = {'schema':'opentallas.v41-physical-envelope.v1',
           'status':'100us_target_restored_capacity_screen_only_physical_performance_unqualified',
           'target_token_us':100, 'assumed_rom_bytes_per_mm2':density,
           'rom_reserve_fraction':.02, 'capacity_screens':screens,
           'necessary_service_using_entire_100us':{
               'all_active_weight_TB_s':active/1e8,
               'routed_weight_TB_s':routed/1e8,
               'tensor_TOP_s_at_200k':a['contexts'][1]['tensor_operations']/1e8,
               'kv_read_TB_s_at_200k':a['contexts'][1]['kv_read_bytes']/1e8,
               'kv_read_TB_s_at_1m':a['contexts'][2]['kv_read_bytes']/1e8,
               'hbm_4_5TB_s_endpoints_uncached_weights':math.ceil(active/1e8/4.5),
               'hbm_4_5TB_s_endpoints_dense_fully_cached':math.ceil(routed/1e8/4.5)},
           'limits':[
               'ROM density is a planning assumption, not a characterized wide-port macro. Capacity rejects configurations but cannot certify speed.',
               '815mm2 is the repository planning die area. Reticle field dimensions and process edge exclusions need qualification.',
               '45000mm2 is the largest square inside an ideal 300mm disk, without exclusion margin; 60000mm2 usable area is a hypothetical irregular wafer layout, not an available implementation.',
               'Gross disk area cannot all become functional circuitry. Streets, edges, repair, yield and fabric topology reduce usable area.',
               'External Engram capacity and service remain charged separately in hybrid placement.',
               '100us rates use the full token interval for each category; they are necessary average service demands, not additive allocations or sufficient performance.',
               'HBM endpoint counts assume independent delivered service to the active token, not capacity-only inactive endpoints.',
               'No justified numeric physical tokens/s ceiling exists without macro read timing, compute area, topology/latency and power/cooling constraints.'],
           'input_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in names}}
    (ROOT/'results/architecture/v41_physical_envelope.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
    print(json.dumps(out,indent=2))


if __name__ == '__main__':
    main()
