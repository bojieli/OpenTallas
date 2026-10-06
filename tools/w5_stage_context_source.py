#!/usr/bin/env python3
"""Source-faithful W5-only kept AO replicas; current source pins are recorded.
No shared parent edits. Original sequential statements and shadow widths copied.
"""
from pathlib import Path
import re,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'rtl/experimental/w5_context/ot_w5_stage.sv'
def add_port(s,p):
 i=s.index(');');lines=s[:i].rstrip().splitlines();code,sep,comment=lines[-1].partition('//');lines[-1]=code.rstrip()+','+(' //'+comment if sep else '');return '\n'.join(lines)+'\n    '+p+'\n'+s[i:]
def kept(s):
 s=re.sub(r'(?m)^(\s*)(st_t\s+st;)',r'\1(* keep, dont_touch *) \2',s)
 s=re.sub(r'(?m)^(\s*)((?:reg|logic)\s)',r'\1(* keep, dont_touch *) \2',s)
 return re.sub(r'(?m)^(\s*)(output\s+(?:reg|logic)\s)',r'\1(* keep, dont_touch *) \2',s)
def module(s,name):
 return re.search(r'(?ms)^module '+name+r'\b.*?^endmodule',s).group()
def build():
 srcs=['rtl/v41rom/ot_v41_rom_stage_pg_cdc.sv','rtl/v41rom/ot_v41_stage_pg_sched.sv','rtl/chip/ot_chip_v41_pg_ctrl.sv']
 raw={p:(ROOT/p).read_text() for p in srcs};stage=raw[srcs[0]]
 names={n:'ot_w5_'+n.replace('ot_v41_rom_','').replace('ot_v41_','').replace('ot_chip_v41_','') for n in re.findall(r'^module (\w+)',stage, re.M)}
 names['ot_v41_stage_pg_sched']='ot_w5_sched'
 names['ot_chip_v41_pg_ctrl']='ot_w5_power_ctl'
 def renamed(s):
  for a,b in names.items():s=re.sub(r'\b'+a+r'\b',b,s)
  return s
 pg=kept(renamed(raw[srcs[2]]))
 pg=add_port(pg,'output wire [3+((NSUB>1)?$clog2(NSUB+1):1)+CW+NSUB+5-1:0] snapshot')
 pg=pg.replace('endmodule','assign snapshot = {st,idx,cnt,sw_en,iso_n,dom_rst_n,clk_en,pwr_good,fault};\nendmodule')
 sch=kept(renamed(raw[srcs[1]]))
 sch=sch.replace('module ot_w5_sched #(', '(* keep_hierarchy = \"yes\" *)\nmodule ot_w5_sched #(',1)
 sch=add_port(sch,'output wire [2*TW+10+3+((NSUB>1)?$clog2(NSUB+1):1)+16+NSUB+5-1:0] snapshot')
 sch=sch.replace('    (* keep, dont_touch *) reg [TW-1:0] cnt;', '    wire [3+((NSUB>1)?$clog2(NSUB+1):1)+16+NSUB+5-1:0] pg_snapshot;\n    (* keep, dont_touch *) reg [TW-1:0] cnt;')
 sch=sch.replace('.clk(clk), .rst_n(rst_n), .req_on(req_on)', '.snapshot(pg_snapshot), .clk(clk), .rst_n(rst_n), .req_on(req_on)')
 sch=sch.replace('endmodule','assign snapshot = {cnt,cnt_v,idle,th,pg_snapshot};\nendmodule')
 # Retain all AO sequential state, not just externally visible status.
 ea=kept(renamed(module(stage,'ot_v41_rom_pg_eao')))
 ea=add_port(ea,'output wire [50*((NB==2)?25:17)+73-1:0] snapshot')
 ea=ea.replace('endmodule', '''wire [48*NA-1:0] shadow_snapshot;
    for (genvar si=0;si<NA;si=si+1) begin:g_snapshot
        assign shadow_snapshot[48*si+:48]=valid[si]?sh_q[si]:48'b0;
    end
    assign snapshot={shadow_snapshot,valid,dirty,ready,pg_q,rq,infl,
      cdc_bs1,bs2,cdc_rr1,rr2,cdc_ak1,ak2,cdc_ra1,ra2,ridx_q,rhit_q,sel_v,iso_q,
      infl?{cdc_rp_a,cdc_rp_d}:53'b0};
endmodule''')
 ctl=kept(renamed(module(stage,'ot_v41_rom_stage_pg_ctl_sp')))
 ctl=ctl.replace('ot_w5_sched #(', '(* keep, dont_touch *) ot_w5_sched #(',1)
 ctl=add_port(ctl,'output wire [2*TW+12+3+((NSUB>1)?$clog2(NSUB+1):1)+16+NSUB+5-1:0] snapshot')
 ctl=ctl.replace('    wire clk_en, req_on;', '    wire [2*TW+10+3+((NSUB>1)?$clog2(NSUB+1):1)+16+NSUB+5-1:0] sched_snapshot;\n    wire clk_en, req_on;')
 ctl=ctl.replace('.clk(a_clk), .rst_n(rst_n)', '.snapshot(sched_snapshot), .clk(a_clk), .rst_n(rst_n)',1)
 ctl=ctl.replace('endmodule','assign snapshot={spine_on,late,sched_snapshot};\nendmodule')
 ao_original=renamed(module(stage,'ot_v41_rom_stage_pg_ao_cdc'))
 ao=add_port(ao_original,'output wire [K*(50*((NB==2)?25:17)+73)+2*TW+12+3+((NSUB>1)?$clog2(NSUB+1):1)+16+NSUB+5-1:0] snapshot')
 ao=ao.replace('.clk(clk), .a_clk(aon_clk)', '.snapshot(snapshot[K*(50*((NB==2)?25:17)+73)+:2*TW+12+3+((NSUB>1)?$clog2(NSUB+1):1)+16+NSUB+5]), .clk(clk), .a_clk(aon_clk)',1)
 ao=ao.replace('.a_clk(aon_clk), .rst_n(rst_n), .cfg_v(cfg_v[g])', '.snapshot(snapshot[g*(50*((NB==2)?25:17)+73)+:50*((NB==2)?25:17)+73]), .a_clk(aon_clk), .rst_n(rst_n), .cfg_v(cfg_v[g])',1)
 # Make a protected alternative with identical functional ports.
 hdr=ao_original[:ao_original.index(');')+2].replace(names['ot_v41_rom_stage_pg_ao_cdc'],'ot_w5_ao_checked')
 hdr=hdr.replace('parameter integer RETENTION_EDGE_WRITE = 0,','parameter integer PROTECT = 0,\n    parameter integer RETENTION_EDGE_WRITE = 0,')
 ports=[]
 for d,width,name in re.findall(r'(?m)^\s*(input|output)\s+wire\s*(\[[^\n]*?\])?\s*(\w+)\s*[,\n]',hdr):ports.append((d,width,name))
 outs=[(w,n) for d,w,n in ports if d=='output']
 ins=[n for d,w,n in ports if d=='input']
 decl='\n'.join('wire '+w+' '+n+'_p, '+n+'_r;' for w,n in outs)
 def inst(tag,aclk):
  conn=['.snapshot(snap_'+tag+')']
  for d,w,n in ports:
   val=n+'_'+tag if d=='output' else ('ao_clk' if n=='aon_clk' else n)
   conn.append('.'+n+'('+val+')')
  return 'ot_w5_stage_pg_ao_cdc #(.K(K),.NB(NB),.NSUB(NSUB),.TW(TW),.RETENTION_EDGE_WRITE(RETENTION_EDGE_WRITE)) u_'+tag+' ('+','.join(conn)+');'
 hdr=add_port(hdr,'input wire external_quarantine')
 wrapper=hdr+'\n'+decl+'''
localparam integer SW=K*(50*((NB==2)?25:17)+73)+2*TW+12+3+((NSUB>1)?$clog2(NSUB+1):1)+16+NSUB+5;
wire [SW-1:0] snap_p,snap_r;
wire ao_clk, bad, quarantine;
(* keep, dont_touch *) reg sticky=0, sticky_inverse=1;
generate if (PROTECT!=0) begin:g_checked
    assign bad=|(snap_p^snap_r);
    wire settled_alarm;
    ot_w5_fault_low u_qualify(.clk(aon_clk),.rst_n(rst_n),
        .alarm(bad|external_quarantine|(|fault_p)),.settled(settled_alarm));
    assign quarantine=settled_alarm|sticky|~sticky_inverse;
    always @(posedge aon_clk or negedge rst_n)
        if(!rst_n) begin sticky<=0;sticky_inverse<=1;end
        else if(quarantine) begin sticky<=1;sticky_inverse<=0;end
    // Freeze both copies at detection. Only coordinated cold reset can erase
    // retained valid/dirty/request/accepted debt. No warm recovery or ACK.
    ot_hdc_cg u_freeze(.clk(aon_clk),.en(!quarantine|!rst_n),.gclk(ao_clk));
'''+inst('r','ao_clk')+'''
end else begin:g_unchecked
 assign ao_clk=aon_clk;assign bad=0;assign quarantine=0;assign snap_r=snap_p;
end endgenerate
'''+inst('p','ao_clk')+'\n'
 for w,n in outs:
  if n=='s_clk':wrapper+='ot_hdc_cg u_fault_spine(.clk(s_clk_p),.en(!quarantine|!rst_n),.gclk(s_clk));\n'
  elif n in ('pg_fault','fault','busy'):wrapper+='assign '+n+'='+n+'_p | '+(('{K{quarantine}}') if n in ('fault','busy') else 'quarantine')+';\n'
  elif n in ('rp_a','rp_d'):wrapper+='assign '+n+'='+n+'_p; // immutable replay tuple under quarantine\n'
  else:wrapper+='assign '+n+'='+n+'_p & {'+str(1 if not w else ('NSUB' if n=='sw_en' else re.sub(r'\[([^:]+)-1:0\]',r'\1',w)))+'{!quarantine}};\n'
 # Width from $bits avoids malformed range conversion and remains source-shaped.
 wrapper=re.sub(r'& \{[^\n]*?\{!quarantine\}\};',lambda m:m.group(),wrapper)
 for w,n in outs:
  if n not in ('s_clk','pg_fault','fault','busy','rp_a','rp_d'):
   wrapper=re.sub(r'assign '+n+r'=.*?;\n','assign '+n+'='+n+'_p & {$bits('+n+'){!quarantine}};\n',wrapper)
 wrapper+='endmodule\n'
 top=renamed(module(stage,'ot_v41_rom_stage_q_pg_cdc_w10'))
 top=top.replace('parameter integer RETENTION_EDGE_WRITE = 0,','parameter integer PROTECTED_AO = 0,\n    parameter integer RETENTION_EDGE_WRITE = 0,',1)
 top=add_port(top,'input wire context_fault')
 top=top.replace('.clk(clk), .aon_clk(aon_clk), .rst_n(rst_n), .cfg_v(cfg_v)', '.external_quarantine(context_fault), .clk(clk), .aon_clk(aon_clk), .rst_n(rst_n), .cfg_v(cfg_v)',1)
 top=top.replace('ot_w5_stage_pg_ao_cdc #(', 'ot_w5_ao_checked #(.PROTECT(PROTECTED_AO),',1)
 text='// Generated by tools/w5_stage_context_source.py; independent W5 context only.\n'+renamed(module(stage,'ot_v41_rom_pg_dif'))+'\n'+ea+'\n'+pg+'\n'+sch+'\n'+ctl+'\n'+ao+'\n'+wrapper+'\n'+top+'\n'
 OUT.write_text(text)
 rec={'source_sha256':{p:hashlib.sha256(raw[p].encode()).hexdigest() for p in srcs},'generated_sha256':hashlib.sha256(text.encode()).hexdigest(),'scope':'kept fullstate AO DMR; same source statements; no default adoption; cold-only quarantine'}
 (ROOT/'results/rtl/rom_stage_context_20261005/source_generation.json').write_text(json.dumps(rec,indent=2)+'\n')
if __name__=='__main__':build()
