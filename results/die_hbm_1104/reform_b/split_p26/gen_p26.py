#!/usr/bin/env python3
"""HBM-REFORM-B4 d44v part 26: ot_hbm_svc_sm_group_rel_id = ot_svgr_top + ot_svgr_own + 2 x ot_svgr_bk, registered faces.
    gen_p26.py REPO RTL_OUT.sv SPLITDIR
ot_svgr_top / ot_svgr_feed are the tip group and feed with the producer swapped for its stream half, so programme, rows and consumer stay byte-equal source.
Also writes the composition in bench (__fs tiles) and plan form, and the glue for mk_split."""
import re, sys
from pathlib import Path
repo, out, sd = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
S = repo / "rtl/hbm_accel/loader/service_native"
feed = (S / "ot_hbm_svc_sm_feed_programmed_rel_id.sv").read_text()
grp = (S / "ot_hbm_svc_sm_group_rel_id.sv").read_text()
SEAM_D = """ output wire seam_res_v,output wire[96:0]seam_res_word,output wire seam_s_fault,input wire seam_h_fault,
 output wire seam_stop,output wire[7:0]seam_read_v,output wire[1:0]seam_read_bank,output wire[47:0]seam_read_row,
 input wire[7:0]seam_complete,input wire[15:0]seam_complete_bank,input wire[7:0]seam_bfault,input wire[2047:0]seam_read_data,
"""
SEAM_C = """.seam_res_v(seam_res_v),.seam_res_word(seam_res_word),.seam_s_fault(seam_s_fault),.seam_h_fault(seam_h_fault),
  .seam_stop(seam_stop),.seam_read_v(seam_read_v),.seam_read_bank(seam_read_bank),.seam_read_row(seam_read_row),
  .seam_complete(seam_complete),.seam_complete_bank(seam_complete_bank),.seam_bfault(seam_bfault),.seam_read_data(seam_read_data),"""
# ---- feed
f = feed[feed.index("module ot_hbm_svc_sm_feed_programmed_rel_id"):feed.rindex("endmodule") + len("endmodule")]
f = f.replace("module ot_hbm_svc_sm_feed_programmed_rel_id", "module ot_svgr_feed", 1)
a = f.index(" input wire [1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,\n"); f = f.replace(" input wire [1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,\n", "", 1)
f = f.replace(" input wire [1:0] id_stack,input wire [2:0] id_sm,\n input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,\n", " input wire [1:0] id_stack,input wire [2:0] id_sm,\n input wire stream_clk,stream_rst_n,hbm_rst_n,\n" + SEAM_D, 1)
a = f.index(" output wire[3:0]k_v,input wire[3:0]k_rdy"); b = f.index(");\n wire cdc_ready")
hdr = f[a:b]; f = f[:a].rstrip().rstrip(",") + "\n" + f[b:]
# The read data crosses the bank tiles, so out_* is DLY = 4 edges late; packed136 expects its 4,4,4,4,1 sectors from the edge it runs, so the open moves with them.
# rows and tag are read at the first stage as before: a reserve may rewrite that landing bank once the last drain word has left. The issuer sees an open in flight as owned.
def rp(s, o, n):
    assert s.count(o) == 1, o
    return s.replace(o, n)
f = rp(f, " wire open_bank_q=open_land_q[0];\n", """ wire open_bank_q=open_land_q[0];
 localparam integer OPEN_DLY=4;
 reg[OPEN_DLY-1:0]od_v,od_bank;reg[15:0]od_epoch[0:OPEN_DLY-1];reg[6:0]od_count[0:OPEN_DLY-1];reg[9:0]od_tag[0:OPEN_DLY-1];integer od;
 always @(posedge stream_clk)begin
  od_bank<={od_bank[OPEN_DLY-2:0],open_bank_q};od_epoch[0]<=open_epoch_q;od_count[0]<=rows_q[open_land_q];od_tag[0]<=tag_q[open_land_q];
  for(od=1;od<OPEN_DLY;od=od+1)begin od_epoch[od]<=od_epoch[od-1];od_count[od]<=od_count[od-1];od_tag[od]<=od_tag[od-1];end
 end
 always @(posedge stream_clk or negedge stream_rst_n)if(!stream_rst_n)od_v<=0;else od_v<={od_v[OPEN_DLY-2:0],open_q};
 wire[1:0]cache_owned_c;
 assign cache_owned=cache_owned_c|((open_q?(2'b01<<open_bank_q):2'b00)|(od_v[0]?(2'b01<<od_bank[0]):2'b00)|(od_v[1]?(2'b01<<od_bank[1]):2'b00)|(od_v[2]?(2'b01<<od_bank[2]):2'b00)|(od_v[3]?(2'b01<<od_bank[3]):2'b00));
""")
f = rp(f, "{LBANKS{!cache_busy&&!open_q}}", "{LBANKS{!cache_busy&&!open_q&&od_v==0}}")
f = rp(f, ".open_v(open_q),.open_bank(open_bank_q),.open_epoch(open_epoch_q),.open_count(rows_q[open_land_q]),.open_tag_base(tag_q[open_land_q]),", ".open_v(od_v[OPEN_DLY-1]),.open_bank(od_bank[OPEN_DLY-1]),.open_epoch(od_epoch[OPEN_DLY-1]),.open_count(od_count[OPEN_DLY-1]),.open_tag_base(od_tag[OPEN_DLY-1]),")
f = rp(f, ".bank_owned(cache_owned),", ".bank_owned(cache_owned_c),")
a = f.index(" ot_hbm_svc_sm4pc_cdc_rel_id #("); b = f.index(" wire[95:0]indices")
f = f[:a] + """ ot_svgr_prod_s #(.LBANKS(LBANKS),.OPEN_IL(OPEN_IL)) producer(.id_stack(id_stack),.id_sm(id_sm),.stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),
  """ + SEAM_C + """
  .reserve_v(reserve_fire),.reserve_ready(cdc_ready),.reserve_base(reserve_base),.reserve_row_base(reserve_row_base),.reserve_total(reserve_total),.reserve_bank(reserve_bank),.reserve_epoch(reserve_epoch),
  .block_ready(producer_ready),.start_v(start_v),.start_bank(start_bank),.start_epoch(start_epoch),
  .out_v(out_v),.out_mask(out_mask),.out_data(out_data),.out_ordinal(out_ordinal),.out_bank(out_bank),.out_epoch(out_epoch),.out_last(out_last),.fault(cdc_fault));
""" + f[b:]
# ---- group: k pins leave, seam comes in
g = grp[grp.index("module ot_hbm_svc_sm_group_rel_id"):grp.rindex("endmodule") + len("endmodule")]
g = g.replace("module ot_hbm_svc_sm_group_rel_id", "module ot_svgr_top", 1)
g = g.replace(" input wire stream_clk,stream_rst_n,hbm_clk,hbm_rst_n,\n input wire[1:0]stream_bank_clk,hbm_fifo_clk,input wire[3:0]hbm_pc_clk,\n", " input wire stream_clk,stream_rst_n,hbm_rst_n,\n" + SEAM_D, 1)
a = g.index(",\n output wire[3:0]k_v,input wire[3:0]k_rdy"); b = g.index("\n);\n wire reserve_v"); g = g[:a] + g[b:]
g = g.replace("ot_hbm_svc_sm_feed_programmed_rel_id #(", "ot_svgr_feed #(", 1)
g = g.replace("  .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),\n  .stream_bank_clk(stream_bank_clk),.hbm_fifo_clk(hbm_fifo_clk),.hbm_pc_clk(hbm_pc_clk),\n", "  .stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),\n  " + SEAM_C + "\n", 1)
a = g.index(",\n  .k_v(k_v),.k_rdy(k_rdy)"); b = g.index(");\nendmodule"); g = g[:a] + g[b:]
for t, n in ((f, "feed"), (g, "group")):
    for w in ("k_rdy", "hbm_pc_clk", "hbm_fifo_clk", "kr_data"):
        assert w not in t, (n, w)
HAND = (Path(__file__).parent / "ot_svgr_hand.sv").read_text()
out.write_text("`timescale 1ns/1ps\n`default_nettype none\n// HBM-REFORM-B4 d44v part 26. GENERATED by results/die_hbm_1104/reform_b/split_p26/gen_p26.py; ot_svgr_top and ot_svgr_feed are the tip group and feed with the k pins replaced by the seam.\n"
               + g + "\n" + f + "\n" + HAND + "`default_nettype wire\n")
# ---- composition
C = "ot_hbm_svc_sm_group_rel_id"
sig = grp[grp.index("module " + C) + len("module " + C):]; sig = sig[:sig.index("\n);\n") + 2]
hdr_par = sig[:sig.index(")(") + 1]; ports = sig[sig.index(")(") + 2:]
PAR = "LBANKS,LB,NID,IDW,PAW,PREL,DD,IMUT,DAW,ID_COHORT,XSLOT,CTXW,OPEN_IL,ATT_MARK".split(",")
names = re.findall(r"(?:wire(?:\s*\[[^\]]*\])?\s*)([a-zA-Z_][\w, a-zA-Z]*?)(?=,\s*(?:input|output)|,?\s*\n|\s*$)", re.sub(r"//.*", "", ports))
pn = [x.strip() for n in names for x in n.split(",") if x.strip()]
def comp(name, fs):
    sfx = "__fs" if fs else ""
    par = "#(" + ",".join(f".{p}({p})" for p in PAR if p not in ("LB", "DAW", "CTXW")) + ") "
    wire = """ wire seam_res_v,seam_s_fault,seam_h_fault,seam_stop;wire[96:0]seam_res_word;wire[7:0]seam_read_v,seam_complete,seam_bfault;wire[1:0]seam_read_bank;wire[47:0]seam_read_row;
 wire[15:0]seam_complete_bank;wire[2047:0]seam_read_data;wire[7:0]bk_in_v,bk_cr;wire[2279:0]bk_in_data;
"""
    mut = ""
    t = [f"// HBM-REFORM-B4 d44v part 26: GENERATED by gen_p26.py. {'Bench' if fs else 'Plan'} form.", "`default_nettype none",
         f"module {name} {hdr_par}(" + ports + ";", wire]
    pp = lambda ps: "#(" + ",".join(f".{p}({p})" for p in ps) + ") " if not fs else ""
    pa = ("LBANKS,NID,IDW,PAW,PREL,DD,IMUT,ID_COHORT,XSLOT,OPEN_IL,ATT_MARK").split(",")
    t.append(f""" ot_svgr_top{sfx} {pp(pa)}u_t(.id_stack(id_stack),.id_sm(id_sm),.stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),
  {SEAM_C}
  .program_cfg_we(program_cfg_we),.program_cfg_addr(program_cfg_addr),.program_cfg_data(program_cfg_data),.desc_we(desc_we),.desc_addr(desc_addr),.desc_data(desc_data),
  .run_v(run_v),.run_base(run_base),.run_count(run_count),.run_layer(run_layer),.ids_v(ids_v),.ids_layer(ids_layer),.ids(ids),.ids_cohort(ids_cohort),
  .running(running),.run_done(run_done),.program_active(program_active),.fault(fault),.sm_packet(sm_packet),.sm_command(sm_command),
  .expected_request(expected_request),.lt0(lt0),.lt1(lt1),.lb0(lb0),.lb1(lb1),.fm(fm));
 ot_svgr_own{sfx} u_o(.id_stack(id_stack),.id_sm(id_sm),.stream_clk(stream_clk),.stream_rst_n(stream_rst_n),.hbm_clk(hbm_clk),.hbm_rst_n(hbm_rst_n),.hbm_pc_clk(hbm_pc_clk),
  .seam_res_v(seam_res_v),.seam_res_word(seam_res_word),.seam_s_fault(seam_s_fault),.seam_h_fault(seam_h_fault),.bk_in_v(bk_in_v),.bk_in_data(bk_in_data),.bk_cr(bk_cr),
  .k_v(k_v),.k_rdy(k_rdy),.k_addr(k_addr),.k_len(k_len),.k_tag(k_tag),.k_we(k_we),.k_wdata(k_wdata),.k_wstrb(k_wstrb),.k_wr_done(k_wr_done),.kr_v(kr_v),.kr_rdy(kr_rdy),.kr_tag(kr_tag),.kr_beat(kr_beat),.kr_data(kr_data));""")
    for b in range(2):
        t.append(f""" ot_svgr_bk{sfx} u_b{b}(.hbm_clk(hbm_fifo_clk[{b}]),.stream_clk(stream_bank_clk[{b}]),.stream_rst_n(stream_rst_n),.hbm_rst_n(hbm_rst_n),.bk_hi(1'b{b}),
  .in_v(bk_in_v[{4*b}+:4]),.in_data(bk_in_data[{1140*b}+:1140]),.cr(bk_cr[{4*b}+:4]),.res_v(seam_res_v),.res_bank(seam_res_word[17:16]),.res_epoch(seam_res_word[15:0]),.res_total(seam_res_word[29:18]),
  .stop(seam_stop),.read_v(seam_read_v[{4*b}+:4]),.read_bank(seam_read_bank),.read_row(seam_read_row[{24*b}+:24]),
  .complete(seam_complete[{4*b}+:4]),.complete_bank(seam_complete_bank[{8*b}+:8]),.bfault(seam_bfault[{4*b}+:4]),.read_data(seam_read_data[{1024*b}+:1024]));""")
    t += ["endmodule", "`default_nettype wire", ""]
    return "\n".join(t)
(sd / f"{C}__p26fs.sv").write_text(comp(C + "__p26fs", True))
(sd / f"{C}__p26comp.sv").write_text(comp(C + "__p26comp", False))
pm = ", ".join(f".{n}({n})" for n in pn)
(sd / f"{C}__p26glue.sv").write_text(f"// HBM-REFORM-B4 d44v part 26: plan module {C} = thin parent glue of the split hard core (wires only).\n`default_nettype none\n"
    + f"module {C}__fcore {hdr_par}({ports};\n {C}__p26comp u_core ({pm});\nendmodule\n"
    + f"module {C} {hdr_par}({ports};\n {C}__fcore u_fcore ({pm});\nendmodule\n`default_nettype wire\n")
(sd / "ports.txt").write_text(" ".join(pn))
