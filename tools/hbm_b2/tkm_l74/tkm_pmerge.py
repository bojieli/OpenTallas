from pathlib import Path
import re,hashlib,json,sys
wt=Path(sys.argv[1]); d=wt/'rtl/hbm_accel/cores_split/ot_hgi_coll_tkm_m_tp192';base=d/'ot_hgi_coll_tkm_tp192_root_core__delpipe1.sv';s=base.read_text()
assert hashlib.sha256(s.encode()).hexdigest()=='101a04825316ac0e65b53059f74a282a82abf572ac692dc48c033a3a64c91fc0'
helper='''module ot_tkm_merge_parallel #(parameter MUT=0)(input [343:0] entry, input [7:0] entry_tag, output [343:0] eso);
  wire [85:0] e0=entry[0+:86], e1=entry[86+:86], e2=entry[172+:86], e3=entry[258+:86];
  wire [86:0] k0={e0[85:1],~entry_tag[0+:2]}, k1={e1[85:1],~entry_tag[2+:2]}, k2={e2[85:1],~entry_tag[4+:2]}, k3={e3[85:1],~entry_tag[6+:2]};
  wire c02=k0>=k2, c13=k1>=k3;
  wire c21=k2>=k1, c23=k2>=k3, c01=k0>=k1, c03=k0>=k3;
  wire cm=c02 ? (c13 ? c21 : c23) : (c13 ? c01 : c03);
  wire pick=(MUT==1)?~cm:cm;
  wire [85:0] m0=c02?e2:e0, m1=c13?e1:e3;
  assign eso[0+:86]=c02?e0:e2;
  assign eso[258+:86]=c13?e3:e1;
  assign eso[86+:86]=pick?m0:m1;
  assign eso[172+:86]=(MUT==2)?(pick?m0:m1):(pick?m1:m0);
endmodule
'''
rx=re.compile(r'(?m)^  assign (?P<lhs>\{ \\u\.eso\[(?P<idx>[0-3])\]\[85\].*?) = .*?;$')
ms=list(rx.finditer(s));assert len(ms)==4
first=min(x.start() for x in ms)
prefix='''`ifdef OT_TKM_PAR_MERGE
  wire [343:0] ot_pm_eso;
  ot_tkm_merge_parallel ot_pm(.entry(_60269_),.entry_tag(_60271_),.eso(ot_pm_eso));
`endif
'''
def sub(m):
 i=int(m['idx']);return '`ifdef OT_TKM_PAR_MERGE\n  assign '+m['lhs']+' = ot_pm_eso['+str(i*86)+'+:86];\n`else\n'+m[0]+'\n`endif'
s=s[:first]+prefix+rx.sub(sub,s[first:]);s+='\n`ifdef OT_TKM_PAR_MERGE\n'+helper+'`endif\n'
out=d/'ot_hgi_coll_tkm_tp192_root_core__delpipe1_pmerge.sv';out.write_text(s)
r=wt/'results/rtl/tkm_pmerge_1106';r.mkdir(parents=True,exist_ok=True)
(r/'candidate_helper.sv').write_text(helper)
canon=(wt/'rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_static_pd.sv').read_text()
func=canon[canon.index(' function automatic [EW:0] stable_key'):canon.index(' always @*begin:pair_sort')]
block=canon[canon.index(' always @*begin:merge_sort'):canon.index(' wire[4*EW-1:0]down')]
gold='module ot_tkm_merge_gold(input[343:0]entry,input[7:0]entry_tag,output[343:0]out);\nlocalparam EW=86;reg[EW-1:0]es[0:3],eso[0:3];reg[1:0]et[0:3];\n'+func+block+'\nassign out={eso[3],eso[2],eso[1],eso[0]};\nendmodule\n'
(r/'gold_helper.sv').write_text(gold)
(r/'miter.sv').write_text('''module miter(input[343:0]entry,input[7:0]entry_tag,output bad,output bad_mut1,output bad_mut2);
wire[343:0]g,c,m1,m2;
ot_tkm_merge_gold gold(entry,entry_tag,g);
ot_tkm_merge_parallel candidate(entry,entry_tag,c);
ot_tkm_merge_parallel #(.MUT(1)) mutant1(entry,entry_tag,m1);
ot_tkm_merge_parallel #(.MUT(2)) mutant2(entry,entry_tag,m2);
assign bad=|(g^c);assign bad_mut1=|(g^m1);assign bad_mut2=|(g^m2);
endmodule
''')
(r/'manifest.json').write_text(json.dumps({'base_sha256':hashlib.sha256(base.read_bytes()).hexdigest(),'candidate_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'helper_sha256':hashlib.sha256(helper.encode()).hexdigest(),'replaced_outputs':4,'added_state_bits':0,'added_edges':0,'canonical_gold_source':'rtl/hbm_accel/generic/collective/tkm/ot_hgi_coll_tkm_static_pd.sv'},indent=2))
print(out)
