import re,json,hashlib
from pathlib import Path
root=Path('/home/ubuntu/OpenTallas');out={'scope':'Contract discrepancy diagnosis only. No view adoption, width truncation or RTL modification.','views':{}}
for name,d in [('declared_plan45','physical/qwen_missing_phy/ot_qfd_ucie_x64_phy'),('existing_1043_lclk_Nface','physical/qwen_missing_phy/nface_tall_g5_lclk_1020/ot_qfd_ucie_x64_phy')]:
 path=root/d/'ot_qfd_ucie_x64_phy.lef';t=path.read_text();pins={}
 for m in re.finditer(r'^\s*PIN\s+(\S+)\s*\n(.*?)^\s*END\s+\1\s*$',t,re.M|re.S):
  n,b=m.groups();rec=re.search(r'RECT\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)\s+([\d.-]+)',b)
  if not rec:continue
  r=list(map(float,rec.groups()));pins[n]={'layer':re.search(r'LAYER\s+(\S+)',b)[1],'rect_um':r,'xy_um':[(r[0]+r[2])/2,(r[1]+r[3])/2]}
 out['views'][name]={'source':d,'lef_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'tx_bits':len([x for x in pins if x.startswith('tx_flit[')]),'rx_bits':len([x for x in pins if x.startswith('rx_flit[')]),'clock_reset':{n:pins.get(n) for n in ['lclk','clk','rst_n']},'all_pin_names':sorted(pins)}
a,b=out['views'].values();out['new_view_extra_pins']=sorted(set(b['all_pin_names'])-set(a['all_pin_names']))
out['actual_RTL']={'source':'rtl/physical/ot_qfd_ucie_six_five.sv','tx_rx_bits':1043,'source_sha256':hashlib.sha256((root/'rtl/physical/ot_qfd_ucie_six_five.sv').read_bytes()).hexdigest(),'six_word_block_bits':6*598,'FDI_active_beats':4,'bound_phy_has_lclk':True}
out['lost_by_truncation']=[{'beat':k,'physical_missing_bits':list(range(1039,1043)),'word':(k*1043+1039)//598,'word_bits':[(k*1043+j)%598 for j in range(1039,1043)]} for k in range(3)]
out['possible_1039_repack']='Capacity permits3588bits in3*1039+471 acrosssame4beats, but changes packing/valid/CRCpad indices and requires exactlockstep+mutant+nativecalendar model. No suchchange made; first resolvewhetherdeclaredviewpointerisstale.'
Path('/tmp/qcclock0336/ucie_view_contract.json').write_text(json.dumps(out,indent=2)+'\n')
print({k:{n:v[n] for n in ['tx_bits','rx_bits','clock_reset']} for k,v in out['views'].items()});print(out['new_view_extra_pins']);print(out['lost_by_truncation'])
