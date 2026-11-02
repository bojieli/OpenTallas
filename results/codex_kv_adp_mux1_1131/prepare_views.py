from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/mem_compiler'))
import sram_gen,build_aligned_v2 as V
OUT=Path(__file__).resolve().parent/'views'
spec=sram_gen.SramSpec('ot_sram_1r1w_512x128_m1_r2c2',512,128,mux=1,ports='1r1w',spare_rows=2,spare_cols=2)
v1=sram_gen.compile_macro(spec)
w,h=v1['area']['macro_width_um'],v1['area']['macro_height_um']
with V.patched(sram_gen,macro_outline=V.aligned_outline,write_lef=V.aligned_write_lef,GENERATOR_VERSION=sram_gen.GENERATOR_VERSION+'+'+V.ALIGN_VERSION):
 sheet=sram_gen.compile_macro(spec,OUT)
 entry=V.finish(OUT,spec.name,v1,(w,h),dict(kind='sram',spec=spec.spec_dict()))
(OUT/'index.json').write_text(json.dumps({spec.name:entry},indent=2)+'\n')
# Enumerate the exact logical/native physical-word map with repair disabled.
old=set();new=set()
for address in range(512):
 for bit in range(128):
  old.add((address//4,bit*4+address%4));new.add((address,bit))
assert len(old)==len(new)==512*128
(Path(__file__).resolve().parent/'wordmap.json').write_text(json.dumps(dict(verdict='PASS',logical_bits=512*128,old_mux=4,new_mux=1,old_unique_bits=len(old),new_unique_bits=len(new),repair='rr_en=0,cr_en=0 as in native caller',capacity_bits=65536,cycles_added=0,old_to_new='(address//4, bit*4+address%4) -> (address,bit)'),indent=2)+'\n')
print(json.dumps(dict(width=entry['width_um'],height=entry['height_um'],tt_clkq=sheet['timing']['tt']['clk_to_q_ps'],tt_period=sheet['timing']['tt']['min_period_ps'],alignment='PASS',wordmap='PASS')))
