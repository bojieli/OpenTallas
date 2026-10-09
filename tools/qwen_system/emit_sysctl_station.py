#!/usr/bin/env python3
"""Emit a default-off packet boundary wrapper without editing the pinned control core."""
import argparse
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def emit(out):
    old=(ROOT/'rtl/qwen_sys/system_20261008/ot_qfd_sysctl.sv').read_text()
    header=old[old.index('module ot_qfd_sysctl #('):old.index('\n);')+4]
    header=header.replace('module ot_qfd_sysctl #(', 'module ot_qfd_sysctl_stn #(\n    parameter integer BOUNDARY_STATIONS = 0,')
    ports=re.findall(r'^    (input|output)\s+wire\s+(\[[^\]]+\])?\s*(\w+)\s*,?\s*(?://[^\n]*)?$',header,flags=re.M)
    assert len(ports)==66,len(ports)
    shapes={n:w for dr,w,n in ports}
    params=re.findall(r'parameter integer (\w+)',header)
    channels=[('s_aw','in',['s_awaddr']),('s_w','in',['s_wdata','s_wstrb']),
              ('s_b','out',['s_bresp']),('s_ar','in',['s_araddr']),('s_r','out',['s_rdata','s_rresp']),
              ('m_ar','out',['m_araddr','m_arlen','m_arsize']),('m_r','in',['m_rdata','m_rresp','m_rlast']),
              ('m_aw','out',['m_awaddr','m_awlen','m_awsize']),('m_w','out',['m_wdata','m_wstrb','m_wlast']),('m_b','in',['m_bresp'])]
    levels=['c_done','c_done_gen','c_next_token','c_next_val','c_drained','c_fault','c_fault_vec','crom_fault','link_up','boot_done','boot_ok']
    stationed=set(levels)
    for prefix,direction,fields in channels:stationed.update([prefix+'valid',prefix+'ready']+fields)
    lines=['`timescale 1ns/1ps','// Generated packet boundary variant; original core remains byte-identical.',header]
    for n in sorted(stationed):lines.append(f'wire {shapes[n]} q_{n};')
    def width(n):
        w=shapes[n]
        if not w:return '1'
        hi,lo=w.strip('[]').split(':');return f'(({hi})-({lo})+1)'
    lines += ['generate if(BOUNDARY_STATIONS==0)begin:g_bypass']
    for dr,w,n in ports:
        if n in stationed:lines.append(f'assign {"q_"+n if dr=="input" else n} = {n if dr=="input" else "q_"+n};')
    lines.append('end else begin:g_stations')
    for prefix,direction,fields in channels:
        extdata='{'+','.join(fields)+'}'
        intdata='{'+','.join('q_'+n for n in fields)+'}'
        v,r=prefix+'valid',prefix+'ready'
        ind,outd=(extdata,intdata) if direction=='in' else (intdata,extdata)
        inv,inr,outv,outr=(v,r,'q_'+v,'q_'+r) if direction=='in' else ('q_'+v,'q_'+r,v,r)
        # System CSR access must work while host_rst_n is low during boot. AXI-Lite
        # survives the host soft reset; only DMA queues belong to that reset domain.
        reset='por_n' if prefix.startswith('s_') else 'host_rst_n'
        lines.append(f'ot_qfd_packet_stn #(.W({"+".join(width(n) for n in fields)})) u_{prefix} (.clk(clk),.rst_n({reset}),.i_valid({inv}),.i_ready({inr}),.i_data({ind}),.o_valid({outv}),.o_ready({outr}),.o_data({outd}));')
    for n in levels:
        reset='por_n' if n in ['link_up','boot_done','boot_ok'] else 'die_rst_n'
        lines += [f'reg {shapes[n]} r_{n};',f'always @(posedge clk or negedge {reset}) if(!{reset})r_{n}<=0;else r_{n}<={n};',f'assign q_{n}=r_{n};']
    lines.append('end endgenerate')
    lines.append('ot_qfd_sysctl #('+','.join(f'.{p}({p})' for p in params if p!='BOUNDARY_STATIONS')+') u_core (')
    lines.append(','.join(f'.{n}({"q_" if n in stationed else ""}{n})' for dr,w,n in ports)+');\nendmodule')
    lines += ['''// Finite one-entry packet queue. Ready depends only on the registered occupancy.
// No bypass or ready propagation; one edge latency, two-edge minimum accept interval.
module ot_qfd_packet_stn #(parameter integer W=1)(
 input wire clk,rst_n,input wire i_valid,output wire i_ready,input wire [W-1:0] i_data,
 output wire o_valid,input wire o_ready,output wire [W-1:0] o_data);
 reg full;reg [W-1:0] data;
 assign i_ready=!full;assign o_valid=full;assign o_data=data;
 always @(posedge clk or negedge rst_n)begin
  if(!rst_n)full<=0;
  else if(full)begin if(o_ready)full<=0;end
  else if(i_valid)begin full<=1;data<=i_data;end
 end
endmodule''']
    out.write_text('\n'.join(lines)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);emit(p.parse_args().out)
