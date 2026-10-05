#!/usr/bin/env python3
"""Actual source-slice formal/four-state gate for fixed Maxwell-priced variant."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from qwen_rom_hold_capture_gate_prepare import prepare,original_logic,TILE,ROOT,BENCH
from qwen_rom_kv_finite_window_gate import guarded_process
CANDIDATE='rtl/hdc/ot_qwen_rom_tile_hold_capture_candidate.sv'
YOSYS='/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys'
SMTBMC='/home/ubuntu/.local/opentallas-tools/yosys-0.68/bin/yosys-smtbmc'
MODEL='645ae1dd79eed8c20319574e4143b3c0c7b5551d'
MODEL_PATH='results/uarch/qwen_rom_direct_capture_control_20261002/model-r2.json'


def candidate_logic(raw):
    s=raw.decode()
    if s.count('parameter integer ROM_HOLD_DIRECT_CAPTURE = 0')!=2 or '.ROM_HOLD_DIRECT_CAPTURE(ROM_HOLD_DIRECT_CAPTURE)' not in s:
        raise ValueError('Candidate default/parent propagation changed')
    start=s.index('    reg  [CODE_BANKS-1:0] code_sel_q;');end=s.index('    // -- KV slice',start)
    body=s[start:end]
    if '(* keep = 1, dont_touch = 1 *) reg local_sel;' not in body:raise ValueError('Physical replica intent absent')
    header=original_logic((ROOT/TILE).read_bytes())[0].decode().split('    reg  [CODE_BANKS-1:0] code_sel_q;')[0]
    header=header.replace('qwen_current_capture_logic','qwen_optin_capture_logic').replace('MEM_EXTRA=1','MEM_EXTRA=1,ROM_HOLD_DIRECT_CAPTURE=0')
    return (header+body+'endmodule\n').encode(),body.encode()


def formal_view(raw,candidate=False):
    s=raw.decode();mark='output wire [CODE_BANKS-1:0] rom_ce,output wire [11:0] rom_addr);'
    s=s.replace(mark,'''output wire [CODE_BANKS-1:0] rom_ce,output wire [11:0] rom_addr,
 output wire [4:0] f_q,f_q2,output wire f_s,
 output wire [79:0] f_mask,output wire [2559:0] f_cap);''')
    extra='assign f_q=code_sel_q; assign f_q2=code_sel_q2; assign f_s=code_rd_q;\n'
    for p in range(2):
        for b in range(5):
            root=f'g_pair[{p}].g_bank[{b}].g_cap'
            if candidate:
                extra+=f'generate if (ROM_HOLD_DIRECT_CAPTURE != 0) begin\nassign f_cap[{(p*5+b)*256} +: 256]={root}.g_direct.cap;\n'
                for chunk in range(8):extra+=f'assign f_mask[{(p*5+b)*8+chunk}]={root}.g_direct.g_mask[{chunk}].local_sel;\n'
                extra+=f'end else begin\nassign f_cap[{(p*5+b)*256} +: 256]={root}.g_original.cap;\n'
                for chunk in range(8):extra+=f'assign f_mask[{(p*5+b)*8+chunk}]=code_sel_q2[{b}];\n'
                extra+='end endgenerate\n'
            else:
                extra+=f'assign f_cap[{(p*5+b)*256} +: 256]={root}.cap;\n'
                for chunk in range(8):extra+=f'assign f_mask[{(p*5+b)*8+chunk}]=code_sel_q2[{b}];\n'
    return s.replace('endmodule',extra+'endmodule')


def miter():
    text='''module qwen_hold_capture_formal(input clk,rst_n,wrom_re,input [23:0] wrom_addr,input [2659:0] payload);
reg [2659:0] rom_rd;
wire [511:0] oq,dq,eq;
wire [4:0] oc,dc,ec,o_sel,o_sel2,d_sel,d_sel2,e_sel,e_sel2;
wire [11:0] oa,da,ea;
wire os,ds,es;
wire [79:0] om,dm,em;
wire [2559:0] og,dg,eg;
qwen_current_capture_logic o(.clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.rom_rd(rom_rd),.wrom_q(oq),.rom_ce(oc),.rom_addr(oa),.f_q(o_sel),.f_q2(o_sel2),.f_s(os),.f_mask(om),.f_cap(og));
qwen_optin_capture_logic d(.clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.rom_rd(rom_rd),.wrom_q(dq),.rom_ce(dc),.rom_addr(da),.f_q(d_sel),.f_q2(d_sel2),.f_s(ds),.f_mask(dm),.f_cap(dg));
qwen_optin_capture_logic #(.ROM_HOLD_DIRECT_CAPTURE(1)) e(.clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.rom_rd(rom_rd),.wrom_q(eq),.rom_ce(ec),.rom_addr(ea),.f_q(e_sel),.f_q2(e_sel2),.f_s(es),.f_mask(em),.f_cap(eg));
always @* if ($initstate) assume(!rst_n);
integer p,b;
always @(posedge clk) for(p=0;p<2;p=p+1) for(b=0;b<5;b=b+1)
  if(oc[b]) rom_rd[(p*5+b)*266 +:266] <= payload[(p*5+b)*266 +:266];
always @* if (!$initstate) begin
 assert(oq==dq);assert(oq==eq);
 assert(oc==dc);assert(oc==ec);assert(oa==da);assert(oa==ea);
 assert(o_sel==d_sel);assert(o_sel==e_sel);assert(os==ds);assert(os==es);
 assert(om==dm);assert(om==em);
end
'''
    for p in range(2):
        for b in range(5):
            lo=(p*5+b)*256;mr=(p*5+b)*266
            text+=f'''always @* if (!$initstate) begin
 if (o_sel2[{b}]) begin assert(og[{lo}+:256]==eg[{lo}+:256]);assert(og[{lo}+:256]==dg[{lo}+:256]);end
 if (o_sel2[{b}] && !(os && o_sel[{b}])) assert(og[{lo}+:256]==rom_rd[{mr}+:256]);
end
'''
    return text+'endmodule\n'


def run(workdir,result):
    if workdir.exists() or result.exists():raise ValueError('Refusing overwrite')
    readiness=prepare(workdir,MODEL,MODEL_PATH)
    if not readiness['RTL_variant_implementation_admitted']:raise ValueError('Maxwell model blocks gate')
    paths=[TILE,CANDIDATE,BENCH,'tools/qwen_rom_hold_capture_literal_gate.py','tools/qwen_rom_hold_capture_gate_prepare.py']
    raw={p:(ROOT/p).read_bytes() for p in paths}
    cone,body=candidate_logic(raw[CANDIDATE]);(workdir/'candidate_logic_cone.sv').write_bytes(cone)
    original=(workdir/'original_logic_cone.sv').read_bytes();steps=[]
    for case,source in [('positive',cone),('wrong_metadata',cone.replace(b'else if (code_rd_q) local_sel <= code_sel_q[b];',b'else if (code_rd_q) local_sel <= ~code_sel_q[b];'))]:
        path=workdir/(case+'.sv');path.write_bytes(source);binary=workdir/(case+'.vvp')
        for phase,command in [('build',['iverilog','-g2012','-s','tb_qwen_rom_hold_capture_equivalence','-o',str(binary),str(workdir/'original_logic_cone.sv'),str(path),str(workdir/'fourstate_bench.sv')]),('simulation',['vvp',str(binary)])]:
            rc,output=guarded_process(command,workdir,workdir/(case+'_'+phase+'.log'))
            steps.append(dict(case=case,phase=phase,returncode=rc,output=output))
            if rc:break
    (workdir/'formal_original.sv').write_text(formal_view(original));(workdir/'formal_candidate.sv').write_text(formal_view(cone,True));(workdir/'formal_miter.sv').write_text(miter())
    script=workdir/'formal.ys';script.write_text(f'''read_verilog -formal -sv {workdir/'formal_original.sv'} {workdir/'formal_candidate.sv'} {workdir/'formal_miter.sv'}
prep -top qwen_hold_capture_formal -flatten
async2sync
dffunmap
write_smt2 -wires {workdir/'formal.smt2'}
''')
    rc,out=guarded_process([YOSYS,'-s',str(script)],workdir,workdir/'formal_build.log');steps.append(dict(case='formal',phase='build',returncode=rc,output=out[-1500:]))
    if rc==0:
        for phase,args in [('base',['-t','4']),('induction',['-i','-t','4'])]:
            rc,out=guarded_process([SMTBMC,'-s','z3',*args,str(workdir/'formal.smt2')],workdir,workdir/('formal_'+phase+'.log'));steps.append(dict(case='formal',phase=phase,returncode=rc,output=out))
    pos=next((s for s in steps if s['case']=='positive' and s['phase']=='simulation'),{})
    neg=next((s for s in steps if s['case']=='wrong_metadata' and s['phase']=='simulation'),{})
    formal=[s for s in steps if s['case']=='formal' and s['phase'] in ['base','induction']]
    stable=all((ROOT/p).read_bytes()==v for p,v in raw.items())
    good=pos.get('returncode')==0 and 'PASS QWEN_ROM_HOLD_CAPTURE_LITERAL_FOURSTATE' in pos.get('output','') and neg.get('returncode',0)!=0 and 'four-state selected output mismatch' in neg.get('output','') and len(formal)==2 and all(s['returncode']==0 and 'Status: PASSED' in s['output'] for s in formal) and stable
    record=dict(schema='opentallas.qwen-rom-hold-capture-literal-gate.v1',status='PASS_LITERAL_FORMAL_AND_FOURSTATE' if good else 'FAIL',source_sha256={p:hashlib.sha256(v).hexdigest() for p,v in raw.items()},source_stable=stable,candidate_body_sha256=hashlib.sha256(body).hexdigest(),model_commit=MODEL,model_path=MODEL_PATH,steps=steps,full_geometry=readiness['full_geometry'],default_off=True,physical_build_ready=False,PnR=False,hardware_adoption=False,new_token_run=False,scope='Actual source bodies extracted verbatim, defaultoff and enabled variant, full5bank10macro-pin/2560capture widths. Shared CE-hold response fixture and arbitrary fullwidth formal payloads. No ROM-array timing, engine, current token or contextual SS/FF credit.')
    result.parent.mkdir(parents=True,exist_ok=True)
    with result.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    print(record['status']);return 0 if good else 1


if __name__=='__main__':
    a=argparse.ArgumentParser(description=__doc__);a.add_argument('--workdir',type=Path,required=True);a.add_argument('--result',type=Path,required=True);x=a.parse_args();raise SystemExit(run(x.workdir.resolve(),x.result))
