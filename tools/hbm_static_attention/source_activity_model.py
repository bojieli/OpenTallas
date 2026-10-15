"""Source-bound useful payload and actual quadport delivery, kept distinct."""
import json
from pathlib import Path
H,D,TD,NL,PW=16,512,32,2,2
NT=NL*(D//TD);quads=NT*4
cases=[]
for T in (128,640):
 pbeats=T//(TD//H*PW)
 cases.append(dict(T=T,source_K_or_V_bytes=544*T,packed_numeric_code_scale_bytes=528*T,packed_format_bits=16*T,packed_staging_bytes=530*T,
 query_FP32_VM_bytes=H*D*4,query_BF16_unique_bytes=H*D*2,query_stationary_consumed_bytes=NL*H*D*2,
 query_quadport_delivery_bytes=quads*H*TD*2,query_quadport_physical_bus_bits=1024,query_meaningful_bits_per_load=512,
 P_FP32_VM_bytes=H*T*4,P_BF16_unique_bytes=H*T*2,P_stationary_consumed_bytes=NT*H*T*2,
 P_quadport_delivery_bytes=quads*pbeats*PW*TD*2,P_issue_load_edges=pbeats,
 expanded_operand_functional_bytes=D*18*T//8,expanded_operand_quadport_bytes=quads*(T//NL)*TD*18//8,
 PVfill_packed_tileport_bytes=NT*(T//NL)*NL*265//8))
model=dict(schema='opentallas.hbm_attn.source_activity.v1',source='rtl/hdc/v41x/static/ot_hdc_v41x_attn_physical_calendar.sv',params=dict(H=H,D=D,TD=TD,NL=NL,PWORDS=PW,logical_tiles=NT,quad_count=quads),
 quad_head_ownership={'0':[0,1,4,5],'2':[2,3,6,7],'8':[8,9,12,13],'10':[10,11,14,15]},
 QK_tile_mapping='g=lane*16+SL; qloadslice SL*TD, QKoperand lane/groupSL',
 PV_tile_mapping='g mapsfeature16dims g*16..g*16+15; fillusesBOTHlanes groupfloor(g/2),XOFF=(g*16)%32',
 native_staging_bit_layout='Interleaved265bgroups:code256,scale8,format1. Existingraw256bmacrostriping isNOT separatecode/meta.',
 interpretation='Usefulstationarywrites differ fromactualexternalquadportbroadcast. Query heads reachall4quads/tile butonlyonequadownseachhead; P1024bword reachallquadports buteachowns4of16heads. No toggleprobability or clockpower invented.',
 source_lines={'query_and_P_tileloads':'g_t: localparamSL=gk%S; ldw=e_ld_mode?e_p_w:zeroextended e_q_w[SL*TD*16+:TD*16]','QK_expansion':'g_qkl/g_qks/g_qke: elem(rd_q_qk[lane*ROWW+SL*265+:265],...)','PVfill':'g_tr/g_g:w_g[gl*265+:265]=rd_q_fl[gl*ROWW+floor(g*DPT/32)*265+:265]'},
 cases=cases,qualification=False,remaining='Actual logicaltile→physicalpair assignment, source/hardpipe binding, whole-system pinexact geometry, clock/cut/route')
p=Path('results/arch/hbm_attention_static_1015/source_activity_model.json');p.write_text(json.dumps(model,indent=2)+'\n')
print(json.dumps(cases,indent=2))
