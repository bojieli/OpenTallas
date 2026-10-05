#!/usr/bin/env python3
"""Default-off registered ME argmax issue/commit; existing NEXT holds descriptor."""
import argparse
from pathlib import Path
import qwen_rom_core_dec_counter_emit_w12 as C


def apply(text):
    old='    parameter integer DEC_LA_COUNT_LA = 0\n) ('
    assert text.count(old)==1
    text=text.replace(old,'    parameter integer DEC_LA_COUNT_LA = 0,\n    parameter integer DEC_LA_AM_COMMIT = 0\n) (')
    first=text.index('    wire issue = (st == S_RUN)')
    end=text.index('    assign me_go =',first)
    original=text[first:end].replace('wire issue =','wire am_issue_eligible =')
    replacement=original+'''    // Reserve only the argmax-enabled ME instruction. Keep NEXT and its
    // entire FIFO descriptor held until the receiver actually accepts it.
    // No intervening go can change either producer's instruction epoch.
    wire am_commit_selected = (DEC_LA != 0 && DEC_LA_AM_COMMIT != 0);
    wire am_commit_target = am_commit_selected && d_unit == 2'd1 && me_amax;
    reg am_issue_pending;
    reg [NW-1:0] am_issue_idx;
    reg [31:0] am_issue_val;
    reg am_issue_any;
    wire am_reserve = am_commit_target && !am_issue_pending && am_issue_eligible;
    wire am_commit = am_commit_target && am_issue_pending && st == S_RUN && nx_v
                     && unit_ready && kv_gate && w_gate;
    wire issue = am_commit_selected
        ? (am_issue_pending ? am_commit : (!am_commit_target && am_issue_eligible))
        : am_issue_eligible;
    generate if (DEC_LA != 0 && DEC_LA_AM_COMMIT != 0) begin : g_am_commit
        always @(posedge clk or negedge rst_n)
            if (!rst_n) am_issue_pending <= 1'b0;
            else if (st == S_IDLE) am_issue_pending <= 1'b0;
            else if (am_reserve) am_issue_pending <= 1'b1;
            else if (am_commit) am_issue_pending <= 1'b0;
        // This local hold enable is independent of the chase/issue cone.
        // At reservation the old producer result is captured on that edge.
        always @(posedge clk) if (!am_issue_pending) begin
            am_issue_idx <= am_idx;
            am_issue_val <= am_val;
            am_issue_any <= am_any;
        end
    end else begin : g_am_original
        assign am_issue_pending = 1'b0;
        assign am_issue_idx = 0;
        assign am_issue_val = 0;
        assign am_issue_any = 0;
    end endgenerate
'''
    text=text[:first]+replacement+text[end:]
    old='    wire am_wins = am_any && (!run_any || ((DEC_LA != 0) ? la_am_gt : (okey(am_val) > run_key)));'
    assert text.count(old)==1
    text=text.replace(old,'''    // END still folds the current final producer result. Only the pending
    // previous-chunk update uses the reservation-edge snapshot.
    wire [NW-1:0] am_fold_idx = am_issue_pending ? am_issue_idx : am_idx;
    wire [31:0] am_fold_val = am_issue_pending ? am_issue_val : am_val;
    wire am_fold_any = am_issue_pending ? am_issue_any : am_any;
    wire am_wins = am_any && (!run_any || ((DEC_LA != 0) ? la_am_gt : (okey(am_val) > run_key)));
    wire la_am_fold_gt;
    ot_qwen_core_key_gt u_la_am_fold_gt (.a(okey(am_fold_val)), .b(run_key), .gt(la_am_fold_gt));
    wire am_fold_wins = am_fold_any && (!run_any || ((DEC_LA != 0) ? la_am_fold_gt : (okey(am_fold_val) > run_key)));''')
    old='''            else if (am_wins) begin
                run_any<=1'b1; run_key<=okey(am_val);
                run_idx<=am_idx+last_row0; run_val<=am_val;'''
    new='''            else if (am_fold_wins) begin
                run_any<=1'b1; run_key<=okey(am_fold_val);
                run_idx<=am_fold_idx+last_row0; run_val<=am_fold_val;'''
    assert text.count(old)==1
    return text.replace(old,new)


def emit(text):
    return apply(C.emit(text))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.write_text(emit(C.C.B.E.V.E.CORE.read_text()))
