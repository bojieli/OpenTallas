#!/usr/bin/env python3
"""Map real historical Markov RTL onto the CURRENT four-rank head row map.

This is a model-before-build source/capacity census, not a plan adoption. It
finds reuse rather than treating stale 'no full-shape RTL' prose as a fact.
Macro-only area is a floor; logic, routing, PG and clocks remain unmeasured.
"""
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/s81_head'))
import head_row_map
PROVIDERS={
 'ot_dsrom_markov_head_full340':'rtl/dsrom_sys/mtp/ot_dsrom_markov_head_full340.sv',
 'ot_dsrom_markov_bundle_glue':'rtl/dsrom_sys/mtp/ot_dsrom_markov_bundle_glue.sv',
 'ot_dsrom_markov_head_driver':'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_head_A.sv',
 'ot_dsrom_markov_row':'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_row.sv',
 'ot_dsrom_markov_embed_rom':'rtl/experimental/dsrom_markov_20261008/ot_dsrom_markov_embed_port.sv'}

def build(plan_path,macro_path):
 rows=head_row_map.build(plan_path)
 macro=json.loads(macro_path.read_text())
 area=macro['alignment_v2']['v2']['area_um2']
 p=json.loads(plan_path.read_text());tile=p['partition_types']['hd_tile']
 source={name:{'path':path,'found':('module '+name) in (ROOT/path).read_text()} for name,path in PROVIDERS.items()}
 if not all(r['found'] for r in source.values()):raise ValueError('missing real Markov provider')
 ranks=[]
 for r in rows['ranks']:
  nb=r['active_bundles'];drivers=4*nb;weights=2*drivers;embedding=506
  ranks.append(dict(rank=r['rank'],controller_row_base=r['controller_row_base'],head_bundles=nb,drivers=drivers,weight_macros=weights,embedding_macros=embedding,
   macro_area_floor_mm2=(weights+embedding)*area/1e6,
   reusable_full_head_parameters={'ENABLE':1,'NB':nb,'ROW_BASE':0,'DIE_ROWS':nb*128,'FIRST_BUNDLE':r['controller_row_base']//128,'LOOKUP':1},
   current_weight_image_contract='local row IDs (ROW_BASE0) retain controller c_rbase; FIRST_BUNDLE is global weight-image bundle prefix; no old images reused implicitly'))
 declared=[(tn,c['module']) for tn,t in p['partition_types'].items() for c in t.get('contents',[]) if 'markov' in c.get('module','').lower()]
 return dict(schema='opentallas.s81.head-mtp-source-census.v1',status='REAL_RTL_REUSE_FOUND; CURRENT_NATIVE_BIND_MISSING',
  sources=source,ranks=ranks,head_dies=4,vocabulary=129280,drivers=sum(r['drivers'] for r in ranks),
  weight_macros=sum(r['weight_macros'] for r in ranks),embedding_macros=sum(r['embedding_macros'] for r in ranks),
  macro_area_floor_mm2=sum(r['macro_area_floor_mm2'] for r in ranks),macro_area_um2=area,
  current_plan_markov_contents=declared,
  current_tile=dict(outline_um=tile['outline_um'],pre_argmax_outputs='ot_s81hd_bundle.head_v[3:0]/head_d[127:0]/head_row[67:0], currently nc_hv/nc_hd/nc_hr',
   must_join='add Markov bias to EACH row before argmax; adding after current tile argmax is incorrect'),
  weight_rom_packing=dict(rows_per_driver=32,K=256,bf16_bits=16,useful_bits=32*256*16,macros_per_driver=2,
   useful_words_per_driver=512,available_words_per_driver=8192,word_fill=512/8192,
   bit_fill=(32*256*16)/(2*4096*274),cause='two 4096x274 macros alternate sixteen beats for each of32rows; only256 words per bank are addressed'),
  no_build_until=['source-pinned current image mapping (including embedding images)','shared embedding lookup/transaction transport on current plan',
   'DHSTEP/ROWS native ring bridge and static issue calendar','master-plan lot+bay+clock+PG capacity with driver logic included','TT/FF new core views; old views are not current signoff'],
  old_claim_correction='Real full-shape Markov RTL exists; missing item is current four-head physical/source/native composition, not an RTL module from scratch')

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--plan',type=Path,default=ROOT/'physical/die_plan/s81_head/die_plan.json');ap.add_argument('--macro',type=Path,default=ROOT/'physical/asap7_memory_macros_v2/ot_rom_4096x274_m8/ot_rom_4096x274_m8.json');ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 m=build(a.plan,a.macro);a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(m,indent=2)+'\n');print(json.dumps({k:m[k] for k in ('status','drivers','weight_macros','embedding_macros','macro_area_floor_mm2')}))
if __name__=='__main__':main()
