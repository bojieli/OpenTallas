#!/usr/bin/env python3
"""Emit a new QC bind recipe selecting the opt-in live image-ROM producer."""
from pathlib import Path
import argparse,json,os,re,sys,hashlib
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tools/mem_compiler'))
import qc_dcal_profile as P

def install(recipe:Path,profile:Path,out:Path):
    recipe=recipe.resolve();profile=profile.resolve();out=out.resolve()
    for p in (recipe,profile,out):p.relative_to(ROOT)
    r=json.loads(recipe.read_text())
    if (recipe.parent/r.get('base','.')).resolve()!=ROOT:raise ValueError('recipe base must resolve to this repository')
    data=json.loads(profile.read_text());P.pack_profile(data)
    if len(data['TX'])!=32:raise ValueError('QC rope implementation requires NE32')
    out.mkdir(parents=True,exist_ok=True);content=P.personalise(data,out/'content')
    rel=lambda p:str(p.relative_to(ROOT))
    rtl=ROOT/'rtl/qwen_sys/d2d_static_20261015'
    source=(rtl/'qfd_d2d_cal_seq_ovl_rope_image64.sv').read_text()
    source=source.replace('module qfd_d2d_cal_seq_ovl_rope_image64 #(','module qfd_d2d_cal_seq_ovl_rope #(',1)
    if source.count('parameter IMAGE_VIAMAP = ""') != 1:raise ValueError('unexpected profile metadata declaration')
    source=source.replace('parameter IMAGE_VIAMAP = ""',f'parameter IMAGE_VIAMAP = "{rel(out/"content"/content["viamap"])}"',1)
    alias=out/'qfd_d2d_cal_seq_ovl_rope_rom64.sv';alias.write_text(source)
    extra=[rel(alias),rel(rtl/'ot_qwen_d2d_ovl_seq_image64.sv'),rel(rtl/'ot_qwen_d2d_cal_seq_image64.sv'),rel(ROOT/f'physical/asap7_memory_macros_v2/{P.NAME}/{P.NAME}_bb.v')]
    for k in ('files','prefer','portbind_prefer'):
        if isinstance(r.get(k),list):r[k]=[s for s in r[k] if not s.endswith('/qfd_d2d_cal_seq_ovl_rope.sv')]
    for k in ('files','prefer'):r[k]=list(dict.fromkeys(r.get(k,[])+extra))
    if r.get('map_file'):r['map_file']=os.path.relpath((recipe.parent/r['map_file']).resolve(),out)
    r['base']=os.path.relpath(ROOT,out)
    r['qc_dcal_rom_note']='Opt-in QC batch2 candidate: LIVE calendar init images in one generated64x64m2 ROM, TX/RX consecutive-edge prefetch retains all init/production edges; frozen external ports unchanged, internal macro and physical re-kit owed.'
    target=out/(recipe.stem+'.image64.json');target.write_text(json.dumps(r,indent=2)+'\n')
    model={'schema':'opentallas.qc-dcal-image-rom.v1','recipe':rel(target),'source_recipe':rel(recipe),'source_profile':rel(profile),
      'source_profile_sha256':hashlib.sha256(profile.read_bytes()).hexdigest(),'manifest':rel(out/'content'/content['manifest']),
      'macro':P.NAME,'macro_instance':'u_cseq.u_seq.u_seq.u_image','macro_size_um':[12.312,9.192],
      'macro_area_um2':113.171904,'macro_read_bits_per_cycle':64,'cfg_write_bits_per_cycle':32,
      'init_edges':66,'new_init_edges':0,'new_production_edges':0,'tt_clk_to_q_ps':250.330,'ff_clk_to_q_ps':201.209,
      'clock_ps':833,'reset_contract':'clock running; reset spans at least one clock edge, as the delivered synchronous wavefront does',
      'physical_obligations':'New internal ROM in frozen QC glue/sys_face; add LEF and TT/FF libs, plan legal placement/tap, review before route, new kit and real-view timing. No frozen interface or token-rate claim changes.'}
    (out/'integration.json').write_text(json.dumps(model,indent=2)+'\n');return model

if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('recipe',type=Path);a.add_argument('profile',type=Path);a.add_argument('out',type=Path)
    q=a.parse_args();print(json.dumps(install(q.recipe,q.profile,q.out),indent=2))
