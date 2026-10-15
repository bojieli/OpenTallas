#!/usr/bin/env python3
"""Real cmd380 packing + actual296-program address consumer gate and mutants."""
import argparse,ast,hashlib,json,re,subprocess,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import hdc_isa as ISA


def command_packer(root):
    source=root/'tools/qwen_missing/emit_partition.py'
    node=next(n for n in ast.parse(source.read_text()).body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='ME'for t in n.targets))
    table={x[0]:x for x in ast.literal_eval(node.value)}
    packing=root/'rtl/physical/ot_qfd_tt_ctlm_split.sv'
    terms=re.search(r'assign cmd\s*=\s*\{([^}]+)\};',packing.read_text()).group(1).split(',')
    mapping=[];offset=0
    for term in reversed(terms):
        name=term.strip().removeprefix('u_me_')
        _,expr,kind,width=table[name]
        assert kind=='out'
        w={'AW':24,'NW':18}.get(width,int(width)if width.isdigit()else 0)
        assert w>0
        mapping.append((expr,offset,w));offset+=w
    assert offset==380
    def encode(fields):
        result=0
        for name,offset,width in mapping:
            value=1 if name=='me_go'else fields[name]
            if not 0<=value<1<<width:raise ValueError('source command field overflow')
            result|=value<<offset
        return result
    return encode,{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in(source,packing)}


def run(root,manifest,out):
    out.mkdir(parents=True,exist_ok=True)
    pack,pins=command_packer(root)
    vectors=[]
    for stage in manifest['programs']:
        for op in stage['rom_operations']:
            fields=ISA.decode(int(op['word'],16));cmd=pack(fields)
            relocated=dict(fields,me_wbase=op['resident_wbase'],me_wcs=op['resident_wcs'])
            expected=pack(relocated)
            vectors.append((cmd,stage['stage'],expected,0))
    actual=len(vectors)
    # Native WSRC1 keeps every bit, including fields that mean KV strides,
    # regardless of ROM stage. Inactive payload is also left bit-identical.
    import random
    rand=random.Random(816)
    for _ in range(512):
        cmd=rand.getrandbits(380)|1|(1<<55)
        vectors.append((cmd,rand.randrange(64),cmd,0))
        cmd=rand.getrandbits(380)&~1
        vectors.append((cmd,rand.randrange(64),cmd,0))
    # A real out-of-range active ROM descriptor must fault without clipping.
    fields=ISA.decode(int(manifest['programs'][0]['rom_operations'][0]['word'],16))
    fields['me_wcs']=816;cmd=pack(fields)
    expected=(cmd&~(((1<<24)-1)<<255))|((816+816)<<255)
    expected=(expected&~(((1<<24)-1)<<56))|((fields['me_wbase']+512)<<56)
    vectors.append((cmd,2,expected,1))
    path=out/'vectors.hex'
    path.write_text(''.join(f'{(fault<<766)|(exp<<386)|(stage<<380)|cmd:0192x}\n'for cmd,stage,exp,fault in vectors))
    src=root/'rtl/qwen_sys/static_schedule_20261014/ot_qwen_tp8_rom_relocate.sv'
    tb=root/'rtl/test/qwen_static_schedule/tb_rom_relocate.sv'
    records=[]
    for mutant in ('normal','old_tp4_stride','missing_relocation'):
        text=src.read_text()
        if mutant=='old_tp4_stride':text=text.replace("24'd816;","24'd1056;")
        if mutant=='missing_relocation':text=text.replace("wire rom=in_cmd[0]&&!in_cmd[55];","wire rom=1'b0;")
        snapshot=out/f'{mutant}.sv';snapshot.write_text(text)
        exe=out/f'{mutant}.vvp'
        compile=subprocess.run(['iverilog','-g2012','-s','tb_rom_relocate',f'-Ptb_rom_relocate.N={len(vectors)}','-o',str(exe),str(snapshot),str(tb)],capture_output=True,text=True)
        if compile.returncode:raise RuntimeError(compile.stdout+compile.stderr)
        result=subprocess.run(['vvp',str(exe),'+VECTORS='+str(path)],capture_output=True,text=True)
        (out/f'{mutant}.log').write_text(result.stdout+result.stderr)
        if (result.returncode==0)!=(mutant=='normal'):raise AssertionError('relocation positive/mutant verdict mismatch')
        records.append(dict(case=mutant,exit_code=result.returncode,output=result.stdout+result.stderr,source_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest()))
    pins.update({str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest()for p in(src,tb,Path(__file__))})
    result=dict(status='ACTUAL_PROGRAM_ROM_RELOCATION_RTL_PASS',actual_programs=len(manifest['programs']),actual_ROM_commands=actual,total_vectors=len(vectors),cases=records,source_sha256=pins,claim='Actual296 program descriptor packing and resident code/scale relocation RTL. No native arithmetic, payload macro timing, full-token or physical closure claim.')
    (out/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(result['status'],actual,len(vectors))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[2]);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();run(a.root,json.loads(a.manifest.read_text()),a.out)
