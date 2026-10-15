#!/usr/bin/env python3
"""Source-bound physical model and reference-flow spec for native PC profile340cfd747.

The clock census extraction is reused byte-for-byte, never a substitute RTL
body. A source-bound geometry assignment is required before emitting a kit spec.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re

ROOT=Path(__file__).resolve().parents[1]
CENSUS=Path('results/arch/hbm_die_v15/native_pc_clock_census')
OUT=Path('physical/hbm_accel_die_views/svc/native_pc_340cfd747')
MACRO=Path('physical/asap7_memory_macros_v2/ot_sram_1r1w_128x256_m1_r2c2')
NAME='ot_sram_1r1w_128x256_m1_r2c2'
LEAF='rtl/hbm_accel/loader/service_native/ot_hbm_svc_native_stream_pc_lease.sv'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def need(c,m):
    if not c:raise ValueError(m)


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--geometry');ap.add_argument('--pc',type=int,default=0);a=ap.parse_args()
    method=json.loads((ROOT/CENSUS/'method.json').read_text());receipt=json.loads((ROOT/CENSUS/'receipt.json').read_text())
    need(receipt['PC_count']==32 and receipt['status']=='complete','all32 census must be complete')
    for p,want in method['source_sha256'].items():need(sha(ROOT/p)==want,'source profile changed: '+p)
    extracted=ROOT/CENSUS/'single_pc.sv';need(sha(extracted)==method['extracted_source_sha256'],'extracted body changed')
    pc=receipt['PC_roots'][a.pc];need(pc['total_clock_pins']==13650,'clock root changed')
    dest=ROOT/OUT;dest.mkdir(parents=True,exist_ok=True);(dest/'rtl').mkdir(exist_ok=True)
    physical_src=dest/'rtl/native_pc.sv';physical_src.write_bytes(extracted.read_bytes())
    lef=ROOT/MACRO/(NAME+'.lef');text=lef.read_text();m=re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',text);need(m,'LEF size absent')
    w,h=map(float,m.groups());obs=text.split('  OBS\n',1)[1].split('\n  END',1)[0]
    pins=re.findall(r'^  PIN (\S+)\n(.*?)^  END \1$',text,re.M|re.S)
    need(pins and {'VDD','VSS','clk'}<={p for p,_ in pins},'actual macro pins incomplete')
    macro_ports={p:dict(layers=sorted(set(re.findall(r'LAYER\s+(M\d+)',body))),rectangles=[[float(x) for x in q] for q in re.findall(r'RECT\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)',body)]) for p,body in pins}
    model=dict(schema='opentallas.native_PC_physical_model.v1',profile='340cfd747',PC=a.pc,
        source=dict(extracted=str(physical_src.relative_to(ROOT)),sha256=sha(physical_src),production_generate_body_sha256=method['original_generate_body_sha256'],production_source_sha256=method['source_sha256'],parameters=dict(FAST_IDLE_DESC=1,AQ_ROW_LEASE=1,COLUMN_CLOSE_GUARD=1,PC=a.pc,PHASE=0)),
        actual_port_table=method['actual_top_port_table'],port_bits=dict(input=601,output=609),
        clock=dict(port='clk',period_ps=1024,FF_clock_pins=pc['mapped_FF_clock_pins'],SRAM_clock_pins=1,total_clock_pins=13650,setup_uncertainty_ps=60,hold_uncertainty_ps=25,IO_setup_skew_ps=90,IO_hold_skew_ps=50),
        macro=dict(view=str(MACRO),name=NAME,instances=['u_response_payload'],width_um=w,height_um=h,area_um2=w*h,min_edge_channel_um=20,obs_layers=sorted(set(re.findall(r'LAYER\s+(M\d+)',obs))),source_sha256={str(MACRO/(NAME+suffix)):sha(ROOT/MACRO/(NAME+suffix)) for suffix in ['.lef','_bb.v','_tt.lib','_ff.lib','_ss.lib']},port_geometry=macro_ports),
        proposal=dict(outline_um=[250,350],status='await_geometry_assignment_and_measured_standard_cell_area',macro_area_only_um2=w*h,standard_cell_area_um2=None,route_density_target=0.50,pin_layers=dict(W='M4',E='M4',N='M5',S='M5'),pin_track_spacing=2,macro_halo_um=20,signal_and_PG_cap='M5',parent_power='M6'),
        workflow=dict(mandatory='tools/ref_tile/README.md',stages=['source_exact_extraction_audit','geometry_assignment','ref_tile_gen','pin_PG_source_pre_route_gate','admitted_synth_area_measurement','exactly_one_CTS_route','TT_setup_FF_hold_DRC0_with_SS_sensitivity'],source_exact_extraction_audit='all32 independently mapped; extracted source byte hash verified; no production behavior rewritten'),
        qualification_status='not_qualified',remaining=['source_bound_geometry_home_outline_clock_entry','measured_library_mapped_stdcell_area','actual_pin_PG_source_gate','CTS_route_TT_setup_FF_hold_DRC0','actual640sector_native_performance_gate'])
    (dest/'model.json').write_text(json.dumps(model,indent=2,sort_keys=True)+'\n')
    if a.geometry:
        gpath=ROOT/a.geometry;g=json.loads(gpath.read_text());need(g['source_profile']=='340cfd747' and g['PC']==a.pc,'geometry binds wrong source/PC')
        width,height=g['outline_um'];need(width>=w+40 and height>=h+40,'geometry violates20um macro edge minimum')
        faces=g['pins'];need(sorted(p for names in faces.values() for p in names)==sorted(method['actual_top_port_table']),'geometry pin coverage mismatch')
        (dest/'clock_1024.sdc').write_text('# Actual native HBM period; no uncertainty or boundary relaxation.\nset ot_hbm_period [expr {$::ot_ref_pre_cts ? 950.0 : 1024.0}]\ncreate_clock -name core_clk -period $ot_hbm_period [get_ports clk]\nset_clock_uncertainty -setup 60 [all_clocks]\nset_clock_uncertainty -hold 25 [all_clocks]\nif {!$::ot_ref_pre_cts} {set_propagated_clock [all_clocks]}\n')
        spec=dict(name=f'hbm_native_pc340_p{a.pc}_ref',top='ot_hbm_svc_native_pc_census',kind='tile',
           sources=[str(physical_src.relative_to(ROOT)),LEAF],params=dict(PC=a.pc,PHASE=0),clock_port='clk',reset_ports=['rst_n'],
           outline=dict(w=width,h=height,exact=True),layer_cap='M5',util=.50,
           macros=[dict(view=str(MACRO),count=1,inst='u_response_payload',at=g['macro_at_um'],at_exact=True)],pins=faces,
           sdc_extra=[str(OUT/'clock_1024.sdc')],route=dict(pd=.50,threads=4,peak_ram_gb=16,period_ps=950,macro_halo_um=20),
           job=dict(owner='Codex:HBM-native-PC-physical',branch='claude/hbm-die-sm-compact-1014',tag='340cfd-p'+str(a.pc),purpose='Source-exact native PC owner/controller and actual response SRAM, sourceprofile340cfd747; sizing/CTS/route candidate only.',no_bench_reason='Source-exact g_pc extraction guarded against all32 independent mapped receipts; actual complete native command functional/performance receipts remain parent-owned.',extra_paths=[str(OUT),str(CENSUS)],views_to=f'physical/ref_tile/hbm_native_pc340_p{a.pc}_ref/views',record_to=f'results/physical/hbm_native_pc340_p{a.pc}_ref'),
           geometry_source=dict(path=a.geometry,sha256=sha(gpath)),physical_model_sha256=sha(dest/'model.json'))
        (dest/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
    print(json.dumps(dict(model=str(OUT/'model.json'),macro_um=[w,h],clock_pins=13650,source_exact=True,spec_emitted=bool(a.geometry))))

if __name__=='__main__':main()
