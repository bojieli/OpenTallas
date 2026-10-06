#!/usr/bin/env python3
"""Assemble measured attention heads inside the selected outer die, without fake blocks.

prepare is lightweight. OpenROAD Python assembly reads only measured head geometry;
all other existing allocations remain routing obstructions. This checkpoint is an
outer placement/interconnect cut, not child hardening or a complete die route.
Routing requires real source/receiver pin locations for every cut net.
"""
import hashlib
import json
import math
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'physical/hbm_outer_revision_20261005'
LEAF = 'physical/hbm_fmax_attn/ot_attn_hgrp_m6h1/ot_attn_hgrp_m6h1.lef'


def prepare():
    import hbm_accel_die_fp as F
    from uarch_model import hbm_existing_attention_source_cut_model
    m = F.build(F.variant_arg('service-attn-r1'))
    model = hbm_existing_attention_source_cut_model()
    text = (ROOT / LEAF).read_text()
    width, height = map(float, re.search(r'SIZE (\S+) BY (\S+) ;', text).groups())
    assert (width, height) == (294.782, 294.782)
    heads = []
    min_gap = float('inf')
    for k, tile in enumerate(m['tiles']):
        axes = []
        for origin, extent, size, grid in [(tile.x, tile.w, width, F.GX),
                                            (tile.y, tile.h, height, F.GY)]:
            lo = F.up(origin + 5, grid)
            hi = F.dn(origin + extent - size - 5, grid)
            positions = [lo, F.dn(lo+(hi-lo)/3, grid), F.dn(lo+2*(hi-lo)/3, grid), hi]
            assert all(positions[i+1]-positions[i] > size+10 for i in range(3))
            min_gap = min(min_gap, min(positions[i+1]-positions[i]-size-10 for i in range(3)))
            axes.append(positions)
        for h in range(16):
            x, y = axes[0][h % 4], axes[1][h // 4]
            assert tile.x+5 <= x and x+width+5 <= tile.x+tile.w+1e-7
            assert tile.y+5 <= y and y+height+5 <= tile.y+tile.h+1e-7
            heads.append(dict(name=f'g_t[{k}].g_ts.u_t.g_g[{h}].u_g',
                              tile=k, slot=k % 16, head=h, allocation=tile.name,
                              xy_um=[x, y], orientation='R0'))
    claims = [dict(name=i.name, master=i.master, kind=i.kind,
                   bbox_um=[i.x, i.y, i.x+i.w, i.y+i.h])
              for i in m['insts'] if i.kind != 'attn_tile']
    assert len(heads) == 1024 and len(claims) == 317
    row_pitch = width+10+min_gap
    row_tracks = math.floor(row_pitch/.08*(1-.1756-.05))-64
    assert row_tracks > 1618+4*34
    spans = []
    for slot in range(16):
        group = [h for h in heads if h['slot'] == slot]
        xs = [h['xy_um'][0] for h in group]; ys = [h['xy_um'][1] for h in group]
        span = max(xs)-min(xs)+max(ys)-min(ys)
        spans.append(dict(slot=slot, actual_macro_origin_span_um=span,
                          source_independent_diameter_wire_stages=math.ceil(span/430.56),
                          added_RTL_cycles=0, clock_qualified=False))
    sources = [LEAF, 'tools/hbm_accel_die_fp.py', 'tools/uarch_model.py',
               'tools/hbm_outer_die_context.py', 'rtl/hdc/v41x/ot_hdc_v41x_attn_s.sv',
               'physical/hbm_fmax_attn_context/ot_attn_tile_m6h1.sv',
               'results/rtl/hbm_child_contract_20261005/child_reservations.json']
    plan = dict(schema='opentallas.existing-outer-real-head-cut.v1',
                die_um=[m['geo']['W'], m['geo']['H']], variant=m['variant'],
                leaf=LEAF, heads=heads, retained_claims=claims, source_model=model,
                head_halo_um=5, minimum_channel_between_halos_um=min_gap,
                actual_row_upper_tracks_after_PG_via_clock_reserve=row_tracks,
                actual_row_upper_track_demand=1618+4*34,
                LD_source_independent_sink_spans=spans,
                actual_driver_to_sink_wire_prices_pending=True,
                native_layer_pitch_um=.064, native_upper_pitch_um=.08,
                PG_removed_fraction=.1756, via_removed_fraction=.05,
                added_transport_RTL_cycles=0, physical_qualified=False,
                full_outer_route_ready=False,
                missing_for_cut_route=['source/receiver pin map of the actual E/mux and golden reduction',
                    'physical clk_sm launch/reset root pins; propagated CTS and input-hold context'],
                missing_for_full_outer=['Harvey CP+association routed LEF/SS/FF',
                    'Jason W2 routed LEF/SS/FF', 'full SM/service/SU/index/spine codec-to-real-abstract bindings'],
                existing_proxy_attention_ports_rejected=['k', 'q', 'iu', 'id', 'i', 'o'],
                source_sha256={s: hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in sources})
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'layout.json').write_text(json.dumps(plan, indent=2)+'\n')
    print(json.dumps({k: plan[k] for k in ('die_um', 'minimum_channel_between_halos_um',
                                          'full_outer_route_ready', 'missing_for_cut_route')}))


def assemble():
    import odb
    from openroad import Design, Tech
    work = Path(os.environ.get('OT_OUTER_WORK', '/work'))
    plan = json.loads((work/'layout.json').read_text())
    for rel, digest in plan['source_sha256'].items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest() == digest, rel
    tech = Tech()
    design = Design(tech)
    plat = '/OpenROAD-flow-scripts/flow/platforms/asap7'
    tech.readLef(plat+'/lef/asap7_tech_1x_201209.lef')
    tech.readLef(plat+'/lef/asap7sc7p5t_28_R_1x_220121a.lef')
    tech.readLef(str(ROOT/plan['leaf']))
    db = design.getDb()
    chip = odb.dbChip_create(db, db.getTech())
    block = odb.dbBlock_create(chip, 'hbm_existing_outer_attention_cut')
    block.setDefUnits(1000)
    dbu = db.getTech().getDbUnitsPerMicron()
    def coord(x): return round(x*dbu)
    block.setDieArea(odb.Rect(0, 0, *[coord(x) for x in plan['die_um']]))
    design.evalTclString('set_thread_count 24')
    design.evalTclString('source '+plat+'/openRoad/make_tracks.tcl')
    design.evalTclString('set_routing_layers -signal M2-M9')
    nets = {}
    def net(name):
        if name not in nets: nets[name] = odb.dbNet_create(block, name)
        return nets[name]
    pg = {name: net(name) for name in ('VDD', 'VSS')}
    for n in pg.values(): n.setSigType('POWER' if n.getName() == 'VDD' else 'GROUND')
    master = db.findMaster('ot_attn_hgrp_m6h1')
    assert master and master.getWidth() == coord(294.782)
    leaf_ports = {p.getName() for p in master.getMTerms()}
    assert len(leaf_ports) == 1664
    cut = {}
    def cut_net(name, direction):
        n = net(name)
        if name not in cut:
            b = odb.dbBTerm_create(n, name)
            b.setIoType(direction)
            cut[name] = b
        return n
    for spec in plan['heads']:
        k, h, slot = spec['tile'], spec['head'], spec['slot']
        inst = odb.dbInst_create(block, master, spec['name'])
        inst.setOrient('R0')
        inst.setLocation(*[coord(v) for v in spec['xy_um']])
        inst.setPlacementStatus('FIRM')
        ties = {}
        for value, cell, pin in [(0, 'TIELOx1_ASAP7_75t_R', 'L'),
                                  (1, 'TIEHIx1_ASAP7_75t_R', 'H')]:
            tie_master = db.findMaster(cell)
            assert tie_master and tie_master.getHeight() <= coord(2.16)
            tie = odb.dbInst_create(block, tie_master, spec['name']+f'_gid{value}')
            tie.setLocation(coord(spec['xy_um'][0])+value*tie_master.getWidth(),
                            coord(spec['xy_um'][1])-tie_master.getHeight())
            tie.setPlacementStatus('FIRM')
            ties[value] = net(spec['name']+f'_gid{value}')
            tie.findITerm(pin).connect(ties[value])
            for p in ('VDD', 'VSS'): tie.findITerm(p).connect(pg[p])
        for it in inst.getITerms():
            p = it.getMTerm().getName()
            if p in pg: n = pg[p]
            elif p.startswith('gid['): n = ties[(h >> int(p[4:-1])) & 1]
            elif p.startswith('ld_w['): n = cut_net(f'e_ldw_sl{slot}[{p[5:-1]}]', 'INPUT')
            elif p.startswith('ib['): n = cut_net(f'e_ib_tile{k}[{p[3:-1]}]', 'INPUT')
            elif p.startswith('oy['): n = cut_net(f't_y[{k*512+h*32+int(p[3:-1])}]', 'OUTPUT')
            elif p.startswith('oflt['): n = cut_net(f't_f[{k*16+h}]', 'OUTPUT')
            elif p == 'ov': n = cut_net(f't_ov[{k}]', 'OUTPUT') if h == 0 else net(f'unused_gov[{k*16+h}]')
            else: n = cut_net('clk_sm' if p == 'clk' else 'rst_sm_n' if p == 'rst_n' else 'e_'+p, 'INPUT')
            it.connect(n)
    # Actual other allocations remain occupied. These are not functional macro substitutes.
    for claim in plan['retained_claims']:
        for layer in ('M1', 'M2', 'M3', 'M4', 'M5', 'M6', 'M7'):
            odb.dbObstruction_create(block, db.getTech().findLayer(layer),
                                     *[coord(v) for v in claim['bbox_um']])
    assert len(cut) == 53266+2+33856, len(cut)
    assert len(block.getInsts()) == 3072
    # Do not run GRT with unplaced external cut pins or a made-up source/receiver.
    odb.write_db(db, str(work/'outer_real_heads.odb'))
    result = dict(instances=len(block.getInsts()), real_heads=1024, real_tie_cells=2048,
                  nets=len(nets), cut_ports=len(cut), source_cut_pin_map_ready=False,
                  native_gcell_um=block.getGCellTileSize()/dbu,
                  physical_qualified=False, GRT_run=False,
                  scope='existing 607.03mm2 outer assembly; other allocations retained as routing obstructions')
    (work/'assembly.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result))


if __name__ == '__main__':
    if os.environ.get('OT_OUTER_ASSEMBLE') == '1': assemble()
    else: prepare()
