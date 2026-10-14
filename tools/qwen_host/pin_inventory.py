#!/usr/bin/env python3
"""Candidate-placement ABI inventory; all sizes remain unverified requests."""
import ast,hashlib,json,re
from pathlib import Path
root=Path(__file__).resolve().parents[2]
base=root/'rtl/qwen_sys/host_20261013'
slot=json.loads((root/'physical/qkd_host_integration/slot_request.json').read_text())
params=dict(NSLOT=1,SB=1,NW=18,PLB=13,AW=24,NCNT=16,NL=6,ND=8)
def value(s):
 tree=ast.parse(s,mode='eval')
 allowed=(ast.Expression,ast.Constant,ast.Name,ast.Load,ast.BinOp,ast.Add,ast.Sub,ast.Mult,ast.Div,ast.FloorDiv,ast.LShift,ast.RShift,ast.UnaryOp,ast.USub)
 assert all(isinstance(x,allowed) for x in ast.walk(tree)),s
 return int(eval(compile(tree,'port width','eval'),{'__builtins__':{}},params))
def ports(name,path):
 s=re.sub(r'//[^\n]*|/\*.*?\*/','',path.read_text(),flags=re.S)
 m=re.search(r'\bmodule\s+'+name+r'\b',s);assert m,name
 h=s[m.end():s.index(');',m.end())];h=h[h.index('input'):]
 out=[];direction=None;width=1
 for entry in h.split(','):
  entry=entry.strip();match=re.match(r'(input|output|inout)\s*(?:(?:wire|reg|logic)\s*)?(?:\[([^:]+):([^\]]+)\]\s*)?(\w+)$',entry)
  if match:
   direction,hi,lo,n=match.groups();width=abs(value(hi)-value(lo))+1 if hi else 1
  else:
   assert re.fullmatch(r'\w+',entry), (name,entry)
   n=entry
  clk='ck'
  if name in ['qkd_host_if_pins','qkd_host_csr_pins','qkd_host_rst_pins','qkd_host_rx_pad']:clk='clk'
  if name=='qkd_ctrl_pc_host' and n in ['ci','co','ki','ko','pi','po','hrst','pc','pll_hbm']:clk='pll_hbm'
  if name=='qkd_host_visibility_fence' and n in ['in_v','in_d','in_cr','out_v','out_d','out_cr','landed_debug','fault']:clk='clk_h'
  special=n in ['ck','clk','pll_hbm','rst_n','rsi','hrst','por_n']
  out.append(dict(name=n,direction=direction,width=width,registered_domain=clk,seam='CLOCK_RESET' if special else ('CAPTURED_INPUT' if direction=='input' else 'REGISTERED_OUTPUT')))
 return out
masters=[]
for x in slot['children']:
 name=x['master'];p=root/x['source'];item={k:v for k,v in x.items() if k not in ['sha256','role']};item.update(source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),ports=ports(name,p));
 if name=='qkd_host_rx_class':item['params']={'STRAPPED':1}
 masters.append(item)
for name,count,wh in [('qkd_host_if_pins',4157,[129.6,172.8]),('qkd_host_csr_pins',1175,[86.4,86.4]),('qkd_host_rst_pins',103,[43.2,64.8]),('qkd_host_ctl_pins',1292,[64.8,108])]:
 p=base/f'{name}.sv';masters.append(dict(master=name,source=str(p.relative_to(root)),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),flop_bits=count,outline_request_um=wh,outline_status='UNVERIFIED_REQUEST_NOT_ROUTED',clock_entries=['ck' if name.endswith('ctl_pins') else 'clk'],instances_per_die=1,ports=ports(name,p),params=({'NSLOT':1,'MODE':0,'ENG_CTX':1,'NW':18,'PLB':13,'CTX_MAX':8192,'AW':24,'KVW':1024,'FMT':1,'PB_VALID_ONLY':1,'PB_READ_PIPE':2} if name=='qkd_host_if_pins' else ({'NL':6,'ND':8} if name=='qkd_host_rst_pins' else {}))))
# Existing CDC master binds actual W546 PIPE2 behavior; view/placement owner IO.
masters.append(dict(master='qfd_xf_ch546',source='rtl/physical/ot_qwen_die_cdc_ch.sv',params={'W':546,'PIPE':2},outline_request_um=[90.72,129.6],outline_status='IO_N2_GATE_PASS_SUBMITTED_HOST_INSTANCE_PLACEMENT_UNPROVEN',source_revision='560d99bef',clock_entries=['wck','rck'],instances_per_die=2,ports=[dict(name=n,direction=d,width=w,registered_domain=c,seam=t) for n,d,w,c,t in [('wck','input',1,'wck','CLOCK'),('rck','input',1,'rck','CLOCK'),('rst_n','input',1,'both','RESET'),('i_v','input',1,'wck','CAPTURED_INPUT'),('i_d','input',546,'wck','CAPTURED_INPUT'),('i_cr','output',1,'wck','REGISTERED_OUTPUT'),('w_fault','output',1,'wck','REGISTERED_OUTPUT'),('o_v','output',1,'rck','REGISTERED_OUTPUT'),('o_d','output',546,'rck','REGISTERED_OUTPUT'),('o_cr','input',1,'rck','CAPTURED_INPUT'),('r_fault','output',1,'rck','REGISTERED_OUTPUT')]]))
p=Path('/home/ubuntu/wt/r3b-io/rtl/physical/ot_qwen_romio_slots.sv');masters.append(dict(master='qfd_link_adp512',source='rtl/physical/ot_qwen_romio_slots.sv',source_checkout=str(p.parent.parent.parent),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),ports=ports('qfd_link_adp512',p),instances_per_die=1,physical_mapping='One required HOST_PHY adapter per same-die physical type; runtime board/control attachment and candidate placement pending',outline_request_um=[237.6,777.6],outline_status='EXISTING_LIVE_JOB_GEOMETRY_HOST_SLOT_UNPROVEN',clock_entries=['ck'],actual_body_params={'W':1024,'RXD':512,'NG':8,'PINREG':1},flop_census='IO_OWNER_MEASURED_REPORT_REQUIRED'))
p=base/'qkd_ctrl_pc_host.sv';masters.append(dict(master='qkd_ctrl_pc_host',source=str(p.relative_to(root)),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),instances_per_die=128,clock_entries=['ck','pll_hbm'],outline_request_um=[246.24,172.8],outline_status='VARIANT_UNVERIFIED_OLD_CONTROLLER_GEOMETRY_ONLY',ports=ports('qkd_ctrl_pc_host',p)))
links=[]
def link(a,b,w,c):links.append(dict(source=a,destination=b,bits=w,clock_family=c))
for st in range(4):
 link(f'host.map.out[{st}]',f'stack{st}.pc0.station.fi',291,'core')
 link(f'stack{st}.pc0.station.co',f'host.map.out_cr[{st}]',32,'core')
 link(f'stack{st}.pc0.station.ao',f'host.ack_sum.acks[{st}]',32,'core')
 for pc in range(32):
  here=f'stack{st}.pc{pc}';
  if pc<31:
   next_node=f'stack{st}.pc{pc+1}'
   link(here+'.station.fo',next_node+'.station.fi',291,'core');link(next_node+'.station.co',here+'.station.ci',32,'core');link(next_node+'.station.ao',here+'.station.ai',32,'core');link(next_node+'.station.fault_o',here+'.station.fault_i',1,'core')
  link(here+'.station.host_es',here+'.static.host_es',288,'core');link(here+'.static.host_cr',here+'.station.host_cr',1,'core');link(here+'.static.host_ack',here+'.station.host_ack',1,'core');link(here+'.static.fault',here+'.station.host_fault',1,'core')
  link(here+'.emb_landing.es',here+'.static.land_es',288,'core');link(here+'.static.land_er',here+'.emb_landing.er',261,'core')
  link(here+'.static.ctrl_es',here+'.controller.es',288,'core');link(here+'.controller.er',here+'.static.ctrl_er',261,'core');link(here+'.controller.completion_v/we',here+'.static.completion_v/we',2,'core');link(here+'.KV_CDC.ho',here+'.controller.ci',319,'hbm');link(here+'.controller.co',here+'.KV_CDC.hi',294,'hbm');link(here+'.KCMD.pi',here+'.controller.ki',33,'hbm');link(here+'.controller.ko',here+'.KCMD.po',33,'hbm');link(here+'.controller.po',here+'.PHY.pi',328,'hbm');link(here+'.PHY.po',here+'.controller.pi',289,'hbm')
link('host.ack_sum.ack_n','host.map.ack_n',8,'core')
link('host.QM.ing','host.map.ing',290,'core');link('host.map.ing_cr','host.QM.o_cr',1,'core')
link('HOST_PHY.adapter.DATA1024','host.rx_pad.in_d',1024,'serdes')
link('host.rx_pad.out_d','host.rx_CDC.i_d',546,'serdes');link('host.rx_CDC.o_d[527:0]','host.rx_class.rx_d',528,'core')
link('host.tx_class.tx_d+zero18','host.tx_CDC.i_d',546,'core');link('host.tx_CDC.o_d+zero478','HOST_PHY.adapter.DATA1024',1024,'serdes')
link('host.rx_class.host_d','host.AXI.rx_d',512,'core');link('host.AXI.tx_d','host.tx_class.host_d',512,'core');link('host.rx_class.ctrl_d','host.CTRL.rx_d',512,'core');link('host.CTRL.tx_d','host.tx_class.ctrl_d',512,'core')
for n in ['s_awvalid','s_awready','s_awaddr','s_wvalid','s_wready','s_wdata','s_wstrb','s_bvalid','s_bready','s_bresp','s_arvalid','s_arready','s_araddr','s_rvalid','s_rready','s_rdata','s_rresp']:
 spec=next(p for m in masters if m['master']=='qkd_host_axi_packet' for p in m['ports'] if p['name']==n)
 a,b=('host.AXI.'+n,'host.CSR.'+n) if spec['direction']=='output' else ('host.CSR.'+n,'host.AXI.'+n)
 link(a,b,spec['width'],'core')
for n in ['m_arvalid','m_arready','m_araddr','m_rvalid','m_rready','m_rdata','m_rresp','m_rlast','m_awvalid','m_awready','m_awaddr','m_wvalid','m_wready','m_wdata','m_wstrb','m_bvalid','m_bready','m_bresp']:
 spec=next(p for m in masters if m['master']=='qkd_host_axi_packet' for p in m['ports'] if p['name']==n)
 a,b=('host.AXI.'+n,'host.HOST.'+n) if spec['direction']=='output' else ('host.HOST.'+n,'host.AXI.'+n)
 link(a,b,spec['width'],'core')
link('host.HOST.eng_req','host.CTL.req',61,'core');link('host.CTL.res','host.HOST.eng_res',120,'core')
link('host.CTRL.tk8','host.CTL.tk',744,'core');link('host.CTRL.kst8','host.CSR.die_kst',80,'core');link('host.CTRL.boot8','host.RESET.boot_done/ok',16,'core');link('host.CTL.hc','host.CTRL.cmd_hc',182,'core')
# Above bundle labels summarize grouped channels; exact pin-level endpoint
# names/widths are in master ports and RTL; no scalar ready is implied here.
d=dict(status='UNVERIFIED_CANDIDATE_PLACEMENT_INPUT_NOT_DIE_CONTRACT',parent_fit='UNPROVEN_NO_LEGACY_FRAME_FIT_ASSERTION',prompt_leaf='SOURCE_PENDING_HELPER: originalprompt combinational ECC output/request decode requires newcapturedrequest/registeredresponse pinleaf; macro8192x18storage physical1024x256, latency/outline/census pending actualbind bench',masters=masters,connectivity=links,clock_delivery='Separate entry per child; core family synchronous and insertion-compensated, PHY crossings only via own two W546 CDC leaves',static_instances=[dict(stack=s,pc=p,station_clock=f'ck_station[{s*32+p}]',arbiter_clock=f'ck_static[{s*32+p}]',controller_hclk=f'pll_hbm[{s*32+p}]',controller_ck=f'ck_ctrl[{s*32+p}]') for s in range(4) for p in range(32)],pc_pocket_candidate=slot['pc_frame_candidate'],QM='NEW NATIVE RTL VIEW AND CLK_I PARTITION REQUIRED; HISTORICAL CHILD_LINT FAIL AND NO BOUNDARY CLK_I REF')
(root/'physical/qkd_host_integration/pin_inventory.json').write_text(json.dumps(d,indent=2)+'\n')
print(f'WROTE {len(masters)} master ABIs, {len(links)} connections, 128 local PC sites')
