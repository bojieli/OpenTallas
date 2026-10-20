#!/usr/bin/env python3
"""Pre-layout model for MC3c's literal-lattice physical successor.

This is a planning artifact, never a substitute for native placed-pin census.
The functional HBM clock remains 1024 ps; 833.333 ps is a conservative logic
mapping/signoff target until production clock/phase integration is qualified.
"""
import hashlib
import itertools
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/rtl/hbm_ds_layer_tput_1018/hbm_bw_safe_1019/mc3c/v6_lattice_plan'
NAME = 'hdie_pc_ctrl_mc3c6_p540'
W = H = 388.8
MW, MH = 33.696, 27.540
CX, CY = 189.648, 208.17
COLS = [43.2, 129.6, 216.0, 302.4]
RECT_DIMS = [(74, 91), (94, 74), (114, 54), (134, 34), (154, 14)]


def corners(b):
    return itertools.product((b[0], b[2]), (b[1], b[3]))


def distance(a, b):
    return max(abs(x-u)+abs(y-v) for x,y in corners(a) for u,v in corners(b))


def union_area(boxes):
    ys = sorted({y for b in boxes for y in (b[1], b[3])})
    area = 0
    for lo, hi in zip(ys, ys[1:]):
        xs = sorted((b[0], b[2]) for b in boxes if b[1] <= lo and b[3] >= hi)
        end = None
        for left, right in xs:
            area += max(0, right-max(left, end if end is not None else left))*(hi-lo)
            end = max(right, end if end is not None else right)
    return area


def main():
    OUT.mkdir(exist_ok=True)
    spec_path = ROOT / f'physical/ref_tile/{NAME}/spec.json'
    spec = json.loads(spec_path.read_text())
    placed = []
    def add(inst, col, row, role):
        placed.append(dict(inst=inst, at=[COLS[col], row], orient='R0', role=role,
                           bbox=[COLS[col],row,COLS[col]+MW,row+MH]))
    for i in range(4):
        add(f'u_native.g_wpay.u_write_payload.M[{i}].P.u_m',i,43.2,'write_payload')
        add(f'u_native.u_response_payload.M[{i}].P.u_m',i,86.4,'response_payload')
        add(f'u_native.METADATA[{i}].u_head.M[0].P.u_m',i,129.6,'head_metadata')
    add('u_native.controller.u_queue.M[0].P.u_m',0,259.2,'queue')
    add('u_native.u_pending_identity.M[0].P.u_m',1,259.2,'pending_identity')
    add('u_native.u_response_identity.M[0].P.u_m',2,259.2,'response_identity')
    positions = [(3,259.2)]+[(i,302.4) for i in range(4)]+[(i,345.6) for i in range(3)]
    for n,(col,row) in enumerate(positions):
        add(f'u_native.METADATA[{n//2}].u_post.M[{n%2}].P.u_m',col,row,'post_metadata')
    regions = [[CX-w/2,CY-h/2,CX+w/2,CY+h/2] for w,h in RECT_DIMS]
    assert len(placed) == 23
    assert all(abs(v/43.2-round(v/43.2)) < 1e-8 for m in placed for v in m['at'])
    reach = max(distance(r,m['bbox']) for r in regions for m in placed)
    assert reach <= 405
    assert all(r[1] >= 157.14+5.4 and r[3] <= 259.2-5.4 for r in regions)
    area = union_area(regions)
    lef = ROOT / 'physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192/ot_sram_1r1w_128x64_m1_p192.lef'
    pin_rects = {}
    for name,body in re.findall(r'  PIN (\S+)\n(.*?)  END \1',lef.read_text(),re.S):
        if 'USE SIGNAL' in body or 'USE CLOCK' in body:
            pin_rects[name] = [list(map(float,z)) for z in re.findall(r'RECT (\S+) (\S+) (\S+) (\S+) ;',body)]
    def pin_distance(zone, macro):
        x,y=macro['at']
        return max(distance(zone,[x+a,y+b,x+c,y+d]) for boxes in pin_rects.values() for a,b,c,d in boxes)
    # Exact source-pinned synth area; v3 placement is only an IO/hold-area estimate.
    synth_std = 27215.406160-23*927.9878
    diagnostic_place_std, diagnostic_firm = 6767.088300, 939.914280
    source_std_delta = 27215.406160-27108.418120
    estimated_free = diagnostic_place_std-diagnostic_firm+source_std_delta
    role_bounds = []
    for m in placed:
        col = COLS.index(m['at'][0]);x=COLS[col]
        north_data = [x-14.472,378.54,x+48.168,386.64]
        south_data = [x-4,2.8,x+MW+4,10.8]
        if m['role'] == 'write_payload':
            role_bounds.append(dict(role='K data capture -> matched write macro',macro=m['inst'],
                                    L1_bbox_upper_um=pin_distance(north_data,m)))
            role_bounds.append(dict(role='write macro -> matched PHY data launch',macro=m['inst'],
                                    L1_bbox_upper_um=pin_distance(south_data,m)))
        if m['role'] == 'response_payload':
            role_bounds.append(dict(role='PHY return capture -> matched response macro',macro=m['inst'],
                                    L1_bbox_upper_um=pin_distance(south_data,m)))
            role_bounds.append(dict(role='response macro -> matched KR data launch',macro=m['inst'],
                                    L1_bbox_upper_um=pin_distance(north_data,m)))
        if m['role'] in ('head_metadata','post_metadata'):
            header = [CX-13.52,354.8,CX+13.52,374.8]
            role_bounds.append(dict(role='central K control capture -> metadata macro',macro=m['inst'],
                                    L1_bbox_upper_um=pin_distance(header,m)))
    assert max(r['L1_bbox_upper_um'] for r in role_bounds) <= 405
    spec['outline'] = dict(w=W,h=H)
    spec['route']['period_ps'] = 833.333
    spec['route'].pop('signoff_period_ps',None)
    spec['route']['macro_halo_um'] = 5.4
    spec['macros'] = [dict(view='physical/asap7_memory_macros/ot_sram_1r1w_128x64_m1_p192',
                           count=1,at=m['at'],at_exact=True,orient=m['orient'],inst=m['inst']) for m in placed]
    spec['std_area_um2'] = synth_std
    # No fill exception is enabled here. ROOT must review the explicit packet.
    spec_path.write_text(json.dumps(spec,indent=2)+'\n')
    rec = dict(schema='opentallas.hbm-mc3-lattice-planning.v1',source_commit='272b37645',
       status='PLANNING ONLY: no layout gate/adoption',outline_um=[W,H],lattice_um=43.2,
       macro_size_um=[MW,MH],macros=placed,macro_halo_xy_um=[5.4,5.4],
       pin_faces=dict(W=dict(pins=105,length_um=MH,pins_per_um=105/MH),
                      E=dict(pins=104,length_um=MH,pins_per_um=104/MH)),
       horizontal_pin_face_channel_um=86.4-MW,vertical_non_signal_face_gap_um=43.2-MH,
       macro_LEF_sha256=hashlib.sha256(lef.read_bytes()).hexdigest(),
       local_signal_clock_pin_rects=pin_rects,
       full_width_open_std_band=[2.16,157.14,W-2.16,259.2],bulk_region_rectangles=regions,
       connected_bulk_area_um2=area,bulk_macro_bbox_L1_upper_um=reach,
       measured_synth_std_area_um2=synth_std,measured_synth_macro_area_um2=23*927.9878,
       diagnostic_old_place_std_area_um2=diagnostic_place_std,
       diagnostic_old_firm_area_um2=diagnostic_firm,estimated_new_free_std_area_um2=estimated_free,
       estimated_bulk_util=estimated_free/area,
       clock=dict(face='W',location_um=[0,CY],logic_target_ps=833.333,
                  functional_JEDEC_period_ps=1024,setup_uncertainty_ps=60,hold_uncertainty_ps=25,
                  production_clock_and_PHY_phase_binding='OPEN; no actual 1024 divider/phase claim'),
       reset=dict(face='W',location_um=[0,CY],landing_edges=2,forest_edges=3,
                  source_native_dynamic_reset_fanout_max=32),
       IO_data_faces=dict(N=['k_wdata','kr_data'],S=['dram_rdata','col_data'],
          quartet_model='64-bit groups share corresponding macro-column span; two interleaved buses at 0.192um pitch,5.25pins/um',
          central_N_controls=dict(x_span_um=[CX-11.52,CX+11.52],bits=115,pins_per_um=115/23.04,
             capturing_FF_bbox=[CX-13.52,354.8,CX+13.52,374.8])),
       paired_IO_macro_bbox_bounds=role_bounds,
       replicas=64,macs_per_cycle=0,HBM_PC_bytes_per_functional_edge=32,
       production_four_PC_B_per_stream_edge=[91.68,92.76,91.70],packed_B_per_stream_edge=103.86,
       bandwidth_conversion='4*32*833.333333/1024 peak; 1024 JEDEC edges preserved',
       extra_controller_edges_over_MC3c=0,
       parent_model=dict(PC_pitch_um=265.584,alternating_row_pitch_um=531.168,
          two_controller_rows_plus_SVG_min_height_um=2*H+228.96,
          old_strip_height_um=637.2,min_strip_growth_um=2*H+228.96-637.2,
          phase_and_parent_relay_edges='OPEN: actual die composition must price them'),
       GPL_support_source='https://raw.githubusercontent.com/The-OpenROAD-Project/OpenROAD/6cb3f2b704/src/gpl/src/placerBase.cpp',
       GPL_support_lines='1227-1252: multiple boundary rectangles unblock actual union sites',
       remaining=['implement/verify exact matched IO and control capture zones',
                  'classify every FIRM macro/IO/hold cell and native endpoint; no uncovered outside-bulk role',
                  'validate mapped fanout at 833.333 before gate',
                  'ROOT review pin/lattice-bound low global fill; no exception enabled',
                  'actual native coordinates, PG access, clock spread, setup/hold after gate',
                  'production-domain/PHY phase/compiler budget proof before adoption'])
    (OUT/'model.json').write_text(json.dumps(rec,indent=2)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    fig,ax=plt.subplots(figsize=(9,9))
    ax.add_patch(Rectangle((0,0),W,H,facecolor='#f9fafb',edgecolor='black'))
    ax.add_patch(Rectangle((2.16,157.14),W-4.32,102.06,color='#ddd6fe',alpha=.45))
    for r in regions:ax.add_patch(Rectangle((r[0],r[1]),r[2]-r[0],r[3]-r[1],color='#b4cfeb',alpha=.8))
    colors=dict(write_payload='#eab676',response_payload='#81b29a',head_metadata='#b8a6d8',
                post_metadata='#d8a6bf',queue='#e9c46a',pending_identity='#e9c46a',response_identity='#e9c46a')
    for m in placed:
        x,y=m['at'];ax.add_patch(Rectangle((x-5.4,y-5.4),MW+10.8,MH+10.8,fill=False,edgecolor='#a8a8a8',linestyle=':'))
        ax.add_patch(Rectangle((x,y),MW,MH,facecolor=colors[m['role']],edgecolor='#344054'))
        ax.text(x+MW/2,y+MH/2,m['role'].replace('_','\n'),ha='center',va='center',fontsize=6)
    ax.plot([0],[CY],marker='>',color='red',markersize=10)
    ax.text(5,CY+4,'clk / reset',fontsize=8,color='red')
    ax.text(CX,CY,'connected bulk region\n~58% estimated free-cell util\nmacro-capture envelope <=401.92 um',ha='center',va='center',fontsize=8)
    for x in COLS:
        ax.plot([x,x+MW],[H,H],color='#1f6fb2',linewidth=5)
        ax.plot([x,x+MW],[0,0],color='#1f6fb2',linewidth=5)
    ax.plot([CX-11.52,CX+11.52],[H,H],color='#8d4b00',linewidth=5)
    ax.set(xlim=(-12,W+12),ylim=(-12,H+12),xlabel='um',ylabel='um',aspect='equal')
    ax.set_title('MC3c v6 literal-lattice PLANNING view\n388.8 x 388.8 um; not a placed/routed result')
    ax.grid(alpha=.15);fig.tight_layout();fig.savefig(OUT/'planned_layout.png',dpi=150);plt.close(fig)
    print(json.dumps(dict(output=str(OUT),bulk_area_um2=area,bulk_macro_bbox_upper_um=reach,
                         estimated_bulk_util=estimated_free/area,maximum_paired_IO_bound_um=max(r['L1_bbox_upper_um'] for r in role_bounds))))


if __name__=='__main__':main()
