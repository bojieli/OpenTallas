#!/usr/bin/env python3
"""Minimum actual core-controller / TP-sequencer completion regression.

Arithmetic engines are replaced by their ready/argmax input ports. The emitted
controller, program fetch, argmax END, pin capture and real TP sequencer remain.
No array/die simulation. Negative removes only the candidate pulse clear.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import qwen_rom_core_dec_emit_w12 as E
import qwen_rom_core_takeover_component as C
import qwen_rom_core_issue_fallback_w12 as F

ROOT = Path(__file__).resolve().parents[1]
PULSE = "            if (DEC_LA_PINREG != 0) done <= 1'b0; // registered completion pulse\n"


def component():
    original = E.emit
    full = F.apply_pinreg(F.apply_amq(original(E.V.E.CORE.read_text())))
    assert full.count(PULSE) == 1
    # Keep C's established controller/argmax extraction boundaries. This marker
    # begins the descriptor block excluded from the component, not tested logic.
    marker = "    always @(posedge clk or negedge rst_n_i) begin\n        if (!rst_n_i) begin kvd_v"
    assert full.count(marker) == 1
    adapted = full.replace(marker, marker.replace('rst_n_i', 'rst_n')).replace(
        '// DYN offsets derived once per token_i.', '// DYN offsets derived once per token.')
    E.emit = lambda _: adapted
    try:
        result = C.component()
    finally:
        E.emit = original
    start = full.index('    // ---- DEC_LA_PINREG (')
    end = full.index('`include', start)
    result = result.replace('parameter DEC_LA=0,', 'parameter DEC_LA_PINREG=0, DEC_LA_AMQ=0, DEC_LA=0,')
    result = result.replace('localparam AW=24,', 'localparam SW=16, AW=24,')
    result = result.replace('assign me_en=1;', 'wire me_mem_ok=1;\n' + full[start:end] + '\nassign me_en=1;')
    return result, full


TB = r'''
module tb;
parameter PINREG=1, AMQ=1, LA=1, CHECK_PULSE=1;
reg clk=0; always #5 clk=~clk;
reg rst_n=0,start=0;
reg [17:0] token=0;
wire done,core_start,core_done;
wire [17:0] core_token,core_pos,core_next_token,next_token;
wire [31:0] core_next_val;
wire desc_re; reg [63:0] desc_q=0;
wire prog_re; reg [1023:0] prog_q=0;
wire [17:0] am_idx=core_token+18'd100;
wire [31:0] am_val=32'h3f800000+core_token;
ot_qwen_tp_seq_w12_vp #(.NW(18),.QWEN_FULLSHAPE(1),.LA(LA)) seq(
 .clk(clk),.rst_n(rst_n),.start(start),.token(token),.pos(18'd0),
 .done(done),.next_token(next_token),.core_start(core_start),
 .core_token(core_token),.core_pos(core_pos),.core_done(core_done),
 .core_next_token(core_next_token),.core_next_val(core_next_val),.core_fault(1'b0),
 .desc_re(desc_re),.desc_q(desc_q),.vm_rq(512'd0),.c_ready(1'b1),
 .r_valid(1'b0),.r_data(512'd0),.r_last(1'b0),.r_rank(2'd0),.r_err(1'b0));
decode_component #(.DEC_LA(1),.DEC_LA_PINREG(PINREG),.DEC_LA_AMQ(AMQ)) core(
 .clk(clk),.rst_n(rst_n),.start(core_start),.token(core_token),.pos(core_pos),
 .me_ready(1'b1),.me_idle(1'b1),.su_ready(1'b1),.su_idle(1'b1),
 .me_progress(16'd0),.su_progress(16'd0),.su_rows(16'd0),
 .prog_q(prog_q),.am_idx(am_idx),.am_val(am_val),.am_any(1'b1),
 .prog_re(prog_re),.done(core_done),.next_token(core_next_token),.next_val(core_next_val));
always @(posedge clk) begin
 if (desc_re) desc_q<=0; // K_END, no collective: isolates the actual CWAIT edge
 if (prog_re) prog_q<=0; // END instruction; actual fetch/decode/fin path
end
integer i,edges=0,completions=0; reg prev_core_done=0;
always @(posedge clk) begin
 edges<=edges+1;
 if (edges>3000) $fatal(1,"bounded transaction count watchdog");
 if (rst_n) begin
  if (core_done && !prev_core_done) completions<=completions+1;
  if (CHECK_PULSE && PINREG!=0 && core_done && prev_core_done) $fatal(1,"completion not a pulse");
 end
 prev_core_done<=core_done;
end
initial begin
 repeat(4) @(negedge clk); rst_n=1;
 repeat(4) @(negedge clk);
 for(i=0;i<8;i=i+1) begin
  token=i+7; start=1; @(negedge clk); start=0;
  wait(!done); wait(done); @(negedge clk);
  if(next_token!==token+18'd100) $fatal(1,"stale completion i=%0d expected=%0d actual=%0d",i,token+100,next_token);
  // Exercise both immediate next transaction and long idle with stale done.
  repeat(i%3) @(negedge clk);
 end
 if(completions!=8) $fatal(1,"completion count %0d",completions);
 $display("PASS transactions=8 edges=%0d pinreg=%0d amq=%0d la=%0d",edges,PINREG,AMQ,LA);
 $finish;
end
endmodule
'''


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out', type=Path, required=True);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    comp, full=component()
    records=[]
    with tempfile.TemporaryDirectory(prefix='qwen-core-done-') as tmp:
        d=Path(tmp); (d/'tb.sv').write_text(TB)
        for neg,pin,amq,la in [(False,p,a,l) for p in (0,1) for a in (0,1) for l in (0,1)]+[(True,1,1,1)]:
            name=f"{'negative_sticky' if neg else 'positive'}_p{pin}_a{amq}_l{la}"
            source=comp.replace(PULSE,'') if neg else comp
            (d/'core.sv').write_text(source)
            cmd=['iverilog','-g2012','-I'+str(ROOT/'rtl/hdc'),'-s','tb',f'-Ptb.PINREG={pin}',f'-Ptb.AMQ={amq}',f'-Ptb.LA={la}',f'-Ptb.CHECK_PULSE={0 if neg else 1}',
                 '-o',str(d/'sim'),str(d/'tb.sv'),str(d/'core.sv'),str(ROOT/'rtl/rom/ot_qwen_tp_seq_w12_vp.sv'),
                 str(ROOT/'rtl/hdc/ot_hdc_prefix.sv'),str(ROOT/'rtl/hdc/ot_hdc_dyn_ttiles.sv')]
            p=subprocess.run(cmd,capture_output=True,text=True)
            (a.out/f'{name}.compile.log').write_text(p.stdout+p.stderr)
            if p.returncode: raise RuntimeError(p.stderr[-4000:])
            p=subprocess.run(['vvp',str(d/'sim')],capture_output=True,text=True)
            log=p.stdout+p.stderr; (a.out/f'{name}.run.log').write_text(log)
            passed=(p.returncode!=0 and ('stale completion' in log or 'completion not a pulse' in log)) if neg else p.returncode==0 and 'PASS transactions=8' in log
            records.append(dict(name=name,returncode=p.returncode,expected_negative=neg,passed=passed,log=log.strip()))
    report=dict(schema='qwen.core.pinreg.done.v1',status='pass' if all(r['passed'] for r in records) else 'fail',
       scope='actual extracted core controller + real TP sequencer; END-only program; arithmetic input boundary',
       added_cycles=0,new_registers=0,default0_unchanged=True,adopted=False,physical_signoff=False,
       emitted_core_sha256=hashlib.sha256(full.encode()).hexdigest(),
       source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in
          [Path(__file__),Path(F.__file__),Path(C.__file__),Path(E.__file__),Path(E.V.__file__),Path(E.V.E.__file__),E.V.E.CORE,
           ROOT/'rtl/rom/ot_qwen_tp_seq_w12_vp.sv']},runs=records)
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
    if report['status']!='pass': raise SystemExit(1)

if __name__=='__main__': main()
