#!/usr/bin/env python3
"""SHLK distinct p192 dual-clock SRAM analytical successors; public defaults unchanged.
Derived from QW build_qw_p192_1019 conservative M4 lead-RC recipe.
No transistor layout, SPICE, current/IR or route-access qualification.
"""
import json, math, sys, hashlib, re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sram_gen as S
import asap7
ROOT = Path(__file__).resolve().parents[2]
BASE = S.timing_model
BASE_OUTLINE = S.macro_outline
BASE_LEF = S.write_lef

def aligned_outline(cw, ch, pins):
    w,h,info=BASE_OUTLINE(cw,ch,pins)
    align=lambda x: (round(x*1000)+(24-round(x*1000))%48)/1000
    w,h=align(w),align(h)
    info['track_alignment']='W,H=24mod48nm; R0/MX/MY/R180; no R90'
    return w,h,info

def aligned_lef(name,w,h,pins,props):
    return BASE_LEF(name,w,h,pins,props).replace('SYMMETRY X Y R90 ;','SYMMETRY X Y ;')

def pin_access_timing(spec, area, cal, corner):
    t = BASE(spec, area, cal, corner)
    lead = max(0.0, area['macro_height_um'] - area['core_height_um'])
    r, c = asap7.SETRC['M4']
    cap = lead * c
    wire_ps = 0.38 * r * c * lead * lead
    delay = wire_ps + max(t.out_r_kohm, cal['corners'][corner]['inv4_r_kohm']) * cap
    t.clk_to_q_ps += delay
    t.setup_ps += delay
    t.min_period_ps += 2 * delay
    t.min_pulse_ps = 0.4 * t.min_period_ps
    t.out_slew_intrinsic_ps += delay
    t.pin_cap_ff += cap
    t.clk_cap_ff += cap
    t.read_energy_fj += spec.bits * cap * t.voltage ** 2
    t.write_energy_fj += spec.bits * cap * t.voltage ** 2
    t.breakdown.update(pin_access_lead_um=lead, pin_access_cap_ff=cap,
                       pin_access_wire_ps=wire_ps, pin_access_total_ps=delay)
    return t


def main():
    asap7.METAL['pin_pitch_um']=0.192
    S.timing_model=pin_access_timing
    S.macro_outline=aligned_outline
    S.write_lef=aligned_lef
    summary=[]
    for bits in (257,289):
        name=f'ot_sram_1r1w2c_16x{bits}_m1_p192'
        out=ROOT/'physical/asap7_memory_macros_v2'
        sheet=S.compile_macro(S.SramSpec(name,16,bits,1,1,'1r1w2c'),out)
        a=sheet['area']
        sheet['pin_access_contract']={
          'pitch_um':0.192,'max_density_per_um':1/0.192,
          'immutable_original':name.removesuffix('_p192'),
          'generator':'tools/mem_compiler/build_shlk_p192_1019.py',
          'same_address_concurrent_rw':'FORBIDDEN; independent always blocks do not specify deterministic old-read',
          'operation':'registered read rclk; masked write wclk; unchanged port count and edge latency',
          'analytical_lead_um':a['macro_height_um']-a['core_height_um'],
          'timing':'M4 longest lead RC added to CQ/setup/slew/cap/energy; twice delay to min-period; hold unchanged',
          'claim':'Analytical new abstract; no transistor layout, IR or native routing qualification'}
        d=out/name
        (d/(name+'.json')).write_text(json.dumps(sheet,indent=2,sort_keys=True)+'\n')
        # Native LEF text coordinates, not just model metadata.
        lef=(d/(name+'.lef')).read_text()
        rects=[]
        for chunk in lef.split('  PIN ')[1:]:
            pin=chunk.splitlines()[0].strip()
            if pin in ('VDD','VSS'): continue
            m=re.search(r'RECT ([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+)',chunk)
            rects.append((pin,*map(float,m.groups())))
        groups={}
        for pin,x1,y1,x2,y2 in rects:
            edge='W' if x1==0 else 'E'; groups.setdefault(edge,[]).append((y1+y2)/2)
            assert round(((y1+y2)/2)*1000)%48==12
            assert 0<=x1<x2<=a['macro_width_um'] and 0<=y1<y2<=a['macro_height_um']
        mingap=min(round(y-x,6) for ys in groups.values() for x,y in zip(sorted(ys),sorted(ys)[1:]))
        assert mingap>=0.192
        assert len(rects)==3*bits+12
        assert all(round(a[k]*1000)%48==24 for k in ('macro_width_um','macro_height_um'))
        summary.append({'name':name,'width_um':a['macro_width_um'],'height_um':a['macro_height_um'],'area_um2':a['macro_area_um2'],'core_width_um':a['core_width_um'],'core_height_um':a['core_height_um'],'signal_pins':len(rects),'per_edge':{k:len(v) for k,v in groups.items()},'minimum_actual_contact_pitch_um':mingap,'maximum_actual_density_per_um':1/mingap,'timing':sheet['timing']})
    result=ROOT/'results/rtl/shlk_p192_macros_1019'; result.mkdir(parents=True,exist_ok=True)
    (result/'geometry_audit.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps([{k:v for k,v in row.items() if k!='timing'} for row in summary],indent=2))
if __name__=='__main__': main()
