#!/usr/bin/env python3
"""Off-default five-root BF front; preserve every production payload edge.

The previous single IO root spans all four faces. Native pass1 has 117 capture
failures (reset329.5ps, data up to210ps). This candidate separates primary north
capture and west/east seam flops from the south capture/lockup bank. All clocks
are synchronous phase-zero roots, with ordinary setup/hold on every crossing.
Five real reset relays add one boot release edge, not a payload pipeline edge.
"""
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]


def once(s,a,b):
    assert s.count(a)==1,(a,s.count(a))
    return s.replace(a,b)


def main():
    fp=ROOT/'rtl/s81/ot_s81_bf_front.sv'
    original=fp.read_text()
    s=once(original,'module ot_s81_bf_front #(','module ot_s81_bf_front_roots #(')
    s=once(s,'    input wire io_clk,','    input wire io_n,io_w,io_e, // separate north/west/east physical roots\n    input wire io_clk,')
    pos=s.index('    // Keep all programme fields together')
    head,body=s[:pos],s[pos:]
    body=re.sub(r'(?<!\.)\brst_n\b','core_rst',body)
    relay='''    // Async assert, one real synchronous boot-release edge at each root.
    wire core_rst,south_rst,north_rst,west_rst,east_rst;
    ot_v41_kreg #(.W(1),.AR(1),.RV(1'b0)) u_core_reset
      (.clk(clk),.arst_n(rst_n),.d(1'b1),.q(core_rst));
    ot_v41_kreg #(.W(1),.AR(1),.RV(1'b0)) u_south_reset
      (.clk(io_clk),.arst_n(rst_n),.d(1'b1),.q(south_rst));
    ot_v41_kreg #(.W(1),.AR(1),.RV(1'b0)) u_north_reset
      (.clk(io_n),.arst_n(rst_n),.d(1'b1),.q(north_rst));
    ot_v41_kreg #(.W(1),.AR(1),.RV(1'b0)) u_west_reset
      (.clk(io_w),.arst_n(rst_n),.d(1'b1),.q(west_rst));
    ot_v41_kreg #(.W(1),.AR(1),.RV(1'b0)) u_east_reset
      (.clk(io_e),.arst_n(rst_n),.d(1'b1),.q(east_rst));
`ifdef BF_FRONT_ROOT_STOP_N
    wire north_clk=1'b0;
`else
    wire north_clk=io_n;
`endif
`ifndef SYNTHESIS
    initial if (STATIC_PROGRAM!=1 || PINLAT!=1 || CPIN!=1 || HALF!=0)
      $fatal(1,"five-root front requires the source-pinned static production pipeline");
`endif
'''
    body=body.replace('posedge pin_clk or negedge core_rst','posedge pin_clk or negedge south_rst')
    for a,b in [('if (!core_rst) programme_pin_q','if (!south_rst) programme_pin_q'),
                ("if (!core_rst) begin r_busy", "if (!south_rst) begin r_busy")]:
        body=once(body,a,b)
    old="""        always @(posedge pin_clk or negedge south_rst)
            if (!core_rst) begin r_cfg_v <= 1'b0; r_go <= 1'b0; r_xs_v <= 1'b0; r_xb_v <= 1'b0; end
            else begin r_cfg_v <= cfg_v; r_go <= go; r_xs_v <= xs_v; r_xb_v <= xb_v; end"""
    new="""        always @(posedge pin_clk or negedge south_rst)
            if (!south_rst) begin r_cfg_v <= 1'b0; r_go <= 1'b0; r_xs_v <= 1'b0; end
            else begin r_cfg_v <= cfg_v; r_go <= go; r_xs_v <= xs_v; end
        always @(posedge north_clk or negedge north_rst)
            if (!north_rst) r_xb_v <= 1'b0; else r_xb_v <= xb_v;"""
    body=once(body,old,new)
    start=body.index('        always @(posedge pin_clk) begin\n            r_cfg_a')
    end=body.index('        end',start)+len('        end')
    block=body[start:end]
    north=[line for line in block.splitlines() if re.search(r'\br_xb_\w+ <=',line)]
    assert len(north)==5,north
    south='\n'.join(line for line in block.splitlines() if line not in north)
    body=body[:start]+south+'\n        always @(posedge north_clk) begin\n'+'\n'.join(north)+'\n        end'+body[end:]
    body=once(body,'u_seam0 (.clk(pin_clk), .rst_n(core_rst),','u_seam0 (.clk(io_w), .rst_n(west_rst),')
    body=once(body,'u_seam1 (.clk(pin_clk), .rst_n(core_rst),','u_seam1 (.clk(io_e), .rst_n(east_rst),')
    # Keep source-low IO lockups on the south physical root. The north->south
    # crossing is still a timed half-cycle path with no new architectural edge.
    out=ROOT/'rtl/s81/ot_s81_bf_front_roots.sv';out.write_text(head+relay+body)
    wp=ROOT/'rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_static.sv'
    w=once(wp.read_text(),'module dsfd_bf_front_static #(','module dsfd_bf_front_roots #(')
    w=once(w,'    input wire io_clk\n','    input wire io_clk,\n    input wire io_n,io_w,io_e\n')
    w=once(w,'    ot_s81_bf_front #(','    ot_s81_bf_front_roots #(')
    w=once(w,'.io_clk(io_clk)', '.io_clk(io_clk), .io_n(io_n), .io_w(io_w), .io_e(io_e)')
    wo=ROOT/'rtl/dsrom_sys/s81_die_bind/dsfd_bf_front_roots.sv';wo.write_text(w)
    record=dict(status='SOURCE_CANDIDATE_UNPROVEN',payload_cycles_added=0,boot_reset_release_edges_added=1,
      roots={'ck':'existing core and core-source seam lockup','io_clk':'south primary capture/status/programme and IO-source lockups','io_n':'north xb primary capture','io_w':'west c0 seam flops','io_e':'east c1 seam flops'},
      inputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [fp,wp]},
      outputs={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [out,wo]},
      physical_qualification=False,clock_pins_homes_and_slot_grant='PENDING',native_capture='PENDING')
    rp=ROOT/'results/rtl/s81_bf_clock_1015/c10/recovery_0253/front_roots_source.json'
    rp.write_text(json.dumps(record,indent=2)+'\n')


if __name__=='__main__':main()
