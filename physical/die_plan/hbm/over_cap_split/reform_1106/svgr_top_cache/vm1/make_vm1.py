#!/usr/bin/env python3
"""DIE-HBM-91-OPEN svgr_top vM1 source delta (all default 0 = byte-equivalent behaviour):
 top/feed VM1 -> producer ROT1H (p_rq chain dropped: p_ord carries the same value; rotation select = registered one-hot
 of p_ord[DLY-2][2:0]), rows WOH (registered one-hot write pointers rotl(wptr,i) = onehot((received+i)%16)),
 issuer IDMUX (a_id by a_sel compare mux, no (a_sel-1)*IDW shift index)."""
import sys, re
from pathlib import Path
d = Path(sys.argv[1])
def sub(path, old, new, count=1):
    t = path.read_text()
    n = t.count(old)
    assert n == count, (path.name, old[:60], n)
    path.write_text(t.replace(old, new))
cc = d / "ot_svgr_top_cachecut.sv"
# --- top params / instances
sub(cc, " parameter integer RRMIR=0)(\n // strap identity",
        " parameter integer RRMIR=0,\n // DIE-HBM-91-OPEN vM1 (default 0 = unchanged): producer ROT1H, cache WOH, issuer IDMUX (see modules). Cycle-exact, ports unchanged.\n parameter integer VM1=0)(\n // strap identity")
sub(cc, ".XSLOT(XSLOT),.MPIPE(P1)) issuer(", ".XSLOT(XSLOT),.MPIPE(P1),.IDMUX(VM1)) issuer(")
sub(cc, ".CACHE_WDEC(CACHE_WDEC),.CACHE_GSEL(CACHE_GSEL),.CACHE_GREP(CACHE_GREP),.RRMIR(RRMIR)) feed(",
        ".CACHE_WDEC(CACHE_WDEC),.CACHE_GSEL(CACHE_GSEL),.CACHE_GREP(CACHE_GREP),.RRMIR(RRMIR),.VM1(VM1)) feed(")
# --- feed
sub(cc, " parameter integer RRMIR=0   // DIE-HBM-88 vL7 reserve_ready mirrors, see top\n)(",
        " parameter integer RRMIR=0,  // DIE-HBM-88 vL7 reserve_ready mirrors, see top\n parameter integer VM1=0     // DIE-HBM-91-OPEN vM1, see top\n)(")
sub(cc, "#(.LBANKS(LBANKS),.OPEN_IL(OPEN_IL),.OREG(P1),.RRMIR(RRMIR)) producer(",
        "#(.LBANKS(LBANKS),.OPEN_IL(OPEN_IL),.OREG(P1),.RRMIR(RRMIR),.ROT1H(VM1)) producer(")
sub(cc, ".WDECOUPLE(CACHE_WDEC),.GSEL(CACHE_GSEL),.GREP(CACHE_GREP)) rows(",
        ".WDECOUPLE(CACHE_WDEC),.GSEL(CACHE_GSEL),.GREP(CACHE_GREP),.WOH(VM1)) rows(")
# --- producer
sub(cc, "parameter integer OREG=0,\n parameter integer RRMIR=0)(",
        "parameter integer OREG=0,\n parameter integer RRMIR=0,\n // ROT1H 1 (DIE-HBM-91-OPEN vM1): read_ordinal_q / p_rq are dropped (o_ord and read_ordinal_q load the same drain_ordinal under the\n // same condition and reset, so p_ord == p_rq at every stage); the rotate select is rsel, a registered one-hot of\n // p_ord[DLY-2][2:0] (== onehot(p_ord[DLY-1][2:0]) every edge), and each 256-bit lane is an AND-OR of 8 chunks.\n parameter integer ROT1H=0)(")
sub(cc, " wire[1023:0]rot_data;\n generate for(g=0;g<4;g=g+1)begin:out_lane\n  assign rot_data[256*g+:256]=seam_read_data[256*((p_rq[DLY-1][2:0]+g)%8)+:256];\n end endgenerate\n",
        " wire[1023:0]rot_data;\n generate if(ROT1H!=0)begin:g_r1h\n  reg [7:0] rsel;\n  always @(posedge stream_clk or negedge srst)if(!srst)rsel<=8'd1;else rsel<=8'd1<<p_ord[DLY-2][2:0];\n  for(g=0;g<4;g=g+1)begin:out_lane\n   reg [255:0] lane;integer k;\n   always @*begin lane=0;for(k=0;k<8;k=k+1)if(rsel[k])lane=lane|seam_read_data[256*((k+g)%8)+:256];end\n   assign rot_data[256*g+:256]=lane;\n  end\n end else begin:g_rq\n  for(g=0;g<4;g=g+1)begin:out_lane\n   assign rot_data[256*g+:256]=seam_read_data[256*((p_rq[DLY-1][2:0]+g)%8)+:256];\n  end\n end endgenerate\n")
# p_rq / read_ordinal_q writes: keep for ROT1H 0 only (yosys removes the unread regs anyway; explicit for LEC clarity)
sub(cc, "p_ep[0]<=o_epoch;p_rq[0]<=read_ordinal_q;", "p_ep[0]<=o_epoch;if(ROT1H==0)p_rq[0]<=read_ordinal_q;")
sub(cc, "p_ep[d]<=p_ep[d-1];p_rq[d]<=p_rq[d-1];end", "p_ep[d]<=p_ep[d-1];if(ROT1H==0)p_rq[d]<=p_rq[d-1];end")
sub(cc, "    read_ordinal_q<=drain_ordinal;drain_phase", "    if(ROT1H==0)read_ordinal_q<=drain_ordinal;drain_phase")
# --- cache WOH
ca = d / "ot_svgr_cache136_native.sv"
sub(ca, " parameter integer WDECOUPLE=0,parameter integer GSEL=0,parameter integer GREP=1)(",
        " parameter integer WDECOUPLE=0,parameter integer GSEL=0,parameter integer GREP=1,\n // WOH 1 (DIE-HBM-91-OPEN vM1): wptr = registered one-hot of received%16 (reset / open_ok: 1, running && !sticky edge:\n // rotate by expected_sectors with received); sector i writes words / tests present at rotl(wptr,i), no adder or decode\n // in front of the 4096 staging-word enables.  Cycle-exact.\n parameter integer WOH=0)(")
sub(ca, "  reg [1:0] ready;integer b,r,j,gk,gc;",
        "  reg [1:0] ready;integer b,r,j,gk,gc;\n  reg [15:0] wptr;wire [15:0] wsel[0:3];\n  genvar wi;for(wi=0;wi<4;wi=wi+1)begin:g_wsel assign wsel[wi]=(wptr<<wi)|(wptr>>(16-wi));end")
sub(ca, "    head<=0;slot_phase<=0;elapsed<=0;record_phase<=0;present<=0;out_valid<=0;out_tag<=0;w_q<=0;",
        "    head<=0;slot_phase<=0;elapsed<=0;record_phase<=0;present<=0;out_valid<=0;out_tag<=0;w_q<=0;wptr<=16'd1;")
sub(ca, "     received<=0;total_sectors<=((open_count*136+127)/128)*4;head<=0;",
        "     received<=0;wptr<=16'd1;total_sectors<=((open_count*136+127)/128)*4;head<=0;")
sub(ca, """       if(sector_epoch[i*16+:16]!=load_epoch||sector_index[i*24+:24]!=received+i||present[(received+i)%16])sticky<=1;
       else if(WDECOUPLE==0)begin words[(received+i)%16]<=sector_data[i*256+:256];present[(received+i)%16]<=1;end
       if(WDECOUPLE!=0)begin words[(received+i)%16]<=sector_data[i*256+:256];present[(received+i)%16]<=1;end""",
"""       if(WOH!=0)begin
        if(sector_epoch[i*16+:16]!=load_epoch||sector_index[i*24+:24]!=received+i||(|(present&wsel[i])))sticky<=1;
        else if(WDECOUPLE==0)begin for(gk=0;gk<16;gk=gk+1)if(wsel[i][gk])begin words[gk]<=sector_data[i*256+:256];present[gk]<=1;end end
        if(WDECOUPLE!=0)begin for(gk=0;gk<16;gk=gk+1)if(wsel[i][gk])begin words[gk]<=sector_data[i*256+:256];present[gk]<=1;end end
       end else begin
       if(sector_epoch[i*16+:16]!=load_epoch||sector_index[i*24+:24]!=received+i||present[(received+i)%16])sticky<=1;
       else if(WDECOUPLE==0)begin words[(received+i)%16]<=sector_data[i*256+:256];present[(received+i)%16]<=1;end
       if(WDECOUPLE!=0)begin words[(received+i)%16]<=sector_data[i*256+:256];present[(received+i)%16]<=1;end
       end""")
sub(ca, "     received<=received+expected_sectors;",
        "     received<=received+expected_sectors;\n     if(WOH!=0)case(expected_sectors)3'd1:wptr<={wptr[14:0],wptr[15]};3'd2:wptr<={wptr[13:0],wptr[15:14]};\n      3'd3:wptr<={wptr[12:0],wptr[15:13]};3'd4:wptr<={wptr[11:0],wptr[15:12]};default:;endcase")
# --- issuer IDMUX
iss = d / "ot_hbm_svc_sm_issuer_rel.sv"
t = iss.read_text()
m = re.search(r"module ot_hbm_svc_sm_issuer_rel #\((.*?)\)\(", t, re.S)
assert m
params = m.group(1)
assert "MPIPE" in params
newp = params.rstrip() + ",\n // IDMUX 1 (DIE-HBM-91-OPEN vM1): a_id by a_sel==k compare mux (k=1..NID), not the (a_sel-1)*IDW shift index\n parameter integer IDMUX=0"
t = t.replace(params, newp, 1)
old = " wire[IDW-1:0]a_id=(a_sel==0||MUT==2)?{IDW{1'b0}}:ids_q[(a_sel-4'd1)*IDW+:IDW];\n"
assert t.count(old) == 1
new = (" wire[IDW-1:0]a_id_sh=(a_sel==0||MUT==2)?{IDW{1'b0}}:ids_q[(a_sel-4'd1)*IDW+:IDW];\n"
       " reg[IDW-1:0]a_id_mx;integer ik;\n"
       " always @*begin a_id_mx={IDW{1'b0}};for(ik=1;ik<=NID;ik=ik+1)if(a_sel==4'(ik))a_id_mx=ids_q[(ik-1)*IDW+:IDW];end\n"
       " wire[IDW-1:0]a_id=(IDMUX!=0)?((MUT==2)?{IDW{1'b0}}:a_id_mx):a_id_sh;\n")
t = t.replace(old, new)
iss.write_text(t)
print("VM1 delta applied", d)
