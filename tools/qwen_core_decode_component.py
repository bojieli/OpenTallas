#!/usr/bin/env python3
"""Extract unchanged sequencer/decode cones from the emitted full core for a component check."""
from pathlib import Path
import argparse,re
import qwen_rom_decode_pipe_emit_w12 as E


def component(text):
    seq=text[text.index('    localparam integer LW'):text.index('    always @(posedge clk or negedge rst_n) begin\n        if (!rst_n) begin kvd_v')]
    # VPOS declarations follow dyn[] and are inside this exact slice.
    dyn=text[text.index('    // DYN offsets derived once per token.'):text.index('    // -- units')]
    fields=list(dict.fromkeys(re.findall(r'\b(\w+)\s*<=',dyn[dyn.index('    // Decode:'):])) )
    seq=seq.replace('    wire       me_ready, me_idle, su_ready, su_idle;','')
    return '''module decode_component #(parameter DECODE_PIPE=0, VPOS=0)(
input clk,rst_n,start, input [17:0] token,pos,
input me_ready,me_idle,su_ready,su_idle,
input [1023:0] prog_q,
output reg prog_re,output reg [11:0] prog_addr,
output reg done,output reg [31:0] cycles,
output reg [17:0] next_token,output reg [31:0] next_val,
output [877:0] decoded,output accepted,output invalid_at_load);
localparam AW=24,NW=18,PAW=12,W=16,IL=1,G=6144,HID=4096,HD=128,HALF=64,
INSTR_BITS=1024,KV_HBM=1,W_HBM=1,KV_VEC_WRITE_BRIDGE=1,QWEN_FULLSHAPE=1;
`include "ot_hdc_isa.svh"
assign me_en=1;
wire kv_ok=1,kvd_v=0,w_ok=1,wd_v=0,emb_ok=1,kv_write_drained=1;
wire [15:0] kv_we=0;
wire kv_write_flush;
wire [17:0] fin_idx=5; wire [31:0] fin_val=32'h3f800000;
assign accepted=issue;
assign invalid_at_load=dyn_tiles_bad_instruction;
'''+seq+dyn+'\nassign decoded={'+','.join(fields)+'};\nendmodule\n'


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args();a.out.parent.mkdir(parents=True,exist_ok=True)
    text=component(E.emit(E.V.E.CORE.read_text()))
    text=text.replace('`include "ot_hdc_isa.svh"', (E.V.E.CORE.parent/'ot_hdc_isa.svh').read_text())
    a.out.write_text(text)

if __name__=='__main__':main()
