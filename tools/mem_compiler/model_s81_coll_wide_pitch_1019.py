#!/usr/bin/env python3
"""Finite analytical MODEL; emits no LEF/Liberty/RTL and never edits calibration."""
import hashlib, json, math, re, subprocess
from pathlib import Path
import asap7
import sram_gen as S
ROOT = Path(__file__).resolve().parents[2]
NAME = 'ot_sram_1r1w_512x128_m4_r2c2_p192_rc2'

def blob(ref, path):
    return subprocess.check_output(['git','-C',str(ROOT),'show',f'{ref}:{path}'])

def sources(ref, directory, name):
    out={}
    for ext in ('.json','.lef','.v','_bb.v','_tt.lib','_ff.lib','_ss.lib'):
        p=f'{directory}/{name}/{name}{ext}'
        b=blob(ref,p)
        out[p]=dict(ref=ref,sha256=hashlib.sha256(b).hexdigest())
    return out

def aligned(v):
    return (math.ceil((round(v*1000)-24)/48)*48+24)/1000

def model():
    spec=S.SramSpec(NAME,512,128,4,1,'1r1w',2,2)
    cal=asap7.calibration(); pins=S.pins_for(spec); area=S.area_model(spec,cal)
    contacts=sum(p.width for p in pins); per=math.ceil(contacts/2)
    # Preserve the compiler core and full end keepouts. Model allocation only.
    w=aligned(math.ceil(area['core_width_um']/.216)*.216)
    pin_h=per*.192+2*.768
    h=aligned(math.ceil(max(area['core_height_um'],pin_h)/.270)*.270)
    area.update(macro_width_um=w,macro_height_um=h,macro_area_um2=w*h)
    # Preserve the OLD terminal-to-core anchors at zero core offset. Merely
    # subtracting core H from outline H is NOT an access displacement bound.
    oldname='ot_sram_1r1w_512x128_m4_r2c2'
    oldlef=blob('eb8141cf8', f'physical/asap7_memory_macros_v2/{oldname}/{oldname}.lef').decode()
    anchors=[]
    for name, body in re.findall(r'^  PIN (\S+)\n(.*?)^  END \1$', oldlef, re.M|re.S):
        if name in ('VDD','VSS'): continue
        rects=re.findall(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) ;', body)
        assert len(rects)==1, (name,rects)
        x1,y1,x2,y2=map(float,rects[0]); left=x1==0
        k=sum(a['face']==('W' if left else 'E') for a in anchors)
        old_y=round((y1+y2)/2,6); new_y=round(.780+k*.192,6)
        assert abs(old_y-(.780+k*.096))<1e-8
        anchors.append(dict(pin=name,face='W' if left else 'E',
            old_xy_um=[round((x1+x2)/2,6),old_y],
            preserved_abstract_anchor_xy_um=[round((x1+x2)/2,6),old_y],
            proposed_xy_um=[round((x1+x2)/2,6),new_y],
            vertical_displacement_um=round(abs(new_y-old_y),6)))
    assert len(anchors)==contacts and len({a['pin'] for a in anchors})==contacts
    lead=max(a['vertical_displacement_um'] for a in anchors)
    assert lead==20.928
    # The following is a straight-access RC budget, not proof of internal
    # routing or a bound on unknown detours. Generation remains blocked until
    # a realizable lead topology either matches it or is repriced.
    pg=[]
    for k in range(1000):
        y=round(.384+k*.384,6)
        if y+.096>=h: break
        pg.append(dict(net='VDD' if k%2==0 else 'VSS',layer='M4',
            rect_um=[.300,y,round(w-.300,6),round(y+.096,6)]))
    obs=[dict(layer=l,rect_um=[0,0,w,h]) for l in ('M1','M2','M3')]
    obs.append(dict(layer='M4',rect_um=[.072,0,round(w-.072,6),h]))
    r,c=asap7.SETRC['M4']; cap=lead*c
    timing={}
    for corner in asap7.CORNERS:
        base=S.timing_model(spec,area,cal,corner)
        d=.38*r*c*lead**2+max(base.out_r_kohm,cal['corners'][corner]['inv4_r_kohm'])*cap
        # Two independently adverse clock/data terminal leads, not a free clock wire.
        timing[corner]=dict(base=vars(base),lead_um=lead,lead_cap_ff=cap,lead_delay_ps=d,
            proposed_clk_to_q_ps=base.clk_to_q_ps+2*d,
            proposed_setup_ps=base.setup_ps+2*d,proposed_hold_ps=base.hold_ps+2*d,
            proposed_min_period_ps=base.min_period_ps+2*d,
            proposed_min_pulse_ps=base.min_pulse_ps+2*d,
            proposed_out_slew_intrinsic_ps=base.out_slew_intrinsic_ps+d,
            proposed_pin_cap_ff=base.pin_cap_ff+cap,proposed_clk_cap_ff=base.clk_cap_ff+cap,
            proposed_read_energy_fj=base.read_energy_fj+(contacts-1)*cap*base.voltage**2,
            proposed_write_energy_fj=base.write_energy_fj+(contacts-1)*cap*base.voltage**2)
    creditname='ot_sram_1r1w_32x128_m1_p192_rc'
    credit=json.loads(blob('bb61ae67c',f'physical/asap7_memory_macros/{creditname}/{creditname}.json'))
    gearboxname='ot_sram_1r1w2c_32x64_m1'
    gearbox=json.loads(blob('e26d92503',f'physical/asap7_memory_macros_v2/{gearboxname}/{gearboxname}.json'))
    old=json.loads(blob('eb8141cf8',f'physical/asap7_memory_macros_v2/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.json'))
    families=[dict(role='payload',count=10,name=NAME,raw_bits=655360,useful_bits=566272,area_each_um2=w*h,clock_contacts=10),
        dict(role='credit',count=5,name=creditname,raw_bits=20480,useful_bits=4424,area_each_um2=credit['area']['macro_area_um2'],clock_contacts=5),
        dict(role='gearbox',count=10,name=gearboxname,raw_bits=20480,useful_bits=2380,area_each_um2=gearbox['area']['macro_area_um2'],clock_contacts=20)]
    hashes=sources('eb8141cf8','physical/asap7_memory_macros_v2','ot_sram_1r1w_512x128_m4_r2c2')
    hashes.update(sources('bb61ae67c','physical/asap7_memory_macros',creditname))
    hashes.update(sources('e26d92503','physical/asap7_memory_macros_v2',gearboxname))
    provenance={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),ROOT/'tools/mem_compiler/sram_gen.py',ROOT/'tools/mem_compiler/views.py',ROOT/'tools/mem_compiler/behav.py',ROOT/'tools/mem_compiler/asap7.py',ROOT/'tools/mem_compiler/asap7_calibration.json',ROOT/'results/asap7_physical/bitcell_density/bitcell_density.json',ROOT/'configs/hardware/technology.json']}
    return dict(status='MODEL_ONLY_NOT_BUILD_OR_ADMISSION',name=NAME,spec=vars(spec),area=area,contacts=contacts,
        anchor_geometry=dict(anchor_kind='source LEF boundary anchors; internal core metal is not represented',core_offset_xy_um=[0,0], core_outline_um=[area['core_width_um'],area['core_height_um']],
            old_outline_um=[174.120,29.736], proposed_outline_um=[w,h],
            one_to_one_anchors=anchors,max_vertical_displacement_um=lead,
            displacement_is_route_length_upper_bound=False,
            internal_lead_topology_qualification=None,
            generation_admission='BLOCKED_PENDING_REALIZABLE_INTERNAL_LEAD_TOPOLOGY',
            pg_rectangles=pg,obstruction_rectangles=obs,
            pg_connectivity_qualification=None,access_energy_activity='all nonclock pins at maximum straight-access capacitance; conservative activity',
            clock_cap_policy='same maximum straight-access budget charged to clock despite zero clock displacement',
            leakage_policy='unchanged core devices; passive access metal adds no device leakage'),
        face_contacts=dict(W=219,E=218),full_face_density=dict(W=219/h,E=218/h),
        face_contact_centers_um=dict(first=.780,last_w=.780+218*.192,last_e=.780+217*.192),
        usable_face_um=h-1.536,required_usable_face_um=219/6,pitch_um=.192,timing=timing,families=families,
        total_macro_area_um2=sum(f['count']*f['area_each_um2'] for f in families),
        old_payload_macro_area_um2=10*old['area']['macro_area_um2'],
        total_raw_bits=sum(f['raw_bits'] for f in families),total_useful_bits=sum(f['useful_bits'] for f in families),
        total_clock_contacts=35,physical_payload_bits_including_spares=10*130*520,
        total_physical_bits_including_spares=10*130*520+20480+20480,source_views=hashes,compiler_provenance=provenance,
        native_qualification=None,array_escape_qualification=None,parent_fit=None,cycle_change_proposed=0)

if __name__=='__main__':
    print(json.dumps(model(),indent=2,sort_keys=True))
