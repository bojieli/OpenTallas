#!/usr/bin/env python3
"""Emit the priced, default-off ready-boundary successor to enabled kc6."""
from pathlib import Path
import hashlib
import json
ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'rtl/experimental/dsrom_reindex_kc6_20261005'
OUT = ROOT / 'rtl/experimental/dsrom_reindex_kc7_20261005'

def once(s, old, new):
    assert s.count(old) == 1, old[:80]
    return s.replace(old, new)

def emit():
    model = json.loads((ROOT / 'results/uarch/dsrom_reindex_kc7_20261005/model.json').read_text())
    assert model['slot']['remaining_cts_buffer_mapping_budget_um2'] > 0
    donor = BASE / 'ot_hdc_v41x_idx_kgather_kc6.sv'
    assert hashlib.sha256(donor.read_bytes()).hexdigest() == model['parent_source_sha256']
    s = donor.read_text().replace('_kc6', '_kc7')
    # OPT_KC6=1 retains the already-qualified reset mask/derived partials.
    # OPT_KC7=0 selects EXACT kc6 behavior, not the unsafe pre-kc6 baseline.
    s = s.replace('parameter integer OPT_KC6 = 0,', 'parameter integer OPT_KC6 = 1,\n    parameter integer OPT_KC7 = 0,')
    s = s.replace('.OPT_KC6(OPT_KC6),', '.OPT_KC6(OPT_KC6), .OPT_KC7(OPT_KC7),')
    anchor = '    reg            dq_v; reg [1:0] dq_m;'
    extra = '''    // All arithmetic and rob comparisons are independent of actual ready.
    wire [QW-1:0] seq_one = d_seq + QW'(1), seq_two = d_seq + QW'(2);
    wire [QW-1:0] left_one = d_left - QW'(1), left_two = d_left - QW'(2);
    wire [QW-1:0] use_base = inuse + (disp ? QW'(2) : QW'(0));
    wire [QW-1:0] use_one = use_base - QW'(1), use_two = use_base - QW'(2);
    wire [QW-1:0] next_seq, next_left, next_use;
    wire next_rob_ok;
    generate for (genvar ds=0; ds<QW; ds=ds+4) begin : g_drain_ready_last
        localparam integer W = (QW-ds < 4) ? QW-ds : 4;
        ot_dsrom_kc7_ready_last #(.W(W)) u_seq (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(d_seq[ds+:W]), .one_head(seq_one[ds+:W]),
            .two_head(seq_two[ds+:W]), .next_head(next_seq[ds+:W]));
        ot_dsrom_kc7_ready_last #(.W(W)) u_left (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(d_left[ds+:W]), .one_head(left_one[ds+:W]),
            .two_head(left_two[ds+:W]), .next_head(next_left[ds+:W]));
        ot_dsrom_kc7_ready_last #(.W(W)) u_use (
            .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
            .old_head(use_base[ds+:W]), .one_head(use_one[ds+:W]),
            .two_head(use_two[ds+:W]), .next_head(next_use[ds+:W]));
    end endgenerate
    ot_dsrom_kc7_ready_last #(.W(1)) u_rob (
        .eligible(drain_eligible), .two(drain_two), .ready(dr_ready),
        .old_head(use_base <= QW'(WB-4)), .one_head(use_one <= QW'(WB-4)),
        .two_head(use_two <= QW'(WB-4)), .next_head(next_rob_ok));
'''
    s = once(s, anchor, extra + anchor)
    old = '''                if (can0) begin
                    d_seq <= d_seq + (can1 ? 2 : 1);
                    d_left <= d_left - (can1 ? 2 : 1);
                    if (!OPT_KC6) hoh <= can1 ? rotl(hoh, 2) : rotl(hoh, 1);
                end'''
    new = '''                if (OPT_KC7) begin
                    d_seq <= next_seq;
                    d_left <= next_left;
                end else if (can0) begin
                    d_seq <= d_seq + (can1 ? 2 : 1);
                    d_left <= d_left - (can1 ? 2 : 1);
                end
                if (can0 && !OPT_KC6) hoh <= can1 ? rotl(hoh, 2) : rotl(hoh, 1);'''
    s = once(s, old, new)
    s = once(s, '''                inuse <= nu;
                rob_ok <= (nu <= QW'(WB - 4));''', '''                inuse <= OPT_KC7 ? next_use : nu;
                rob_ok <= OPT_KC7 ? next_rob_ok : (nu <= QW'(WB - 4));''')
    # Separate FIFO read/priority from eligibility and final ready selection.
    anchor = '    // ---- data (no reset: every word is written before it is read)'
    extra = '''    localparam integer RQPW = AW + LENW + TAGW;
    wire [NPC*RQPW-1:0] next_payload;
    generate for (genvar pp=0; pp<NPC; pp=pp+1) begin : g_payload_ready_last
        wire [RQPW-1:0] code_payload = {fq_addr[pp*DF+fq_rp[pp]],
            LENW'(4), TAGW'({1'b0, fq_slot[pp*DF+fq_rp[pp]]})};
        wire [RQPW-1:0] scale_payload = {fq_addr[(NPC+pp)*DF+fq_rp[NPC+pp]],
            LENW'(1), TAGW'({1'b1, fq_slot[(NPC+pp)*DF+fq_rp[NPC+pp]]})};
        wire [RQPW-1:0] old_payload = {req_addr[pp*AW+:AW],
            req_len[pp*LENW+:LENW], req_tag[pp*TAGW+:TAGW]};
        for (genvar ps=0; ps<RQPW; ps=ps+8) begin : g_slice
            localparam integer W = (RQPW-ps < 8) ? RQPW-ps : 8;
            ot_dsrom_kc7_payload_last #(.W(W)) u_select (
                .eligible(run && ((fq_n[pp] != 0) || use_s[pp])),
                .scale(use_s[pp]), .valid(req_v[pp]), .ready(req_rdy[pp]),
                .old_data(old_payload[ps+:W]), .code_data(code_payload[ps+:W]),
                .scale_data(scale_payload[ps+:W]), .next_data(next_payload[pp*RQPW+ps+:W]));
        end
    end endgenerate
'''
    s = once(s, anchor, extra + anchor)
    s = once(s, '''        for (p2 = 0; p2 < NPC; p2 = p2 + 1)
            if (iss[p2]) begin''', '''        for (p2 = 0; p2 < NPC; p2 = p2 + 1)
            if (OPT_KC7) begin
                {req_addr[p2*AW+:AW], req_len[p2*LENW+:LENW], req_tag[p2*TAGW+:TAGW]}
                    <= next_payload[p2*RQPW+:RQPW];
            end else if (iss[p2]) begin''')
    s += '''
// Combinational partition only: no ready sample, state, or protocol edge.
(* keep_hierarchy = "yes" *)
module ot_dsrom_kc7_payload_last #(parameter integer W=8) (
    input wire eligible, scale, valid, ready,
    input wire [W-1:0] old_data, code_data, scale_data,
    output wire [W-1:0] next_data
);
    (* keep = 1 *) wire [W-1:0] selected = scale ? scale_data : code_data;
    (* keep = 1 *) wire [W-1:0] available = eligible ? selected : old_data;
    assign next_data = (ready || !valid) ? available : old_data;
endmodule
'''
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'ot_hdc_v41x_idx_kgather_kc7.sv').write_text(s)
    for name in ['ot_hdc_v41x_idx_kgctl_kc6_ctx.sv','tb_hdc_v41x_idx_kgather_kc6.sv']:
        t=(BASE/name).read_text().replace('_kc6','_kc7')
        t=t.replace('parameter integer OPT_KC6 = 0,','parameter integer OPT_KC6 = 1,\n    parameter integer OPT_KC7 = 0,')
        t=t.replace('.OPT_KC6(OPT_KC6),','.OPT_KC6(OPT_KC6), .OPT_KC7(OPT_KC7),')
        (OUT/name.replace('_kc6','_kc7')).write_text(t)
    paths=[donor,ROOT/'tools/dsrom_reindex_kc7_emit.py',ROOT/'tools/uarch_model.py',*sorted(OUT.glob('*.sv'))]
    manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    (ROOT/'results/uarch/dsrom_reindex_kc7_20261005/source_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(OUT)
if __name__=='__main__': emit()
