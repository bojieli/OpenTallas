#!/usr/bin/env python3
"""One full six-column lookup+credit service; reuse across eight static straps."""
import hashlib,json,subprocess,tempfile
from pathlib import Path
import engram_boot_image as B
import hdc_v41_engram_shipped as E
R=Path(__file__).resolve().parents[1]
paths=[E.PKG,E.HASH_OUT,*[R/'rtl/dsrom_sys/engram'/x for x in ['ot_dsrom_engram_lookup.sv','dsfd_engram_lkp.sv','ot_dsrom_engram_rowstripe_read.sv','ot_dsrom_engram_rowstripe_service.sv']],R/'rtl/dsrom_sys/s81_ctrl/ot_s81_secded.sv',R/'rtl/test/tb_dsrom_engram_rowstripe_lookup.sv',R/'rtl/test/hdc_v41_tb_harness.cpp']
out=R/'results/rtl/engram_rowstripe_lookup_gate_20261009.json'
def main():
    if out.exists():raise FileExistsError(out)
    t=E.shipped_tables();hashes=E.hashes(t,[1,2,3,4]);primes=t.primes.reshape(2,24);offsets=t.offsets.reshape(2,24)
    rec=dict(schema='opentallas.engram-rowstripe-lookup-gate.v1',boundary='one full six-column lookup/hardened credit wrapper/read service, eight sequential static layer/rank straps; synthetic row content, released hash/CRC/addresses; no physical/die claim',input_sha256={str(p.relative_to(R)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths+[R/'tools/uarch_model.py',R/'tools/engram_boot_image.py',Path(__file__)]},cases={})
    with tempfile.TemporaryDirectory() as tmp:
        work=Path(tmp);obj=work/'obj';top='tb_dsrom_engram_rowstripe_lookup'
        build=subprocess.run(['verilator','--cc','--exe','--build','-O2','-Wno-fatal','-Wno-WIDTH','-Wno-UNUSED','-Wno-BLKSEQ','--top-module',top,'-Mdir',str(obj),*[str(p) for p in paths],'-CFLAGS',f'-O1 -DVTOP=V{top}'],capture_output=True,text=True)
        if build.returncode:raise RuntimeError(build.stderr[-3000:])
        for layer in range(2):
            for rank in range(4):
                atoms=[];beats=[];requests=[];bases=B.column_bases(primes[layer,rank*6:rank*6+6],True)
                for j in range(6):
                    col=rank*6+j;row=hashes[layer][col];res=row-int(offsets[layer,col])
                    codes,scale=E.row_bytes(layer,row)
                    payload=bytes(codes)+bytes([scale])+bytes(7)
                    packed=B.packed_row(payload,True)
                    atoms += [packed[i:i+32] for i in range(0,288,32)]
                    beats += [packed[i:i+32]+bytes([scale]) for i in range(0,256,32)]
                    ordinal=(bases[j]+res*288)//288
                    pc=(ordinal%2)*32+(ordinal//2)%32;local=(ordinal//64)*9
                    requests.append((pc<<32)|local)
                af=work/'atoms.hex';bf=work/'beats.hex';rf=work/'rq.hex'
                af.write_text(''.join(f'{int.from_bytes(x,"little"):064x}\n' for x in atoms));bf.write_text(''.join(f'{int.from_bytes(x,"little"):066x}\n' for x in beats));rf.write_text(''.join(f'{x:016x}\n' for x in requests))
                run=subprocess.run([str(obj/f'V{top}'),f'+LAYER={layer}',f'+RANK={rank}',f'+ATOMS={af}',f'+BEATS={bf}',f'+RQ={rf}'],capture_output=True,text=True)
                rec['cases'][f'L{layer}_R{rank}']=dict(returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,expected_observed=run.returncode==0 and 'ENGRAM_ROWSTRIPE_LOOKUP PASS' in run.stdout)
    rec['status']='pass' if all(x['expected_observed'] for x in rec['cases'].values()) else 'fail'
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(rec,indent=1)+'\n');print(rec['status']);return int(rec['status']!='pass')
if __name__=='__main__':raise SystemExit(main())
