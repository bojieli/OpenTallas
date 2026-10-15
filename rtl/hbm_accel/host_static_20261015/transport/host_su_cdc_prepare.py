#!/usr/bin/env python3
"""Bind the actual full-shape native SU AXI bench through a real host CDC mailbox."""
import argparse
import json
import pathlib
import shutil

p = argparse.ArgumentParser()
p.add_argument('image')
p.add_argument('out')
p.add_argument('--target-mhz',type=int,choices=[900,1200],default=900)
a = p.parse_args()
src = pathlib.Path(a.image)
out = pathlib.Path(a.out)
out.mkdir(parents=True, exist_ok=True)
for name in ['config.mem', 'expected.mem', 'host_su_model.json', 'manifest.json', 'programme_params.svh']:
    if (src / name).exists():
        shutil.copyfile(src / name, out / name)
s = (src / 'host_su_axi_tb.sv').read_text().replace(
    'module host_su_axi_tb;', 'module host_su_cdc_tb;\nparameter integer MUT=0;')
target_period='5' if a.target_mhz==900 else '3.75'
s = s.replace('logic clk=0;always #5 clk=~clk;',
              'logic clk=0;always #'+target_period+' clk=~clk;\nlogic hostclk=0;always #3.75 hostclk=~hostclk;')
s = s.replace('wire block_ready,busy,valid,done,fault;', '''wire[11:0]ma,mra;wire mav,mar,mwv,mwr,mbv,mbr,mrav,mrar,mrv,mrr;wire[31:0]mwd,mrd;wire[3:0]mws;wire[1:0]mbresp,mrresp;
wire block_ready,busy,valid,done,fault;''')
mp = {'awaddr': 'ma', 'awvalid': 'mav', 'awready': 'mar', 'wdata': 'mwd', 'wstrb': 'mws',
      'wvalid': 'mwv', 'wready': 'mwr', 'bresp': 'mbresp', 'bvalid': 'mbv', 'bready': 'mbr',
      'araddr': 'mra', 'arvalid': 'mrav', 'arready': 'mrar', 'rdata': 'mrd', 'rresp': 'mrresp',
      'rvalid': 'mrv', 'rready': 'mrr'}
for k, v in mp.items():
    s = s.replace('.s_' + k + '(' + k + ')', '.s_' + k + '(' + v + ')')
bridge = 'ot_hbm_host_cfg_cdc #(.MUT(MUT)) bridge(.s_clk(hostclk),.m_clk(clk),.rst_n(rst_n),\n'
bridge += ','.join('.s_' + k + '(' + k + ')' for k in mp) + ',\n'
bridge += ','.join('.m_' + k + '(' + v + ')' for k, v in mp.items()) + ');\n'
s = s.replace('task automatic tick;', bridge + 'task automatic htick;@(posedge hostclk);#0.5;endtask\ntask automatic tick;')
a0 = s.index('task automatic wr(')
a1 = s.index('always @(posedge clk)', a0)
s = s[:a0] + '''task automatic wr(input logic[11:0] a,input logic[31:0] d,input logic[1:0] expected,input integer skew=0,input integer stall=0,input logic[3:0] strobe=15);
 @(negedge hostclk);awaddr=a;wdata=d;wstrb=strobe;
 fork
 begin if(skew==2)repeat(2)htick();@(negedge hostclk);awvalid=1;do @(posedge hostclk);while(!awready);@(negedge hostclk);awvalid=0;end
 begin if(skew==1)repeat(2)htick();@(negedge hostclk);wvalid=1;do @(posedge hostclk);while(!wready);@(negedge hostclk);wvalid=0;end
 join
 while(!bvalid)htick();
 if(bresp!=expected)$fatal(1,"HOST_SU_CDC BRESP a=%h got=%h expected=%h",a,bresp,expected);
 repeat(stall)begin htick();if(!bvalid||bresp!=expected)$fatal(1,"HOST_SU_CDC heldBRESP");end
 @(negedge hostclk);bready=1;htick();@(negedge hostclk);bready=0;
endtask
task automatic rd(input logic[11:0] a,input logic[1:0] expected,input integer stall=0);
 reg[31:0]held;
 @(negedge hostclk);araddr=a;arvalid=1;do @(posedge hostclk);while(!arready);@(negedge hostclk);arvalid=0;
 while(!rvalid)htick();if(rresp!=expected)$fatal(1,"HOST_SU_CDC RRESP");held=rdata;
 repeat(stall)begin htick();if(!rvalid||rdata!==held||rresp!=expected)$fatal(1,"HOST_SU_CDC heldRRESP");end
 @(negedge hostclk);rready=1;htick();@(negedge hostclk);rready=0;
endtask
''' + s[a1:]
s = s.replace('HOST_SU_AXI_PASS', 'HOST_SU_CDC_PASS')
(out / 'host_su_cdc_tb.sv').write_text(s)
print(json.dumps({'source_image': str(src), 'out': str(out), 'clock_ratio': f'1200host:{a.target_mhz}target',
                  'native_start_to_present_local_edges': 3, 'native_start_to_consumer_local_edges': 4,
                  'execution_transport_stalls': 0}))
