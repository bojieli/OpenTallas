"""Ram-requested further-shard geometry sensitivity, no placement authority."""
import hashlib
import json
import math
import subprocess
from pathlib import Path

ROOT=Path('results/quality/w16_engram_rom_constructive_home_20261001')
raw=(ROOT/'final/candidate.json').read_bytes();prior=json.loads(raw)
pin=subprocess.check_output(['git','rev-parse','541a1d2f'],text=True).strip()
p='results/floorplan/v41_pack_refit_w10_interim.json'
src=subprocess.check_output(['git','show',pin+':'+p]);g=json.loads(src)['geometry']
cx0,cy0,cx1,cy1=g['core'];hx,hy,hw,hh=g['hub'];halo=g['hub_halo_um']
px=prior['coordinate_inventory']['planning_reservation_macro_width_um']+16
py=prior['coordinate_inventory']['planning_reservation_macro_height_um']+16
# Keep actual macro R0 orientation. Change the grid to 64 columns x128rows;
# rotating a grid or macro is NOT how this sensitivity achieves the fit.
width,height=64*px,128*py
origin=[hx+hw+halo,cy0]
assert origin[0]+width<=cx1 and origin[1]+height<=cy1
assert origin[0]>=hx+hw+halo
levels=[dict(level=i,edges=0,length_um=0.,max_edge_um=0.,wire_stages=0,max_path_wire_stages=0) for i in range(13)]
leaves={}
def visit(x,y,nx,ny,depth,index,path):
    if depth==13:
        assert nx==ny==1
        leaves[index]=(x,y,path)
        return
    for b in (0,1):
        if depth%2==0: # y has seven decisions; x has six.
            xx,yy,nnx,nny=x,y+b*ny//2,nx,ny//2;L=ny*py/4
        else:
            xx,yy,nnx,nny=x+b*nx//2,y,nx//2,ny;L=nx*px/4
        stages=max(1,math.ceil(L/504));q=levels[depth]
        q['edges']+=1;q['length_um']+=L;q['max_edge_um']=max(q['max_edge_um'],L)
        q['wire_stages']+=stages;q['max_path_wire_stages']=max(q['max_path_wire_stages'],stages)
        visit(xx,yy,nnx,nny,depth+1,index*2+b,path+stages)
visit(0,0,64,128,0,0,0)
assert len(leaves)==8192 and len({(x,y) for x,y,_ in leaves.values()})==8192
nodes=8191;stages=sum(r['wire_stages'] for r in levels)
tree_FF=339*(nodes+stages)+2*nodes
home_rows=[];digest=hashlib.sha256()
for col in range(48):
    n=sum(h['actual_macros'] for h in prior['homes'] if h['home_id']//2==col)
    for shard in range(4):
        lo=shard*8192;hi=min(lo+8192,n);actual=hi-lo;home=4*col+shard
        state=tree_FF+actual*298+4864+64
        home_rows.append(dict(home_id=home,column_ordinal=col,macro_start=lo,macro_end_exclusive=hi,
            actual_macros=actual,empty_grid_slots=8192-actual,grid_origin_um=origin,
            grid_maximum_point_um=[origin[0]+width,origin[1]+height],
            tree_wire_FF_bits=tree_FF,macro_tag_capture_FF_bits=actual*298,
            total_storage_FF_bits=state,held_state_feedback_MUX2_bits=state,
            response_MUX2_bits=nodes*288,request_demux_AND2_bits=2*nodes*51,
            actual_macro_orientation='R0',clock_gating_credit=False))
        for m in range(lo,hi):
            local=m&8191;assert (m>>13)==shard
            x,y,_=leaves[local]
            # Each predictive macro fits inside the planning reserved cell;
            # every cell stays in core and to right of halo. Other obstacles
            # and physical tracks/pin escape remain separate obligations.
            mx=origin[0]+x*px+8;my=origin[1]+y*py+8
            assert mx>=cx0 and my>=cy0
            assert mx+125.28<=cx1 and my+62.91<=cy1
            assert mx>=hx+hw+halo
            digest.update(f'{home},{m},{local},{x},{y}\n'.encode())
assert sum(h['actual_macros'] for h in home_rows)==1500067
out=dict(schema='opentallas.engram.192-home-retained-hub-sensitivity.v1',
    status='PASS_RECTANGLE_CORE_HUB_HALO_ONLY_NOT_LEGAL_FLOORPLAN_OR_ADMISSION',
    source_pin=dict(commit=pin,path=p,sha256=hashlib.sha256(src).hexdigest()),
    prior96candidate_sha256=hashlib.sha256(raw).hexdigest(),
    generator_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    owner_authority='Ram requested this geometry-only sensitivity; whole placement remains his',
    homes=home_rows,homes_count=192,full_table_copies=1,macros=1500067,
    grid_shape=[64,128],grid_size_um=[width,height],grid_origin_um=origin,
    right_core_strip_width_um=cx1-(hx+hw+halo),
    right_strip_grid_horizontal_slack_um=cx1-origin[0]-width,
    core_grid_vertical_slack_um=cy1-origin[1]-height,
    grid_area_mm2=width*height/1e6,
    full_macro_coordinate_digest=hashlib.sha256(digest.digest()).hexdigest(),
    full_coordinate_tuple_SHA256=digest.hexdigest(),
    mapping='home=4*column_ordinal+(macro15>>13); local_macro13=macro15&8191; y-first binary partition; macro remains R0',
    tree=dict(levels=levels,logic_levels=13,wire_path_cycles=max(p for _,_,p in leaves.values()),
        tree_wire_FF_bits_per_home=tree_FF,
        local_first_beat_cycles_conditional=2*max(p for _,_,p in leaves.values())+26+1,
        local_row_cycles_conditional=2*max(p for _,_,p in leaves.values())+26+1+7,
        routing_tracks_per_edge=341,two_child_junction_tracks=682,
        assumed16um_four_layer_tracks=800,actual_available_layers=None),
    all_storage_FF_bits=sum(h['total_storage_FF_bits'] for h in home_rows),
    maximum_home_FF_bits=max(h['total_storage_FF_bits'] for h in home_rows),
    actual_signal_pin_halo_and_track_phase=False,
    other_source_floorplan_obstacles_reused_or_removed=False,
    hold_mux_CTS_IO_controller_PHY_placement=False,
    framing_CRC_sharedport_calendar=None,power_source_join=None,
    interpretation='Right-strip rectangle avoids retained hub+43.2um halo and remains inside source core at exact stated origin. Existing HBM/IO/macros are NOT retired by this record. A new Engram-role die floorplan must reserve or replace every other obstacle explicitly; this is not a complete legal floorplan.',
    no_wake_or_idle_power_credit=True,L1_generated_source=None,checkpoint_reads=0,
    RTL_or_PnR_runs=False,physical_admission=False,full_token_rate=None)
target=ROOT/'sensitivity_192_homes.json';assert not target.exists()
target.write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
print(json.dumps(dict(sha256=hashlib.sha256(target.read_bytes()).hexdigest(),grid_size_um=out['grid_size_um'],origin=origin,FF=out['all_storage_FF_bits'],rowcycles=out['tree']['local_row_cycles_conditional'])))
