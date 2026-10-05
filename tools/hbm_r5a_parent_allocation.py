#!/usr/bin/env python3
"""Finite R5a successor reservation in the existing HBM die; no child RTL/route."""
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUEST = 'results/uarch/hbm_r5a_protected_successor_20261005/model.json'


def intersects(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def allocate(m):
    """Called before parent waypoint placement; occupied old slots are preserved."""
    req = json.loads((ROOT/REQUEST).read_text())
    assert req['shape']['macro_count'] == 96
    assert req['area']['requested_outline_um'] == [2000.16, 2000.16]
    # 8.64um is a common native M1..M9/site translation quantum.
    source = 'rtl/hbm_accel/service/ot_hbm_accel_expert_fetch_p2.sv'
    # Actual full-shape source boundary, including configuration and commands.
    ports = dict(clk=1,hclk=1,rst_n=1,hrst_n=1,cfg_lines=128,cfg_lut=6272,
                 e_valid=1,e_code=72,e_ready=1,notice=1,row_v=32,col_v=32,
                 row_op=96,row_bank=160,col_bank=160,col_col=160,row_row=608,
                 rd_v=32,rd_code=11520,s_valid=8,s_ready=8,s_data=8192,fault=1)
    actual_demand = sum(ports.values())
    assert actual_demand == 27488
    # Smallest native-common-grid band meeting EVERY real boundary pin.
    child = 2000.16
    def capacity(width):
        return sum(math.floor(width/p)-math.ceil(math.floor(width/p)*pg)
                   -math.ceil(math.floor(width/p)*.05)-64
                   for p,pg in [(.064,0),(.064,0),(.08,.3278),(.08,.3278)])
    band = 2600.64
    while capacity(band-child) < actual_demand:
        band = round(band+8.64,2)
    channel = round(band-child,2)
    old_w, height = m['geo']['W'], m['geo']['H']
    new_w = old_w+2*band
    assert new_w <= 33000 and height <= 26000
    east_boundary = old_w-m['variant'].get('strip_d', 864.0)-20
    moved_east = []
    for inst in m['insts']:
        old_x = inst.x
        inst.x += band
        if old_x >= east_boundary-1e-6:
            inst.x += band
            moved_east.append(inst.name)
    for group in m['groups'].values():
        group['x'] += band
    for key in ('x0', 'cx'):
        m['geo'][key] += band
    m['geo']['W'] = new_w
    m['variant'].update(W=new_w, H=height)
    for region in m['regions']:
        a,b,c,d = region['rect']
        dx = 2*band if region['name']=='strip_E' else band
        region['rect'] = [a+dx,b,c+dx,d]
    allocations = []
    for name, group in m['groups'].items():
        east = group['half']=='E'
        y = group['svc'].y if group['side']=='S' else group['svc'].y+group['svc'].h-child
        # Align to native placement rows without changing the child dimensions.
        y = math.ceil(y/2.16)*2.16
        if east:
            left = east_boundary+band
            core = [left+channel,y,left+channel+child,y+child]
            corridor = [left,y,left+channel,y+child]
        else:
            core = [0,y,child,y+child]
            corridor = [child,y,band,y+child]
        # Keep an actual edge setback while retaining the same 600.48um width.
        # West child stays 20um from the reticle edge; the child+channel remains
        # within the widened band plus the existing empty west-edge margin.
        if not east:
            core = [v+25.92 if i%2==0 else v for i,v in enumerate(core)]
            corridor = [v+25.92 if i%2==0 else v for i,v in enumerate(corridor)]
        for rect in (core, corridor):
            assert 0 <= rect[0] < rect[2] <= new_w
            assert 0 <= rect[1] < rect[3] <= height
            assert not any(intersects(rect, i.box()) for i in m['insts']), (name,rect)
        # Fresh extended-sideband capacity; no old trunk or PG is released.
        layers = []
        for layer, pitch, pg in [('M6',.064,0),('M7',.064,0),
                                  ('M8',.08,2*.1639),('M9',.08,2*.1639)]:
            raw = math.floor(channel/pitch)
            pg_tracks = math.ceil(raw*pg)
            via_tracks = math.ceil(raw*.05)
            remaining = raw-pg_tracks-via_tracks-64
            layers.append(dict(layer=layer,pitch_um=pitch,raw_tracks=raw,
                               retained_PG_tracks=pg_tracks,via_tracks=via_tracks,
                               clock_other_tracks=64,available_tracks=remaining))
        available = sum(x['available_tracks'] for x in layers)
        assert available >= actual_demand
        # Bounds for new links, not measured lengths or installed pipelines.
        endpoints = [group['phy'], group['svc'], *group['sms']]
        lengths = {}
        for endpoint in endpoints:
            a,b,c,d = endpoint.box()
            length = max(abs(x-u)+abs(y0-v)
                         for x in (core[0],core[2]) for y0 in (core[1],core[3])
                         for u in (a,c) for v in (b,d))
            lengths[endpoint.name] = dict(rectilinear_envelope_um=length,
                        wire_stage_bound=math.ceil(length/430.56),
                        source_receiver_pin_load_measured=False)
        allocations.append(dict(name='r5a_'+name,core_bbox_um=core,
                       local_channel_bbox_um=corridor,element_count=1,macro_count=96,
                       body_cell_ceiling_um2=req['area']['standard_cell_upper_um2'],
                       SRAM_body_um2=req['area']['macro_area_um2'],
                       channel_layers=layers,channel_demand=actual_demand,
                       available_tracks=available,residual_tracks=available-actual_demand,
                       competing_reserved_local_signal_tracks=0,
                       exclusive_new_sideband_reservation=True,
                       source_to_existing_endpoint_envelopes=lengths,
                       signal_pin_names_and_actual_loads_ready=False))
    rects = [r[k] for r in allocations for k in ('core_bbox_um','local_channel_bbox_um')]
    assert all(not intersects(a,b) for i,a in enumerate(rects) for b in rects[i+1:])
    m['reserved_regions'] = rects
    max_stages = max(x['wire_stage_bound'] for a in allocations
                     for x in a['source_to_existing_endpoint_envelopes'].values())
    # Expose a deliberately conservative serial one-request/one-response price
    # until the caller's actual source/sink pin map and route determine the cuts.
    extra_roundtrip_cycles = 2*max_stages
    record = dict(schema='opentallas.existing-hbm-r5a-finite-allocation.v1',
                  baseline_outline_um=[old_w,height],outline_um=[new_w,height],
                  actual_source=source,actual_source_sha256=hashlib.sha256((ROOT/source).read_bytes()).hexdigest(),
                  actual_fullshape_port_bits=ports,actual_boundary_pin_tracks=actual_demand,
                  earlier_600p48_channel_rejected_for_actual_configuration_and_command_ports=True,
                  baseline_area_mm2=old_w*height/1e6,area_mm2=new_w*height/1e6,
                  extra_die_area_mm2=(new_w-old_w)*height/1e6,
                  reticle_margin_mm2=858-new_w*height/1e6,
                  old_logic_translation_x_um=band,
                  existing_east_boundary_blocks_relocated=moved_east,
                  existing_claims_released=0,allocations=allocations,
                  SRAM_macro_replicas_per_die=384,replicas_per_die=4,
                  request=REQUEST,request_sha256=hashlib.sha256((ROOT/REQUEST).read_bytes()).hexdigest(),
                  child_successor_latency=req['latency'],
                  conservative_parent_roundtrip_wire_cycles=extra_roundtrip_cycles,
                  conservative_DS40_fetch_wire_us=40*extra_roundtrip_cycles/1.2/1000,
                  transport_registers_installed=False,
                  clk_sm_period_ps=833.333333333,hclk_period_ps=1024,
                  setup_uncertainty_ps=60,hold_uncertainty_ps=25,
                  actual_clock_source_phase_insertion_and_IO_loads_ready=False,
                  ready_hardened_abstract=False,physical_admitted=False,adopted=False,
                  previous_e11b_failure_preserved=True)
    m['r5a_reservations'] = record
    return record


def export():
    import hbm_accel_die_fp as F
    base = F.variant_arg('service-attn-r1')
    candidate = dict(base, r5a_sidebands=True)
    m = F.build(candidate)
    record = m['r5a_reservations']
    import contextlib
    import io
    import hbm_accel_die_price as P
    with contextlib.redirect_stdout(io.StringIO()):
        baseline_price = P.floor(F.build(F.variant_arg('service-attn-r1')))
        revised_price = P.floor(m)
    delta = revised_price['ds_added_us']-baseline_price['ds_added_us']
    record['retained_bus_geometry_reprice'] = dict(baseline=baseline_price,
        revised=revised_price,DS_existing_bus_delta_us=delta,
        basis='Analytical minimum Manhattan path stages; not actual route or inserted RTL')
    record['remaining_old_measured_gain_us_after_conservative_parent_and_child_charge'] = (
        13.343-record['conservative_DS40_fetch_wire_us']-
        record['child_successor_latency']['DS_token_added_us_upper']-max(0,delta))
    record['analytical_existing_instance_legality'] = F.legality(m)
    assert record['analytical_existing_instance_legality']['overlaps']==0
    assert record['analytical_existing_instance_legality']['outside']==0
    out = ROOT/'results/uarch/hbm_r5a_finite_parent_20261005'
    out.mkdir(parents=True,exist_ok=True)
    (out/'model.json').write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps({k:record[k] for k in ('outline_um','area_mm2','extra_die_area_mm2',
                        'reticle_margin_mm2','conservative_DS40_fetch_wire_us')}))


if __name__=='__main__': export()
