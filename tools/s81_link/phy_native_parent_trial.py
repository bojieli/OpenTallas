#!/usr/bin/env python3
"""Prepare a native SerDes parent synthesis vehicle from actual digital views.

Only the two analog PMA leaves are modeled. Neither analog shape is a qualified
IP view. A synthesis result establishes resource sizing, never physical closure.
"""
from pathlib import Path
import argparse,json,re,sys,shutil,hashlib
R=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--analog-shape',choices=('original','area_square'),default='original')
a=p.parse_args()
O=a.out;O.mkdir(parents=True,exist_ok=False)
(O/'macros').mkdir(exist_ok=True);(O/'rtl').mkdir(exist_ok=True)
models=[]
for name,kit in [(f'ot_s81_kp4_{x}',f's81lk_kp4_{x}') for x in ('dsyn','ddly','dchn','dout','enc')]+[('ot_s81_rate_match','s81lk_rate_match')]:
 d=R/'physical/ref_tile'/kit/'views'/name
 lef=(d/(name+'.lef')).read_text();w,h=map(float,re.search(r'\bSIZE\s+([\d.]+)\s+BY\s+([\d.]+)',lef).groups())
 for c in ('.lef','_tt.lib','_ff.lib'):shutil.copyfile(d/(name+c),O/'macros'/(name+c))
 models.append(dict(module=name,kind='real routed digital view, legacy qualification pending',outline_um=[w,h],area_um2=w*h,source=str(d.relative_to(R))))
# Analog-only model: reshape on the same43.2um lattice, EXACT original area.
sys.path.insert(0,str(R/'tools/mem_compiler'));import s81_pma_gen as P
if a.analog_shape=='area_square':
 P.W_UM,P.H_UM=561.6,518.4
assert abs(P.W_UM*P.H_UM-129.6*2246.4)<1e-6
P.asap7.CORNERS={k:v for k,v in P.asap7.CORNERS.items() if k in ('tt','ff')}
P.generate(O/'analog')
wrappers=[]
for name,ports in P.macros()[0].items():
 leaf=name+'_analog_m4'
 d=O/'analog'/name
 for ext in ('.lef','_tt.lib','_ff.lib'):
  (O/'macros'/(leaf+ext)).write_text((d/(name+ext)).read_text().replace(name,leaf))
 decl=[];conn=[]
 for p in ports:
  rng=f'[{p.width-1}:0] ' if p.width>1 else ''
  decl.append(f'{p.direction} wire {rng}{p.name}');conn.append(f'.{p.name}({p.name})')
 wrappers.append(f'module {name} #(parameter integer LAT=4) ('+', '.join(decl)+');\n'+f'  if (LAT != 4) begin : g_invalid_pma_latency OT_UNSUPPORTED_PMA_LAT bad(); end\n  {leaf} u_analog ('+', '.join(conn)+');\nendmodule\n')
 models.append(dict(module=leaf,kind='ANALOG ONLY model, assumed timing and footprint',outline_um=[P.W_UM,P.H_UM],area_um2=P.W_UM*P.H_UM,basis='Existing129.6x2246.4PMA area preserved exactly; shape is an unqualified planning assumption, LAT4 model'))
(O/'rtl/analog_wrappers.sv').write_text('\n'.join(wrappers))
col=(R/'rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv').read_text();col=col[:col.index('endmodule')+len('endmodule')]+'\n'
(O/'rtl/ot_pdie_serdes_col.sv').write_text(col)
for src in ('rtl/dsrom_sys/s81_link/lp/ot_s81_kp4_dec_native_flat_lp.sv','rtl/common/landed_parent/ot_pl_land.sv','rtl/common/ot_dp_clk_landing.sv','rtl/common/ot_meso_fifo.sv'):
 shutil.copyfile(R/src,O/'rtl'/Path(src).name)
W,H=3318.0,1013.0
(O/'constraint.sdc').write_text('create_clock -name clk -period833 [get_ports clk]\n'.replace('-period833','-period 833')+'create_clock -name rck -period 833 [get_ports pma_rck]\nset_clock_groups -asynchronous -group clk -group rck\nset_clock_uncertainty -setup 60 [all_clocks]\nset_clock_uncertainty -hold 25 [all_clocks]\n')
config=['export PLATFORM = asap7','export DESIGN_NAME = ot_pdie_serdes_col','export VERILOG_FILES = $(wildcard /work/rtl/*.sv)','export SDC_FILE = /work/constraint.sdc','export ADDITIONAL_LEFS = $(wildcard /work/macros/*.lef)','export ADDITIONAL_LIBS = $(wildcard /work/macros/*_tt.lib)','export DIE_AREA = 0 0 3318 1013','export CORE_AREA = 8.64 8.64 3309.36 1004.36','export CORE_UTILIZATION = 40','export SYNTH_HIERARCHICAL = 0','export SYNTH_MINIMUM_KEEP_SIZE = 1','export SYNTH_MEMORY_MAX_BITS = 65536','export NUM_CORES = 8']
(O/'config.mk').write_text('\n'.join(config)+'\n')
summary=dict(analog_shape=a.analog_shape,analog_physical_qualified=False,analog_original_fits_window=False,top='ot_pdie_serdes_col',window_um=[W,H],model_before_build=dict(area_um2=sum(x['area_um2'] for x in models),window_um2=W*H,macro_fill=sum(x['area_um2'] for x in models)/(W*H)),macros=models,source_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (R/'rtl/dsrom_sys/s81_link/col/ot_pdie_serdes_col.sv',R/'rtl/dsrom_sys/s81_link/lp/ot_s81_kp4_dec_native_flat_lp.sv')},source_contract='TXL2 and RX+8 unchanged; actual native LP and6real digital tiles, ONLY2analog-modeled leaves; no whole-PHY blackbox; no current SIGNED claim')
(O/'sizing.json').write_text(json.dumps(summary,indent=1)+'\n')
print(json.dumps(summary['model_before_build']))
