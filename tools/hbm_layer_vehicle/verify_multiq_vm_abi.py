"""Pure actual-cut VM-address ABI proof; never executes or qualifies RTL."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--legacy-case',type=Path,required=True)
    p.add_argument('--multi-boundary',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    generator=Path(__file__).with_name('gen_slice_tb.py')
    def generate(boundary,out,replays,nev=None):
        cmd=[sys.executable,str(generator),'--boundary',str(boundary),'--out',str(out)]
        if nev is not None:cmd+=['--nev',str(nev)]
        for r in replays:cmd+=['--replay',str(r)]
        return subprocess.run(cmd,capture_output=True,text=True)
    source=a.legacy_case/'bundle/slice'
    result=generate(source/'boundary.json',a.out/'legacy',sorted((a.legacy_case/'rj').glob('*.json')),11651)
    assert result.returncode==0,result.stderr
    assert (source/'tb_slice.sv').read_bytes()==(a.out/'legacy/tb_slice.sv').read_bytes()
    compared=0
    for old in sorted((source/'replay').rglob('*')):
        if old.is_file() and old.name in ('hdr.mem','val.mem','msk.mem','vm_pre.txt'):
            new=a.out/'legacy/replay'/old.relative_to(source/'replay')
            assert new.read_bytes()==old.read_bytes(),str(old)
            compared+=1
    events=[]
    for q in range(4):
        for bank in range(8):
            sector=(q<<13)|8|bank;value=f'{(q+1)*0x100+bank:08x}'*8
            events +=[dict(k='M',dom='stream',cyc=0,mem='vm',quarter=q,sector=sector,bank=bank,row=1,
                          val=value,src='PURE_ABI_SYNTHETIC_INPUT_NOT_HARDWARE_PROOF'),
                      dict(k='C',dom='stream',cyc=40+8*q+bank,port=f'vm:{sector:x}',val=value,mask='f'*64)]
    replay=a.out/'distinct_quarters.json';replay.write_text(json.dumps(dict(events=events)))
    result=generate(a.multi_boundary,a.out/'multi',[replay]);assert result.returncode==0,result.stderr
    d=a.out/'multi/replay/distinct_quarters'
    headers=[int(s,16) for s in (d/'hdr.mem').read_text().split()][:-1]
    assert [((h>>44)&0x6000)>>13 for h in headers]==[q for q in range(4) for _ in range(8)]
    assert [((h>>44)&0x1c00)>>10 for h in headers]==list(range(8))*4
    assert len({(h>>44)&0xffff for h in headers})==32
    rows=[s.split() for s in (d/'vm_pre.txt').read_text().splitlines()]
    assert len(rows)==32 and all(len(row)==5 for row in rows)
    assert [int(row[0],16) for row in rows]==[q for q in range(4) for _ in range(8)]
    tb=(a.out/'multi/tb_slice.sv').read_text()
    assert all(f'{i}: vm_get =' in tb for i in range(32))
    events[-1]['port']='vm:8008'
    invalid=a.out/'invalid_mirror.json';invalid.write_text(json.dumps(dict(events=events)))
    bad=generate(a.multi_boundary,a.out/'mirror_refused',[invalid])
    assert bad.returncode and 'does not encode mirror' in bad.stderr
    events[-1]['port']='vm:600f';events[0]['quarter']=1
    invalid2=a.out/'ambiguous_quarter.json';invalid2.write_text(json.dumps(dict(events=events)))
    bad=generate(a.multi_boundary,a.out/'ambiguous_refused',[invalid2])
    assert bad.returncode and 'quarter disagrees' in bad.stderr
    b=json.loads(a.multi_boundary.read_text());b['instances'].remove('hb_ckgen')
    clockless=a.out/'clockless_boundary.json';clockless.write_text(json.dumps(b))
    bad=generate(clockless,a.out/'clockless_refused',[])
    assert bad.returncode and 'actual hb_ckgen' in bad.stderr
    receipt=dict(status='PASS_PURE_SOURCE_ABI_ONLY',hardware_executed=False,legacy_TB_byte_identical=True,
        legacy_TB_sha256=hashlib.sha256((source/'tb_slice.sv').read_bytes()).hexdigest(),
        legacy_replay_memory_files_byte_identical=compared,multi_quarter_bank_addresses_distinct=32,
        mirror_refused=True,ambiguous_M_quarter_refused=True,missing_clock_source_refused=True,
        boundary_sha256=hashlib.sha256(a.multi_boundary.read_bytes()).hexdigest(),
        new_TB_sha256=hashlib.sha256((a.out/'multi/tb_slice.sv').read_bytes()).hexdigest(),
        source_case=str(a.legacy_case),new_boundary=str(a.multi_boundary),artifact_root=str(a.out))
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(receipt))


if __name__=='__main__':main()
