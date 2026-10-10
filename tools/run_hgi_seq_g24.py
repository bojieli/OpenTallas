#!/usr/bin/env python3
"""Focused G24 transaction gate; reuse sequencer bench, leave pinned vectors intact."""
import json
import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path
import hgi_seq_vectors as S
ROOT = Path(__file__).resolve().parents[1]

def main():
    out = ROOT / 'results/rtl/hgi_seq_g24_20261010'
    out.mkdir(parents=True, exist_ok=True)
    td = Path(tempfile.mkdtemp(prefix='hgi-g24-'))
    src = ROOT / 'rtl/hbm_accel/generic'
    for p in (src / 'tb').glob('hgi_seq*'):
        shutil.copy(p, td / p.name)
    words, cases, ex, vmi, vmw, names = [], [], [], [], [], []
    end = S.record(S.header('CTL', 'END', wait=0xFFFE), descs={'A': S.mdesc(space=1, fmt=5, base=0x8001, n=1)})
    body = S.record(S.header('DMA', 'LOAD'))
    for name, count, addr, nested, producer in [
        ('wait_snapshot', 3, 0x7000, False, True),
        ('65535_accepted', 65535, 0x7000, False, False),
        ('one', 1, 0x7000, False, False),
        ('nested_levels', 2, 0x7000, True, False),
        ('zero', 0, 0x7000, False, False),
        ('65536', 65536, 0x7000, False, False),
        ('all_bits', 0xffffffff, 0x7000, False, False),
        ('address_range', 2, 1 << 18, False, False),
        ('last_address', 2, (1 << 18)-1, False, False)]:
        entry = len(words)
        prog = S.record(S.header('IDX', 'TOPK')) if producer else []
        if nested:
            prog += S.record(S.header('CTL', 'LOOP', param=2))
        prog += S.record(S.header('CTL', 'LOOP', param=(1 << 17) | (int(nested) << 16), imm_a=addr, wait=1 << 9 if producer else 0))
        if name != '65535_accepted':
            prog += body + S.record(S.header('CTL', 'ENDLOOP'))
        if nested:
            prog += S.record(S.header('CTL', 'ENDLOOP'))
        prog += end
        words += prog
        ci = len(cases)
        vm = {0x8001: 4242, addr: 1 if producer else count}
        disp = lambda k,u,o: [(addr, count)] if producer and u == 'IDX' else []
        ref = S.Ref(words, entry, 1, 100, 0, 151936, 40960, vm, disp)
        tr, cpl = ref.run()
        first = len(ex)//11
        for k,d in enumerate(tr):
            mw=d['unit'] | d['L'] << 4 | d['L1'] << 20 | d['pos1'] << 36 | d['pslot1'] << 57
            ex += [mw,d['hdr'],d['sut']] + d['eff'] + [sum(n << (21*j) for j,n in enumerate(d['n']))]
            for a,v in disp(k,S.UNITS[d['unit']],S.OPS[S.UNITS[d['unit']]][S.field(d['hdr'],S.UOP,'op')]):
                vmw.append(((first+k) << 64) | (a << 32) | v)
        cases.append((entry,1,100,0,151936,40960,len(tr),cpl[0],cpl[1],0xffff,first,0))
        vmi += [(ci,0x8001,4242),(ci,addr,1 if producer else count)] if addr < 1 << 18 else [(ci,0x8001,4242)]
        names.append(dict(name=name,dispatches=len(tr),status=cpl[1]))
    def write(n,lines): (td/n).write_text('\n'.join(lines)+'\n')
    write('hgi_seq_image_conf.mem',[f'{v:032X}' for v in words])
    write('hgi_seq_expect_conf.mem',[f'{v:064X}' for v in ex])
    write('hgi_seq_cfg_conf.mem',[' '.join(f'{v:08X}' for v in c) for c in cases])
    write('hgi_seq_vmi_conf.mem',[f'{c:08X}{a:08X}{v:08X}' for c,a,v in vmi])
    write('g24_vmw.mem',[f'{v:024X}' for v in vmw] + ['F'*24]*(4096-len(vmw)))
    write('hgi_seq_sizes_conf.svh',[f'localparam integer CONF_{k} = {v};' for k,v in dict(NCASE=len(cases),NW=len(words),NEXP=len(ex),NVMI=len(vmi)).items()])
    bench=(src/'tb/tb_hgi_seq.sv').read_text().replace('endmodule', "initial begin #1; $readmemh(\"g24_vmw.mem\", vmw); end\nendmodule")
    (td/'tb_hgi_seq.sv').write_text(bench)
    result=[]
    for mutant in (False,True):
        args=['iverilog','-g2012','-DSEQ_CONF','-I'+str(td),'-s','tb_hgi_seq','-o',str(td/'sim.vvp'),str(td/'tb_hgi_seq.sv'),str(src/'ot_hgi_seq.sv')]
        if mutant: args.insert(2,'-DOT_HGI_SEQ_MUT_WAIT')
        subprocess.run(args,check=True,cwd=td,capture_output=True)
        run=subprocess.run(['vvp',str(td/'sim.vvp')],cwd=td,text=True,capture_output=True)
        (out/('mut_wait.log' if mutant else 'pass.log')).write_text(run.stdout+run.stderr)
        passed='HGI_SEQ PASS' in run.stdout and run.returncode==0
        result.append(dict(mutant=mutant,passed=passed,returncode=run.returncode))
    rec=dict(cases=names,runs=result,source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in (src/'ot_hgi_seq.sv', Path(__file__), ROOT/'tools/hgi_seq_vectors.py')},rtl_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip())
    (out/'gate.json').write_text(json.dumps(rec,indent=2)+'\n')
    shutil.rmtree(td)
    print(json.dumps(rec))
    return 0 if result[0]['passed'] and not result[1]['passed'] else 1
if __name__ == '__main__': raise SystemExit(main())
