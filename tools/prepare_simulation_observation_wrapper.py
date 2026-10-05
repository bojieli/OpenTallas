#!/usr/bin/env python3
"""Prepare only: no elaboration, binary selection, images or engine writes."""
import hashlib
import json
import subprocess
from pathlib import Path

SOURCE = "4e38326d6f361bc85e660f48c59c355e2bb95274"
ORIGINAL = "rtl/test/v41_runtime/ot_v41_rt_die.sv"
COPY = "rtl/test/v41_runtime/ot_v41_rt_die_sim_observe.sv"
D = "dut.g_packed_kv"
W = D + ".g_window_hbm_attention.u_source"
P = W + ".u_window"
C = D + ".g_window_hbm_attention.g_ckv.u_ckv"
# name, width, exact pre-edge expression, conditional CKV availability
FIELDS = []
def field(name, width, expression, ckv=False):
    FIELDS.append((name, width, expression, ckv))
field("epoch",64,"sim_obs_epoch")
field("cycle",64,"sim_obs_cycle")
field("rank",2,"2'(RANK)")
field("ckv_available",1,"SIM_OBS_CKV_SELECTED")
field("user",10,"dut.step_user")
field("desc_gen",16,"dut.att_packed_desc_gen")
field("desc_accept",1,"dut.att_packed_desc_accept")
field("desc_done",1,"dut.att_packed_desc_done")
field("source_accept",1,W+".start_v && "+W+".start_ready")
field("source_gen",16,W+".retain_generation")
field("active_gen",16,"dut.win_service_gen")
field("source_first",21,W+".start_first")
field("source_count",8,W+".start_count")
for name, expr in [("source_done","done"),("staged","staged_v"),("merge_accept","issue_v && @.issue_ready"),("merge_done","merge_done"),("stream_take","kv_v && @.kv_ready")]:
    field(name,1,W+"."+expr.replace("@",W))
field("stream_mask",4,W+".kv_m")
for role in ("blk", "prime", "prefetch"):
    field("window_"+role+"_accept",1,P+"."+role+"_v && "+P+"."+role+"_ready")
    field("window_"+role+"_user",10,P+"."+role+"_user")
    field("window_"+role+"_row",21,P+"."+role+"_row")
field("window_blk_idx",4,P+".blk_idx")
for name, width, expr in [("state",3,"state"),("row",21,"row"),("active_user",10,"user_id"),("sector",5,"sec"),("block",4,"bidx"),("req_take",1,"grant"),("req_offer",1,"m_v[0]"),("req_ready",1,"m_rdy[0]"),("req_we",1,"m_we[0]"),("req_addr",30,"m_addr[0 +: 30]"),("req_tag",16,"m_tag[0 +: 16]"),("rsp_take",1,"s_v[0] && @.s_rdy[0]"),("rsp_tag",16,"s_tag[0 +: 16]"),("rsp_beat",4,"s_beat[0 +: 4]"),("rsp_poison",1,"response_poison"),("write_done",1,"done_write")]:
    field("window_"+name,width,P+"."+expr.replace("@",P))
field("window_reply_ok",1,f"{P}.state == 3'd6 && {P}.response && {P}.s_tag[0 +: 16] == 16'({P}.sec) && {P}.s_beat[0 +: 4] == 0 && !{P}.response_poison")
field("window_row_publish",1,"sim_obs_raw[%ROW_OK%] && "+P+".sec == 5'd16")
field("window_block_publish",1,P+".state == 3'd4 && "+P+".done_write")
for prefix in ("req","rsp"):
    field("stage_"+prefix+"_take",1,W+(".wb_req_v && "+W+".wb_req_ready" if prefix=="req" else ".wb_rsp_v"))
    for suffix,width,native in [("user",10,"user"),("first",21,"first"),("mask",4,"m")]:
        field("stage_"+prefix+"_"+suffix,width,W+".wb_"+prefix+"_"+native)
field("stage_rsp_valid",4,W+".wb_rsp_lane_valid")
field("stage_rsp_fault",1,W+".wb_rsp_fault")
for name,width,expr in [("select_accept",1,"sel_v && @.rd_act == 0"),("select_vmword",15,"sel_vmword"),("fetch_accept",1,"f_job && @.f_ready"),("fetch_done",1,"f_done"),("job_accept",1,"job_v && @.rel_ok"),("job_done",1,"job_done"),("stream_take",1,"kv_v && @.kv_ready"),("stream_mask",4,"kv_m"),("rows_ready",1,"rows_ready"),("collect_take",5,"wv"),("collect_rank",50,"wrank"),("collect_gid",105,"wgid"),("collect_bad",1,"dup || @.oor || @.gidbad"),("fault",1,"fault"),("fault_code",6,"fault_code")]:
    field("ckv_"+name,width,C+"."+expr.replace("@",C),True)
field("ckv_job_gen",16,"dut.win_service_gen",True)
for stack in range(4):
    for name,width,expr in [("req_take",1,f"c_v[{stack}] && @.c_rdy[{stack}]"),("req_offer",1,f"c_v[{stack}]"),("req_ready",1,f"c_rdy[{stack}]"),("req_we",1,f"c_we[{stack}]"),("req_addr",30,f"c_addr[{stack*30} +: 30]"),("req_tag",16,f"c_tag[{stack*16} +: 16]"),("rsp_take",1,f"c_sv[{stack}] && @.c_srdy[{stack}]"),("rsp_tag",16,f"c_stag[{stack*16} +: 16]"),("rsp_beat",4,f"c_sbeat[{stack*4} +: 4]")]:
        field(f"ckv{stack}_"+name,width,C+"."+expr.replace("@",C),True)

def layout():
    out=[]; offset=0
    for name,width,expr,ckv in FIELDS:
        out.append(dict(name=name,width=width,offset=offset,expression=expr,ckv=ckv)); offset+=width
    reply=next(f["offset"] for f in out if f["name"]=="window_reply_ok")
    for f in out: f["expression"]=f["expression"].replace("%ROW_OK%",str(reply))
    return out
BITS=sum(f[1] for f in FIELDS)
def original(repo):
    return subprocess.check_output(["git","show",SOURCE+":"+ORIGINAL],cwd=repo).decode()
def render(text):
    text=text.replace("module ot_v41_rt_die #(","module ot_v41_rt_die_sim_observe #(\n    parameter bit SIM_OBS_ENABLE = 0,\n    parameter bit SIM_OBS_CKV_SELECTED = 0,")
    text=text.replace("    input  wire              clk,",f"    input wire [63:0] sim_obs_epoch, // host reset era; never drives engine\n    output reg sim_obs_valid,\n    output reg [{BITS-1}:0] sim_obs_packet, // simulation API only, no product port\n    input  wire              clk,")
    text=text.replace(".WINDOW_HBM_ATTENTION(1),", ".WINDOW_HBM_ATTENTION(1), .CKV_SELECTED(SIM_OBS_CKV_SELECTED),")
    lines=["// BEGIN SIM OBSERVER: pre-edge fields registered once; no payload, no DUT writes", "`ifdef SYNTHESIS", 'initial $fatal(1, "simulation observer cannot be synthesized");', "`endif", "reg [63:0] sim_obs_cycle;",f"wire [{BITS-1}:0] sim_obs_raw;", "initial begin", '  if (SIM_OBS_CKV_SELECTED && !SIM_OBS_ENABLE) $fatal(1, "CKV observation requires opt-in");', '  if (RANK < 0 || RANK > 3) $fatal(1, "observer rank envelope");', "end", "generate if (SIM_OBS_ENABLE) begin : g_sim_observe"]
    for f in layout():
        assignment=f"assign sim_obs_raw[{f['offset']} +: {f['width']}] = {f['expression']};"
        if f['ckv']:
            lines.extend([f"if (SIM_OBS_CKV_SELECTED) begin : g_{f['name']}",assignment,"end else begin",f"assign sim_obs_raw[{f['offset']} +: {f['width']}] = '0;","end"])
        else: lines.append(assignment)
    lines.extend(["end else begin", "assign sim_obs_raw = '0;", "end endgenerate", "always @(posedge clk or negedge rst_n) begin", "  if (!rst_n) begin sim_obs_cycle <= 0; sim_obs_valid <= 0; sim_obs_packet <= '0; end", "  else begin", "    sim_obs_cycle <= sim_obs_cycle + 1'b1;", "    sim_obs_valid <= SIM_OBS_ENABLE && dut.rn;", "    sim_obs_packet <= sim_obs_raw;", "  end", "end", "// END SIM OBSERVER"])
    return text.replace("endmodule", "\n"+"\n".join(lines)+"\nendmodule")
def inverse(text):
    start=text.index("\n// BEGIN SIM OBSERVER")
    end=text.index("// END SIM OBSERVER",start)+len("// END SIM OBSERVER")
    text=text[:start]+text[end+1:]
    text=text.replace("module ot_v41_rt_die_sim_observe #(\n    parameter bit SIM_OBS_ENABLE = 0,\n    parameter bit SIM_OBS_CKV_SELECTED = 0,","module ot_v41_rt_die #(")
    text=text.replace(f"    input wire [63:0] sim_obs_epoch, // host reset era; never drives engine\n    output reg sim_obs_valid,\n    output reg [{BITS-1}:0] sim_obs_packet, // simulation API only, no product port\n","")
    return text.replace(".WINDOW_HBM_ATTENTION(1), .CKV_SELECTED(SIM_OBS_CKV_SELECTED),", ".WINDOW_HBM_ATTENTION(1),")
def prepare(repo):
    repo=Path(repo); src=original(repo); target=repo/COPY
    target.parent.mkdir(parents=True,exist_ok=True); generated=render(src)
    assert inverse(generated)==src
    target.write_text(generated)
    return dict(source_commit=SOURCE,original_sha256=hashlib.sha256(src.encode()).hexdigest(),copy_sha256=hashlib.sha256(generated.encode()).hexdigest(),bits=BITS,fields=layout())
if __name__=="__main__":
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument("--repo",default="."); ap.add_argument("--record",required=True); a=ap.parse_args()
    Path(a.record).write_text(json.dumps(prepare(a.repo),indent=2)+"\n")
