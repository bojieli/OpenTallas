from pathlib import Path
import re,json,hashlib
out=Path(__file__).resolve().parent
native=Path('/srv/opentallas-scratch/claude/wt/codex-ft-obstacle-union-2149/results/hbm_storeA_sourceproof_intake_0030/native')
orig=(native/'ot_hgi_su_lgroup2.sv').read_text()
model=dict(status='DEFAULT_OFF_SOURCE_PROPOSAL_NO_PHYSICAL_RELEASE',source_macro_count=32,regional_macro_count=[8,8,8,8],memory_bits=32*256*256,
 producer_data_bits_per_cycle=2048,producer_addr_bits_per_cycle=120,producer_group_bits_per_cycle=16,producer_expect_scalar_bits_per_cycle=16,
 regional_capture_FF=4*(2048+120+16+16),regional_capture_fields=dict(data=2048,addr=120,group=16,expect=8,scalar=8),
 added_logical_cycles=0,source_mask='actualSOURCE13 constant64ones, not unconstrained standaloneABI equivalence',
 write_priority='exact ascending ws/word last-writer wins, collision sticky fault preserved',
 regional_capture_cost='8800strict FF copies; existing originals remain unless separate caller proof permits deletion; no global delta claimed',
 routing='4 independent2192variablebit regional input sets; necessary405 body-bound passed earlier, actual cell/pin/localglobalD/clockPG unmeasured',
 holds=['parent producerDpaths/VMdates/resetSTART/currentnativeview not joined','sourceoffdefault only','nativeG0C/proof/GEN/physical intakes separate'])
(out/'MODEL.json').write_text(json.dumps(model,indent=1)+'\n')
# Exact selected generic read/memory/fault behavior retained. Only sector write selection is split.
s=orig.replace('module ot_hgi_su_lgroup2 #(', 'module ot_hgi_su_lgroup2_regional_write #(')
s=s.replace('input  wire [NS-1:0]     sw_v,','input  wire [2*NS-1:0]     sw_v,')
s=s.replace('input  wire [NS*LWB-1:0] sw_addr,','input  wire [2*NS*LWB-1:0] sw_addr,')
s=s.replace('input  wire [NS*8-1:0]   sw_mask,','input  wire [2*NS*8-1:0]   sw_mask,')
s=s.replace('input  wire [NS*256-1:0] sw_d,','input  wire [2*NS*256-1:0] sw_d,')
start=s.index('    reg  [N-1:0] b_we;')
end=s.index('    reg [N-1:0] rq_q,',start)
writer='''    // Exact selected SOURCE13 StoreA specialization: NLW0 and s1_v0.
    // Each half receives its own already-captured same-edge source fields.
    initial if(N!=16 || M!=16 || LWB!=15 || AW!=24 || NS!=8 || NLW!=0 || MUT_XBAR!=0)
        $fatal(1,"regional writer requires exact selected StoreA parameters");
    wire [N-1:0] b_we;
    wire [RB-1:0] b_wa[0:N-1];
    wire [31:0] b_wd[0:N-1];
    wire [1:0] local_wcoll;
    wire wcoll=|local_wcoll;
    for(genvar region=0;region<2;region=region+1)begin:g_write_region
        reg collision;
        reg[7:0] rwe;
        reg[RB-1:0] rwa[0:7];
        reg[31:0] rwd[0:7];
        for(genvar bj=0;bj<8;bj=bj+1)begin
            assign b_we[(bj/2)*4+2*region+(bj%2)]=rwe[bj];
        end
        for(genvar bi=0;bi<8;bi=bi+1)begin
            assign b_wa[(bi/2)*4+2*region+(bi%2)]=rwa[bi];
            assign b_wd[(bi/2)*4+2*region+(bi%2)]=rwd[bi];
        end
        assign local_wcoll[region]=collision;
        always @* begin : wsel
            integer bb,ws,wj;
            reg [LWB-1:0] sb;
            sb=0; collision=0;
            for(bb=0;bb<8;bb=bb+1)begin
                rwe[bb]=0; rwa[bb]=0; rwd[bb]=0;
            end
            for(ws=0;ws<NS;ws=ws+1)if(sw_v[region*NS+ws])
                for(wj=0;wj<8;wj=wj+1)if(sw_mask[region*NS*8+ws*8+wj])begin
                    sb=sw_addr[region*NS*LWB+ws*LWB+:LWB]+wj;
                    if(sb[1]==region)begin
                        if(rwe[{sb[3:2],sb[0]}])collision=1;
                        rwe[{sb[3:2],sb[0]}]=1;
                        rwa[{sb[3:2],sb[0]}]=sb[LWB-1:LN];
                        rwd[{sb[3:2],sb[0]}]=sw_d[region*NS*256+ws*256+32*wj+:32];
                    end
                end
        end
    end
'''
s=s[:start]+writer+s[end:]
# Drop pp provenance directives from standalone extracted artifacts only.
s=re.sub(r'^`line.*$','',s,flags=re.M)
for port in ['lw','lwa','lwd','s1_v','s1_a','s1_d']:
 s,n=re.subn(r'^    input  wire[^\n]*\b'+port+r'\b[, ]*[^\n]*\n','',s,flags=re.M);assert n==1,(port,n)
(out/'ot_hgi_su_lgroup2_regional_write.sv').write_text(s)
# Proof exposes only the unchanged native source writer and proposed regional writer cones.
ref_start=orig.index('    reg  [N-1:0] b_we;');ref_end=orig.index('    reg [N-1:0] rq_q,',ref_start)
refbody=orig[ref_start:ref_end]
# Constants exactly selected by StoreA m0/m1 in SOURCE13; no s1 or lane writes.
prefix='''module writer_gold(input [7:0] sw_v,input [119:0] sw_addr,input [63:0] sw_mask,input [2047:0] sw_d,
 output [15:0] we,output[175:0] wa,output[511:0] wd,output collision);
 localparam N=16,NS=8,LWB=15,LN=4,RB=11,NLW=0,NL=1,AW=24,NROT=1,M=16,MUT_XBAR=0;
 wire[0:0]lw=0;wire[23:0]lwa=0;wire[31:0]lwd=0;
 wire s1_v=0;wire[14:0]s1_a=0;wire[31:0]s1_d=0;
 integer b;
 function automatic[3:0]cbank(input integer l,input integer k);cbank=0;endfunction
'''
suffix='''assign we=b_we;assign collision=wcoll;
 for(genvar i=0;i<16;i=i+1)begin assign wa[11*i+:11]=b_wa[i];assign wd[32*i+:32]=b_wd[i];end
 endmodule
'''
gold=prefix+refbody+suffix
new=prefix.replace('writer_gold','writer_regional').replace('[7:0] sw_v','[15:0] sw_v').replace('[119:0] sw_addr','[239:0] sw_addr').replace('[63:0] sw_mask','[127:0] sw_mask').replace('[2047:0] sw_d','[4095:0] sw_d')+writer+suffix
(out/'writer_cones.sv').write_text(re.sub(r'^`line.*$','',gold+'\n'+new,flags=re.M))
(out/'source_identity.json').write_text(json.dumps(dict(original_lgroup_sha256=hashlib.sha256(orig.encode()).hexdigest(),selected_profile='N16 M16 LWB15 AW24 NS8 NLW0 MUT0 s1_v0',original_files_intact=True),indent=1)+'\n')
top=(native/'ot_hnx_sfu_store_a__da81d76763c9.sv').read_text()
oldname='ot_hnx_sfu_store_a__da81d76763c9'
newtop=top.replace('module '+oldname+' (','module ot_hnx_sfu_store_a_regional4 (',1)
removed={'store0_sw_addr':120,'store0_sw_d':2048,'store0_sw_mask':64}
removed.update({'comb'+str(i)+'_A':1 for i in range(32,40)})
removed.update({'comb'+str(i)+'_A':2 for i in range(80,88)})
for name,width in removed.items():
 pat=r'^    input wire \['+str(width-1)+r':0\] '+name+r',\n'
 newtop,n=re.subn(pat,'',newtop,flags=re.M);assert n==1,(name,n)
# New public ABI: four regional variable-input sets; mask remains actual SOURCE13 all ones.
needle='    input wire [0:0] store0_clk,\n'
newtop=newtop.replace(needle,needle+'''    input wire [8191:0] region_data,
    input wire [479:0] region_addr,
    input wire [63:0] region_group,
    input wire [31:0] region_stage_v,
''',1)
body='''    wire[119:0]store0_sw_addr=region_addr[119:0];
    wire[2047:0]store0_sw_d=region_data[2047:0];
    wire[63:0]store0_sw_mask=64'hffffffffffffffff;
    wire[31:0]regional_sw_v;
    for(genvar r=0;r<4;r=r+1)begin:g_region_write_valid
        for(genvar b=0;b<8;b=b+1)begin:g_bank_valid
            assign regional_sw_v[8*r+b]=region_stage_v[8*r+b]&&(region_group[16*r+2*b+:2]==(r/2));
        end
    end
'''
# Old source-only aliases retain dangling extraction glue; every sector writer
# below receives its OWN regional source. No old public input is substituted.
for b in range(8):
 body+=f'    wire[0:0]comb{32+b}_A=region_stage_v[{b}];\n'
 body+=f'    wire[1:0]comb{80+b}_A=region_group[{2*b}+:2];\n'
newtop=newtop.replace('    wire n0;',body+'    wire n0;',1)
lines=[];changed=[]
for line in newtop.splitlines():
 if 'ot_hgi_su_lgroup2 #' in line:
  m=re.search(r'\) m([01]) \(',line);assert m
  group=int(m.group(1));before=line
  line=line.replace('ot_hgi_su_lgroup2 #','ot_hgi_su_lgroup2_regional_write #',1)
  # Source export uses only brace-packed literals/bitnames in these four fields.
  for port,expr in [('sw_v',f'regional_sw_v[{16*group}+:16]'),('sw_addr',f'region_addr[{240*group}+:240]'),('sw_d',f'region_data[{4096*group}+:4096]'),('sw_mask',"128'hffffffffffffffffffffffffffffffff")]:
   line,n=re.subn(r'\.'+port+r'\(\{[^}]*\}\)',f'.{port}({expr})',line);assert n==1,(port,n)
  for fixed_port in ['lw','lwa','lwd','s1_v','s1_a','s1_d']:
   line,n=re.subn(r'\.'+fixed_port+r'\(\{[^}]*\}\), ', '', line);assert n==1,(fixed_port,n)
  changed.append(dict(instance='m'+str(group),original_sha256=hashlib.sha256(before.encode()).hexdigest(),regional_sha256=hashlib.sha256(line.encode()).hexdigest(),bank_regions=[2*group,2*group+1]))
 lines.append(line)
assert len(changed)==2
newtop='\n'.join(lines)+'\n'
newtop=re.sub(r'^`line.*$','',newtop,flags=re.M)
(out/'ot_hnx_sfu_store_a_regional4.sv').write_text(newtop)
abi=[]
for direction,hi,name in re.findall(r'^    (input|output) wire \[(\d+):0\] (\w+)[,\n]',newtop,flags=re.M):abi.append(dict(direction=direction,bus=name,width=int(hi)+1))
assert sum(x['width'] for x in abi)==12552,sum(x['width'] for x in abi)
(out/'regional_ABI.json').write_text(json.dumps(dict(top='ot_hnx_sfu_store_a_regional4',ABI_bits=12552,old_ABI=6040,removed_shared_bits=sum(removed.values()),added_regional_bits=8768,ports=abi,selected_mask_ones=True,changed_writer_instances=changed,no_parent_caller_activation=True),indent=1)+'\n')
# True provider export: bridge port, then CTL port. No hierarchical-reference alias.
closure=(out.parent/'hbm_ctl_native_intake_0440/closure_ot_hgi_sfu_core_split3__ctl.sv').read_text()
def module(text,name):
 m=re.search(r'^module\s+'+re.escape(name)+r'\s*(?:#|\()',text,re.M);assert m
 e=text.index('endmodule',m.start())+len('endmodule')
 return re.sub(r'^`line.*$','',text[m.start():e],flags=re.M)
bridge=module(closure,'ot_hgi_sfu_vm_static_bridge')
bridge=bridge.replace('module ot_hgi_sfu_vm_static_bridge #','module ot_hgi_sfu_vm_static_bridge_regional_export #',1)
bridge=bridge.replace(' input wire clk,rst_n,',' output wire[151:0] storeA_meta87_D,\n input wire clk,rst_n,',1)
bridge=bridge.replace(' localparam META=', ' initial if(LWB!=15 || READ_RETURN!=88 || WRITE_RETURN!=85)$fatal(1,"exact selected StoreA calendar export required");\n localparam META=',1)
bridge=bridge.replace('  reg [META-1:0] meta[0:READ_RETURN];','  reg [META-1:0] meta[0:READ_RETURN];\n  assign storeA_meta87_D[38*g+:38]=meta[87][43:6];',1)
ctl=module(closure,'ot_hgi_sfu_core_split3__ctl')
ctl=ctl.replace('module ot_hgi_sfu_core_split3__ctl (','module ot_hgi_sfu_ctl_storeA_regional_export (\n    output wire[151:0] storeA_meta87_D,\n    output wire storeA_ctl_reset_n,',1)
ctl=ctl.replace('    wire n0;','    assign storeA_ctl_reset_n=n6;\n    wire n0;',1)
ctl=ctl.replace('ot_hgi_sfu_vm_static_bridge #','ot_hgi_sfu_vm_static_bridge_regional_export #',1)
ctl=ctl.replace(') m56 (.clk(',') m56 (.storeA_meta87_D(storeA_meta87_D), .clk(',1)
(out/'ot_hgi_sfu_ctl_storeA_regional_export.sv').write_text(ctl+'\n'+bridge+'\n'+module(closure,'ot_rst_relay')+'\n')
# Disabled exact native B113 source caller projection. All ordinary ports/logic remain.
def project_parent(parent_path,oldmodule):
    parent=parent_path.read_text()
    for name,width in [('u_u_sfucore_Q_ctl',None),('u_u_sfucore_Q_opstore_a',None)]:assert parent.count(' '+name+' (')==1,name
    ctl_match=re.search(r'ot_hgi_sfu_core_split3__ctl\s+u_u_sfucore_Q_ctl\s*\((.*?)\n    \);',parent,re.S);assert ctl_match
    ctl_call=ctl_match.group(0)
    def namedport(call,name):
     m=re.search(r'\.'+name+r'\((.*?)\)(?:,|\s*\n)',call,re.S);assert m,name
     return m.group(1)
    rr_expr=namedport(ctl_call,'u_core_procdff_66926__D')
    meta_reset=namedport(ctl_call,'rst_n')
    clk_expr=namedport(ctl_call,'clk')
    assert meta_reset=='rst_n_t22',meta_reset
    newcall=ctl_call.replace('ot_hgi_sfu_core_split3__ctl','ot_hgi_sfu_ctl_storeA_regional_export',1).replace('u_u_sfucore_Q_ctl (','u_u_sfucore_Q_ctl (\n        .storeA_meta87_D(storeA_meta87_D),\n        .storeA_ctl_reset_n(storeA_ctl_reset_n),',1)
    parent=parent.replace(ctl_call,newcall,1)
    store_match=re.search(r'ot_hnx_sfu_store_a__da81d76763c9\s+u_u_sfucore_Q_opstore_a\s*\((.*?)\n    \);',parent,re.S);assert store_match
    store_call=store_match.group(0)
    assert namedport(store_call,'store0_sw_mask')=="w_u_sfucore_Q_ctl_u_core_u_vm_stage_mask[63:0]",namedport(store_call,'store0_sw_mask')
    assert "assign stage_mask=64'hffffffffffffffff;" in bridge
    newstore=store_call.replace('ot_hnx_sfu_store_a__da81d76763c9','ot_hnx_sfu_store_a_regional4',1)
    for port in removed:
     newstore,n=re.subn(r'^        \.'+port+r'\([^\n]*\),?\n','',newstore,flags=re.M);assert n==1,(port,n)
    newstore=newstore.replace('u_u_sfucore_Q_opstore_a (','u_u_sfucore_Q_opstore_a (\n        .region_data(storeA_region_data),\n        .region_addr(storeA_region_addr),\n        .region_group(storeA_region_group),\n        .region_stage_v(storeA_region_stage_v),',1)
    parent=parent.replace(store_call,newstore,1)
    newwires='''    wire[151:0]storeA_meta87_D;
        wire storeA_ctl_reset_n;
        wire[2055:0]storeA_capture_rr_D;
    wire[2047:0]storeA_capture_payload_D;
    wire[8191:0]storeA_region_data;
        wire[479:0]storeA_region_addr;
        wire[63:0]storeA_region_group;
        wire[31:0]storeA_region_stage_v;
    '''
    # Insert before the exact CTL instance, so no fixed partition ABI changes are hidden.
    pos=parent.index('    ot_hgi_sfu_ctl_storeA_regional_export ')
    parent=parent[:pos]+newwires+f'''    assign storeA_capture_rr_D={rr_expr};
    for(genvar rb=0;rb<8;rb=rb+1)assign storeA_capture_payload_D[256*rb+:256]=storeA_capture_rr_D[257*rb+:256];
    ot_hgi_sfu_store_a_regional_capture u_storeA_regional_capture(
            .clk({clk_expr}),.ctl_reset_n(storeA_ctl_reset_n),.meta_reset_n({meta_reset}),
            .payload_D(storeA_capture_payload_D),.meta87_D(storeA_meta87_D),
            .region_data(storeA_region_data),.region_addr(storeA_region_addr),
            .region_group(storeA_region_group),.region_stage_v(storeA_region_stage_v));
    '''+parent[pos:]
    parent,n=re.subn(r'^module '+re.escape(oldmodule)+r'\b','module '+oldmodule+'_storeA_regional4',parent,count=1,flags=re.M);assert n
    (out/(oldmodule+'_storeA_regional4.sv')).write_text(parent)
    (out/(oldmodule+'_provider_event.json')).write_text(json.dumps(dict(status='DISABLED_EXACT_NATIVE_CALLER_PROPOSAL',source_caller=str(parent_path),source_sha256=hashlib.sha256(parent_path.read_bytes()).hexdigest(),new_CTL_ABI_bits=11963,extra_CTL_outputs=['storeA_meta87_D[151:0]','storeA_ctl_reset_n'],bridge_export='real declared m56 port assigned from each g_lg[g].meta[87]; no hierarchy reference from caller',data_D='same existing actual CTL u_core_procdff_66926__D parent expression',metadata_reset=meta_reset,data_reset='actual CTL n6 exported, not metadata reset alias',clock=clk_expr,mask_binding='verified actual selected64ones',new_StoreA_ABI_bits=12552,added_capture_FF=8800,existing_originals_retained=True,cycles_added=0,physical_and_full_parent_proof='NOT_RUN'),indent=1)+'\n')

for name in ['hbm_arch_q_b113','hbm_arch_q_b113__physical_v1']:
 project_parent(Path('/srv/opentallas-scratch/claude/codex-hbm-programme-move-0216/input')/(name+'.sv'),name)
# Physical native capsule includes the same-edge capture copies inside the
# SRAM body. They are not parent soft FFs hidden inside a hard obstruction.
internal=(out/'ot_hnx_sfu_store_a_regional4.sv').read_text()
header=internal[:internal.index(');')+2]
header=header.replace('module ot_hnx_sfu_store_a_regional4 (','module ot_hnx_sfu_store_a_regional4_captured (',1)
for bus in ['region_data','region_addr','region_group','region_stage_v']:
 header,n=re.subn(r'^    input wire \[\d+:0\] '+bus+r',\n','',header,flags=re.M);assert n
header=header.replace('    input wire [0:0] store0_clk,','''    input wire [0:0] store0_clk,
    input wire [2047:0] capture_payload_D,
    input wire [151:0] capture_meta87_D,
    input wire [0:0] capture_ctl_reset_n,
    input wire [0:0] capture_meta_reset_n,''',1)
ports=[n for _,_,n in re.findall(r'^    (input|output) wire \[(\d+):0\] (\w+)[,\n]',header,flags=re.M)]
wrap=header+'''
    wire[8191:0]region_data;
    wire[479:0]region_addr;
    wire[63:0]region_group;
    wire[31:0]region_stage_v;
    ot_hgi_sfu_store_a_regional_capture u_regional_capture(
       .clk(store0_clk[0]),.ctl_reset_n(capture_ctl_reset_n[0]),.meta_reset_n(capture_meta_reset_n[0]),
       .payload_D(capture_payload_D),.meta87_D(capture_meta87_D),
       .region_data(region_data),.region_addr(region_addr),.region_group(region_group),.region_stage_v(region_stage_v));
    ot_hnx_sfu_store_a_regional4 u_store(
'''
inner_ports=[n for _,_,n in re.findall(r'^    (input|output) wire \[(\d+):0\] (\w+)[,\n]',internal[:internal.index(');')+2],flags=re.M)]
wrap+=',\n'.join('        .'+n+'('+n+')' for n in inner_ports)+'\n    );\nendmodule\n'
assert sum(int(w)+1 for _,w,_ in re.findall(r'^    (input|output) wire \[(\d+):0\] (\w+)[,\n]',header,flags=re.M))==5986
(out/'ot_hnx_sfu_store_a_regional4_captured.sv').write_text(wrap)
for name in ['hbm_arch_q_b113','hbm_arch_q_b113__physical_v1']:
 f=out/(name+'_storeA_regional4.sv');text=f.read_text()
 text,n=re.subn(r'^    ot_hgi_sfu_store_a_regional_capture u_storeA_regional_capture\(.*?;\n','',text,flags=re.M|re.S);assert n==1
 for decl in ['wire[8191:0]storeA_region_data;','wire[479:0]storeA_region_addr;','wire[63:0]storeA_region_group;','wire[31:0]storeA_region_stage_v;']:
  text=text.replace('    '+decl+'\n','')
 text=text.replace('ot_hnx_sfu_store_a_regional4 u_u_sfucore_Q_opstore_a','ot_hnx_sfu_store_a_regional4_captured u_u_sfucore_Q_opstore_a',1)
 for bus in ['data','addr','group','stage_v']:
  text,n=re.subn(r'^        \.region_'+bus+r'\([^\n]*\),\n','',text,flags=re.M);assert n==1,(bus,n)
 text=text.replace('u_u_sfucore_Q_opstore_a (','''u_u_sfucore_Q_opstore_a (
        .capture_payload_D(storeA_capture_payload_D),
        .capture_meta87_D(storeA_meta87_D),
        .capture_ctl_reset_n(storeA_ctl_reset_n),
        .capture_meta_reset_n(rst_n_t22),''',1)
 f.write_text(text)
 eventfile=out/(name+'_provider_event.json');event=json.loads(eventfile.read_text())
 event.update(new_StoreA_ABI_bits=5986,internal_region_ABI_bits=12552,physical_master='ot_hnx_sfu_store_a_regional4_captured',capture_location='INSIDE native32SRAM capsule, not parent soft FF hidden under hardbody',capture_payload_inputs=2048,capture_metadata_inputs=152,native_reset_inputs=['store0_rst_n','capture_ctl_reset_n','capture_meta_reset_n'])
 eventfile.write_text(json.dumps(event,indent=1)+'\n')
model=json.loads((out/'MODEL.json').read_text());model.update(physical_master='ot_hnx_sfu_store_a_regional4_captured',physical_ABI_bits=5986,internal_region_ABI_bits=12552,capture_location='same-edge8800copies inside native32macro capsule; extra source resetinputs explicit; originalCTL originals retained',clockload='oldnative mapped2914FF+8800strictnewcopyFF+32SRAM, finalnewmapping UNMEASURED')
model.update(bank_ownership={f'm{m}_columns{r}':[b for b in range(16) if ((b//2)%2)==r] for m in range(2) for r in range(2)},ownership_reason='Actual4column grid split by bankindexbit1; no numerical low/high8 geometry credit')
(out/'MODEL.json').write_text(json.dumps(model,indent=1)+'\n')
# Remove stale pre-capsule event if generated by an earlier local draft.
if(out/'provider_event.json').exists():(out/'provider_event.json').unlink()
