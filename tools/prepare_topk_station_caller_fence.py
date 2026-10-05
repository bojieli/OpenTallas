"""Added-only fixed full-shape DMA station/fence preparation; no HDL execution."""
import argparse
import hashlib
import json
from pathlib import Path
import uarch_topk_buffered_station_source_model as M
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'results/rtl/topk_station_caller_fence_prepare_20261002'
SOURCE=ROOT/'results/uarch/topk_finite_source_context_20261002/inputs/c429b2732aea08d9f6fa9ddc850afdbd7b4bd6ea/rtl/chip/ot_w15_coll_dma.sv'


def replace_once(s,a,b):
    if s.count(a)!=1:raise ValueError('unique pinned caller anchor required: '+a)
    return s.replace(a,b)


def prepare(source):
    # All edits are opt-in transport and retirement wiring. Core geometry,
    # loader acceptance, arithmetic and original non-TOPK path are unchanged.
    s=replace_once(source,'module ot_w15_coll_dma #(','module ot_w15_coll_dma_station_prepare #(')
    s=replace_once(s,'    parameter integer TK_DIG = 8,','    parameter integer TK_STATION = 0,       // fixed source-bound100/29 station proposal, default off\n    parameter integer TK_DIG = 8,')
    s=replace_once(s,'    wire tk_ov, tk_ol, tk_done, tk_fault;','    wire tk_ov, tk_ol, tk_done, tk_fault;\n    wire tk_drained_done;')
    a='''        ot_coll_topk_merge #(.N(N), .NMAX(TK_NMAX), .LW(LANES), .LDW(GW == 4 ? N : 1), .P(TKW * LANES),
                             .DIG(TK_DIG)) u_tk (
'''
    b='''        localparam integer IPW = 1+1+RB+$clog2(N*TK_NMAX/LANES)+(GW==4?N:1)*FW+1+2*TCB+32;
        localparam integer OPW = 1+1+1+1+$clog2(TKW+1)+TKW*FW+1+32;
        wire [IPW-1:0] tk_input_native, tk_input_core;
        wire [OPW-1:0] tk_output_core, tk_output_dma;
        wire [1:0] tk_ld_control;
        wire [RB-1:0] tk_ld_rank;
        wire [$clog2(N*TK_NMAX/LANES)-1:0] tk_ld_word;
        wire [(GW==4?N:1)*FW-1:0] tk_ld_data;
        wire tk_core_go;
        wire [TCB-1:0] tk_core_n, tk_core_k;
        wire [31:0] tk_core_stride;
        wire tk_core_busy, tk_core_done, tk_core_fault, tk_core_ov, tk_core_ol;
        wire [$clog2(TKW+1)-1:0] tk_core_nw;
        wire [TKW*FW-1:0] tk_core_od;
        wire [31:0] tk_core_cycles;
        assign tk_input_native = {tk_ld, tk_wi >= CW'(nh_r), o_rank,
            $clog2(N*TK_NMAX/LANES)'(tk_wi >= CW'(nh_r) ? tk_wi-CW'(nh_r) : tk_wi),
            o_data[(GW == 4 ? N : 1)*FW-1:0], tk_go,
            TCB'(32'(nh_r)*LANES), TCB'(tk_k_r), tk_stride_r};
        assign {tk_ld_control, tk_ld_rank, tk_ld_word, tk_ld_data, tk_core_go,
                tk_core_n, tk_core_k, tk_core_stride} = tk_input_core;
        assign tk_output_core = {tk_core_busy, tk_core_done, tk_core_fault, tk_core_ov,
            tk_core_nw, tk_core_od, tk_core_ol, tk_core_cycles};
        assign { /* unused busy */ , tk_done, tk_fault, tk_ov, tk_nw, tk_od, tk_ol,
                 /* unused stat_cycles */ } = tk_output_dma;
        generate if (TK_STATION != 0) begin : g_station
            ot_topk_fixed_packet_delay_prepare #(.WIDTH(IPW), .EDGES(99), .MASK((IPW'(1)<<(IPW-1)) | (IPW'(1)<<(2*TCB+32)))) u_input (
                .clk(clk), .rst_n(rst_n), .in_packet(tk_input_native), .out_packet(tk_input_core));
            ot_topk_fixed_packet_delay_prepare #(.WIDTH(OPW), .EDGES(99), .MASK((OPW'(15)<<(OPW-4)) | (OPW'(1)<<32))) u_return (
                .clk(clk), .rst_n(rst_n), .in_packet(tk_output_core), .out_packet(tk_output_dma));
        end else begin : g_direct
            assign tk_input_core = tk_input_native;
            assign tk_output_dma = tk_output_core;
        end endgenerate
        ot_coll_topk_merge #(.N(N), .NMAX(TK_NMAX), .LW(LANES), .LDW(GW == 4 ? N : 1), .P(TKW * LANES),
                             .DIG(TK_DIG)) u_tk (
'''
    # Explicit unused sinks, no empty concat lvalues.
    b=b.replace('wire tk_core_busy,','wire tk_dma_busy_unused;\n        wire [31:0] tk_dma_cycles_unused;\n        wire tk_core_busy,')
    b=b.replace('{ /* unused busy */ ,','{tk_dma_busy_unused,').replace('/* unused stat_cycles */','tk_dma_cycles_unused')
    # No nested generate/endgenerate inside the existing generate region.
    b=b.replace('        generate if (TK_STATION','        if (TK_STATION').replace('        end endgenerate\n','        end\n')
    s=replace_once(s,a,b)
    s=replace_once(s,".ld_valid(tk_ld), .ld_id(tk_wi >= CW'(nh_r)), .ld_rank(o_rank),",'.ld_valid(tk_ld_control[1]), .ld_id(tk_ld_control[0]), .ld_rank(tk_ld_rank),')
    s=replace_once(s,".ld_word($clog2(N * TK_NMAX / LANES)'(tk_wi >= CW'(nh_r) ? tk_wi - CW'(nh_r) : tk_wi)),",'.ld_word(tk_ld_word),')
    s=replace_once(s,'.ld_data(o_data[(GW == 4 ? N : 1)*FW-1:0]),','.ld_data(tk_ld_data),')
    s=replace_once(s,".go(tk_go), .n(TCB'(32'(nh_r) * LANES)), .k(TCB'(tk_k_r)), .stride(tk_stride_r),",'.go(tk_core_go), .n(tk_core_n), .k(tk_core_k), .stride(tk_core_stride),')
    s=replace_once(s,'.busy(), .done(tk_done), .fault(tk_fault),\n            .out_valid(tk_ov), .out_nw(tk_nw), .out_data(tk_od), .out_last(tk_ol), .stat_cycles());','.busy(tk_core_busy), .done(tk_core_done), .fault(tk_core_fault),\n            .out_valid(tk_core_ov), .out_nw(tk_core_nw), .out_data(tk_core_od), .out_last(tk_core_ol), .stat_cycles(tk_core_cycles));')
    a='''    assign vm_we4 = (GW == 4 && tk_r) ? tk_we : (GW == 4 && e_mode) ? tr_we : {3'b000, vm_we};
    assign vm_waddr4 = (GW == 4 && tk_r) ? tk_wa : (GW == 4 && e_mode) ? tr_addr : {{3*WA{1'b0}}, vm_waddr};
    assign vm_wdata4 = (GW == 4 && tk_r) ? {{(4-TKW)*FW{1'b0}}, tk_od} :
                       (GW == 4 && e_mode) ? tr_data : {{3*FW{1'b0}}, vm_wdata};
'''
    b='''    wire [3:0] tk_sink_we;
    wire [4*WA-1:0] tk_sink_addr;
    wire [4*FW-1:0] tk_sink_data;
    localparam integer WPW=4+4*WA+4*FW+1;
    wire [WPW-1:0] tk_write_native, tk_write_sink;
    // Addresses are formed using the SAME preedge tk_oidx as native writes.
    // Delay addresses/enables/data/done together; never recompute delayed addresses.
    assign tk_write_native = {tk_we, tk_wa, {{(4-TKW)*FW{1'b0}},tk_od}, tk_done};
    assign {tk_sink_we,tk_sink_addr,tk_sink_data,tk_drained_done} = tk_write_sink;
    generate if (TK_STATION != 0) begin : g_write_station
        initial begin
            if (TOPK!=1 || N!=4 || GW!=4 || FW!=512 || WA!=15 || TK_NMAX!=2048 || TK_DIG!=8)
                $fatal(1,"STATION_FULL_GEOMETRY_REQUIRED");
            if (VM_ALWAYS_READY!=1) $fatal(1,"STATION_UNSTALLED_VM_REQUIRED");
        end
        ot_topk_fixed_packet_delay_prepare #(.WIDTH(WPW), .EDGES(28), .MASK((WPW'(15)<<(WPW-4)) | WPW'(1))) u_write (
            .clk(clk), .rst_n(rst_n), .in_packet(tk_write_native), .out_packet(tk_write_sink));
        // synthesis translate_off
        always @(posedge clk) if(rst_n && tk_r && !vm_ready4)
            $fatal(1,"STATION_VM_CREDIT_CONTRACT_VIOLATION");
        // synthesis translate_on
    end else begin : g_write_direct
        assign tk_write_sink = tk_write_native;
    end endgenerate
    // rst_n suppresses late write enables immediately, independently of payload FFs.
    assign vm_we4 = (GW == 4 && tk_r) ? (TK_STATION ? (tk_sink_we & {4{rst_n}}) : tk_we) :
                     (GW == 4 && e_mode) ? tr_we : {3'b000, vm_we};
    assign vm_waddr4 = (GW == 4 && tk_r) ? tk_sink_addr : (GW == 4 && e_mode) ? tr_addr : {{3*WA{1'b0}}, vm_waddr};
    assign vm_wdata4 = (GW == 4 && tk_r) ? tk_sink_data :
                       (GW == 4 && e_mode) ? tr_data : {{3*FW{1'b0}}, vm_wdata};
'''
    s=replace_once(s,a,b)
    s=replace_once(s,'if (tk_done) begin busy <= 0; tk_r <= 0; tk_sel <= 0; end','if (tk_drained_done) begin busy <= 0; tk_r <= 0; tk_sel <= 0; end')
    return s


def emit(out):
    if out.exists():raise ValueError('fresh prepared directory required')
    model=M.build();source=SOURCE.read_text();prepared=prepare(source)
    out.mkdir(parents=True)
    (out/'ot_w15_coll_dma_station_prepare.sv').write_text(prepared)
    helper=(ROOT/'tools/rtl_templates/ot_topk_fixed_packet_delay_prepare.sv').read_bytes()
    (out/'ot_topk_fixed_packet_delay_prepare.sv').write_bytes(helper)
    record={'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      'station_model':'results/uarch/topk_buffered_station_source_model_20261002/model_r2.json','geometry':model['fixed_geometry'],
      'input_edges':99,'return_edges':99,'formed_write_edges':28,'additional_cycles_per_call':226,'ninecall_extra_cycles':2034,
      'default_off':True,'actual_source_acceptance_preserved':'tk_ld with o_ready=1; existing busy/bad command/fault checks unchanged',
      'drain':'tk_drained_done is same formed-write packet as original tk_done; busy/dst ownership retained to delayed done',
      'reset':'payload FFs reset-free; packet present flags clear asynchronously; TK write enables additionally gated by rst_n',
      'arithmetic_core_unchanged':True,'balanced_selector_implementation_dependency_still_open':True,
      'full_shape_only_when_enabled':True,'no_new_ACK_ready_or_command_context':True,
      'control_guard_area_addition':{'mask_bits_at_terminal_groups':[2,5,5],'group_present_AND_rst_guards':3,'explicit_VM_rst_enable_ANDs':4,'AND2x2_upper_cell_count':19,'AND2x2_cell_area_um2':19*0.08748,'AND2x2_reservation_mm2_at50pct':19*0.08748*2/1e6,'must_add_to84b_once':True,'sink_control_timing_load_not_qualified':True},
      'cell_mapping_clock_PG_hold_and_async_reset_guards_not_qualified':True,'compile_admitted':False,'PR_admitted':False,
      'independent_tests_scope':'transport control/bit-order and actual source indexing only, no selector arithmetic or numerical claim'}
    (out/'sourceplan.json').write_text(json.dumps(record,indent=2,sort_keys=True)+'\n')
    pins={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir() if p.is_file()}
    (out/'artifact_manifest.json').write_text(json.dumps(pins,indent=2,sort_keys=True)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();emit(a.out)
