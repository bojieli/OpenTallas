"""Size the A0 structural successor before RTL/placement. Geometry is not a gate."""
import json
from pathlib import Path

LATTICE = 43.2
W, H = 1209.6, 648.0
children = [dict(name='node', at=[43.2, 129.6], size=[47.52, 432.0])]
for row in range(2):
    for col in range(5):
        children.append(dict(name=f'rom{row*5+col}', at=[129.6+216*col,43.2+172.8*row],size=[172.8,110.16]))
for col in range(8):
    children.append(dict(name=f'lsl{col}',at=[129.6+129.6*col,432.0],size=[99.792,140.4]))
for a in children:
    x,y=a['at'];w,h=a['size']
    assert all(abs(v/LATTICE-round(v/LATTICE))<1e-9 for v in (x,y))
    assert min(x,y,W-x-w,H-y-h)>=20
for i,a in enumerate(children):
    for b in children[i+1:]:
        x,y=a['at'];w,h=a['size']; xx,yy=b['at'];ww,hh=b['size']
        dx=max(x-xx-ww,xx-x-w);dy=max(y-yy-hh,yy-y-h)
        assert dx>=20 or dy>=20,(a['name'],b['name'],dx,dy)
hard_area=322971.5
std_area=8756.0
out=dict(schema='opentallas.qwen.a0.safe_model.v1',status='MODEL_ONLY_NO_GATE',
    source='985e49d6e+c980cbe47 / immutable NK c1r9f actual synth area',
    dimensions_um=[W,H],aspect=W/H,area_um2=W*H,
    previous_dimensions_um=[457.92,1166.4],
    parent_area_delta_um2=W*H-457.92*1166.4,
    hard_area_um2=hard_area,historical_std_area_um2=std_area,
    raw_fill=(hard_area+std_area)/(W*H),
    full_width_std_band_um=[0,345.6,W,362.88],
    std_band_fill_historical=std_area/(W*17.28),
    children=children,
    operand_select_plan=dict(default_off='REGROOT4',lanes=64,bits_per_operand=32,
         variable_bits_per_lane=16,lanes_per_copy=2,max_select_mux_inputs=32,
         wsrc_copies=32,group_mask_copies=32,old_select_registers=6,
         operand_added_registers=58,round_added_registers=7,added_registers=65,added_edges=0,
         upstream_wsrc_fanout=32,
         requirement='Actual synthesis must retain copies and prove all primitive-driver loads, including decode logic, <=32.'),
    reset_plan=dict(face_stages_required=2,raw_pin_max_sinks=2,local_branch_max_sinks=32,
        existing_face_stages=1,adopted=False,
        requirement='Additional registered reset tree and warmup to be sized from actual census; one sampled reset_q is insufficient.'),
    schedule=dict(compute_macs_per_cycle=64,rom_bytes_per_port_cycle=33.25,
        physical_rom_ports=10,raw_rom_return_bits_per_cycle=5120,
        tile_output_bits_per_cycle=514,upper_node_output_bits_per_cycle=514,
        authorized_node_path_relay_edges=1,node_landing_data_ff=512,node_landing_valid_ff=1,node_landing_clock_entries="existing eight ck_tx entries",operand_copy_edges=0,
        rom_return_landing_edges=None,reset_warmup_edges=None,
        full_token_delta=None,
        requirement='Long paths must be bound to actual master pins and source event ledgers before choosing fixed landing depth.'),
    unresolved=['Native ROM/LSL/node pin geometry and PG/via escape on proposed orientations',
        'Source-to-destination static relay epochs and every routed reach <=405um',
        'Synthesized reset tree, operand copies, area and actual register/comb driver census',
        'Keep all parent standard cells in the modeled full-width17.28um band; historical mass fills41.9%, new mapped mass and clock/repair overhead must be re-sized',
        'Native clock pairs, TT setup and FF hold, source reset mutants and numerical production proof',
        'Die slot/area placement changes and compiler age pricing; no parent fit claimed'])
dest=Path(__file__).resolve().parents[2]/'results/arch/qwen_a0_safe_1019/model.json'
dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(json.dumps(out,indent=2)+'\n')
print('A0_MODEL_PASS',W,H,'aspect',W/H,'raw_fill',out['raw_fill'],'UNQUALIFIED')
