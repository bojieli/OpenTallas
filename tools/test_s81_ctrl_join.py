#!/usr/bin/env python3
"""Minimum join connectivity, registered pin fit and one-PC mechanism regression."""
import ast
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace

os.environ['OT_S81_CTRL_JOINS'] = '1'
import dsrom_s81_fulldie as die
from s81_ctrl_join import joins, pin_xs, service_pc_bank, require_service_top
from s81_ctrl_join_model import model, read, TILE, BASE, PORTS


def main():
    out = Path(__file__).resolve().parents[1] / 'results/rtl/s81_ph_20261006/ctrl_join_repair'
    report = model()
    # Execute the actual generator's four-stack join loop in isolation.
    tree = ast.parse(Path(die.__file__).read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'buses_r8')
    loop = next(n for n in fn.body if isinstance(n, ast.For) and ast.unparse(n.target) == '(st, ph)')
    stacks = ('SW','SE','NW','NE')
    m = {'phys': dict.fromkeys(stacks), 'ctrls': {s: SimpleNamespace(name='ctrl_'+s) for s in stacks},
         'svcs': {s: SimpleNamespace(name='svc_'+s) for s in stacks}}
    m['phys'] = {s: SimpleNamespace(name='phy_'+s) for s in stacks}
    buses = []
    ctx = dict(m=m, npins=22238, CTRL_JOINS=True, HBM_RD_BITS=8896, bus=lambda *args: buses.append(args))
    exec(compile(ast.Module(body=[loop], type_ignores=[]), die.__file__, 'exec'), ctx)
    usage = die.port_usage({'buses': buses})
    for s in stacks:
        for p,w in [('rd',8896),('rq',10912),('rk',32),('wd',32)]:
            assert usage['ctrl_'+s][p] == ('input' if p=='rq' else 'output',w)
            assert usage['svc_'+s][p] == ('output' if p=='rq' else 'input',w)
    # Old-width/drop-credit controls must fail this complete endpoint check.
    def complete(bs):
        u=die.port_usage({'buses':bs})
        return all(u.get('ctrl_'+s,{}).get(p)==('input' if p=='rq' else 'output',w)
                   and u.get('svc_'+s,{}).get(p)==('output' if p=='rq' else 'input',w)
                   for s in stacks for p,w in [('rd',8896),('rq',10912),('rk',32),('wd',32)])
    assert complete(buses)
    assert not complete([(n,c,8864 if n.startswith('rd_') else w,e) for n,c,w,e in buses])
    assert not complete([b for b in buses if not b[0].startswith('rq_')])
    assert not complete([(n,c,w,list(reversed(e)) if n.startswith('rq_') else e) for n,c,w,e in buses])
    xs=pin_xs()
    assert all(len(set(v))==len(v) for v in xs.values())
    ctrl=read(TILE,'rtl/dsrom_sys/s81_ph/dsfd_ctrl.sv').decode()
    for fragment in ['.rq(rq[g*341 +: 341])','.rk(rk[g])','.wd(wd[g])',
                     '.r_data(rd[g*256 +: 256])','.r_tag(rd[8192 + g*17 +: 17])',
                     '.r_beat(rd[8736 + g*4 +: 4])','assign rd[8895:8864] = rv;',
                     'assign phy[12808] = ckh;']:
        assert fragment in ctrl,fragment
    bank = service_pc_bank()
    for fragment in ['.rq(rq[p*341 +: 341])', '.qrq(qrq[p*341 +: 341])',
                     '.rk(rk[p])', '.qrk(qrk[p])', '.wd(wd[p])', '.qwd(qwd[p])',
                     '.rv(rd[8864+p])', '.qrv(qrd[8864+p])',
                     '.r_data(rd[p*256 +: 256])', '.qr_data(qrd[p*256 +: 256])',
                     '.r_tag(rd[8192+p*17 +: 17])', '.qr_tag(qrd[8192+p*17 +: 17])',
                     '.r_beat(rd[8736+p*4 +: 4])', '.qr_beat(qrd[8736+p*4 +: 4])',
                     '.ck(ck)', '.rst(rst)']:
        assert fragment in bank, fragment
    # Reciprocal leaf directions from literal source, independent of bus helper.
    for kind in ('ctrl', 'svc'):
        rtl = read(TILE, f'rtl/dsrom_sys/s81_ph/{kind}/dsfd_{kind}_pc.sv').decode()
        ports = {n:(d,int(hi)+1) for d,hi,n in re.findall(
            r'(input|output)\s+(?:wire|reg)\s+\[(\d+):0\]\s+(\w+)',rtl)}
        for p,w in PORTS.items():
            direction = 'input' if p=='rq' else 'output'
            if kind=='svc': direction = 'output' if direction=='input' else 'input'
            assert ports[p] == (direction,w)
    # Literal registered pin placements are consumed by the real pin serializer.
    for face,height in [('N',248.376),('S',1576.776)]:
        mst=die.Q.Master('boundary',8500.032,height,7,'component check')
        for p,v in xs.items(): mst.ports[p]=('xy',v,face); mst.order.append(p)
        rects=die.pin_rects(mst,1,{p:len(v) for p,v in xs.items()})
        assert len(rects)==19872
        assert all(0<=r[0]<r[2]<=mst.w and 0<=r[1]<r[3]<=mst.h for _,_,r in rects)
        assert all(abs(r[1]-(height-.192 if face=='N' else 0))<1e-6 for _,_,r in rects)
    # Preserve the receiver capture edge in the unchanged pinned primitive.
    assert 'negedge fclk_i' in read(BASE,'rtl/common/ot_fwd_link_stage.sv').decode()
    # Every response bit has one producer/consumer slice, including all valids.
    cover=[]
    for p in range(32):
        cover += list(range(p*256,p*256+256))+list(range(8192+p*17,8192+p*17+17))
        cover += list(range(8736+p*4,8736+p*4+4))+[8864+p]
    assert sorted(cover)==list(range(8896))
    # Exact AST comparison: unrelated generator functions remain unchanged.
    base=ast.parse(read(BASE,'tools/dsrom_s81_fulldie.py').decode())
    old={n.name: ast.dump(n) for n in base.body if isinstance(n,ast.FunctionDef)}
    changed={n.name for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in old and ast.dump(n)!=old[n.name]}
    assert changed == {'pin_rects','buses_r8','main','_faces_r8'}, changed
    with tempfile.TemporaryDirectory(prefix='s81-join-') as tmp:
        t=Path(tmp)
        (t/'pc.sv').write_bytes(read(TILE,'rtl/dsrom_sys/s81_ph/svc/dsfd_svc_pc.sv'))
        (t/'bank.sv').write_text(service_pc_bank())
        # Elaboration of packing only; no full-array simulation.
        subprocess.run(['iverilog','-g2012','-s','dsfd_svc_pc_bank','-o',str(t/'bank'),str(t/'pc.sv'),str(t/'bank.sv')],check=True)
        bench='''`timescale 1ns/1ps
module tb;
 reg ck=0,rst=0; always #5 ck=~ck;
 reg [340:0] qrq=0; wire [340:0] rq;
 reg rk=0,wd=0,rv=0; wire qrk,qwd,qrv;
 reg [255:0] r_data=0; wire [255:0] qr_data;
 reg [16:0] r_tag=0; wire [16:0] qr_tag;
 reg [3:0] r_beat=0; wire [3:0] qr_beat;
 dsfd_svc_pc dut(.*);
 integer i,j;
 initial begin
 repeat(4) @(negedge ck); rst=1;
 repeat(4) @(negedge ck);
 for(i=0;i<128;i=i+1) begin
  for(j=0;j<341;j=j+1) qrq[j]=$random;
  for(j=0;j<256;j=j+1) r_data[j]=$random;
  r_tag=$random; r_tag[0]=1; r_beat=$random; rv=1; rk=i%2; wd=i%3==0;
  @(posedge ck); #1;
  if(rq!==qrq || qr_data!==r_data || qr_tag!==r_tag || qr_beat!==r_beat || qrv!==rv || qrk!==rk || qwd!==wd)
    $fatal(1,"complete port transfer mismatch");
  @(negedge ck);
 end
 rst=0; #1; if(rq[0]!==0 || qrv!==0 || qrk!==0 || qwd!==0) $fatal(1,"reset");
 $display("ONE_PC_COMPLETE_PORTS_PASS"); $finish;
 end
endmodule
'''
        (t/'tb.sv').write_text(bench)
        logs={}
        for name,defs in [('baseline',[]),('drop_valid',['-DS81PH_SVCPC_MUT_DROP'])]:
            exe=str(t/name)
            subprocess.run(['iverilog','-g2012',*defs,'-s','tb','-o',exe,str(t/'pc.sv'),str(t/'tb.sv')],check=True)
            r=subprocess.run(['vvp',exe],capture_output=True,text=True)
            logs[name]=dict(exit_code=r.returncode,stdout=r.stdout)
            assert (r.returncode==0)==(name=='baseline')
    try: require_service_top()
    except ValueError: pass
    else: raise AssertionError('missing service top must block physical adoption')
    out.mkdir(parents=True,exist_ok=True)
    (out/'service_pc_bank.sv').write_text(service_pc_bank())
    (out/'connectivity.json').write_text(json.dumps(dict(buses=buses,port_directions=usage),indent=2)+'\n')
    (out/'declarations.v').write_text('\n'.join('module '+n+'(\n'+die._decl(usage[n])+'\n); endmodule // DECLARATION ONLY' for n in sorted(usage)))
    result=dict(component_checks='PASS',assembled_die='BLOCKED_MISSING_SERVICE_TOP',timing='UNQUALIFIED',
                negatives=['old_rd_width','missing_rq','reverse_rq','drop_valid','missing_service_top'],
                one_pc_mechanism=logs,unrelated_generator_functions_unchanged=True,
                changed_functions=sorted(changed),source_sha256=report['source_sha256'])
    for p in ['tools/s81_ctrl_join.py','tools/s81_ctrl_join_model.py','tools/test_s81_ctrl_join.py','tools/dsrom_s81_fulldie.py','tools/uarch_model.py']:
        result['source_sha256'][p]=hashlib.sha256((out.parents[3]/p).read_bytes()).hexdigest()
    (out/'checks.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))

if __name__=='__main__': main()
