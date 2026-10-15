#!/usr/bin/env python3
"""Native embedding composition gate. Python supplies immutable ROM contents and
expected values only. Every output bit is computed and framed by actual RTL.
Consumes --words dumped by a prior real reader, or --row-bf16 raw5120xuint16.
These are ROM personalization inputs, never internal activation injections.
"""
import argparse, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fixtures(a):
    out=a.out;out.mkdir(parents=True,exist_ok=True)
    if a.row_bf16:
        raw=a.row_bf16.read_bytes()
        if len(raw)!=10240:raise ValueError('requires 5120 BF16 elements')
        row=[int.from_bytes(raw[2*i:2*i+2],'little') for i in range(5120)]
    else:
        row=[None]*5120;seen=set()
        for ln in a.words.read_text().splitlines():
            idx,d=ln.split();idx=int(idx);d=int(d,16);h,b=divmod(idx,8)
            if idx in seen or not 0<=idx<320:raise ValueError('duplicate/invalid word')
            seen.add(idx)
            for l in range(16):
                v=(d>>(32*l))&0xffffffff
                if v&65535:raise ValueError('not exact BF16')
                row[h*128+l*8+b]=v>>16
        if seen!=set(range(320)):raise ValueError('missing words')
    # Physical macro viamap: bit b of word a is cell [a//8][b*8+a%8].
    via=[0]*1024
    base=(a.token%32320*320)%4096
    if base+320>4096:raise ValueError('selected one-bank fixture crosses 4096 row boundary')
    for w in range(320):
        h,b=divmod(w,8);addr=base+w
        for l in range(16):
            word=row[h*128+l*8+b]
            for bit in range(16):
                if word>>bit&1:via[addr//8]|=1<<((16*l+bit)*8+addr%8)
    (out/'embed.viamap.hex').write_text(''.join(f'{r:0548x}\n' for r in via))
    # Expected-only oracle. Never read by the DUT, only by its scoreboard.
    expected=[sum(row[8*q+b]<<(16*(4*b+k)) for b in range(8) for k in range(4)) for q in range(640)]
    (out/'expected.mem').write_text(''.join(f'{r:0128x}\n' for r in expected))
    (out/'fixture.json').write_text(json.dumps(dict(token=a.token,base=base,owner=a.token//32320,
        bank=(a.token%32320*320)//4096,input_sha=sha(a.row_bf16 or a.words),
        rom_sha=sha(out/'embed.viamap.hex'),expected_sha=sha(out/'expected.mem')),indent=2)+'\n')
def run(a):
    a.out.mkdir(parents=True,exist_ok=True)
    files=[ROOT/'rtl/dsrom_sys/s81_embedding/tb_s81_embed_expand.sv',
      ROOT/'rtl/dsrom_sys/s81_embedding/ot_s81_embed_expand.sv',ROOT/'rtl/dsrom_sys/s81_embedding/ot_s81_embedding_bank.sv',ROOT/'rtl/dsrom_sys/ot_dsrom_embed_row_reader.sv',
      ROOT/'physical/asap7_memory_macros/ot_rom_8192x274_m8/ot_rom_8192x274_m8.v',
      ROOT/'physical/asap7_memory_macros/ot_sram_1r1w_512x128_m4_r2c2/ot_sram_1r1w_512x128_m4_r2c2.v']
    vl=Path.home()/'.local/opentallas-tools/verilator-5.050/bin/verilator'
    if not vl.exists():vl='verilator'
    evidence={'sources':{str(p.relative_to(ROOT)):sha(p) for p in files},'runs':{},'fixture':json.loads((a.vectors/'fixture.json').read_text())}
    for mutant in (0,1):
        obj=a.out/f'obj_m{mutant}'
        with (a.out/f'build_m{mutant}.log').open('w') as f:
            subprocess.run([str(vl),'--binary','--timing','-j','4','-Wno-fatal','--top-module','tb_s81_embed_expand',
              f'-GMUTANT={mutant}',f"-GTOKEN={json.loads((a.vectors/'fixture.json').read_text())['token']}",'--Mdir',str(obj),'-o','tb',*map(str,files)],stdout=f,stderr=subprocess.STDOUT,check=True)
        base=json.loads((a.vectors/'fixture.json').read_text())['base']
        p=subprocess.run([str(obj/'tb'),f'+BASE={base}',f'+OUT={a.out/f"hin_m{mutant}.mem"}'],cwd=a.vectors,
            capture_output=True,text=True)
        (a.out/f'run_m{mutant}.log').write_text(p.stdout+p.stderr)
        evidence['runs'][str(mutant)]={'returncode':p.returncode,'stdout':p.stdout}
        if (mutant==0 and (p.returncode!=0 or 'EMBED_NATIVE PASS' not in p.stdout)) or (mutant and p.returncode==0):
            raise RuntimeError(f'qualification failed m{mutant}: {p.stdout}')
    evidence['hin_sha256']=sha(a.out/'hin_m0.mem')
    evidence['scope']='ROM reader + mapped SRAM transpose + RTL expansion/VM port/hop framing; NOT whole die qualification'
    evidence['pass']=True
    (a.out/'record.json').write_text(json.dumps(evidence,indent=2)+'\n')
def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='cmd',required=True)
    f=sub.add_parser('fixtures');g=f.add_mutually_exclusive_group(required=True)
    g.add_argument('--words',type=Path);g.add_argument('--row-bf16',type=Path)
    f.add_argument('--token',type=int,required=True);f.add_argument('--out',type=Path,required=True)
    r=sub.add_parser('run');r.add_argument('--vectors',type=Path,required=True);r.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve()
    if a.cmd=='fixtures':fixtures(a)
    else:a.vectors=a.vectors.resolve();run(a)
if __name__=='__main__':main()
