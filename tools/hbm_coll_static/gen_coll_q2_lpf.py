#!/usr/bin/env python3
"""PL-COLLQ (PARENTS-LANDED 10-18): expand the HBM COLL quadrant parent ot_hfd_coll_q2_hard_v8g (SE/NW/NE, NLINK 2,
SOLO 0) into the WIRES-ONLY flat parent tools/landed_parent/lp.py needs, at the granularity of the closed child views:

  ot_hfd_coll_q2_lpf   same ports and clock-entry ports as ot_hfd_coll_q2_hard_v8g; no generate / always / params on
                       children.  Children: u_fj (fj_q2), u_issuer (issuer_m), u_up<s> x16 (uop_slice96), u_va<s> x16
                       (vmasm_slice16), u_control (ctl_v5_q2), u_qc<s> x9 (qslots_capture_pin_v2), u_qo<k> x18
                       (qso_q2_b32 x17 + qso_q2_b1), u_link<k> x2 (link_e), u_reduce (reduce_static), u_writer
                       (vmwrite_roots_v6_physical), u_rctl (ring_ag_ctl) + u_rst<l> x8 (state_capture_lane) + u_radd<l>
                       x8 (pring_static_add_lane) = the v8g u_ring (ot_hgi_coll_ring_ag SPLIT_CLOCKS 1, AG 1) expanded.
  The v8g body's bit-interleave generate loops become concatenation assigns; nets that leave the switch region for the
  VM writer get their own wires (w_*), so a landing carries only the bits the writer reads.
  tb_hfd_coll_q2_lpf_eq: random-stimulus lockstep ot_hfd_coll_q2_hard_v8g vs ot_hfd_coll_q2_lpf, every output, every
  cycle (the expansion is exact: zero offsets).

  python3 tools/hbm_coll_static/gen_coll_q2_lpf.py      (writes both files into rtl/hbm_accel/generic/collective/p2p)

TW2-COLLAR (10-19): the XDIE-HBM4 parameters (v8g #(.AR_ITER(1), .ROWS(128)), commit 26a9b51eb):
  python3 tools/hbm_coll_static/gen_coll_q2_lpf.py q2 q3 --ar-iter --rows 128 --suffix _ar
  -> ot_hfd_coll_<v>_lpf_ar: u_issuer / u_fj #(.ROWS(128)) with 7-bit uop_pc / hgi_start_pc; the v8g g_ariter flops as
  the leaf u_ariter (ot_hgi_coll_ariter_tag: it_d1/it_d2 on clk_issue, tags on clk_reduce[0]); u_control.inst =
  inst_ctl (inst_d2 with [717:714] zeroed).  tb_hfd_coll_<v>_lpf_ar_eq: lockstep vs the v8g/v8x #(AR_ITER 1, ROWS 128)
  parent under the scripted programme rtl/.../p2p/landed/stim_<v>_lp_ar.vh (looped AR rows, iter_ar_tag_step != 0).
  Defaults (no options) = the original output, byte-identical.

HBM-ELEMOWN3/COLLQ3 (10-19): --safe (with --ar-iter --rows 128 --suffix _ars) = the SAFE successor's flat parent: every soft
  mass that put raw SRAMs or tens of thousands of flops on the sw region root becomes ONE hard child with one scalar clock
  pin and no instance parameters (rtl/.../p2p/ot_hgi_coll_safe_leaves.sv): u_issuer = ot_hgi_coll_issuer_m_r128 (6 SRAMs),
  u_fj = <fj>_r128, u_link<k> = ot_hgi_coll_link_e1 (clk = clk_link[5k]; 4 SRAMs), and the reduce = u_rdc
  (ot_hgi_coll_reduce_static_ctl, soft: tags / faults / writeback pipe / out_flit) + u_rdl0..15 (ot_hgi_coll_reduce_lane,
  hard: 16 x 32 b state + LAT-8 add, clk = clk_reduce[1+l]).  Exact: the same lockstep vs the v8g/v8x reference
  (tb_hfd_coll_<v>_lpf_ars_eq, the _ar scripted programme stim_<v>_lp_ar.vh).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "rtl/hbm_accel/generic/collective/p2p"
NPT, ND, NSL, PWT, SELW = 2, 15, 18, 545, 4
# q2 = ot_hfd_coll_q2_hard_v8g (SE/NW/NE, SOLO 0); q3 = ot_hfd_coll_q3_hard_v8x #(NLINK 2, TP 192) (SW, SOLO 1: argmax
# source 9 + capture slot p_ring[82], ctl/fj/qso n2s1 masters, TKM interface tkx_* on pins: the die's tkm_SW)
VARIANTS = {
    "q2": {"SOLO": 0, "NS": 9, "ref": "ot_hfd_coll_q2_hard_v8g", "ctl": "ot_hgi_coll_ctl_v5_q2", "fj": "ot_hgi_coll_fj_q2",
           "qso": "ot_hgi_coll_qso_q2"},
    "q3": {"SOLO": 1, "NS": 10, "ref": "ot_hfd_coll_q3_hard_v8x #(.NLINK(2),.TP(192))", "ctl": "ot_hgi_coll_ctl_v5_n2s1",
           "fj": "ot_hgi_coll_fj_n2s1", "qso": "ot_hgi_coll_qso_n2s1"},
}

HEADER_PORTS = """ input wire rst_n,input wire [1:0] qid,qid_rg,qid_wr,
 input wire clk_program,clk_control,input wire [15:0] clk_vmasm,clk_upipe,input wire clk_issue,input wire [@NCK@:0] clk_qslots,
 input wire [16:0] clk_ring,input wire [32:0] clk_reduce,@ARG@
 input wire [15:0] clk_vmwrite,input wire [9:0] clk_link,
 input wire cfg_v,input wire [7:0] cfg_target,input wire [11:0] cfg_addr,input wire [255:0] cfg_data,
 input wire desc_v,input wire [11:0] desc_base,input wire [12:0] desc_limit,input wire [15:0] desc_loops,
 input wire launch_v,
 output wire program_configured,program_init_busy,program_fault,hgi_busy,hgi_done,hgi_fault,
 output wire [1:0] inj_rd,output wire [31:0] inj_idx,output wire [159:0] hgi_inj_addr,input wire [1023:0] inj_d,
 output wire [3:0] del_valid,output wire [2179:0] del_flit,output wire [159:0] hgi_del_obase,
 input wire rc_v,input wire [2:0] rc_tag,input wire [255:0] rc_d,
 output wire rr_v,output wire [2:0] rr_tag,output wire [255:0] rr_d,
 input wire [1:0] phy_up,output wire [1:0] tx_pin_v,output wire [1223:0] tx_pin_flit,
 input wire [1:0] rx_pin_v,input wire [1223:0] rx_pin_flit,output wire [1:0] retry_requested,
 input wire [279:0] pr_cw_i,pr_ccw_i,output wire [279:0] pr_cw_o,pr_ccw_o,
 output wire [57:0] isa_ring,output wire [255:0] isa_lp_data,
 input wire ra_lp_we,input wire [2:0] ra_lp_tag,input wire [255:0] ra_lp_data,
 input wire ra_state_read_add,ra_state_read_tx,ra_state_read_rr,input wire [2:0] ra_state_add_tag,ra_state_tx_tag,ra_state_rr_tag,
 input wire [1:0] ra_state_add_src,input wire ra_state_add_rhs_acc,ra_state_tx_acc,ra_add_v,input wire [2:0] ra_add_tag,
 input wire [1:0] ra_add_src,input wire ra_add_rhs_acc,input wire [1:0] ra_tx_inject,ra_tx_forward,input wire [2:0] ra_tx_tag,
 input wire [1:0] ra_tx_dst,input wire ra_tx_result,ra_tx_acc,ra_tx_gather,input wire [3:0] ra_tx_ttl,
 input wire [1:0] ra_rx_slot,input wire [3:0] ra_rx_kind,ra_rx_src,input wire [5:0] ra_rx_tag,input wire ra_rr_local,
 input wire [2:0] ra_rr_local_tag,
 output wire [1:0] ag_v,output wire [3:0] ag_src,output wire [5:0] ag_tag,output wire [511:0] ag_d,
 output wire [135:0] vm_rq,input wire [2055:0] vm_rr,output wire [2247:0] vm_kq,@TKX@
 output wire fault,output wire [15:0] fault_cause,output wire done,output wire [31:0] stat_cycles"""


TKX = """
 output wire tkx_start,tkx_arg_mode,output wire [11:0] tkx_cfg_n,output wire [12:0] tkx_cfg_k,tkx_cfg_nout,
 output wire [7:0] tkx_cfg_g,tkx_cfg_gbase,output wire [15:0] tkx_cfg_pf,output wire [39:0] tkx_cfg_obase,tkx_cfg_rbase,
 output wire tkx_cfg_has_r,output wire [3:0] tkx_del_slot,tkx_del_valid,output wire [2179:0] tkx_del_flit,
 input wire tkx_w_v,input wire [39:0] tkx_w_addr,input wire [15:0] tkx_w_mask,input wire [511:0] tkx_w_data,
 input wire tkx_busy,tkx_done,tkx_fault,"""


def header(v):
    solo = VARIANTS[v]["SOLO"]
    return (HEADER_PORTS.replace("@ARG@", "input wire clk_arg," if solo else "")
            .replace("@NCK@", str(VARIANTS[v]["NS"] + NSL - 1)).replace("@TKX@", TKX if solo else ""))


def cat(bits):
    """MSB-first concatenation of bit-select strings given LSB-first"""
    return "{" + ",".join(reversed(bits)) + "}"


def flat(v="q2", ar=False, rows=64, suffix="", safe=False) -> str:
    VV = VARIANTS[v]
    SOLO, NS = VV["SOLO"], VV["NS"]
    PW = 7 if rows > 64 else 6
    rp = f" #(.ROWS({rows}))" if rows != 64 else ""
    if safe and not (ar and rows == 128):
        raise SystemExit("--safe is the AR_ITER 1 / ROWS 128 successor: use --ar-iter --rows 128")
    L = []
    w = L.append
    w("`timescale 1ns/1ps")
    w("`default_nettype none")
    w("// GENERATED by tools/hbm_coll_static/gen_coll_q2_lpf.py (PL-COLLQ 10-18) -- do not edit.")
    if not SOLO:
        w("// WIRES-ONLY flat expansion of ot_hfd_coll_q2_hard_v8g (q2 COLL quadrant parent, NLINK 2, SOLO 0) at closed-view")
    else:
        w("// WIRES-ONLY flat expansion of ot_hfd_coll_q3_hard_v8x #(NLINK 2, TP 192) (q3 SW COLL quadrant parent, SOLO 1) at closed-view")
    if ar or rows != 64:
        w(f"// TW2-COLLAR (10-19): parameters AR_ITER={int(ar)}, ROWS={rows} (XDIE-HBM4 26a9b51eb); lockstep-identical to the"
          f" parent #(AR_ITER {int(ar)}, ROWS {rows}) (tb_hfd_coll_{v}_lpf{suffix}_eq).")
        w(f"// granularity: same ports / clock entries. Input of lp.py (landed parent).")
    else:
        w(f"// granularity: same ports / clock entries; lockstep-identical (tb_hfd_coll_{v}_lpf_eq). Input of lp.py (landed parent).")
    w(f"module ot_hfd_coll_{v}_lpf{suffix}(")
    w(header(v))
    w(");")
    w(" localparam integer PWT=545;")
    # issuer / fj / upipe
    w(f" wire [36:0] program_cfg;wire hgi_start;wire [{PW - 1}:0] hgi_start_pc;")
    w(f" wire issue_fault,issue_done,uop_v;wire [1535:0] inst,inst_d1,inst_d2;wire [{PW - 1}:0] uop_pc;wire busy_d2,start_d3;")
    w(" wire issue_busy_raw,issue_done_raw,start_d2;wire [31:0] tap_iteration;wire [87:0] tap_steps;")
    if safe:
        w("// HBM-ELEMOWN3/COLLQ3 --safe: issuer / fj / link_e / reduce lanes are hard children (ot_hgi_coll_safe_leaves.sv).")
    w(f" {'ot_hgi_coll_issuer_m_r128' if safe else 'ot_hgi_coll_issuer_m' + rp} u_issuer(.clk_control(clk_issue),.rst_n(rst_n),")
    w("  .cfg(program_cfg),.start(hgi_start),.start_pc(hgi_start_pc),.busy(issue_busy_raw),.done(issue_done_raw),")
    w("  .fault(issue_fault),.uop_v(uop_v),.uop_pc(uop_pc),.uop_d1(inst_d1),.busy_d3(hgi_busy),.done_d3(issue_done),")
    w("  .start_d3(start_d3),.busy_d2(busy_d2),.start_d2(start_d2),.tap_iteration(tap_iteration),.tap_steps(tap_steps));")
    for s in range(16):
        w(f" ot_hgi_coll_uop_slice96 u_up{s}(.clk(clk_upipe[{s}]),.d1(inst_d1[{s * 96}+:96]),.d2(inst_d2[{s * 96}+:96]),"
          f".d3(inst[{s * 96}+:96]));")
    w(" assign hgi_done=issue_done;assign done=issue_done;assign hgi_fault=fault;")
    # ISA fields
    w(" wire [9:0] p_capture_slot=inst[0+:10];")
    w(" wire [15:0] p_sink_slot=inst[10+:16];")
    w(" wire [63:0] p_sink_select=inst[26+:64];")
    w(" wire [2:0] p_lk_wr_v=inst[350+:3],p_lk_rd_v=inst[371+:3],p_lk_rx_expect=inst[392+:3],p_lk_epoch_begin=inst[413+:3];")
    w(" wire [7:0] p_lk_epoch=inst[416+:8];")
    w(" wire [87:0] p_ring=inst[630+:88];")
    w(" wire p_tkm_start=inst[718];")
    w(" wire [3:0] p_tkm_del_slot=inst[719+:4];")
    w(" wire [7:0] p_tkm_cfg_g=inst[761+:8],p_tkm_cfg_gbase=inst[769+:8];")
    if SOLO:
        w(" wire [11:0] p_tkm_cfg_n=inst[723+:12];")
        w(" wire [12:0] p_tkm_cfg_k=inst[735+:13],p_tkm_cfg_nout=inst[748+:13];")
        w(" wire [15:0] p_tkm_cfg_pf=inst[777+:16];")
        w(" wire [39:0] p_tkm_cfg_obase=inst[793+:40],p_tkm_cfg_rbase=inst[833+:40];")
        w(" wire p_tkm_cfg_has_r=inst[873];")
    w(" wire [30:0] p_ar_low=inst[1505+:31];")
    w(" wire [54:0] ar={p_ring[81:58],p_ar_low};")
    if ar:
        # v8g g_ariter (XDIE-HBM4): iterated reduce tags, the flops in the leaf u_ariter (clk_issue / clk_reduce[0])
        w(" wire a_load_v=ar[0];wire a_add_read=ar[5];wire [3:0] a_load_tag,a_read_tag,a_pub_tag_a,a_pub_tag_b;wire [15:0] a_pub_index;")
        w(" wire a_add_issue=ar[10];wire a_pub_read=ar[11];")
        w(" wire a_pub_bf16=ar[20],a_pub_release=ar[21],a_pub_issue=ar[22];wire [7:0] a_pub_src=ar[23+:8];")
        w(" wire [1535:0] inst_ctl={inst_d2[1535:718],4'b0,inst_d2[713:0]};")
        w(" ot_hgi_coll_ariter_tag u_ariter(.clk_issue(clk_issue),.clk_tag(clk_reduce[0]),.iteration(tap_iteration[15:0]),")
        w("  .ar2({inst_d2[688+:24],inst_d2[1505+:31]}),.st2(inst_d2[714+:4]),.load_tag(a_load_tag),.read_tag(a_read_tag),")
        w("  .pub_tag_a(a_pub_tag_a),.pub_tag_b(a_pub_tag_b),.pub_index(a_pub_index));")
    else:
        w(" wire a_load_v=ar[0];wire [3:0] a_load_tag=ar[1+:4];wire a_add_read=ar[5];wire [3:0] a_read_tag=ar[6+:4];")
        w(" wire a_add_issue=ar[10];wire a_pub_read=ar[11];wire [3:0] a_pub_tag_a=ar[12+:4],a_pub_tag_b=ar[16+:4];")
        w(" wire a_pub_bf16=ar[20],a_pub_release=ar[21],a_pub_issue=ar[22];wire [7:0] a_pub_src=ar[23+:8];")
        w(" wire [15:0] a_pub_index=ar[31+:16];")
    if SOLO:
        w(" wire a_arg_mode=ar[47],a_arg_start=ar[48],a_arg_flush=ar[49],a_arg_publish=ar[50];")
        w(" wire [3:0] a_arg_in_slot=ar[51+:4];")
    # VM writer inputs taken from the ISA word: own wires (they cross to the writer region)
    w(" wire w_rgx_vm=inst[584];")
    w(" wire [4:0] w_ingress_slot=inst[585+:5];")
    w(" wire [7:0] w_slot_valid=inst[590+:8];")
    w(" wire [31:0] w_slot_owner=inst[598+:32];")
    # protocol leaf + VM read assembly
    w(" wire [135:0] vm_req_pin;wire [1:0] inj_req_pin,inj_source_v;wire [31:0] inj_idx_pin;")
    w(" wire [159:0] inj_addr_pin,delivery_obase_pin,rgx_addr_pin;wire [65:0] inj_source_meta;wire [131:0] vm_source_meta;")
    w(" wire [2047:0] vm_assembled;wire [3:0] vm_assembled_v;wire [15:0] held_epoch;")
    w(" wire [7:0] vm_rv;wire [2047:0] vm_rd_il,vm_as_il;")
    w(" wire [23:0] vm_sel=inst[1383+:24];")
    w(" assign vm_rv=" + cat([f"vm_rr[{b * 257 + 256}]" for b in range(8)]) + ";")
    w(" assign vm_rd_il=" + cat([f"vm_rr[{b * 257 + i}]" for i in range(256) for b in range(8)]) + ";")
    asm = [None] * 2048
    for j in range(4):
        for i in range(256):
            asm[j * 512 + i] = f"vm_as_il[{i * 8 + 2 * j}]"
            asm[j * 512 + 256 + i] = f"vm_as_il[{i * 8 + 2 * j + 1}]"
    w(" assign vm_assembled=" + cat(asm) + ";")
    for s in range(16):
        w(f" ot_hgi_coll_vmasm_slice16 u_va{s}(.clk(clk_vmasm[{s}]),.sel(vm_sel),.rd_il(vm_rd_il[{s * 128}+:128]),"
          f".as_il(vm_as_il[{s * 128}+:128]));")
    w(" wire [31:0] wr_sequence_pin,rd_sequence_pin,rx_sequence_pin;wire protocol_fault;")
    w(" wire [14:0] dest_v;wire [8174:0] dest_d;")
    w(" assign hgi_del_obase=delivery_obase_pin;assign inj_rd=inj_req_pin;assign inj_idx=inj_idx_pin;")
    w(" assign hgi_inj_addr=inj_addr_pin;assign vm_rq=vm_req_pin;")
    # sources
    w(" wire reduce_out_v,reduce_fault;wire [544:0] reduce_out_data;wire [7:0] reduce_fault_cause;")
    w(" wire [1:0] link_rx_v,link_abort;wire [1089:0] link_rx_data;wire [21:0] link_cause;")
    w(f" wire [{NS - 1}:0] capture_fault;wire [17:0] select_fault,unavailable_fault;wire ring_fault,writer_fault;")
    sv = ["inj_source_v[0]", "inj_source_v[1]", "link_rx_v[0]", "link_rx_v[1]"] + \
         [f"vm_assembled_v[{j}]" for j in range(4)] + ["reduce_out_v"]
    sd = [f"{{inj_source_meta[{j * 33}+:33],inj_d[{j * 512}+:512]}}" for j in range(2)] + \
         [f"link_rx_data[{k * PWT}+:{PWT}]" for k in range(2)] + \
         [f"{{vm_source_meta[{j * 33}+:33],vm_assembled[{j * 512}+:512]}}" for j in range(4)] + ["reduce_out_data"]
    if SOLO:
        w(" wire arg_out_v,arg_fault;wire [544:0] arg_out_data;")
        sv += ["arg_out_v"]
        sd += ["arg_out_data"]
    w(f" wire [{NS - 1}:0] source_v=" + cat(sv) + ";")
    w(f" wire [{NS * PWT - 1}:0] source_d=" + cat(sd) + ";")
    if SOLO:
        w(" wire [9:0] capture_calendar={p_ring[82],p_capture_slot[8:0]};")
    else:
        w(" wire [8:0] capture_calendar=p_capture_slot[8:0];")
    w(f" {VV['ctl']} u_control(.clk_control(clk_control),.rst_n(rst_n),.inst({'inst_ctl' if ar else 'inst_d2'}),")
    w("  .tap_iteration(tap_iteration),.tap_steps(tap_steps),.hgi_start(start_d2),.hgi_busy(busy_d2),.issue_done(issue_done),"
      + (".tkm_done(tkx_done),.tkm_busy(tkx_busy)," if SOLO else ".tkm_done(1'b0),.tkm_busy(1'b0),"))
    w("  .dest_v(dest_v),.rc_v(rc_v),.rc_tag(rc_tag),.vm_rv(vm_rv),")
    w("  .vm_req_pin(vm_req_pin),.inj_req_pin(inj_req_pin),.inj_idx_pin(inj_idx_pin),.inj_addr_pin(inj_addr_pin),")
    w("  .delivery_obase_pin(delivery_obase_pin),.rgx_addr_pin(rgx_addr_pin),")
    w("  .inj_source_v(inj_source_v),.inj_source_meta(inj_source_meta),.vm_source_meta(vm_source_meta),")
    w("  .vm_assembled_v(vm_assembled_v),.held_epoch(held_epoch),")
    w("  .wr_sequence_pin(wr_sequence_pin),.rd_sequence_pin(rd_sequence_pin),.rx_sequence_pin(rx_sequence_pin),")
    w("  .protocol_fault(protocol_fault),.cycles(stat_cycles));")
    if SOLO:
        w(" ot_hgi_coll_argmax_m_tp192 u_arg(.clk(clk_arg),.rst_n(rst_n),.start(a_arg_start),.mode(a_arg_mode),")
        w("  .cfg_g(p_tkm_cfg_g),.cfg_gbase(p_tkm_cfg_gbase),.cfg_rank(a_pub_src),")
        w("  .in_slot(a_arg_in_slot),.in_v(dest_v[10+:4]),")
        w("  .in_key(" + cat([f"dest_d[{(10 + i) * PWT}+:64]" for i in range(4)]) + "),")
        w("  .in_meta(" + cat([f"dest_d[{(10 + i) * PWT + 512}+:33]" for i in range(4)]) + "),")
        w("  .flush_slot(a_arg_flush),.publish_slot(a_arg_publish),.out_v(arg_out_v),.out_flit(arg_out_data),.fault(arg_fault));")
        w(" assign tkx_start=p_tkm_start;assign tkx_arg_mode=a_arg_mode;assign tkx_cfg_n=p_tkm_cfg_n;assign tkx_cfg_k=p_tkm_cfg_k;")
        w(" assign tkx_cfg_nout=p_tkm_cfg_nout;assign tkx_cfg_g=p_tkm_cfg_g;assign tkx_cfg_gbase=p_tkm_cfg_gbase;")
        w(" assign tkx_cfg_pf=p_tkm_cfg_pf;assign tkx_cfg_obase=p_tkm_cfg_obase;assign tkx_cfg_rbase=p_tkm_cfg_rbase;")
        w(" assign tkx_cfg_has_r=p_tkm_cfg_has_r;assign tkx_del_slot=p_tkm_del_slot;assign tkx_del_valid=dest_v[10+:4];")
        w(f" assign tkx_del_flit=dest_d[{10 * PWT}+:{4 * PWT}];")
    else:
        w(" wire [9:0] tkm_dest_v_w;")
    w(f" {VV['fj'] + '_r128' if safe else VV['fj'] + rp} u_fj(.clk(clk_program),.rst_n(rst_n),.qid(qid),.cfg_v(cfg_v),.cfg_target(cfg_target),")
    w("  .cfg_addr(cfg_addr),.cfg_data(cfg_data),.desc_v(desc_v),.desc_base(desc_base),.desc_limit(desc_limit),")
    w("  .desc_loops(desc_loops),.launch_v(launch_v),.program_active(issue_busy_raw),.issuer_busy(issue_busy_raw),")
    w("  .issuer_fault(issue_fault),.issuer_uop_v(uop_v),.issuer_uop_pc(uop_pc),")
    w("  .issuer_cfg(program_cfg),.issuer_start(hgi_start),.issuer_start_pc(hgi_start_pc),")
    w("  .configured(program_configured),.init_busy(program_init_busy),.program_fault(program_fault),")
    w("  .protocol_fault(protocol_fault),.capture_fault(capture_fault),.select_fault(select_fault),")
    w("  .unavailable_fault(unavailable_fault),.link_abort(link_abort),.ring_fault(ring_fault),")
    w("  .writer_fault(writer_fault),.reduce_fault(reduce_fault),")
    if SOLO:
        w("  .arg_fault(arg_fault),.tkm_fault(tkx_fault),")
        w("  .fault(fault),.fault_cause(fault_cause));")
    else:
        w("  .arg_capture_slot(p_capture_slot[9]),.tkm_start(p_tkm_start),.tkm_del_slot(p_tkm_del_slot),")
        w("  .tkm_dest_v(dest_v[10+:4]),.fault(fault),.fault_cause(fault_cause));")
    # reduction
    if safe:     # control soft (u_rdc) + 16 hard lanes (u_rdl<l>): ot_hgi_coll_reduce_static split exactly
        w(" wire rd_wb;wire [3:0] rd_wb_tag;wire [15:0] rd_add_valid;wire [511:0] rd_pub_a,rd_pub_b;")
        for l in range(16):
            w(f" ot_hgi_coll_reduce_lane u_rdl{l}(.clk(clk_reduce[{1 + l}]),.rst_n(rst_n),.load_v(a_load_v),.load_tag(a_load_tag),"
              f".in_data(dest_d[{7630 + 32 * l}+:32]),.wb(rd_wb),.wb_tag(rd_wb_tag),.add_read(a_add_read),.read_tag(a_read_tag),"
              f".add_issue(a_add_issue),.pub_read(a_pub_read),.pub_tag_a(a_pub_tag_a),.pub_tag_b(a_pub_tag_b),"
              f".pub_a(rd_pub_a[{32 * l}+:32]),.pub_b(rd_pub_b[{32 * l}+:32]),.add_valid(rd_add_valid[{l}]));")
        w(" ot_hgi_coll_reduce_static_ctl u_rdc(.clk_control(clk_reduce[0]),.rst_n(rst_n),.clear(p_ring[83]),.in_v(dest_v[14]),")
        w("  .load_v(a_load_v),.load_tag(a_load_tag),.add_read(a_add_read),.read_tag(a_read_tag),.add_issue(a_add_issue),")
        w("  .pub_read(a_pub_read),.pub_tag_a(a_pub_tag_a),.pub_tag_b(a_pub_tag_b),.pub_bf16(a_pub_bf16),")
        w("  .pub_meta({1'b1,8'hff,a_pub_src,a_pub_index}),.pub_release(a_pub_release),.pub_issue(a_pub_issue),")
        w("  .add_valid(rd_add_valid),.pub_a(rd_pub_a),.pub_b(rd_pub_b),.wb(rd_wb),.wb_tag(rd_wb_tag),")
        w("  .out_v(reduce_out_v),.out_flit(reduce_out_data),.fault(reduce_fault),.fault_cause(reduce_fault_cause));")
    else:
        w(" ot_hgi_coll_reduce_static u_reduce(")
        w("  .clk_control(clk_reduce[0]),.clk_state(clk_reduce[16:1]),.clk_add(clk_reduce[32:17]),")
        w("  .rst_n(rst_n),.clear(p_ring[83]),.in_v(dest_v[14]),.in_flit(dest_d[7630+:545]),")
        w("  .load_v(a_load_v),.load_tag(a_load_tag),.add_read(a_add_read),.read_tag(a_read_tag),.add_issue(a_add_issue),")
        w("  .pub_read(a_pub_read),.pub_tag_a(a_pub_tag_a),.pub_tag_b(a_pub_tag_b),.pub_bf16(a_pub_bf16),")
        w("  .pub_meta({1'b1,8'hff,a_pub_src,a_pub_index}),.pub_release(a_pub_release),.pub_issue(a_pub_issue),")
        w("  .out_v(reduce_out_v),.out_flit(reduce_out_data),.fault(reduce_fault),.fault_cause(reduce_fault_cause));")
    # qslots capture
    w(f" wire [{NS * PWT - 1}:0] captured;wire [{NS - 1}:0] captured_slot;")
    for s in range(NS):
        w(f" ot_hgi_coll_qslots_capture_pin_v2 u_qc{s}(.clk(clk_qslots[{s}]),.rst_n(rst_n),.src_v(source_v[{s}]),"
          f".capture_slot(capture_calendar[{s}]),.src_d(source_d[{s * PWT}+:{PWT}]),.captured(captured[{s * PWT}+:{PWT}]),"
          f".captured_slot(captured_slot[{s}]),.fault(capture_fault[{s}]));")
    # qslots switch slices
    dbits = [None] * (ND * PWT)
    for k in range(NSL):
        cw = 32 if k < NSL - 1 else 1
        mod = VV["qso"] + ("_b32" if cw == 32 else "_b1")
        words = cat([f"captured[{s * PWT + k * 32}+:{cw}]" if cw > 1 else f"captured[{s * PWT + k * 32}]" for s in range(NS)])
        w(f" wire [{NS * cw - 1}:0] qo_w{k}={words};wire [{ND * cw - 1}:0] qo_r{k};wire [14:0] qo_v{k};")
        w(f" {mod} u_qo{k}(.clk(clk_qslots[{NS + k}]),.rst_n(rst_n),.captured(qo_w{k}),.captured_slot(captured_slot),"
          f".sink_slot(p_sink_slot[14:0]),.sink_select(p_sink_select[59:0]),.dst_v(qo_v{k}),.dst_d(qo_r{k}),"
          f".select_fault(select_fault[{k}]),.unavailable_fault(unavailable_fault[{k}]));")
        for d in range(ND):
            for b in range(cw):
                dbits[d * PWT + k * 32 + b] = f"qo_r{k}[{d * cw + b}]"
    assert all(dbits)
    # compress runs of consecutive bits of one slice into part selects
    parts, i = [], 0
    while i < len(dbits):
        nm, idx = dbits[i][:dbits[i].index("[")], int(dbits[i][dbits[i].index("[") + 1:-1])
        j = i + 1
        while j < len(dbits) and dbits[j] == f"{nm}[{idx + (j - i)}]":
            j += 1
        parts.append(f"{nm}[{idx}+:{j - i}]" if j - i > 1 else dbits[i])
        i = j
    w(" assign dest_v=qo_v0;")
    w(" assign dest_d=" + cat(parts) + ";")
    # rails
    for k in range(NPT):
        if safe:
            w(f" ot_hgi_coll_link_e1 u_link{k}(.clk(clk_link[{k * 5}]),.rst_n(rst_n),")
        else:
            w(f" ot_hgi_coll_link_e u_link{k}(.ck(clk_link[{k * 5}+:5]),.rst_n(rst_n),")
        w(f"  .epoch_begin(p_lk_epoch_begin[{k}]),.epoch_new(p_lk_epoch),.held_epoch(held_epoch[{k * 8}+:8]),")
        w(f"  .wr_v(p_lk_wr_v[{k}]),.wr_observed_v(dest_v[{k}]),.wr_seq(wr_sequence_pin[{k * 16}+:16]),")
        w(f"  .wr_flit(dest_d[{k * PWT}+:{PWT}]),.rd_v(p_lk_rd_v[{k}]),.rd_seq(rd_sequence_pin[{k * 16}+:16]),")
        w(f"  .rx_expect_v(p_lk_rx_expect[{k}]),.rx_expect_seq(rx_sequence_pin[{k * 16}+:16]),")
        w(f"  .phy_up(phy_up[{k}]),.tx_pin_v(tx_pin_v[{k}]),.tx_pin_flit(tx_pin_flit[{k * 612}+:612]),")
        w(f"  .rx_pin_v(rx_pin_v[{k}]),.rx_pin_flit(rx_pin_flit[{k * 612}+:612]),")
        w(f"  .rx_v(link_rx_v[{k}]),.rx_flit(link_rx_data[{k * PWT}+:{PWT}]),")
        w(f"  .epoch_abort(link_abort[{k}]),.retry_requested(retry_requested[{k}]),.fault_cause(link_cause[{k * 11}+:11]));")
    # deliveries
    w(" assign del_valid=dest_v[2+:4];")
    w(f" assign del_flit=dest_d[{2 * PWT}+:{4 * PWT}];")
    # VM writer (its inputs on own wires: they leave the switch region)
    w(" wire [3:0] w_rgx_v=dest_v[6+:4];wire [159:0] w_rgx_addr=rgx_addr_pin;")
    for j in range(4):
        w(f" wire [511:0] w_rgx_d{j}=dest_d[{(6 + j) * PWT}+:512];")
    w(" wire [280:0] kq0,kq1,kq2,kq3,kq4,kq5,kq6,kq7;")
    w(" ot_hgi_coll_static_vmwrite_roots_v6_physical u_writer(")
    names = ["rgx_data0", "rgx_data1", "rgx_data2", "rgx_data3", "rgx_ctrl", "tkw", "meta", "body"] + [f"bank{b}" for b in range(8)]
    w("  " + ",".join(f".clk_{n}(clk_vmwrite[{i}])" for i, n in enumerate(names)) + ",")
    w("  .rst_n(rst_n),.sid(qid_wr),.rgx_v(w_rgx_v),.rgx_addr(w_rgx_addr),")
    w("  .rgx_data0(w_rgx_d0),.rgx_data1(w_rgx_d1),.rgx_data2(w_rgx_d2),.rgx_data3(w_rgx_d3),")
    if SOLO:
        w("  .rgx_vm(w_rgx_vm),.tkw_v(tkx_w_v),.tkw_d({tkx_w_addr,tkx_w_mask,tkx_w_data}),")
    else:
        w("  .rgx_vm(w_rgx_vm),.tkw_v(1'b0),.tkw_d(568'd0),")
    w("  .ingress_slot(w_ingress_slot),.slot_valid(w_slot_valid),.slot_owner(w_slot_owner),")
    w("  .kq0(kq0),.kq1(kq1),.kq2(kq2),.kq3(kq3),.kq4(kq4),.kq5(kq5),.kq6(kq6),.kq7(kq7),")
    w("  .launch_done(),.fault(writer_fault));")
    w(" assign vm_kq={kq7,kq6,kq5,kq4,kq3,kq2,kq1,kq0};")
    # ring A (ot_hgi_coll_ring_ag SPLIT_CLOCKS 1, AG 1) expanded: control root + 8 state-capture + 8 add lanes
    w(" assign isa_ring=p_ring[57:0];assign isa_lp_data=rc_d;")
    w(" wire [279:0] r_pin0,r_pin1;wire [1:0] r_carry_write;wire r_acc_we;wire [2:0] r_acc_tag;")
    w(" wire [255:0] r_rhs_add,r_carry_add,r_state_tx,r_acc_rr,r_ay;wire [7:0] r_av;")
    w(" ot_hgi_coll_ring_ag_ctl u_rctl(")
    w("  .clk(clk_ring[0]),.rst_n(rst_n),.qid(qid_rg),.cw_i(pr_cw_i),.ccw_i(pr_ccw_i),.cw_o(pr_cw_o),.ccw_o(pr_ccw_o),")
    w("  .lp_we(ra_lp_we),.lp_tag(ra_lp_tag),")
    w("  .state_read_add(ra_state_read_add),.state_read_tx(ra_state_read_tx),.state_read_rr(ra_state_read_rr),")
    w("  .state_add_tag(ra_state_add_tag),.state_tx_tag(ra_state_tx_tag),.state_rr_tag(ra_state_rr_tag),")
    w("  .state_add_src(ra_state_add_src),.state_add_rhs_acc(ra_state_add_rhs_acc),.state_tx_acc(ra_state_tx_acc),")
    w("  .add_v(ra_add_v),.add_tag(ra_add_tag),.add_src(ra_add_src),.add_rhs_acc(ra_add_rhs_acc),")
    w("  .tx_inject(ra_tx_inject),.tx_forward(ra_tx_forward),.tx_tag(ra_tx_tag),.tx_dst(ra_tx_dst),.tx_result(ra_tx_result),")
    w("  .tx_acc(ra_tx_acc),.tx_gather(ra_tx_gather),.tx_ttl(ra_tx_ttl),.rx_slot(ra_rx_slot),.rx_kind(ra_rx_kind),")
    w("  .rx_src(ra_rx_src),.rx_tag(ra_rx_tag),.rr_local(ra_rr_local),.rr_local_tag(ra_rr_local_tag),")
    w("  .pin0_q(r_pin0),.pin1_q(r_pin1),.carry_write(r_carry_write),.acc_we(r_acc_we),.acc_tag(r_acc_tag),")
    w("  .state_tx(r_state_tx),.acc_rr(r_acc_rr),.av(r_av),")
    w("  .rr_v(rr_v),.rr_tag(rr_tag),.rr_d(rr_d),.ag_v(ag_v),.ag_src(ag_src),.ag_tag(ag_tag),.ag_d(ag_d),.fault(ring_fault));")
    for l in range(8):
        s = f"[{l * 32}+:32]"
        w(f" ot_hgi_coll_pring_static_state_capture_lane u_rst{l}(.clk(clk_ring[{1 + l}]),")
        w(f"  .lp_we(ra_lp_we),.lp_tag(ra_lp_tag),.lp_data(ra_lp_data{s}),.acc_we(r_acc_we),.acc_tag(r_acc_tag),"
          f".acc_data(r_ay{s}),")
        w("  .carry_we(r_carry_write),.carry0_tag(r_pin0[270:268]),.carry0_src(r_pin0[276:275]),"
          ".carry1_tag(r_pin1[270:268]),.carry1_src(r_pin1[276:275]),")
        w(f"  .carry0_data(r_pin0{s}),.carry1_data(r_pin1{s}),")
        w("  .read_add(ra_state_read_add),.read_tx(ra_state_read_tx),.read_rr(ra_state_read_rr),"
          ".read_rhs_acc(ra_state_add_rhs_acc),.read_tx_acc(ra_state_tx_acc),")
        w("  .add_tag(ra_state_add_tag),.add_src(ra_state_add_src),.tx_tag(ra_state_tx_tag),.rr_tag(ra_state_rr_tag),")
        w(f"  .rhs_add(r_rhs_add{s}),.carry_add(r_carry_add{s}),.tx_data(r_state_tx{s}),.acc_rr(r_acc_rr{s}));")
        w(f" ot_hgi_coll_pring_static_add_lane u_radd{l}(.clk(clk_ring[{9 + l}]),.rst_n(rst_n),.valid_in(ra_add_v),"
          f".a(r_carry_add{s}),.b(r_rhs_add{s}),.y(r_ay{s}),.valid_out(r_av[{l}]));")
    w("endmodule")
    w("`default_nettype wire")
    return "\n".join(L) + "\n"


def tb_eq(v="q2", cycles=3000) -> str:
    """random-stimulus lockstep: the v8g/v8x hard parent vs ot_hfd_coll_<v>_lpf (all outputs, all cycles)"""
    import re
    ports = []
    for it in header(v).replace("\n", " ").strip().rstrip(",").split(","):
        it = " ".join(it.split())
        m = re.match(r"(input|output)?\s*(?:wire)?\s*(\[[^\]]*\])?\s*(\w+)$", it)
        if m.group(1):
            d, r = m.group(1), m.group(2)
        elif m.group(2):
            r = m.group(2)
        ports.append((d, r, m.group(3)))
    W = {}
    for d, r, n in ports:
        W[n] = 1 if not r else int(r[1:-1].split(":")[0]) + 1
    L = ["`timescale 1ns/1ps", f"// GENERATED by tools/hbm_coll_static/gen_coll_q2_lpf.py: {'v8g q2' if v == 'q2' else 'v8x q3'} parent vs its flat expansion.",
         f"module tb_hfd_coll_{v}_lpf_eq;", " reg clk=1'b0; always #0.5 clk=~clk; reg rst_n=1'b0;"]
    ins = [(n) for d, r, n in ports if d == "input" and not n.startswith("clk_") and n not in ("rst_n",)]
    outs = [n for d, r, n in ports if d == "output"]
    cks = [n for d, r, n in ports if n.startswith("clk_")]
    for n in ins:
        L.append(f" reg [{W[n] - 1}:0] i_{n};")
    for n in outs:
        L.append(f" wire [{W[n] - 1}:0] a_{n},b_{n};")
    # QF-COLLQ 10-18: qid_rg = the ring's copy of the quadrant identity strap (N face beside u_rctl; the die ties it to the
    # same constant as qid); the reference parent has the single qid.  TW-HBM-COLLP 10-19: qid_wr = the writer region's
    # copy (W face beside ck_wr / u_writer.sid): one qid owned by the sw region fed the wr-region writer (kit OT_MULTI_ROOT
    # "input qid has wrong domain for u_writer"); a strap is never landed, so each region gets its own pin
    conn_a = [f".{c}({{{W[c]}{{clk}}}})" for c in cks] + [".rst_n(rst_n)"] + [f".{n}(i_{n})" for n in ins if n not in ("qid_rg", "qid_wr")] + [f".{n}(a_{n})" for n in outs]
    conn_b = [f".{c}({{{W[c]}{{clk}}}})" for c in cks] + [".rst_n(rst_n)"] + [f".{n}(i_{n})" for n in ins] + [f".{n}(b_{n})" for n in outs]
    L.append(f" {VARIANTS[v]['ref']} u_ref(" + ",".join(conn_a) + ");")
    L.append(f" ot_hfd_coll_{v}_lpf u_flat(" + ",".join(conn_b) + ");")
    L.append(" integer cyc,bad,nc;")
    L.append(" initial begin bad=0;nc=0;")
    L.append("  i_qid=2'd1; i_qid_rg=2'd1; i_qid_wr=2'd1;")
    for n in ins:
        if n not in ("qid", "qid_rg", "qid_wr"):
            L.append(f"  i_{n}={{{','.join(['$urandom'] * ((W[n] + 31) // 32))}}};")
    L.append(f"  for(cyc=0;cyc<{cycles};cyc=cyc+1)begin @(negedge clk); if(cyc==16) rst_n=1'b1;")
    for n in ins:
        if n in ("qid", "qid_rg", "qid_wr"):
            continue
        # sparse control strobes so the parents run real programmes between faults
        if W[n] == 1:
            L.append(f"   i_{n}=($urandom%8)==0;")
        else:
            L.append(f"   i_{n}={{{','.join(['$urandom'] * ((W[n] + 31) // 32))}}};")
    L.append("   if(cyc>20)begin")
    for n in outs:
        L.append(f"    nc=nc+1; if(a_{n}!==b_{n})begin bad=bad+1; if(bad<=5)$display(\"EQ_MISMATCH port={n} cyc=%0d\",cyc); end")
    L.append("   end end")
    L.append("  if(bad==0)$display(\"LPF_EQ PASS compared=%0d\",nc); else $display(\"LPF_EQ FAIL mismatches=%0d of %0d\",bad,nc);")
    L.append("  $finish; end")
    L.append("endmodule")
    return "\n".join(L) + "\n"


def ref_inst(v, ar=False, rows=64):
    """the hard parent with the XDIE-HBM4 parameters (defaults = VARIANTS[v]['ref'])"""
    r = VARIANTS[v]["ref"]
    if not ar and rows == 64:
        return r
    ps = ([".AR_ITER(1)"] if ar else []) + ([f".ROWS({rows})"] if rows != 64 else [])
    if "#(" in r:
        return r[:-1] + "," + ",".join(ps) + ")"
    return f"{r} #({','.join(ps)})"


def tb_eq_scripted(v, ar, rows, suffix, stim) -> str:
    """TW2-COLLAR: lockstep of the hard parent #(AR_ITER, ROWS) vs ot_hfd_coll_<v>_lpf<suffix> under a SCRIPTED programme
    (the lp.py tb_stimulus include: fi_<port> inputs, rst = rst_n, fo_<port> = the reference's outputs, lp_finish); every
    output compared every cycle after reset release.  Random words alone never start the issuer (cfg_target 1 / 256)."""
    import re
    ports = []
    for it in header(v).replace("\n", " ").strip().rstrip(",").split(","):
        it = " ".join(it.split())
        m = re.match(r"(input|output)?\s*(?:wire)?\s*(\[[^\]]*\])?\s*(\w+)$", it)
        if m.group(1):
            d, r = m.group(1), m.group(2)
        elif m.group(2):
            r = m.group(2)
        ports.append((d, r, m.group(3)))
    W = {n: (1 if not r else int(r[1:-1].split(":")[0]) + 1) for d, r, n in ports}
    ins = [n for d, r, n in ports if d == "input" and not n.startswith("clk_") and n != "rst_n"]
    outs = [n for d, r, n in ports if d == "output"]
    cks = [n for d, r, n in ports if n.startswith("clk_")]
    top = f"ot_hfd_coll_{v}_lpf{suffix}"
    L = ["`timescale 1ns/1ps",
         f"// GENERATED by tools/hbm_coll_static/gen_coll_q2_lpf.py (TW2-COLLAR): {ref_inst(v, ar, rows)} vs {top},",
         f"// scripted programme {stim}; every output, every cycle after reset release.",
         f"module tb_hfd_coll_{v}_lpf{suffix}_eq;", " reg clk=1'b0; always #0.5 clk=~clk; reg rst=1'b0;"]
    for n in ins:
        L.append(f" reg [{W[n] - 1}:0] fi_{n};")
    for n in outs:
        L.append(f" wire [{W[n] - 1}:0] fo_{n},lo_{n};")
    conn_a = [f".{c}({{{W[c]}{{clk}}}})" for c in cks] + [".rst_n(rst)"] + \
             [f".{n}(fi_{n})" for n in ins if n not in ("qid_rg", "qid_wr")] + [f".{n}(fo_{n})" for n in outs]
    conn_b = [f".{c}({{{W[c]}{{clk}}}})" for c in cks] + [".rst_n(rst)"] + [f".{n}(fi_{n})" for n in ins] + \
             [f".{n}(lo_{n})" for n in outs]
    L.append(f" {ref_inst(v, ar, rows)} u_ref(" + ",".join(conn_a) + ");")
    L.append(f" {top} u_flat(" + ",".join(conn_b) + ");")
    L.append(" integer cyc=0,nc=0,bad=0;")
    L.append(" always @(negedge clk) begin")
    L.append("  cyc<=cyc+1;")
    L.append("  if(cyc>20)begin")
    for n in outs:
        L.append(f"   nc=nc+1; if(lo_{n}!==fo_{n})begin bad=bad+1; if(bad<=5)$display(\"EQ_MISMATCH port={n} cyc=%0d\",cyc); end")
    L.append("  end")
    L.append(" end")
    L.append(" task lp_finish; input [8*48-1:0] what; begin")
    L.append("  if(bad==0&&nc>0)$display(\"LPF_EQ PASS compared=%0d cycles=%0d stimulus=%0s\",nc,cyc,what);")
    L.append("  else $display(\"LPF_EQ FAIL mismatches=%0d of %0d stimulus=%0s\",bad,nc,what);")
    L.append("  $finish; end endtask")
    L.append(f" `include \"{stim}\"")
    L.append("endmodule")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("variants", nargs="*", default=["q2", "q3"])
    ap.add_argument("--ar-iter", action="store_true", help="v8g AR_ITER=1: u_ariter leaf + inst_ctl")
    ap.add_argument("--rows", type=int, default=64, choices=[64, 128], help="issuer / fj ROWS")
    ap.add_argument("--suffix", default="", help="module / file suffix (required with --ar-iter or --rows 128)")
    ap.add_argument("--safe", action="store_true", help="COLLQ3 SAFE successor: hard issuer / fj / link_e1 / reduce lanes")
    ap.add_argument("--stim-suffix", default=None, help="stimulus file suffix (default = --suffix)")
    a = ap.parse_args()
    if (a.ar_iter or a.rows != 64) and not a.suffix:
        ap.error("--ar-iter / --rows 128 need --suffix (never overwrite the closed-view lpf)")
    for v in a.variants:
        (OUT / f"ot_hfd_coll_{v}_lpf{a.suffix}.sv").write_text(flat(v, a.ar_iter, a.rows, a.suffix, a.safe))
        if a.suffix:
            ss = a.suffix if a.stim_suffix is None else a.stim_suffix
            stim = f"rtl/hbm_accel/generic/collective/p2p/landed/stim_{v}_lp{ss}.vh"
            (OUT / f"tb_hfd_coll_{v}_lpf{a.suffix}_eq.sv").write_text(tb_eq_scripted(v, a.ar_iter, a.rows, a.suffix, stim))
        else:
            (OUT / f"tb_hfd_coll_{v}_lpf_eq.sv").write_text(tb_eq(v))
        print("wrote", OUT / f"ot_hfd_coll_{v}_lpf{a.suffix}.sv", f"and tb_hfd_coll_{v}_lpf{a.suffix}_eq.sv")
