#!/usr/bin/env python3
"""Full-width image/allocator component gate; no hardware installation claim."""
import hashlib,json,tempfile,subprocess
from pathlib import Path
from hbm_sm_native_install import install,sha,ROOT
from gpu_sys.mem_image import placement
from hbm_sm_native_allocation_build import build

def run():
    with tempfile.TemporaryDirectory(prefix='native_install_') as d:
        d=Path(d); seq=[2,8,1,2,2,1,1,8,1,121,2,8,1,2,2,1,0,8,1,121]
        lines=[(1<<1087)|(i<<256)|i for i in range(4)]
        xs=[(1<<25215)|(i<<2048)|i for i in range(8)]
        for name,vals in [('seq.hex',seq),('lines.hex',lines),('x.hex',xs)]:
            (d/name).write_text('\n'.join(f'{v:x}' for v in vals)+'\n')
        manifest=dict(schema='opentallas.native_sm.payload.v1',nc=8,provenance='deterministic full-width installer mechanism fixture; not checkpoint or arithmetic evidence',artifacts={n:dict(path=n,sha256=sha(d/n)) for n in ('seq.hex','lines.hex','x.hex')})
        mp=d/'source.json';mp.write_text(json.dumps(manifest))
        original_book=ROOT/'results/rtl/dshbm_installer_book_20261005/workspace.json'
        fixture_book=json.loads(original_book.read_text())
        # Test-only cursor, never represented as an actual live installation.
        fixture_book['recipe_successor']=dict(emitted_image_bytes=fixture_book['original_image_bytes'],allocations=[])
        bp=d/'fixture_workspace.json';bp.write_text(json.dumps(fixture_book))
        r=install(bp,mp,d/'out');mem={}
        for part in range(2):
            tokens=(d/'out'/f'native_p{part}.hex').read_text().split()
            for at,data in zip(tokens[::2],tokens[1::2]):mem[(part,int(at[1:],16))]=bytes.fromhex(data)[::-1]
        def read(addr,size):
            data=b''
            for off in range(0,size,32):
                p,s,_,lane=placement(addr+off,2,2097152);assert lane==0;data+=mem[(p,s)]
            return data[:size]
        assert read(r['program_base'],80)==b''.join(v.to_bytes(4,'little') for v in seq)
        for i,rec in enumerate(r['records']):
            assert rec['weight_byte_base']==rec['weight_line_base']*160
            for j in range(2):
                raw=read(rec['weight_byte_base']+160*j,160)
                assert raw[:136]==lines[i*2+j].to_bytes(136,'little') and raw[136:]==bytes(24)
            for j in range(8):
                raw=read(rec['x_byte_base']+3328*j,3328)
                assert raw[:3152]==xs[j].to_bytes(3152,'little') and raw[3152:]==bytes(176)
            assert all(not(s['base']<=rec['result_byte_base']<s['end']) or s['reserved_only'] for s in r['spans'])
        assert r['records'][0]['x_byte_base']==r['records'][1]['x_byte_base']
        assert not r['hardware_ownership_granted'] and not r['loader_acknowledged']
        build(d/'out/installed_spans.json',d/'allocation.sv')
        tb="""module tb;reg clk=0;always #5 clk=~clk;reg rst_n=0,req_valid=0,rsp_ready=0;
reg[15:0]req_record=0;reg[23:0]req_lines=2;wire req_ready,rsp_valid,rsp_error,fault;wire[15:0]rsp_record;wire[31:0]rsp_base;
ot_hbm_sm_native_allocation #(.ENABLE(1)) dut(.*);
task request(input[15:0]r,input[23:0]n);begin @(negedge clk);req_record=r;req_lines=n;req_valid=1;@(negedge clk);req_valid=0;end endtask
initial begin #12;rst_n=1;request(0,2);if(!rsp_valid||rsp_error||rsp_record!=0||rsp_base!=BASE)$fatal(1,"literal allocation");
repeat(3)begin @(negedge clk);if(!rsp_valid||req_ready)$fatal(1,"held response");end
rsp_ready=1;@(negedge clk);rsp_ready=0;request(1,3);if(!rsp_valid||!rsp_error)$fatal(1,"line mismatch accepted");
rsp_ready=1;@(negedge clk);rsp_ready=0;request(9,2);if(!rsp_valid||!rsp_error)$fatal(1,"unknown record accepted");
force dut.b=0;#1;if(!fault||rsp_valid||req_ready)$fatal(1,"fault not contained");@(negedge clk);release dut.b;
@(negedge clk);if(!fault)$fatal(1,"fault not sticky");$display("PASS allocation");$finish;end endmodule
""".replace('BASE',str(r['records'][0]['weight_line_base']))
        (d/'tb.sv').write_text(tb)
        subprocess.run(['iverilog','-g2012','-s','tb','-o',str(d/'sim'),str(d/'allocation.sv'),str(d/'tb.sv')],check=True,capture_output=True)
        sim=subprocess.run(['vvp',str(d/'sim')],check=True,capture_output=True,text=True)
        assert 'PASS allocation' in sim.stdout
        negatives=[]
        def reject(name,fn):
            try:fn()
            except (ValueError,KeyError):negatives.append(name);return
            raise AssertionError('negative accepted: '+name)
        (d/'lines.hex').write_text('0\n');reject('modified_source_hash',lambda:install(bp,mp,d/'bad1'))
        manifest['artifacts']['lines.hex']['sha256']=sha(d/'lines.hex');mp.write_text(json.dumps(manifest))
        reject('missing_native_lines',lambda:install(bp,mp,d/'bad2'))
        (d/'lines.hex').write_text('\n'.join(f'{v:x}' for v in lines)+'\n');manifest['artifacts']['lines.hex']['sha256']=sha(d/'lines.hex')
        manifest['nc']=1;mp.write_text(json.dumps(manifest));reject('narrow_shape',lambda:install(bp,mp,d/'bad3'))
        manifest['nc']=8;mp.write_text(json.dumps(manifest))
        b=json.loads(bp.read_text());b['recipe_successor']['emitted_image_bytes']=b['memory_bytes']-4096
        full=d/'full.json';full.write_text(json.dumps(b));reject('workspace_capacity',lambda:install(full,mp,d/'bad4'))
        (d/'x.hex').write_text(f'{1<<25216:x}\n');manifest['artifacts']['x.hex']['sha256']=sha(d/'x.hex');mp.write_text(json.dumps(manifest))
        reject('fragment_overflow',lambda:install(bp,mp,d/'bad5'))
        return dict(status='PASS',scope=manifest['provenance'],records=2,full_width_X_fragments=8,weight_lines=4,
            installation_sectors=r['installation_sectors'],allocation_RTL='PASS literal bases, held response, wrong line count, unknown record, duplicate bank fault',negative_controls=negatives,
            source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'tools/hbm_sm_native_install.py',ROOT/'tools/hbm_sm_native_install_model.py',ROOT/'tools/hbm_sm_native_allocation_build.py',ROOT/'tools/hbm_sm_native_allocation_model.py',original_book,ROOT/'tools/gpu_sys/v41_hbm.py']},
            physical_admitted=False,hardware_installation_complete=False)
if __name__=='__main__':
    result=run();out=ROOT/'results/rtl/hbm_sm_native_install_20261007/component.json';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
