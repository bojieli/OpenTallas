#!/usr/bin/env python3
"""Opt-in held decode successor; pinned base/VPOS emitters remain unchanged."""
from pathlib import Path
import argparse
import re
import qwen_rom_verify_core_emit_w12 as V


def once(text, old, new):
    if text.count(old) != 1:
        raise ValueError(f'expected unique source anchor: {old}')
    return text.replace(old, new, 1)


def emit(core_text):
    text = V.emit(core_text)
    text = once(text, '    parameter integer VPOS = 0',
                '    parameter integer VPOS = 0,\n    parameter integer DECODE_PIPE = 0')
    text = once(text, 'wire [INSTR_BITS-1:0] ir = fq[fq_rd];',
                'wire [INSTR_BITS-1:0] ir = DECODE_PIPE ? dp_ir : fq[fq_rd];')
    text = once(text, '    reg        nx_v;', '''    reg [INSTR_BITS-1:0] dp_ir;
    reg [2:0] dp_phase;
    reg [NW-1:0] dp_pos, dp_shifted, dp_rounds;
    reg dp_invalid;
    reg [AW-1:0] dp_dyn [0:10];
    reg        nx_v;''')
    # Retain original calculator exclusively in the default branch.
    text = once(text, 'u_dyn_tiles_split (', 'u_dyn_tiles_split_legacy (')
    text = once(text, '.rounds(dyn_tiles_split),\n        .invalid_split(dyn_tiles_invalid));',
                '.rounds(dp_legacy_rounds),\n        .invalid_split(dp_legacy_invalid));\n'
                '    wire [NW-1:0] dp_legacy_rounds;\n    wire dp_legacy_invalid;\n'
                '    assign dyn_tiles_split = DECODE_PIPE ? dp_rounds : dp_legacy_rounds;\n'
                '    assign dyn_tiles_invalid = DECODE_PIPE ? dp_invalid : dp_legacy_invalid;')
    text = once(text, 'wire load = (st == S_RUN) && (fq_n != 0) && (!nx_v || issue);',
                'wire load = (st == S_RUN) && (fq_n != 0) && (!nx_v || issue) && (!DECODE_PIPE || dp_phase == 4);')
    # Extract the actual eleven source selectors, preserving destination order.
    selectors = re.findall(r'`DYNS\(`F\(([A-Z_]+)\)\)', text)
    if len(selectors) != 11:
        raise ValueError('DYN selector source changed')
    for i, field in enumerate(selectors):
        old = f'`DYNS(`F({field}))'
        text = once(text, old, f'(DECODE_PIPE ? dp_dyn[{i}] : {old})')
    assignments = '\n'.join(f'                    dp_dyn[{i}] <= `DYNS(`F({f}));' for i,f in enumerate(selectors))
    block = '''
    // Five distinct edges: capture raw FIFO word, position, selectors/shift,
    // constant odd division, then load NEXT. FIFO ownership changes only at load.
    function automatic integer dp_tz(input integer value);
        integer n;
        begin
            n=0;
            while (value>0 && (value & 1)==0) begin value=value>>1; n=n+1; end
            dp_tz=n;
        end
    endfunction
    localparam integer DP_WT=dp_tz(W), DP_GT=dp_tz(G), DP_ODD=G>>DP_GT;
    wire [4:0] dp_amount=DP_WT+DP_GT-`F(ME_SPLIT);
    generate if (DECODE_PIPE != 0) begin : g_decode_pipe
        always @(posedge clk or negedge rst_n) begin
            if (!rst_n) dp_phase <= 0;
            else if (st != S_RUN || fin) dp_phase <= 0;
            else begin
                case (dp_phase)
                    0: if (fq_n != 0) begin dp_ir <= fq[fq_rd]; dp_phase <= 1; end
                    1: begin dp_pos <= (VPOS != 0) ? pos_r+vp_off : pos_r; dp_phase <= 2; end
                    2: begin
                        dp_shifted <= dp_pos >> dp_amount;
                        dp_invalid <= (W != (1<<DP_WT)) || `F(ME_SPLIT)>DP_GT || `F(ME_SPLIT)>DP_WT+DP_GT;
ASSIGNMENTS
                        dp_phase <= 3;
                    end
                    3: begin dp_rounds <= dp_invalid ? {NW{1'b0}} : (dp_shifted/DP_ODD)+1'b1; dp_phase <= 4; end
                    4: if (load) dp_phase <= 0;
                    default: dp_phase <= 0;
                endcase
            end
        end
    end endgenerate
'''.replace('ASSIGNMENTS',assignments)
    text = once(text, '    // Decode: every base and count may add one DYN value.', block+'\n    // Decode: every base and count may add one DYN value.')
    return '// Generated held-decode candidate: DECODE_PIPE default OFF; no timing/adoption claim.\n'+text


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(emit(V.E.CORE.read_text()))

if __name__=='__main__':
    main()
