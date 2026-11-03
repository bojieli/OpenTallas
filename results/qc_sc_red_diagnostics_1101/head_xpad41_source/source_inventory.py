from pathlib import Path
import json,re,hashlib
P=Path(__file__).parent;T=Path('/srv/opentallas-scratch/claude/codex-head-typed70-0248');S=Path('/srv/opentallas-scratch/claude/head-ld-source-1102');m=json.load(open(T/'subject/lec/gold.aliases.json'))['modules']['lec_top'];s=(S/'1_2_yosys.v').read_text();dr={}
for n,c in m['cells'].items():
 for port,bs in c['connections'].items():
  if c.get('port_directions',{}).get(port)=='output':
   for i,b in enumerate(bs):dr[b]=(n,c,i)
def goldbit(name):
 ix=0
 if name not in m['netnames']:name,z=name.rsplit('[',1);ix=int(z.rstrip(']'))
 Q=m['netnames'][name]['bits'][ix];cell,c,i=dr[Q];D=c['connections']['D'][i];_,dc,j=dr.get(D,('',{},0))
 return {'Qbit':Q,'type':c['type'],'CLK':c['connections'].get('CLK'),'async_reset':c['connections'].get('ALOAD'),'reset_value':c['connections'].get('AD',[None]*len(c['connections']['Q']))[i],'enable_pin':c['connections'].get('EN'),'Dbit':D,'Droot_type':dc.get('type'),'Droot_cell':dr.get(D,('',{},0))[0],'source':c.get('attributes',{}).get('src')}
def mapped(name):
 pattern=lambda n:r'^\s*(\w+)\s+\\'+re.escape(n)+r'(\$_[^\s]*)\s*\((.*?)\n\s*\);'
 match=re.search(pattern(name),s,re.M|re.S);original=name;alias_bit=None
 if not match:
  gn='u_dut.'+name;ix=0
  if gn not in m['netnames']:gn,z=gn.rsplit('[',1);ix=int(z.rstrip(']'))
  alias_bit=m['netnames'][gn]['bits'][ix]
  for an,entry in m['netnames'].items():
   if not an.startswith('u_dut.'):continue
   for ai,bit in enumerate(entry['bits']):
    if bit!=alias_bit:continue
    candidate=an.removeprefix('u_dut.')+('['+str(ai)+']'if len(entry['bits'])>1 else'')
    match=re.search(pattern(candidate),s,re.M|re.S)
    if match:name=candidate;break
   if match:break
 assert match,original
 return {'requested_logical_name':original,'mapped_instance':name+match[2],'gold_Q_alias_bit_if_renamed':alias_bit,'master':match[1],'ports':{p:v.strip()for p,v in re.findall(r'\.(\w+)\((.*?)\)',match[3])}}

old=json.load(open(T/'subject/lec/lec.json'));rows=[x for x in old['failing']if x['cone_unmatched_keys']];out=[]
for row in rows:
 p=row['point'];native=mapped(p.removeprefix('ff:u_dut.'));g=goldbit(p.removeprefix('ff:'));assert native['ports'].get('CLK')=='clk'
 if '.u_wtx.'in p:
  bit=int(p.split('[')[-1].rstrip(']'));hold=goldbit('u_dut.u_core.u_wtx.g_multi.hold['+str(bit)+']')
  role={'class':'UNRESET_TAIL_STORAGE_INITIAL_AND_LIFETIME','wire':'m_rx_o['+str(bit)+']','beat0_field':'realheader+BEST/bodybit'+str(bit),'beat1_field':'zero-padding wordbit'+str(62+bit),'word_W':110,'N':2,'payload_P':62,'control_reset':'u_wtx owe/nxt/vb/bi/fault reset rn=r_rx; datahold/oq_p noreset','write_lifetime':'holdpad startsarbitrary;start writes0;owe shift62writes0; otherwiseholds. oq_p readsoldhold on!start, includingidlebeforefirstwrite.','valid_lifetime':'Afterpostreset firststart, owedvalidbeat1tailis0; owe1/holdpad1 isunreachableafterthatwrite, although presentininductioncut.','macro_cause':False,'hold_primitive':hold,'contract':'Validbeats specifyzerotail; payloadstorage unreset. Rawidle payload beforefirstword isnotdeclaredzero byIDLE_ZERO0.'}
 else:
  field=p.split('.u_ep.')[-1];kind='pace'if field.startswith('pace')else field
  equations={'pace':'iflaunch:pace-PCOST+PNUM; elseif!pace_ok:pace+PNUM; elsehold','pace_ok_r':'iflaunch:pace_ok_launch; elseif!pace_ok:pace_ok_inc; elsehold','pv':'rr_ok0?1:p_take?0:pv','pnak':'rr_ok0?(rr_nak0|(pv&&!p_take&&pnak)):p_take?0:pnak','fault':'fault || (priority_fault_n !=0)'}
  eq=equations['pace_ok_r'if field=='pace_ok_r'else kind]
  role={'class':'MASKED_FRONTEND_LITERAL_X_FULLY_DEFINED_RTL','field':field,'source_equation':eq,'reset_role':'rst_v7 forpace/pace_ok; rst_v0 forpv/pnak; rst_v8 forfault. Native/sourcedetailsabove preserve actualreset values.','macro_cause':False,'literal_X_policy_change_needed':False,'diagnosis':'Syntactic temporaryXarms unreachable underconsistentselectors; actualnative mismatchtracks missingcohortcutrelations, not intentionalinvalid-cycle X.'}
 out.append({'point':p,'original_unmatched':row['cone_unmatched_keys'],'native_support_count':row['cone_support_count'],'gold':g,'mapped':native,'roles':role,'current_snapshot_verdict':'DIFFERS_UNCHANGED'})
files=[T/'subject/lec/gold.aliases.json',T/'subject/lec/hyp.json',S/'1_2_yosys.v',S/'rtl/ot_s81ph_link_ep_safe4.sv',S/'rtl/ot_s81hd_beat_link.sv',S/'rtl/ot_s81hd_mesh_ep_core.sv']
result={'scope':'EXACT_41_SOURCE_DRIVER_ABI_INVENTORY_ONLY_NO_PROOF_MASK_HINT_OR_JOB','source_sha256':{str(f):hashlib.sha256(f.read_bytes()).hexdigest()for f in files},'gold_X_points':27,'unreset_tail_points':14,'current_word_ABI':{'word':'{ep_fault[11:0],copy,header+BEST[96:0]}','word_width':110,'port':'m_rx_o[63:0]={bi,vb,pay[61:0]}','beat0':'word0..61','beat1':'word62..109 +14zero-tailbits110..123','latency_and_fault_policy':'existing beat contract unchanged','warning':'Portbits48..61 areREALDATA inbeat0; neverblanketmask orzero them.'},'rows':out}
(P/'source41_inventory.json').write_text(json.dumps(result,indent=1)+'\n');print('sourcepoints',len(out),'goldX27/tail14, all mappedCLKclk')
