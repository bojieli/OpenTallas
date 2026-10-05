"""Exact archived capture libraries; no historical ECC tool dependencies."""
import functools,gzip,hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/uarch/dsrom_noECC_capture_intrinsic_20261002'
def block(text,start):
    pos=text.index('{',start);depth=1;end=pos+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}');end+=1
    return text[start:end]
@functools.lru_cache(maxsize=12)
def library_text(name):
    path=BASE/'terminal_r4'/(name+'.gz')
    hashes=json.loads((BASE/'terminal_hashes.json').read_text())
    if hashlib.sha256(path.read_bytes()).hexdigest()!=hashes[str(path.relative_to(BASE))]:raise ValueError('Archived actual STA library changed')
    text=gzip.decompress(path.read_bytes()).decode()
    if not re.search(r'time_unit\s*:\s*"1ps"',text) or not re.search(r'capacitive_load_unit\s*\(1,\s*ff\)',text):raise ValueError('Unexpected archived library units')
    return text
@functools.lru_cache(maxsize=2)
def cell_bodies(corner):
    if corner not in ('ss','ff'):raise ValueError('SS/FF only')
    out={}
    for family in ('ao','invbuf','oa','simple','seq'):
        text=library_text(f'{family}_{corner}.lib')
        for m in re.finditer(r'\bcell\s*\(([^)]+)\)',text):
            name=m[1].strip(' "');body=block(text,m.start())
            if name in out and out[name]!=body:raise ValueError('Conflicting archived cell')
            out[name]=body
    return out
