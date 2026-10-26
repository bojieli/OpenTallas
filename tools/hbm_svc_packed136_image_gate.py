#!/usr/bin/env python3
"""Bit-preserving packed image and real RTL inverse-map component gate."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from hbm_svc_packed136_image import install,mapped_sector,sector_address,sector_pc

ROOT=Path(__file__).resolve().parents[1]


def gate(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    a=dict(schema='opentallas.hbm-packed136-allocation.v1',allocation_id='component-test-only',
        provenance='Procedural byte-identity vectors, not a released checkpoint or production allocation',
        pcs=[4,17,2,31],stack=3,row_base=101,row_count=4,stack_bytes=1<<35)
    ap=out/'allocation.json';ap.write_text(json.dumps(a))
    sizes=[1,2,3,4,5,15,16,17,63,64,127]
    rows=0;sectors=0;cases=[]
    for n in sizes:
        raw=b''.join(bytes(((row*19+byte*7+(byte>>2))&255) for byte in range(136)) for row in range(n))
        source=out/f'logical_{n}.hex';source.write_text(''.join(f'{int.from_bytes(raw[r*136:(r+1)*136],"little"):0272x}\n' for r in range(n)))
        sha=hashlib.sha256(source.read_bytes()).hexdigest()
        r=install(source,sha,n,ap,out/f'image_{n}')
        index=[json.loads(x) for x in (out/f'image_{n}'/'ordinal.jsonl').read_text().splitlines()]
        lines=(out/f'image_{n}'/'physical.hex').read_text().splitlines()
        packed=b''.join(int(lines[2*j+1],16).to_bytes(32,'little') for j in range(r['sectors']))
        assert packed[:len(raw)]==raw and not any(packed[len(raw):])
        assert len(packed)==((n*136+127)//128)*128
        for j,e in enumerate(index):
            assert e['sector']==int(lines[2*j][1:],16)==sector_address(j,a)
            assert e['pc']==a['pcs'][j%4]==sector_pc(e['sector'])
            assert e['global_sector']==(3<<30)|e['sector']
        assert len({x['sector'] for x in index})==len(index)
        rows+=n;sectors+=r['sectors'];cases.append(dict(rows=n,sectors=r['sectors'],bytes=len(packed)))
    # Wrong source pins, malformed allocations and bounds fail before publishing.
    rejects=0
    try:install(source,'0'*64,n,ap,out/'wrongsha')
    except ValueError:rejects+=1
    for update in [dict(pcs=[1,1,2,3]),dict(row_count=0),dict(stack_bytes=32),dict(provenance='')]:
        bad=dict(a,**update);p=out/'bad_allocation.json';p.write_text(json.dumps(bad))
        try:install(source,sha,n,p,out/'bad_output')
        except ValueError:rejects+=1
        else:raise AssertionError('invalid allocation accepted')
        assert not (out/'bad_output').exists()
    # Compare Python packed allocator against actual inverse mapping RTL on all
    # PC IDs, bank permutations and nonzero rows (including high native regions).
    tb=['module tb;reg [4:0] pc,bank,col;reg [18:0] row;wire[29:0]s;wire fault;ot_hbm_kport_map dut(.*);initial begin']
    count=0
    for pc in range(32):
        for row in [0,1,2,7,101,20736,32767]:
            for bank in [0,1,3,7,16,31]:
                col=(pc+bank+row)%32;expected=mapped_sector(pc,bank,row,col)
                tb.append(f'pc=5\'d{pc};bank=5\'d{bank};row=19\'d{row};col=5\'d{col};#1;if(fault||s!==30\'d{expected})$fatal(1,"actual RTL mapping disagreement");')
                count+=1
    tb+=['$display("PACKED136_RTL_MAP PASS vectors='+str(count)+'");$finish;end endmodule']
    (out/'tb.sv').write_text('\n'.join(tb)+'\n')
    exe=out/'map.vvp';subprocess.run(['iverilog','-g2012','-s','tb','-o',str(exe),str(ROOT/'rtl/hbm_accel/service/ot_hbm_kport_map.sv'),str(out/'tb.sv')],check=True)
    log=subprocess.check_output(['vvp',str(exe)],text=True);assert 'PACKED136_RTL_MAP PASS' in log
    (out/'rtl_map.log').write_text(log)
    # Mutate a real row/bank mapping bit; RTL comparison must reject it.
    original=(ROOT/'rtl/hbm_accel/service/ot_hbm_kport_map.sv').read_text()
    mutant=original.replace('bank[1:0] ^ row[1:0]','bank[1:0]')
    assert mutant!=original;(out/'mutant.sv').write_text(mutant)
    subprocess.run(['iverilog','-g2012','-s','tb','-o',str(out/'mutant.vvp'),str(out/'mutant.sv'),str(out/'tb.sv')],check=True)
    bad=subprocess.run(['vvp',str(out/'mutant.vvp')],text=True,capture_output=True)
    assert bad.returncode!=0 and 'mapping disagreement' in bad.stdout
    (out/'mutant.log').write_text(bad.stdout)
    receipt=dict(status='PACKED136_IMAGE_MAPPING_PASS_PRODUCTION_UNBOUND',fixture_scope='procedural byte identity, not checkpoint',rows=rows,sectors=sectors,layout_cases=cases,rejected_invalid_inputs=rejects,actual_RTL_map_vectors=count,mutant_rejected=True,source_sha256={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in ['tools/hbm_svc_packed136_image.py','tools/hbm_svc_packed136_image_gate.py','tools/w19_payload_loader.py','rtl/hbm_accel/service/ot_hbm_kport_map.sv']})
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',required=True);a=p.parse_args();print(json.dumps(gate(a.out),indent=2))
