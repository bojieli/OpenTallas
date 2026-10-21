from pathlib import Path
import json
p=Path('/home/ubuntu/wt/codex-s81-xfin-takeover2-1021/rtl/dsrom_sys/s81_dv/ot_s81dv_finish_sram.sv');s=p.read_text();profiles=json.loads(Path('/home/ubuntu/scratch/codex-s81-xfin-takeover2-1021/read_oh_capture_masks.json').read_text())
cut1=s.index('module ot_s81dv_eng_finish_sram');cut2=s.index('module ot_s81dv_finish_banks');parts=[s[:cut1],s[cut1:cut2],s[cut2:]]
for i,(kind,width,flag,mut) in enumerate([('norm','NVP','OT_S81DV_MUT_LEAF','norm_mutleaf'),('eng','NC','OT_S81DV_MUT_EASSOC','eng_mutassoc')]):
 a=parts[i];wire='wire[7:0] read_fire;wire[71:0] read_tags;';assert a.count(wire)==1
 def literal(n):return str(profiles[n]['width'])+"'h"+profiles[n]['mask_hex']
 decl=f'''// Only retain one-hot captures with a real macro-field consumer.
    // Group validity still captures ALL ready nodes before this filter, so
    // dropping a zero-output node cannot select a different priority winner.
`ifdef {flag}
    localparam [MREAD*{width}-1:0] MEM_NODE_USED={literal(mut)};
`else
    localparam [MREAD*{width}-1:0] MEM_NODE_USED={literal(kind)};
`endif
    wire[8*{width}-1:0] read_nodes;''';a=a.replace(wire,decl)
 start=a.index('for(genvar mc=0;mc<MREAD;mc=mc+1)begin:g_mem_command');end=a.index('ot_s81dv_finish_banks',start);x=a[start:end]
 x=x.replace('if(Q*8+mb>=1 && isadd(Q*8+mb))begin:g_node',f'if(Q*8+mb>=1 && isadd(Q*8+mb) && MEM_NODE_USED[mc*{width}+mq*8+mb])begin:g_node')
 x=x.replace(f'      wire[8:0] mt[0:{width}];assign mt[0]=0;\n','')
 x=x.replace("        assign mt[mn+1]=mt[mn] | ({9{mw[mn]}} & 9'(mn));\n",'')
 x=x.replace(f'      assign read_fire[mc]=|mw;\n      assign read_tags[mc*9+:9]=mt[{width}];',f'      assign read_nodes[mc*{width}+:{width}]=mw;')
 x=x.replace("      assign read_fire[mc]=1'b0;assign read_tags[mc*9+:9]=9'd0;",f"      assign read_nodes[mc*{width}+:{width}]='0;")
 assert 'read_tags' not in x and 'read_fire' not in x;a=a[:start]+x+a[end:]
 a=a.replace('.read_fire(read_fire),.read_tags(read_tags)', '.read_nodes(read_nodes)');parts[i]=a
b=parts[2];b=b.replace('module ot_s81dv_finish_banks #(parameter integer NV=80,K=5,P=3,TREES=1)(', 'module ot_s81dv_finish_banks #(parameter integer NV=80,K=5,P=3,TREES=1,NVP=(1<<$clog2(NV)))(',1);b=b.replace('input wire[7:0] read_fire,input wire[71:0] read_tags','input wire[8*TREES*NVP-1:0] read_nodes',1);b=b.replace('// One bounded descriptor per three actual banks, rather than a full\n // descriptor copy per bank. Its real outputs remain below32 consumers.', '// One one-hot descriptor per three actual banks. The already captured\n // command identity drives constant owner indices, avoiding the measured201-load variable-index mux.');b=b.replace('ot_s81dv_finish_readgroup #(.NV(NV),.K(K),.P(P),.TREES(TREES),.FIRST(rg*3),.CNT(CNT)) u_read(', 'ot_s81dv_finish_readgroup_oh #(.NV(NV),.K(K),.P(P),.TREES(TREES),.FIRST(rg*3),.CNT(CNT)) u_read(',1);b=b.replace('.fire(read_fire[rg]),.tag(read_tags[rg*9+:9]),.owner(','.nodes(read_nodes[rg*TREES*NVP+:TREES*NVP]),.owner(',1);parts[2]=b;p.write_text(''.join(parts))
