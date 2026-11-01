from pathlib import Path
import json
import math
import re
import shutil
import sys
sys.path.insert(0, '/srv/opentallas-scratch/claude/wt/codex-hbm-mesh-core-union-1131/tools/die_plan')
import schema as S
import die_trial as DT
r = Path(__file__).resolve().parent
plan = S.Plan(S.load(r/'current_C11E_plan.json'))
site = DT.SiteMap(plan)
source = json.loads((r/'native_tail_source.json').read_text())
macro_origin = [950.4, 5512.32]
macro_size = [218.592, 187.488]
clock_xy = [1058.376, 5607.36]
source_xy = source['source_xy_um']
assert not source['source_fanout']
assert all(site.legal((source_xy[0]+dx,source_xy[1]+dy)) for dx,dy in [(0,0),(1.62,.27)])
x0, y0, x1, y1 = 920., 5480., 1200., 5740.
pg_pitch, pg_width = 4.32, .672
source_window = [source_xy[0]-3.24, source_xy[1]-3.24, source_xy[0]+4.86, source_xy[1]+3.51]
clock_window = [clock_xy[0]-3.24, clock_xy[1]-3.24, clock_xy[0]+3.24, clock_xy[1]+3.24]
# Source test boundary is in a PG gap and on the M9 preferred track.
drive_xy = [1064.916, 5704.56]
blocks = []
for layer in range(2,8):
    windows = [source_window] + ([clock_window] if layer >= 6 else [])
    ys = sorted({y0,y1}|{max(y0,min(y1,y)) for a,b,c,d in windows for y in (b,d)})
    for low, high in zip(ys,ys[1:]):
        spans = sorted((max(x0,a),min(x1,c)) for a,b,c,d in windows if b<(low+high)/2<d)
        cursor = x0
        for left,right in spans+[(x1,x1)]:
            if left>cursor:
                blocks.append(f'- LAYER M{layer} RECT ( {round(cursor*1000)} {round(low*1000)} ) ( {round(left*1000)} {round(high*1000)} ) ;')
            cursor=max(cursor,right)
other_cores=[]
for part, placement in plan.parts.items():
    for core in plan.types[placement['type']].get('hard_cores',[]):
        if part=='NW_b103' and core['inst']=='u_hb_idx__s_Q_tail1':
            continue # Actual native LEF/OBS/pin replaces this rectangle.
        ox,oy=core['origin_um']; w,h=core['outline_um']
        a,b=plan.to_die(part,(ox,oy)),plan.to_die(part,(ox+w,oy+h))
        box=[min(a[0],b[0]),min(a[1],b[1]),max(a[0],b[0]),max(a[1],b[1])]
        if box[2]<x0 or box[0]>x1 or box[3]<y0 or box[1]>y1:
            continue
        other_cores.append(dict(part=part,inst=core['inst'],box=box))
        for layer in range(1,6):
            blocks.append(f'- LAYER M{layer} RECT ( {round(max(x0,box[0])*1000)} {round(max(y0,box[1])*1000)} ) ( {round(min(x1,box[2])*1000)} {round(min(y1,box[3])*1000)} ) ;')
pg={'VDD':[],'VSS':[]}
for index in range(math.ceil(y0/pg_pitch),math.floor(y1/pg_pitch)+1):
    y=round(index*pg_pitch*1000)
    pg['VDD' if index%2 else 'VSS'].append(f'M8 {round(pg_width*1000)} + SHAPE STRIPE ( {round(x0*1000)} {y} ) ( {round(x1*1000)} {y} )')
for index in range(math.ceil(x0/pg_pitch),math.floor(x1/pg_pitch)+1):
    x=round(index*pg_pitch*1000)
    pg['VDD' if index%2 else 'VSS'].append(f'M9 {round(pg_width*1000)} + SHAPE STRIPE ( {x} {round(y0*1000)} ) ( {x} {round(y1*1000)} )')
for form,width in [('narrow',.04),('wide',.16)]:
    out=r/f'native_tail_pin_{form}'
    out.mkdir(exist_ok=True)
    for path in (r/'native_tail_views').iterdir():
        shutil.copy2(path,out/path.name)
    lines=['VERSION 5.8 ;','DIVIDERCHAR "/" ;','BUSBITCHARS "[]" ;','DESIGN native_clock_probe ;','UNITS DISTANCE MICRONS 1000 ;',
           f'DIEAREA ( {round(x0*1000)} {round(y0*1000)} ) ( {round(x1*1000)} {round(y1*1000)} ) ;','COMPONENTS 2 ;',
           f'- b5607 {source["master"]} + FIXED ( {round(source_xy[0]*1000)} {round(source_xy[1]*1000)} ) N ;',
           '- native_tail ot_hbm_idx_tail_native + FIXED ( 950400 5512320 ) N ;','END COMPONENTS','PINS 1 ;',
           f'- drive + NET input + DIRECTION INPUT + USE CLOCK + LAYER M9 ( -20 -40 ) ( 20 40 ) + FIXED ( {round(drive_xy[0]*1000)} {round(drive_xy[1]*1000)} ) N ;','END PINS',
           f'BLOCKAGES {len(blocks)} ;',*blocks,'END BLOCKAGES','SPECIALNETS 2 ;']
    for net,shapes in pg.items():
        lines += [f'- {net} + ROUTED '+'\n    NEW '.join(shapes)+f' + USE {"POWER" if net=="VDD" else "GROUND"} ;']
    lines += ['END SPECIALNETS','NETS 2 ;','- input ( PIN drive ) ( b5607 A ) + USE CLOCK ;',
              '- native_clock ( b5607 Y ) ( native_tail clk ) + USE CLOCK ;','END NETS','END DESIGN']
    (out/'pilot.def').write_text('\n'.join(lines)+'\n')
    manifest=dict(form=form,ndr_width_um=width,source_cell='b5607',source_master=source['master'],source_xy_um=source_xy,
                  native_instance='NW_b103.u_hb_idx__s_Q_tail1',probe_instance='native_tail',master='ot_hbm_idx_tail_native',
                  native_origin_um=macro_origin,native_size_um=macro_size,clock_pin='clk',clock_pin_layer='M5',clock_xy_um=clock_xy,
                  lib_clock=True,lef_use='SIGNAL',clock_cap_ff={'TT':.5502,'FF':.5934},source_fanout=[],
                  source_to_clock_manhattan_um=sum(abs(a-b)for a,b in zip(source_xy,clock_xy)),source_window_um=source_window,
                  native_upper_M6_M7_window_um=clock_window,other_core_obstacles=other_cores,drive_xy_um=drive_xy,
                  scope='Physical actual-source to actual native macro CLK ITerm at current C11E pose; no virtual K/BTerm clock alias. Functional/current-source qualification held; signed native physical view has outer IO FF latency1/1.',release_qualified=False)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('Native exact current-tail clock probe built; source-to-clk99.384um, .04/.16 NDR, native M5 + M6/M7 access, PG intact.')
