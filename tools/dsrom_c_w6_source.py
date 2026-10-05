#!/usr/bin/env python3
"""Source-select W6 event instrumentation into the actual system harness.
No component campaign is rerun; use this top for the next combined parent run.
"""
import argparse
from pathlib import Path


def instrument(source):
    assert 'W6_TRACE' not in source, 'Already instrumented'
    anchor='    parameter integer USERS = 2,'
    assert source.count(anchor)==1
    source=source.replace(anchor,'    parameter integer W6_TRACE = 0,\n'+anchor)
    anchor='            // -- accounting and the lm_head logit check'
    assert source.count(anchor)==1
    trace='''            // W6: actual stage issue/done and accepted handoff events.
            // No acceptance, timing or state ownership is changed by this observer.
            reg [7:0] w6_user;
            reg [NW-1:0] w6_pos;
            reg [63:0] w6_issue;
            always @(posedge clk) if (rst_n && W6_TRACE) begin
                if (core_start) begin
                    w6_user <= cur_u; w6_pos <= core_pos; w6_issue <= cyc;
                    $display("W6_STAGE_ISSUE node=%0d user=%0d pos=%0d cycle=%0d", n, cur_u, core_pos, cyc);
                end
                if (done && !done_q && cyc > 40)
                    $display("W6_STAGE_DONE node=%0d user=%0d pos=%0d cycle=%0d issue=%0d delta=%0d", n, w6_user, w6_pos, cyc, w6_issue, cyc-w6_issue);
                if (g_out_valid && c_in_ready)
                    $display("W6_HOP_ACCEPT node=%0d cycle=%0d last=%0d flit=%h", n, cyc, g_out_last, g_out_data);
                if (c_out_valid && tx_r[n] && out_ok)
                    $display("W6_HOP_SEND node=%0d cycle=%0d last=%0d flit=%h", n, cyc, tx_l[n], tx_d[n*FLIT +: FLIT]);
            end

'''
    source=source.replace(anchor,trace+anchor)
    anchor='                wire [127:0] h_v, h_rdy, h_we, h_wr_done;'
    assert source.count(anchor)==1
    # Raw accepted port/address/tag and visible-completion bitmap: no request
    # acceptance is promoted to visibility and no current-user ACK attribution.
    trace='''
                integer w6_port;
                always @(posedge clk) if (rst_n && W6_TRACE) begin
                    for (w6_port=0; w6_port<128; w6_port=w6_port+1)
                        if (h_v[w6_port] && h_rdy[w6_port])
                            $display("W6_HBM_ACCEPT node=%0d port=%0d cycle=%0d write=%0d addr=%0d tag=%0d len=%0d", n, w6_port, cyc, h_we[w6_port], h_addr[w6_port*28+:28], h_tag[w6_port*16+:16], h_len[w6_port*4+:4]);
                    if (|h_wr_done)
                        $display("W6_HBM_VISIBLE node=%0d cycle=%0d ports=%h", n, cyc, h_wr_done);
                end
'''
    return source.replace(anchor,anchor+trace)


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--out',type=Path,required=True)
    a=ap.parse_args()
    if a.out.exists(): raise SystemExit('Refusing to overwrite retained source')
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(instrument(a.input.read_text()))

if __name__=='__main__': main()
