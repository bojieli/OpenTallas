#!/usr/bin/env python3
"""Create a NEW repo-relative bind recipe using the single physical KV dcal ROM.

The source recipe and its running bind remain untouched. The generated alias
retains the old instance's module/port names. Only the macro via map carries
the compiled calendar, so all profiles have one physical controller design.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/mem_compiler'))
import kv_dcal_profile as P


def install(recipe: Path, profile: Path, out: Path):
    recipe=recipe.resolve();profile=profile.resolve();out=out.resolve()
    for p in (recipe,profile,out):p.relative_to(ROOT)
    r=json.loads(recipe.read_text())
    if (recipe.parent/r.get('base','.')).resolve()!=ROOT:
        raise ValueError('source recipe base must resolve to this repository')
    data=json.loads(profile.read_text());P.pack_profile(data)
    if out.exists() and any(out.iterdir()):raise ValueError('output must be a new empty bind cohort; existing source is immutable')
    out.mkdir(parents=True,exist_ok=True)
    content=P.personalise(data,out/'content',instance='kv_dcal')
    via=out/'content'/content['viamap']
    # +OT_ROM_DIR resolves INSTANCE, while the canonical compiler tile has a _r0_c0 suffix.
    simulation_alias=out/'content'/'kv_dcal.viamap.hex'
    simulation_alias.write_bytes(via.read_bytes())
    rel=lambda p:str(p.relative_to(ROOT))
    rtl=ROOT/'rtl/qwen_sys/d2d_static_20261015'
    source=(rtl/'qkd_d2d_cal_seq_rom64.sv').read_text()
    source=source.replace('module qkd_d2d_cal_seq_pin_rom64 #(', 'module qkd_d2d_cal_seq_pin_bc4 #(',1)
    if source.count('parameter VIAMAP = ""') != 1:raise ValueError('unexpected profile metadata declaration')
    source=source.replace('parameter VIAMAP = ""',f'parameter VIAMAP = "{rel(via)}"',1)
    alias=out/'qkd_d2d_cal_seq_bc4_rom64.sv';alias.write_text(source)
    bb=ROOT/f'physical/asap7_memory_macros_v2/{P.NAME}/{P.NAME}_bb.v'
    extra=[rel(alias),rel(rtl/'ot_qwen_d2d_cal_seq_rom64_core.sv'),rel(bb)]
    old=lambda s:bool(re.search(r'/qkd_d2d_cal_seq_bc4(?:_[^/]*)?\.sv$',s))
    for key in ('files','prefer','portbind_prefer'):
        if key in r and isinstance(r[key],list):
            r[key]=[s for s in r[key] if not old(s)]
    for key in ('files','prefer'):
        r[key]=list(dict.fromkeys(r.get(key,[])+extra))
    if r.get('map_file'):
        r['map_file']=os.path.relpath((recipe.parent/r['map_file']).resolve(),out)
    r['base']=os.path.relpath(ROOT,out)
    r['dcal_rom_note']='Approved D-ROM-3b: TX/RX init images are dead and removed; START/PERIOD/SEG/ADM/FIRST data comes from one generated64x32m2 ROM. No production or boot edge added; eight scalar reads occupy existing suppressed init. New recipe only.'
    target=out/(recipe.stem+'.rom64.json');target.write_text(json.dumps(r,indent=2)+'\n')
    sheet=json.loads(P.MACRO.read_text())
    model={
      'schema':'opentallas.kv-dcal-rom.v1','recipe':rel(target),
      'source_recipe':rel(recipe),'source_profile':rel(profile),
      'source_profile_sha256':hashlib.sha256(profile.read_bytes()).hexdigest(),
      'macro':P.NAME,'macro_sheet':rel(P.MACRO),'manifest':rel(out/'content'/content['manifest']),
      'macro_view_area_um2':81.404352,'macro_size_um':[8.856,9.192],
      'macro_instance':'dcal.u_profile','cache_scalar_bits':256,
      'simulation_alias':rel(simulation_alias),'simulation_instance':'kv_dcal',
      'functional_model':f'physical/asap7_memory_macros_v2/{P.NAME}/{P.NAME}.v',
      'scalar_read_order':[39,40,36,37,38,41,42,43],
      'existing_init_edges':66,'new_boot_edges':0,'new_production_edges':0,
      'layer_read_lead_edges_max':2,'layer_start_gap_min':min(b-a for a,b in zip(data['START'],data['START'][1:])),
      'physical_obligations':'Add macro LEF and TT/FF libraries and place the81.4um2 generated macro inside the sys_c dcal region; review before any route. New physical signoff required; no preexisting view reused.'}
    (out/'integration.json').write_text(json.dumps(model,indent=2)+'\n')
    return model


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('recipe',type=Path);ap.add_argument('profile',type=Path);ap.add_argument('out',type=Path)
    a=ap.parse_args();print(json.dumps(install(a.recipe,a.profile,a.out),indent=2))
