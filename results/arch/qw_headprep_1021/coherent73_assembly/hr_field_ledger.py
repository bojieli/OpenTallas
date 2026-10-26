#!/usr/bin/env python3
"""Source-bound HR field/producer offsets. No GEN or direct event timestamp claim."""
import hashlib,json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent/'HR_FIELD_LEDGER.json'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 native_path=ROOT/'rtl/qwen_dv/headprep13/native32/qfd_tt_ctlm_dv_hp13_rrloc_native32.sv'
 lp_path=ROOT/'results/arch/qw_headprep_1021/tt_lp_recipe/generated/qfd_tt_ctlm_dv_lpf_hp13_lp_record.json'
 nb=native_path.read_bytes();lb=lp_path.read_bytes();n=nb.decode();lp=json.loads(lb)
 assert sha(nb)=='66cd44bf35e5bbb8a3f2cf9bf0698ca9c75f7e2f676dcf4ee2727c46627eb9da'
 assert sha(lb)=='468a9704f3fb5f0df53e8a4e7d0d89e860fdee6597d5b052f2f800ec67f9807f'
 # Source-fixed native uses scalar named nets; parse only these exact output lists.
 hr=re.search(r'^assign hr = \{([^}]+)\};',n,re.M).group(1).split(',');assert len(hr)==453
 hr={452-i:x for i,x in enumerate(hr)}
 call=re.search(r'\bu_hr\(([^;]+)\);',n).group(1)
 cmd=re.search(r'\.rom_cmd\(\{([^}]+)\}\)',call).group(1).split(',');assert len(cmd)==380
 cmd={379-i:x for i,x in enumerate(cmd)}
 assert '.ck_head(n_3160)'in call and 'assign n_3160 = ck_hr;'in n
 reverse={wire:bit for bit,wire in cmd.items()};assert len(reverse)==380
 observed={bit:reverse[hr[bit]]for bit in range(73,453)}
 # Field table is the observed bijection in this exact native, with names checked
 # against the source-bound ASBUILT0 pack dependency; no extra register is inserted.
 names=[('go',379,379,0,0),('nout',378,361,18,1),('tiles',360,343,36,19),('k',342,325,54,37),('wsrc',324,324,55,55),('wbase',323,300,79,56),('ts',299,276,103,80),('ks',275,252,127,104),('js',251,228,151,128),('xbase',227,204,175,152),('xks',203,180,199,176),('xjs',179,156,223,200),('xcs',155,132,247,224),('jsh',131,129,250,248),('split',128,125,254,251),('wcs',124,101,278,255),('round',100,100,279,279),('obase',99,76,303,280),('ots',75,52,327,304),('ojs',51,28,351,328),('mmode',27,27,352,352),('oen',26,26,353,353),('amax',25,25,354,354),('rmax',24,24,355,355),('mbase',23,0,379,356)]
 fields=[]
 for name,hi,lo,chi,clo in names:
  assert hi-lo==chi-clo
  for b in range(lo,hi+1):assert observed[b+73]==clo+(b-lo),(name,b,observed[b+73])
  fields.append({'field':name,'hr_bits':[hi+73,lo+73],'head_rom_cmd_bits':[chi,clo],'post_head_source_capture_edges':0,'producer':'u_hr.rom_cmd (already registered child output)','LP_producer_offset':lp['compiler']['child_offset_edges']['u_hr'],'LP_hr_output_offset':lp['compiler']['output_port_offset_edges']['hr'],'knownness':'EXACT_NATIVE_DIRECT_NET_BIJECTION_AND_EQUAL_LP_OFFSETS'})
 # Every low arm bit has its own actual final Q; the D is the source-scheduler
 # register output. This is a real capture edge, unlike parallel source Q copies.
 flops={}
 for m in re.finditer(r'qfd_bmath_dff_pn0 #\(\.ID\(0\)\) (u_\d+)\(([^;]+)\);',n):
  ports=dict(re.findall(r'\.([A-Za-z]+)\(([^()]+)\)',m.group(2)))
  if 'Q'in ports:flops[ports['Q']]=dict(instance=m.group(1),**ports)
 arm=[]
 for bit in range(1,73):
  f=flops[hr[bit]];src=flops[f['D']]
  assert f['C']==src['C']=='n_3160'
  assert f['Q']!=src['Q']and f['D']==src['Q']
  arm.append({'hr_bit':bit,'arm_bit':bit-1,'source_register':src,'extra_hr_capture':f})
 valid=flops[hr[0]];hv=flops[valid['D']];assert hv['D']=="1'b1"and valid['C']==hv['C']=='n_3160'
 po=lp['compiler']['child_offset_edges']['u_go'];oo=lp['compiler']['output_port_offset_edges']['hr'];assert po==oo==6
 result={'status':'SOURCE_FIELD_LEDGER_NOT_GEN_ROUTE_AUTHORITY','native_sha256':sha(nb),'LP_record_sha256':sha(lb),'clock':'ck_hr via exact assign n_3160; hardchild ck_head=n_3160','groups':{'arm72':{'hr_bits':[72,1],'producer_checkpoint':'u_go.u_xpf_schedule.xpf registered scheduler output; native source Q rows below','producer_offset_edges':po,'output_offset_edges':oo,'extra_flat_hr_capture_edges':1,'source_local_candidate_edges':1+(oo-po),'basis':'1 actual final HR capture + (6 output -6 producer) =1; source register counts, not direct event timestamps','native_bit_rows':arm},'valid1':{'hr_bits':[0,0],'source_checkpoint':'startup hv register constant1 after reset','native_hv_source':hv,'native_hr_capture':valid,'post_hv_capture_edges':1,'reset_startup_constant_capture_chain_edges':2,'scope':'valid startup separate from ARM payload; not an extra steady-state programme edge'},'head380':{'hr_bits':[452,73],'producer_checkpoint':'u_hr.rom_cmd actual hardchild output, already registered within H16ZA','producer_offset_edges':lp['compiler']['child_offset_edges']['u_hr'],'output_offset_edges':oo,'extra_post_source_capture_edges':0,'field_count':len(fields),'fields':fields,'bijective_all380':True,'scope':'Field permutation/direct nets add0 post-head edges; internal hardchild issue-to-rom_cmd latency is not inferred here and is not a pin-copy edge.'}},'register_copy_law':'A new edge is counted only when an output Q captures a prior source Q (arm rows D==sourceQ). Same-clock parallel copies with identical D are not successive stages. Upper380 uses actual same net at u_hr.rom_cmd and hr output, so no parent capture exists after that checkpoint.','functional_support':{'receipt':'results/arch/qw_headprep_1021/rrloc_projection/realcalendar_native/REPRO.json','bench':'samefolder/tb_hp13_native.sv line214 compares all453 HR bits against flat delay6 in both existing CALR10 modes','scope':'Recorded component native/flat phase equivalence only; no arm/source event timestamp or full selected73 schedule/GEN proof'},'still_unknown':['Actual full GEN TT.hr-to-slice field transport ages and fixed constructionXPF21 reconciliation','Any new RRrole/RRloc mapping/view/clock relationship','Absolute H16 command-issue-to-rom_cmd event age, not priced by this post-source identity proof'],'guard':'482 unconditional fixed-native gen_params refusal RETAINED until owner/publisher review of all required source groups and route-law integration; this ledger does not assign measured ages.'}
 OUT.write_text(json.dumps(result,indent=2)+'\n');print(result['status'],'72 actual capture rows;380 exact bijective source bits;25 field groups;valid startup2')
if __name__=='__main__':main()
