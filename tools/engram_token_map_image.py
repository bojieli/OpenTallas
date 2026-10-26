#!/usr/bin/env python3
"""Pack the committed released tokenizer map into eight real no-ECC ROM masks."""
import ast,hashlib,json
from pathlib import Path
import numpy as np
from mem_compiler.rom_content import write_viamap
R=Path(__file__).resolve().parents[1]
SOURCE=R/'results/uarch/h4_c0_ds_external_source_provenance_20261003/r1/payloads/fbc8c3ec76fc1143_L01_token_map.npy'
SHA='fbc8c3ec76fc11430b854fb2ff267fdf923b5ff2d4f869e3c0433d8edc6479b1'
def prepare(out):
    if out.exists():raise FileExistsError(out)
    if hashlib.sha256(SOURCE.read_bytes()).hexdigest()!=SHA:raise ValueError('released map identity')
    a=np.load(SOURCE,allow_pickle=False)
    if a.shape!=(129280,) or a.dtype!=np.int64 or int(a.min())!=0 or int(a.max())!=99091 or len(set(a.tolist()))!=99092:raise ValueError('released map geometry')
    out.mkdir(parents=True)
    words=[sum(int(a[i+j])<<(17*j) for j in range(4)) for i in range(0,len(a),4)]
    for bank in range(8):
        chunk=words[bank*4096:(bank+1)*4096]
        write_viamap(out/f'tmap{bank}.viamap.hex',chunk,'ot_rom_4096x72_m8')
    (out/'expected.hex').write_text(''.join(f'{int(v):05x}\n' for v in a))
    src=R/'tools/uarch_model.py';tree=ast.parse(src.read_text())
    fn=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='dsrom_engram_lead_model']
    ns={};exec(compile(ast.Module(body=fn,type_ignores=[]),str(src),'exec'),ns)
    rec=ns['dsrom_engram_lead_model']();rec.update(pad_compressed=int(a[2]),source_sha256=SHA,
        unified_model_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
        images={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()})
    (out/'receipt.json').write_text(json.dumps(rec,indent=1)+'\n')
    return rec
if __name__=='__main__':
    import sys
    print(json.dumps(prepare(Path(sys.argv[1])),indent=1))
