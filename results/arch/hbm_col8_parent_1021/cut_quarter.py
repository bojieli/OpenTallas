"""Expose real columns as quarter siblings without changing a register or age.
Generate controllers by replacing only instance cuts/wires in the tested source.
The controller is hierarchical soft logic, not a claimed 1512-square hard macro.
"""
import pathlib,json,hashlib
r=pathlib.Path.cwd();d=r/'results/arch/hbm_col8_parent_1021';hd=r/'rtl/hdc/v41x';qd=r/'rtl/hbm_accel/index/quad_1017'
ports=[('output','rst_n',1),('output','qv',1),('output','q',568),('output','key',544),('output','hid',64),('input','cs',32),('input','cf',1),('input','prdy',4)]
def declarations(n,wire=False):
 return ',\n'+',\n'.join(f' {"wire" if wire else io+" wire"} [{n*w-1}:0] cut_{name}' for io,name,w in ports)
def append_ports(s,n):return s.replace('\n);',declarations(n)+'\n);',1)
def bindings(index,n):return ','.join(f'.cut_{name}(cut_{name}[({index})*{w}+:{n*w}])' for _,name,w in ports)
def allbindings():return ','.join(f'.cut_{name}(cut_{name})' for _,name,_ in ports)
def wiredecl(n):return '\n'.join(f' wire [{n*w-1}:0] cut_{name};' for _,name,w in ports)+'\n'

def repair_residual(s):
 import re
 s=re.sub(r' wire rst_c;\n ot_rst_relay #\(\.REGIONS\(1\),\.SYNC_STAGES\(2\),\.TREE_STAGES\(1\)\) u_rst\(\.clk\(clk_ctl\),\.rst_n_in\(rst_n\),\.rst_n\(rst_c\)\);', ' wire[12:0]rst_regions;\n ot_hidx_rst_tree_3e_f32 #(.REGIONS(13)) u_rst(.clk(clk_ctl),.rst_n_in(rst_n),.rst_n(rst_regions));\n wire rst_c=rst_regions[12];',s)
 assert 'wire[12:0]rst_regions' in s
 s=s.replace(' // ---------------- W glue',' // Same input edge as bi_r; isolate bitmap high-index loads from ordinal arithmetic.\n (*keep="true",dont_touch="true"*)reg[3:0]bi_keep_hi;\n always@(posedge clk_ctl)bi_keep_hi<=beat_index[7:4];\n wire bitmap_bit;\n ot_hidx_keep171_f32 keep_select(.clk(clk_ctl),.kb_registered(kb_r),.index_registered({bi_keep_hi,bi_r[3:0]}),.index_next(beat_index[3:0]),.q(bitmap_bit));\n // ---------------- W glue')
 s=s.replace('!ke_r||kb_r[bi_r]','!ke_r||bitmap_bit').replace('.rst_n(rst_c), .hb(8', '.rst_n(rst_regions[e*4+c]), .hb(8')
 start=s.index('  // ---------------- E glue');end=s.index(' // ---------------- output pin flops')
 middle=s[start:end].replace('rst_c','rst_e').replace('wire eclk=clk_engine[e];','wire eclk=clk_engine[e];\n  wire rst_e=rst_regions[8+e],rst_t=rst_regions[10+e];').replace('ot_hbm_idx_tail_native u_t','ot_hbm_idx_tail_col8_f32 u_t').replace('.rst_n(rst_e), .i_v','.rst_n(rst_t), .i_v')
 return s[:start]+middle+s[end:]

old=(hd/'ot_hbm_idx_chunk_col8_face.sv').read_text();chunk=append_ports(old.replace('module ot_hbm_idx_chunk_col8_face','module ot_hbm_idx_chunk_col8_control',1),4);chunk=chunk.replace('#(.QLATE(QLATE),.VL_EXTRA(23)) u_glue','#(.RESET_F32_FAST3(1),.QLATE(QLATE),.VL_EXTRA(23)) u_glue');chunk=chunk[:chunk.index(' genvar g;')]+''' assign cut_rst_n=crst;assign cut_qv={4{cqv}};assign cut_q={4{cq}};
 assign cut_key=ckey;assign cut_hid={4{chid}};
 assign ccs=cut_cs;assign ccf=cut_cf;assign cprdy=cut_prdy;
endmodule
`default_nettype wire
''';(hd/'ot_hbm_idx_chunk_col8_control.sv').write_text(chunk)
leaf=(qd/'ot_hbm_idx_score_leaf_col8_sram.sv').read_text();leaf=append_ports(leaf.replace('module ot_hbm_idx_score_leaf_col8_sram','module ot_hbm_idx_score_leaf_col8_control',1),4).replace('ot_hbm_idx_chunk_col8_face core','ot_hbm_idx_chunk_col8_control core').replace('.n_fault(n_f));','.n_fault(n_f),'+allbindings()+');');(qd/'ot_hbm_idx_score_leaf_col8_control.sv').write_text(leaf)
quarter=(qd/'ot_hbm_idx_score_quarter_col8_sram.sv').read_text();ctl=append_ports(quarter.replace('module ot_hbm_idx_score_quarter_col8_sram','module ot_hbm_idx_score_quarter_col8_control',1),32).replace('ot_hbm_idx_score_leaf_col8_sram #','ot_hbm_idx_score_leaf_col8_control #').replace('.e_bus(bo));','.e_bus(bo),'+bindings('4*(e*4+c)',4)+');');ctl=repair_residual(ctl);(qd/'ot_hbm_idx_score_quarter_col8_control.sv').write_text(ctl)
qports='clk_ctl clk_engine clk_meta clk_tail clk_chunk clk_hslice rst_n half rank first_ord nkeys keep_en keep_bitmap ql_v ql_head ql_codes ql_sc ql_w beat_v beat_index key_lines score fault'.split();head=quarter[:quarter.index(' localparam integer')];head=head.replace('ot_hbm_idx_score_quarter_col8_sram','ot_hbm_idx_score_quarter_col8_split').replace('output reg[305:0]score','output wire[305:0]score');body=wiredecl(32)+' ot_hbm_idx_score_quarter_col8_control #(.TP(TP),.RANK_W(RANK_W)) u_control('+','.join(f'.{a}({a})' for a in qports)+','+allbindings()+');\n';body+=''' for(genvar e=0;e<2;e=e+1)begin:ge
  for(genvar c=0;c<4;c=c+1)begin:gc
   for(genvar g=0;g<4;g=g+1)begin:g_col
    localparam integer I=(e*4+c)*4+g;
    wire[3:0]cp;
    for(genvar rid=0;rid<4;rid=rid+1)begin:gp
     assign cp[rid]=clk_hslice[e*128+c*32+g*8+rid*2];
    end
    ot_hidx_col8_sram_face_col u_col(.ctl(clk_chunk[e*4+c]),.cp(cp),.rst_n(cut_rst_n[I]),.qv_b(cut_qv[I]),.q_b(cut_q[I*568+:568]),.key(cut_key[I*544+:544]),.hid(cut_hid[I*64+:64]),.cs_out(cut_cs[I*32+:32]),.cf_out(cut_cf[I]),.prdy(cut_prdy[I*4+:4]));
   end
  end
 end
endmodule
`default_nettype wire
''';(qd/'ot_hbm_idx_score_quarter_col8_split.sv').write_text(head+body)
cp='clk clk_pair rst_n hb ql_v ql_head ql_codes ql_sc ql_w k_v k_kv k_key c_v c_kv c_sum c_fault online n_v n_kv n_sum n_fault'.split();head=old[:old.index(' localparam integer')].replace('ot_hbm_idx_chunk_col8_face','ot_hbm_idx_chunk_col8_rejoined');body=' localparam integer NB=4,NKT=4;\n'+wiredecl(4)+' ot_hbm_idx_chunk_col8_control #(.QLATE(QLATE)) u_control('+','.join(f'.{a}({a})' for a in cp)+','+allbindings()+');\n';body+=''' for(genvar g=0;g<4;g=g+1)begin:g_col
  ot_hidx_col8_sram_face_col u_col(.ctl(clk),.cp(clk_pair[g*4+:4]),.rst_n(cut_rst_n[g]),.qv_b(cut_qv[g]),.q_b(cut_q[g*568+:568]),.key(cut_key[g*544+:544]),.hid(cut_hid[g*64+:64]),.cs_out(cut_cs[g*32+:32]),.cf_out(cut_cf[g]),.prdy(cut_prdy[g*4+:4]));
 end
endmodule
`default_nettype wire
''';(hd/'ot_hbm_idx_chunk_col8_rejoined.sv').write_text(head+body)
contract=[]
for q in ['SW','SE','NW','NE']:
 root=f'hb_idx__s_{q}';net=lambda n:f'{root}.cut_{n}'
 contract.append(dict(instance=f'{root}.u_control',placement_key=f'{q}.residual_control',master='ot_hbm_idx_score_quarter_col8_control',params={'TP':192,'RANK_W':8},kind='hierarchical_soft_controller',connections={**{a:f'{root}.{a}' for a in qports},**{f'cut_{n}':{'net':net(n),'lsb':0,'width':32*w} for _,n,w in ports}},physical_status='Residual reserve is diagnostic; no hard 1512-square footprint or timing claim.'))
 for e in range(2):
  for c in range(4):
   for g in range(4):
    i=(e*4+c)*4+g;clock=lambda rid:f'{root}.clk_hslice[{e*128+c*32+g*8+rid*2}]'
    cs={'ctl':f'{root}.clk_chunk[{e*4+c}]','cp':{'bits_lsb_first':[clock(j) for j in range(4)]}}
    names={'rst_n':'rst_n','qv_b':'qv','q_b':'q','key':'key','hid':'hid','cs_out':'cs','cf_out':'cf','prdy':'prdy'}
    for a,n in names.items():w=next(w for _,nn,w in ports if nn==n);cs[a]={'net':net(n),'lsb':i*w,'width':w}
    contract.append(dict(instance=f'{root}.ge[{e}].gc[{c}].g_col[{g}].u_col',placement_key=f'{q}.engine{e}.leaf{c}.column{g}',master='ot_hidx_col8_sram_face_col',params={},kind='hierarchical_column',column_index=i,connections=cs,pair_master_paths=[f'u_pair{j}' for j in range(4)],raw_sram_paths=[f'l{s}.u_ring.g_bank[{b}].u_mem' for s in range(4) for b in range(3)]))
x=dict(status='SOURCE CUT, DIAGNOSTIC ONLY; exact cut/rejoin bench and physical qualification required',base_source_commit='c6989e9ea',top='ot_hbm_idx_score_quarter_col8_split',quarter_params={'TP':192,'RANK_W':8},active_clocks_per_quarter=143,instances=contract,buses=[dict(name=f'cut_{n}',direction_at_controller=io,width_per_column=w,width_per_quarter=32*w) for io,n,w in ports],calendar={'active_delta_edges':23,'meta_D':146,'keep_D':129,'extra_die_hops':'OPEN: regenerate from actual placed graph'},notes=['No registers added or removed by the cut. All leaf W/E registers, shared glue, engine, metadata and tail remain in u_control.','Connections of replicated query and head-ID fields are wires to the original shared glue outputs, not extra register copies.','All pair and SRAM bodies retain real masters. R3 is still an explicit stand-in.','Controller clock ports for pair hslice are retained but unused; all 128 active pair clocks go to real columns.'])
view='physical/ref_tile/hidx_meta146_main_1021/views/ot_hidx_meta_sram146'
helper='rtl/hdc/v41x/ot_hidx_meta_sram146.sv';hs=hashlib.sha256((r/helper).read_bytes()).hexdigest()
for a in x['instances']:
 if a['kind']=='hierarchical_soft_controller':
  root=a['instance'].removesuffix('.u_control')
  a['hard_children']=[{'instance':a['instance']+f'.ge[{e}].md','master':'ot_hidx_meta_sram146','view':view,'record_commit':'06d0f5e44','main_publish_commit':'6a5b95375','params':{'D':146},'fixed_width':25,'source':helper,'source_sha256':hs,'clock_pins':{'clk':root+f'.clk_meta[{e}]','clk_mem':root+f'.clk_meta[{e}]'},'outline_um':[259.2,172.8],'status':'CLOSED TT197.51 FF31.10 ps DRC0; SS sensitivity -60.10 ps'}for e in range(2)]
x['metadata_binding']='Eight real CLOSED D146 masters; exact source bytes and literal clk_meta connections. This is component binding, not parent delivery/return timing qualification.'
(d/'split_contract.json').write_text(json.dumps(x,indent=2)+'\n');print('Generated 5 RTL modules and',len(contract),'real contract instances.')
