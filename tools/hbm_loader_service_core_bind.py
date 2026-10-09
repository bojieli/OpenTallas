#!/usr/bin/env python3
"""Generate actual full32-PC service wrapper without changing pinned core."""
import argparse,re
from pathlib import Path
R=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--core',type=Path,required=True);a=p.parse_args()
s=a.core.read_text();start=s.index('module ot_hbm_svc_core #(');end=s.index(');',start)+2
header=s[start:end];params=re.findall(r'parameter\s+(?:integer|\[[^]]+\])\s*(\w+)\s*=',header)
# The original core names every direction separately in its ANSI interface.
ports=re.findall(r'(?:input|output)\s+(?:wire|reg)\s*(?:\[[^]]+\])?\s*(\w+)',header)
assert len(ports)==len(set(ports))
assert 'wq_pending' in ports and 'wq_source_busy' in ports,'real WB pending/source export required'
header=header.replace('module ot_hbm_svc_core #(','module ot_hbm_svc_core_native #(',1)
header=header.replace('parameter integer NSM = 8','parameter integer NATIVE=0, NSM = 8',1)
header=header[:-3]+',\n input wire outer_write_pending,\n input wire native_v,output wire native_rdy,input wire[4:0]native_pc,input wire[29:0]native_addr,input wire[15:0]native_tag,\n output wire native_rsp_v,input wire native_rsp_rdy,output wire[4:0]native_rsp_pc,output wire[15:0]native_rsp_tag,\n output wire[3:0]native_rsp_beat,output wire[255:0]native_rsp_data,output wire native_fault\n);'
# Rename only the actual controller K boundary, preserving every other core port.
widths={'k_v':1,'k_rdy':1,'k_we':1,'k_addr':30,'k_len':4,'k_tag':17,'k_wdata':256,'k_wstrb':32,'kr_v':1,'kr_rdy':1,'kr_tag':17,'kr_beat':4,'kr_data':256}
out=['`default_nettype none',header]
for n,w in widths.items():out.append(f' wire [NPC{f"*{w}" if w>1 else ""}-1:0] n_{n};')
out+=[' wire n_pending;wire[NPC-1:0]n_busy,native_busy;',' assign wq_pending=n_pending;assign wq_source_busy=n_busy;',
 ' ot_hbm_svc_core #('+','.join(f'.{x}({x})' for x in params)+') u_core (']
for n in ports:out.append(f' .{n}({"n_"+n if n in widths else "n_pending" if n=="wq_pending" else "n_busy" if n=="wq_source_busy" else n}),')
out[-1]=out[-1][:-1]+');'
out+=[' ot_hbm_loader_service_boundary #(.ENABLE(NATIVE),.NPC(NPC)) u_native(',
 ' .clk(ck),.rst_n(phy_rst_n),.normal_pending_write({NPC{outer_write_pending||n_pending}}|n_busy),',
 ' .native_v(native_v),.native_rdy(native_rdy),.native_pc(native_pc),.native_addr(native_addr),.native_tag(native_tag),',
 ' .native_rsp_v(native_rsp_v),.native_rsp_rdy(native_rsp_rdy),.native_rsp_pc(native_rsp_pc),.native_rsp_tag(native_rsp_tag),',
 ' .native_rsp_beat(native_rsp_beat),.native_rsp_data(native_rsp_data),.native_busy(native_busy),.fault(native_fault),']
mapnorm={'k_v':'v','k_rdy':'rdy','k_we':'we','k_addr':'addr','k_len':'len','k_tag':'tag','k_wdata':'wdata','k_wstrb':'wstrb','kr_v':'rsp_v','kr_rdy':'rsp_rdy','kr_tag':'rsp_tag','kr_beat':'rsp_beat','kr_data':'rsp_data'}
for n in widths:out.append(f' .normal_{mapnorm[n]}(n_{n}),.{n}({n}),')
out+=[' .k_wr_done(k_wr_done));','endmodule','`default_nettype wire','']
d=R/'rtl/hbm_accel/loader/service_native/ot_hbm_svc_core_native.sv';d.write_text('\n'.join(out))
