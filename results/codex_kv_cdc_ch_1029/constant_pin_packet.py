#!/usr/bin/env python3
import hashlib,json,re,sys
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
k=root/'kits/qkd_hr_cdc_pc__319.68x319.68'
f=json.loads((k/'freeze.json').read_text());pins=json.loads((k/'pins.json').read_text())
np=k/'run/results/asap7/hc_qkd_hr_cdc_pc__319_68x319_68/base/1_2_yosys.v';s=np.read_text()
sp=root/'rtl/qkd_hr_cdc_pc/qkd_hr_cdc_pc.sv';sv=sp.read_text();tx=sv[sv.index(' u_tx ('):]
inp=re.search(r'\.i_d\(\{(.*?)\}\),',tx,re.S).group(1).split(',')
assert len(inp)==546 and all(x.strip()=='1'+chr(39)+'b0' for x in inp[:18])
rows=[]
for bit in range(528,546):
 pin=next(x for x in pins if x.get('bus')=='u_tx__o_d' and x.get('bit')==bit)
 pat=r'  (BUFx\w+) (\S+) \(\s*\.A\((\S+)\),\s*\.Y\(u_tx__o_d\['+str(bit)+r'\]\)\s*\);'
 m=re.search(pat,s);assert m,(bit,'buffer missing');master,cell,net=m.groups()
 m2=re.search(r'  (TIELOx\w+) (\S+) \(\s*\.L\('+re.escape(net)+r'\)\s*\);',s);assert m2,(bit,'TIELO missing')
 rows.append(dict(pin=f'u_tx__o_d[{bit}]',value=0,buffer=cell,buffer_master=master,const_net=net,tielo=m2[2],tielo_master=m2[1],physical=pin))
packet=dict(status='PROPOSED_CANONICAL_REMOVAL_NOT_APPLIED',source_commit=f.get('source_commit'),plan_inst=f['plan_inst'],pins_file=f['pins_file'],
 proposed_core_port=['u_tx__o_d',527,0],old_core_port=['u_tx__o_d',545,0],pin_count_before=len(pins),pin_count_after=len(pins)-18,
 original_gate=dict(shared_total=22,control_shared=4,constant_reserved_shared=18),
 source_constant_proof=dict(source=str(sp),sha256=hashlib.sha256(sv.encode()).hexdigest(),tx_leaf_width=546,top_input_payload_bits=528,prefix_zero_bits=18,qualification='transmitted valid words; initial invalid data is not an interface value'),
 physical_proof=dict(netlist=str(np),sha256=hashlib.sha256(s.encode()).hexdigest(),all_pins_buffered_from_tielo=True),removed_pins=rows,
 neighbour=dict(parent_type='kv3_hub_Wi',producer='host__qkd_hr_cdc_pc.u_tx__o_d',producer_bits=[528,545],signal='qkd_host_phy_cdc5.phy_tx_d[545:528]',consumer='host__qkd_hr_phy_adp_4.c_d[33:16]',consumer_type='qkd_hr_phy_adp',consumer_port_width=128,type_instances=8,elab_basis=str(root/'elab/host_elab.json')),
 impact=['CDC_PC physical pin file/core_json port_decl and pin_class need coherent updates; keep all528 payload bits, valid, credit, fault, resets, clock unchanged.',
 'Parent hub_Wi core binding must regenerate together with CDC_PC wrapper. Declaring18 pins dead or waiving face_guard is not the proposal.',
 'Adapter slice4 input c_d[33:16] is reserved zero in this instance, but qkd_hr_phy_adp is reused8 times and those positions carry payload in other instances. Narrowing the common adapter type globally would be wrong.',
 'A die-owner-approved coherent adapter/bind delta or a distinct specialized adapter type must resolve those18 inputs; deleting only the producer pins would leave open/constant stub inputs. Do not apply an ad-hoc tie class.',
 'Regenerate pins/kit/clock sink census and parent bind/portbind after approval; do not modify current event23 during this proposal.'],
 cycles_added=0,clock_or_outline_change_proposed=False)
(out/'cdc_pc_constant18.json').write_text(json.dumps(packet,indent=1)+'\n')
with open(out/'cdc_pc_constant18.tsv','w')as h:
 h.write('pin\tvalue\tx_um\ty_um\tface\tlayer\ttielo\tbuffer\n')
 for r in rows:
  p=r['physical'];h.write(f"{r['pin']}\t0\t{p['x']}\t{p['y']}\t{p['face']}\t{p['layer']}\t{r['tielo']}\t{r['buffer']}\n")
print('PROPOSED18 exact constant pins',len(pins),'->',len(pins)-18,'; no plan edits')
