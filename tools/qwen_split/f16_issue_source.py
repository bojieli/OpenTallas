"""Add the missing typed F16 source lane to the actual selected slice.

No expected schedule is converted to an event: the tap is connected directly
to the existing physical PROG read-enable and selected PC signals. Its22-bit
context input must come from the same actual calendar command context, and must
be forwarded beside command at the same hop age. No final-read receipt is made.
"""
import argparse,hashlib,json
from pathlib import Path
from f16_auth_source import replace_once


def generate(source, output):
    source, output = Path(source), Path(output)
    original = source.read_text()
    # The current frozen source's actual program-read selection is normative.
    if original.count('.p_re(c_su), .p_idx(cmd_q[12:4])') != 1:
        raise ValueError('actual selected slice PROG read path differs')
    s = replace_once(original, 'module qfd_dv_slice2 #(', 'module qfd_dv_slice2_f16 #(')
    s = replace_once(s, '    input  wire [115:0]   cmd_i,', '    input wire [21:0] cmd_context_i,\n    output reg [21:0] cmd_context_o,\n    output wire [37:0] f16_issue_o,\n    input  wire [115:0]   cmd_i,')
    s = replace_once(s, '    reg [115:0]  cmd_q;', "    reg [21:0] f16_context_q;\n    always @(posedge ck or negedge rst)\n      if(!rst) begin f16_context_q<=22'd0;cmd_context_o<=22'd0;end\n      else begin f16_context_q<=cmd_context_i;cmd_context_o<=f16_context_q;end\n    reg [115:0]  cmd_q;")
    s = replace_once(s, "    // SU issue: the program word answers 2 edges after the command's pin register", "    qfd_dv_f16_issue_tap u_f16_issue (\n      .ck(ck),.rst_n(rst),.program_re(c_su),.program_pidx(cmd_q[12:4]),\n      .slice_id(sid_q),.command_context(f16_context_q),.observation(f16_issue_o));\n    // SU issue: the program word answers 2 edges after the command's pin register")
    output.mkdir(parents=True, exist_ok=True)
    (output/'qfd_dv_slice2_f16.sv').write_text(s)
    # Source-extracted minimum dispatch cut, excluding all arithmetic engines.
    start=original.index('    reg  [3:0] sid_q; reg sid_ok;')
    end=original.index('    reg [23:0] stn_dbase;',start)
    decode=original[start:end]
    cut='`timescale 1ns/1ps\nmodule qfd_dv_f16_dispatch_cut #(parameter MUT=0)(\n input wire ck,rst_n,input wire[115:0]cmd_i,input wire[21:0]context_i,\n output reg[115:0]cmd_o,output reg[21:0]context_o,output wire[37:0]observation);\n reg rs1,rst;\n always @(posedge ck or negedge rst_n)\n  if(!rst_n)begin rs1<=0;rst<=0;end else begin rs1<=1;rst<=rs1;end\n reg[115:0]cmd_q;reg[21:0]context_q;\n always @(posedge ck or negedge rst)\n  if(!rst)begin cmd_q<=0;context_q<=0;context_o<=0;end\n  else begin cmd_q<=cmd_i;context_q<=context_i;context_o<=context_q;end\n'+decode+'\n qfd_dv_f16_issue_tap tap(.ck(ck),.rst_n(rst),.program_re(c_su),\n .program_pidx(cmd_q[12:4]),.slice_id(sid_q),.command_context(context_q),.observation(observation));\nendmodule\n'
    (output/'qfd_dv_f16_dispatch_cut.sv').write_text(cut)
    return dict(source_path=str(source),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),candidate_sha256=hashlib.sha256(s.encode()).hexdigest(),cut_sha256=hashlib.sha256(cut.encode()).hexdigest(),scope='Actual source dispatch cut and source lane only; no actual upstream context producer/GEN/physical/whole-token claim',context_bits=22,observation_bits=38,context_relative_cmd_edges=0,issue_to_event_output_edges=1)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True);p.add_argument('--output',required=True);a=p.parse_args()
    print(json.dumps(generate(a.source,a.output),indent=2))
