#!/usr/bin/env python3
"""Personalise one content-independent QC TX/RX calendar ROM.

Word i = {RX[i][31:0], TX[i][31:0]}, for32or64 image entries. A32-entry image
uses zero in rows32..63. Only the via layer depends on the compiled calendar.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path
import rom_gen

NAME="ot_rom_64x64_m2"
ROOT=Path(__file__).resolve().parents[2]
MACRO=ROOT/'physical/asap7_memory_macros_v2'/NAME/f'{NAME}.json'


def compile_shape(out: Path) -> dict:
    import build_aligned_v2 as aligned
    spec=rom_gen.RomSpec(NAME,64,64,2)
    v1=rom_gen.compile_macro(spec)
    with aligned.patched(rom_gen,macro_outline=aligned.aligned_outline,
                         write_lef=aligned.aligned_write_lef,
                         GENERATOR_VERSION=f"{rom_gen.GENERATOR_VERSION}+{aligned.ALIGN_VERSION}"):
        sheet=rom_gen.compile_macro(spec,out)
    aligned.finish(out,NAME,v1,(v1['area']['macro_width_um'],v1['area']['macro_height_um']),
                   {'kind':'rom','spec':sheet['spec']})
    return json.loads((out/NAME/f'{NAME}.json').read_text())


def pack_profile(profile: dict) -> list[int]:
    if set(profile)!={'TX','RX'}:
        raise ValueError('profile must have exactly TX and RX word arrays')
    tx,rx=profile['TX'],profile['RX']
    if not isinstance(tx,list) or not isinstance(rx,list) or len(tx)!=len(rx) or len(tx) not in(32,64):
        raise ValueError('TX and RX must each have32or64entries')
    for port,words in [('TX',tx),('RX',rx)]:
        for i,value in enumerate(words):
            if isinstance(value,bool) or not isinstance(value,int) or not 0<=value<(1<<32):
                raise ValueError(f'{port}[{i}] must be an unsigned32-bitword')
    return [a|(b<<32) for a,b in zip(tx,rx)]+[0]*(64-len(tx))


def extract_sv(text: str,prefix: str='D2D_CAL_C') -> dict:
    """Extract literal packed images from generated localparams, LSB entry first."""
    text=re.sub(r'/\*.*?\*/','',text,flags=re.S)
    text=re.sub(r'//[^\n]*','',text)
    profile={}
    for port in ('TX','RX'):
        name=prefix+'_'+port+'_IMG'
        matches=re.findall(r'\blocalparam\b[^;]*?\b'+re.escape(name)+r'\s*=\s*([^;]+);',text)
        if len(matches)!=1:raise ValueError(f'expected one{name},found{len(matches)}')
        raw=matches[0].strip().replace('_','')
        m=re.fullmatch(r"(\d+)'([hdb])([0-9a-f]+)",raw,re.I)
        if not m:raise ValueError(f'{name} is not a known sized literal')
        width=int(m.group(1));value=int(m.group(3),{'h':16,'d':10,'b':2}[m.group(2).lower()])
        if width not in(1024,2048) or value>=(1<<width):raise ValueError(f'{name} must fit32or64packedwords')
        profile[port]=[(value>>(32*i))&0xffffffff for i in range(width//32)]
    pack_profile(profile)
    return profile


def personalise(profile: dict,out: Path,instance: str='qc_dcal',macro: Path=MACRO) -> dict:
    if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',instance):raise ValueError('invalid instance identifier')
    spec=rom_gen.spec_from_sheet(macro)
    if spec!=rom_gen.RomSpec(NAME,64,64,2):raise ValueError('QC calendar requires64x64m2shape')
    words=pack_profile(profile);out.mkdir(parents=True,exist_ok=True)
    image=out/f'{instance}.hex';image.write_text(''.join(f'{w:016x}\n' for w in words))
    rec=rom_gen.personalise_instance(spec,words,instance+'_r0_c0',out)
    pf=out/f'{instance}.profile.json';pf.write_text(json.dumps(profile,indent=2,sort_keys=True)+'\n')
    manifest={'schema':'opentallas.rom-personalisation.v1','macro':NAME,'ecc':'none',
      'image':image.name,'image_sha256':rom_gen.asap7.sha256_file(image),'data_bits':64,'tile_data_bits':64,
      'instances':[rec],'content_signature':rom_gen.die_signature([rec]),
      'viamap_set_sha256':hashlib.sha256(rec['viamap_sha256'].encode()).hexdigest(),
      'profile':pf.name,'profile_sha256':rom_gen.asap7.sha256_file(pf),
      'profile_schema':'opentallas.qc-dcal-profile.v1','word_layout':{'TX':[0,31],'RX':[32,63]},
      'image_entries':len(profile['TX'])}
    mf=out/f'{instance}.personalisation.json';mf.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    check=rom_gen.verify_personalisation(mf,image,macro)
    if check['verdict']!='PASS':raise ValueError(f'ROM content verification failed:{check}')
    return {'manifest':mf.name,'image':image.name,'viamap':rec['viamap'],'check':check}


def main() -> int:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('profile',nargs='?',type=Path)
    ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--compile-shape',action='store_true')
    ap.add_argument('--sv',action='store_true')
    ap.add_argument('--prefix',default='D2D_CAL_C')
    ap.add_argument('--instance',default='qc_dcal')
    ap.add_argument('--macro',type=Path,default=MACRO)
    a=ap.parse_args()
    if a.compile_shape:
        sheet=compile_shape(a.out);print(json.dumps({'spec':sheet['spec'],'area':sheet['area'],'timing':sheet['timing']},indent=2));return 0
    if a.profile is None:ap.error('profile required unless --compile-shape')
    data=extract_sv(a.profile.read_text(),a.prefix) if a.sv else json.loads(a.profile.read_text())
    print(json.dumps(personalise(data,a.out,a.instance,a.macro),indent=2));return 0


if __name__=='__main__':raise SystemExit(main())
