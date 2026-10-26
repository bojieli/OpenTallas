"""Exact no-ECC content publication for existing generated ROM shapes.

Existing content tools keep their logical payload, address order and macro width.
This adapter delegates physical bit placement and read-back to rom_gen, and keeps
the published via-map filename unchanged. Sidecars live below .rom-personalisation.
"""
from __future__ import annotations
from functools import lru_cache
import hashlib,json
from pathlib import Path
from . import rom_gen

ROOT=Path(__file__).resolve().parents[2]


@lru_cache(maxsize=None)
def contract(name):
    sheet=ROOT/'physical/asap7_memory_macros_v2'/name/f'{name}.json'
    if not sheet.is_file():raise ValueError(f'no generated ROM datasheet for{name}')
    return rom_gen.spec_from_sheet(sheet),sheet


def read_sparse_hex(path: Path,depth=4096) -> dict[int,int]:
    """Read existing @address logical images without changing holes or values."""
    address=0;words={}
    for line in Path(path).read_text().splitlines():
        line=line.split('//',1)[0].strip()
        if not line:continue
        if line.startswith('@'):
            address=int(line[1:],16);continue
        if not 0<=address<depth:raise ValueError(f'ROM address out of range:{address}')
        value=int(line,16)
        if address in words and words[address]!=value:raise ValueError(f'conflicting ROM writes at{address}')
        words[address]=value;address+=1
    return words


def write_viamap(path: Path,words,macro: str) -> dict:
    """Publish bit-identical physical via rows and verify the actual no-ECC image."""
    path=Path(path);suffix='.viamap.hex'
    if not path.name.endswith(suffix):raise ValueError('expected a .viamap.hex output name')
    instance=path.name[:-len(suffix)]
    spec,sheet=contract(macro)
    if isinstance(words,dict):
        dense=[0]*spec.words
        for a,v in words.items():
            if not isinstance(a,int) or not 0<=a<spec.words:raise ValueError(f'ROM address out of range:{a}')
            dense[a]=int(v)
    else:
        dense=[int(v) for v in words]
        if len(dense)>spec.words:raise ValueError('logical words exceed macro depth')
        dense += [0]*(spec.words-len(dense))
    if any(v<0 or v>=(1<<spec.bits) for v in dense):raise ValueError('logical word exceeds existing macro width')
    side=path.parent/'.rom-personalisation'/instance;side.mkdir(parents=True,exist_ok=True)
    image=side/'logical.hex';digits=(spec.bits+3)//4
    image.write_text(''.join(f'{v:0{digits}x}\n' for v in dense))
    rec=rom_gen.personalise_instance(spec,dense,instance+'_r0_c0',side)
    generated=side/rec['viamap'];path.parent.mkdir(parents=True,exist_ok=True)
    generated.replace(path)
    rec['viamap']='../../'+path.name
    manifest={'schema':'opentallas.rom-personalisation.v1','macro':macro,'ecc':'none',
      'image':image.name,'image_sha256':rom_gen.asap7.sha256_file(image),
      'data_bits':spec.bits,'tile_data_bits':spec.bits,'instances':[rec],
      'content_signature':rom_gen.die_signature([rec]),
      'viamap_set_sha256':hashlib.sha256(rec['viamap_sha256'].encode()).hexdigest(),
      'payload_policy':'existing logical words and macro width unchanged; no ECC or numerical conversion'}
    target=side/f'{instance}.personalisation.json';target.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    check=rom_gen.verify_personalisation(target,image,sheet)
    if check['verdict']!='PASS':raise ValueError(f'ROM content verification failed:{check}')
    (side/'verify.json').write_text(json.dumps(check,indent=2,sort_keys=True)+'\n')
    return {'manifest':str(target.relative_to(path.parent)),'verdict':check['verdict'],
            'macro':macro,'ecc':'none','words_checked':check['words_checked'],'viamap_sha256':rec['viamap_sha256']}
