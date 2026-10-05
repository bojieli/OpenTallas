#!/usr/bin/env python3
"""Literal same-edge bank5/control gate; no mapped/physical adoption."""
import argparse,gzip,hashlib,json
from pathlib import Path
from qwen_rom_hold_capture_literal_gate import candidate_logic,formal_view,YOSYS
from qwen_rom_hold_capture_gate_prepare import original_logic
from qwen_rom_kv_finite_window_gate import guarded_process

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/uarch/qwen_rom_bank5_control_20261002'
OLD='rtl/hdc/ot_qwen_rom_tile_hold_capture_candidate.sv'
NEW='rtl/hdc/ot_qwen_rom_tile_bank5_control_candidate.sv'
TILE='rtl/hdc/ot_qwen_rom_tile_w12.sv'
BENCH='rtl/test/qwen_rom_capture/tb_qwen_rom_hold_capture_equivalence.sv'

def bank_logic(raw):
    source=raw.decode()
    assert source.count('parameter integer ROM_BANK5_CONTROL = 0,')==2
    assert '.ROM_BANK5_CONTROL(ROM_BANK5_CONTROL)' in source
    start=source.index('    reg  [CODE_BANKS-1:0] code_sel_q;')
    end=source.index('    // -- KV slice',start)
    old,_=candidate_logic((ROOT/OLD).read_bytes())
    header=old.decode().split('    reg  [CODE_BANKS-1:0] code_sel_q;')[0]
    header=header.replace('ROM_HOLD_DIRECT_CAPTURE=0','ROM_HOLD_DIRECT_CAPTURE=0,ROM_BANK5_CONTROL=0')
    return (header+source[start:end]+'endmodule\n').encode()

def validate_model():
    model=json.loads((OUT/'model_packet/model-r3.json').read_text())
    origin=json.loads((OUT/'model_packet/origin.json').read_text())
    for path,digest in origin['artifact_sha256'].items():
        assert hashlib.sha256((OUT/'model_packet'/path).read_bytes()).hexdigest()==digest,path
    c=model['fixed_candidate']
    assert c['id']=='QROM_HOLD_DIRECT_CAPTURE_BANK5_CONTROL'
    assert c['total_added_buffers']==76 and c['new_FFs']==4 and c['total_metadata_FFs_after']==90
    assert c['new_token_cycles']==0 and c['local_mask_FFs']==80 and c['off_by_default']
    assert not model['admission']['tile_PR'] and model['admission']['priced_cause_model_ready']
    assert model['input_sha256']['results/uarch/qwen_rom_control_closure_cause_20261002/inputs/matvec_source.sv']==hashlib.sha256((ROOT/'rtl/hdc/ot_qwen_w12_matvec.sv').read_bytes()).hexdigest()
    return model

def miter():
    return '''module bank5_formal(input clk,rst_n,wrom_re,input [23:0] wrom_addr,input [2659:0] payload);
reg [2659:0] rom_rd;
wire [511:0] a_out,b_out,c_out;
wire [4:0] a_ce,b_ce,c_ce,aq,aq2,bq,bq2,cq,cq2,banks;
wire [11:0] a_addr,b_addr,c_addr;
wire a_s,b_s,c_s;
wire [79:0] a_mask,b_mask,c_mask;
wire [2559:0] a_cap,b_cap,c_cap;
qwen_prior_capture #(.ROM_HOLD_DIRECT_CAPTURE(1)) a(.clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.rom_rd(rom_rd),.wrom_q(a_out),.rom_ce(a_ce),.rom_addr(a_addr),.f_q(aq),.f_q2(aq2),.f_s(a_s),.f_mask(a_mask),.f_cap(a_cap));
qwen_optin_capture_logic #(.ROM_HOLD_DIRECT_CAPTURE(1)) b(.clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.rom_rd(rom_rd),.wrom_q(b_out),.rom_ce(b_ce),.rom_addr(b_addr),.f_q(bq),.f_q2(bq2),.f_s(b_s),.f_mask(b_mask),.f_cap(b_cap));
qwen_optin_capture_logic #(.ROM_HOLD_DIRECT_CAPTURE(1),.ROM_BANK5_CONTROL(1)) c(.clk(clk),.rst_n(rst_n),.wrom_re(wrom_re),.wrom_addr(wrom_addr),.rom_rd(rom_rd),.wrom_q(c_out),.rom_ce(c_ce),.rom_addr(c_addr),.f_q(cq),.f_q2(cq2),.f_s(c_s),.f_mask(c_mask),.f_cap(c_cap),.f_bank(banks));
always @* if ($initstate) assume(!rst_n);
integer p,i;
always @(posedge clk) for(p=0;p<2;p=p+1) for(i=0;i<5;i=i+1)
 if(a_ce[i]) rom_rd[(p*5+i)*266+:266] <= payload[(p*5+i)*266+:266];
always @* if (!$initstate) begin
 assert(banks=={5{a_s}});
 assert(a_out==b_out);assert(a_out==c_out);
 assert(a_ce==b_ce);assert(a_ce==c_ce);assert(a_addr==b_addr);assert(a_addr==c_addr);
 assert(aq==bq);assert(aq==cq);assert(aq2==bq2);assert(aq2==cq2);
 assert(a_s==b_s);assert(a_s==c_s);assert(a_mask==b_mask);assert(a_mask==c_mask);
end
endmodule
'''

def run(work,result):
    if work.exists() or result.exists():raise ValueError('Refusing overwrite')
    model=validate_model();work.mkdir(parents=True)
    paths=[OLD,NEW,TILE,BENCH,'rtl/hdc/ot_qwen_w12_matvec.sv','tools/qwen_rom_bank5_control_gate.py']
    raw={p:(ROOT/p).read_bytes() for p in paths}
    old,_=candidate_logic(raw[OLD]);new=bank_logic(raw[NEW])
    prior=formal_view(old,True).replace('qwen_optin_capture_logic','qwen_prior_capture')
    repaired=formal_view(new,True).replace('output wire [4:0] f_q,f_q2,output wire f_s,','output wire [4:0] f_q,f_q2,output wire f_s,output wire [4:0] f_bank,')
    repaired=repaired.replace('endmodule','assign f_bank=code_rd_bank;\nendmodule')
    (work/'prior.sv').write_text(prior);(work/'repaired.sv').write_text(repaired)
    (work/'miter.sv').write_text(miter())
    steps=[]
    for case,body in [('positive',repaired),('wrong_bank4_strobe',repaired.replace('else read_q <= wrom_re;','else read_q <= (rb == 4) ? ~wrom_re : wrom_re;',1))]:
        source=work/(case+'.sv');source.write_text(body)
        ys=work/(case+'.ys');ys.write_text(f'''read_verilog -formal -sv {work/'prior.sv'} {source} {work/'miter.sv'}
prep -top bank5_formal -flatten
async2sync
dffunmap
opt_clean
sat -seq 2 -tempinduct -set-assumes -prove-asserts -verify
''')
        rc,out=guarded_process([YOSYS,'-s',str(ys)],work,work/(case+'.log'))
        steps.append(dict(case=case,returncode=rc,output_tail=out[-2500:]))
    original=original_logic(raw[TILE])[0]
    (work/'original.sv').write_bytes(original);(work/'bank_cone.sv').write_bytes(new)
    bench=raw[BENCH].decode().replace('.ROM_HOLD_DIRECT_CAPTURE(1)', '.ROM_HOLD_DIRECT_CAPTURE(1),.ROM_BANK5_CONTROL(1)')
    (work/'fourstate.sv').write_text(bench)
    for phase,cmd in [('build',['iverilog','-g2012','-s','tb_qwen_rom_hold_capture_equivalence','-o',str(work/'gate.vvp'),str(work/'original.sv'),str(work/'bank_cone.sv'),str(work/'fourstate.sv')]),('run',['vvp',str(work/'gate.vvp')])]:
        rc,out=guarded_process(cmd,work,work/('fourstate_'+phase+'.log'))
        steps.append(dict(case='fourstate_'+phase,returncode=rc,output_tail=out[-2500:]))
        if rc:break
    good=steps[0]['returncode']==0 and 'Induction step proven: SUCCESS!' in steps[0]['output_tail'] and steps[1]['returncode']!=0 and len(steps)==4 and all(s['returncode']==0 for s in steps[2:]) and 'checks=77' in steps[-1]['output_tail']
    stable=all((ROOT/p).read_bytes()==data for p,data in raw.items())
    record=dict(schema='opentallas.qwen-rom-bank5-source-gate.v1',status='PASS_LITERAL_BANK5_SAMEEDGE_AND_FOURSTATE' if good and stable else 'FAIL',
        source_sha256={p:hashlib.sha256(data).hexdigest() for p,data in raw.items()},source_stable=stable,steps=steps,
        model_commit='cdcbe60a34389a5671f9e303c4f5023e83b23710',model_sha256=hashlib.sha256((OUT/'model_packet/model-r3.json').read_bytes()).hexdigest(),
        geometry=dict(ROM=10,capture_FF_bits=2560,local_mask_FF=80,bank_strobe_FF=5,metadata_FF_after=90),
        semantic_added_cycles=0,buffer_plan=model['fixed_candidate']['buffer_counts'],buffers_materialized=False,
        parent_mapped_arrival_bound=False,reset_physical_release_bound=False,contextual_STA_admitted=False,tile_PR=False,adoption=False,
        passing_scope='Literal same-edge bank strobes and full output/mask equivalence, arbitrary data/address/idle/reset after initial reset, defaultbankoff preserved. Functional shared CEhold fixture only. No timing credit.')
    result.parent.mkdir(parents=True,exist_ok=True)
    with result.open('x') as f:json.dump(record,f,indent=2,sort_keys=True);f.write('\n')
    print(record['status']);return 0 if good and stable else 1

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--workdir',type=Path,required=True);ap.add_argument('--result',type=Path,required=True)
    args=ap.parse_args();raise SystemExit(run(args.workdir,args.result))
