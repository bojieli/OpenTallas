#!/usr/bin/env python3
"""Keep proved source versions intact; expose one real nested gateway clock."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE='96f30a6a0';GATEWAY='d8fdf94f1'
D='rtl/qwen_sys/static_schedule_20261014/'
def read(ref,path):return subprocess.check_output(['git','show',ref+':'+path],cwd=ROOT,text=True)
def replace_once(s,a,b):
    if s.count(a)!=1:raise ValueError(f'nonunique source clock cut: {a!r}')
    return s.replace(a,b,1)
def main():
    definitions=[
      (GATEWAY,D+'ot_qwen_rom_core_ctrl_su_static.sv',D+'ot_qwen_rom_core_ctrl_su_gateway.sv',[
        ('module ot_qwen_rom_core_ctrl_su_static #(','module ot_qwen_rom_core_ctrl_su_gateway #('),
        ('    input  wire              clk,','    input wire ck_gateway,\n    input  wire              clk,'),
        ('u_a_gateway (\n      .clk(clk),','u_a_gateway (\n      .clk(ck_gateway),')]),
      (BASE,D+'ot_qfd_seq_su_bi_static.sv',D+'ot_qfd_seq_su_bi_gateway.sv',[
        ('module ot_qfd_seq_su_bi_static #(','module ot_qfd_seq_su_bi_gateway #('),
        ('    input wire clk,','    input wire ck_gateway,\n    input wire clk,'),
        ('ot_qwen_rom_core_ctrl_su_static #(','ot_qwen_rom_core_ctrl_su_gateway #('),
        ('u_ctrl (\n        .clk(clk),','u_ctrl (\n        .clk(clk),.ck_gateway(ck_gateway),')]),
      (BASE,'rtl/qwen_split/qfd_seq_su_static.sv','rtl/qwen_split/qfd_seq_su_gateway.sv',[
        ('module qfd_seq_su_static (','module qfd_seq_su_gateway ('),
        ('    input wire ck_sched,','    input wire ck_sched,\n    input wire ck_gateway,'),
        ('ot_qfd_seq_su_bi_static #(','ot_qfd_seq_su_bi_gateway #('),
        ('.clk(ck),.ck_sched(ck_sched),','.clk(ck),.ck_sched(ck_sched),.ck_gateway(ck_gateway),')])]
    receipt=[]
    for ref,source,target,edits in definitions:
        original=read(ref,source)
        # Helpers retain their original definitions in the canonical BI source.
        selected=original[:original.index('endmodule')+len('endmodule')]+'\n' if source.endswith('ot_qfd_seq_su_bi_static.sv')else original
        candidate=selected
        for a,b in edits:candidate=replace_once(candidate,a,b)
        restored=candidate
        for a,b in reversed(edits):restored=replace_once(restored,b,a)
        assert restored==selected
        p=ROOT/target;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(candidate)
        receipt.append(dict(source_ref=ref,source=source,source_sha256=hashlib.sha256(original.encode()).hexdigest(),
            target=target,target_sha256=hashlib.sha256(candidate.encode()).hexdigest(),
            exact_except_module_references_and_gateway_clock=True,edits=[dict(before=a,after=b)for a,b in edits]))
    out=ROOT/'results/arch/qwen_split_compute_1014/gateway_clock';out.mkdir(parents=True,exist_ok=True)
    (out/'source_audit.json').write_text(json.dumps(dict(schema='opentallas.qwen.gateway-clock-cut.v1',qualified=False,
        data_state_added=0,data_edges_added=0,additional_clock_roots=1,seq_clock_roots=3,
        gateway_path='u_seq.u_seq.u_ctrl.u_a_gateway',source_gate_evidence='1680c684e',sources=receipt,
        physical_phase_binding=None,scope='Exact source clock cut; physical timing and complete successor hierarchy remain separate gates.'),indent=2)+'\n')
if __name__=='__main__':main()
