from pathlib import Path
import re,json,hashlib,shutil
S=Path('/srv/opentallas-scratch2/claude/fable-fix-qc-cbglue/headseg44/group44/src_804_complete')
R=Path('/srv/opentallas-scratch2/claude/qc-types-r/w0_lec_diag_1116');R.mkdir(parents=True,exist_ok=True)
p=S/'rtl/hdc/ot_hdc_sfu_q.sv';raw=p.read_text();m=re.search(r'function automatic \[63:0\] ln2_nk\(input \[7:0\] nk\);.*?endfunction',raw,re.S);assert m
fn=m.group();lows=[int(x,16) for x in re.findall(r"ln2_nk\s*=\s*\{32'h[0-9a-fA-F]+,\s*32'h([0-9a-fA-F]+)\}",fn)];assert len(lows)==254 and all((x>>30)&1==0 for x in lows)
assert 'default: ln2_nk = 64\'d0;' in fn
h='module table_chain(input wire clk,input wire rst_n,input wire [7:0] nk,output wire ok,output wire rawzero,output wire [31:0] lo_d);\n'
t='\nreg [31:0] a_hi,a_lo;\nalways @(posedge clk) {a_hi,a_lo} <= ln2_nk(nk);\not_hdc_delay #(.W(32),.D(4)) d_lo(clk,rst_n,a_lo,lo_d);\nassign ok=(lo_d[30]==1\'b0);\nwire[63:0] rawword=ln2_nk(nk);assign rawzero=(rawword[30]==1\'b0);\nendmodule\n'
(R/'table_chain.v').write_text(h+fn+t)
mut=fn.replace("32'hB93CBF94","32'hF93CBF94",1);assert mut!=fn
(R/'table_chain_mutant.v').write_text(h+mut+t)
shutil.copy2(S/'rtl/hdc/ot_hdc_delay.sv',R/'ot_hdc_delay.sv')
base='read_verilog -sv /out/ot_hdc_delay.sv /out/table_chain.v\nhierarchy -check -top table_chain\nproc\nflatten\nmemory_map\nopt_clean\n'
for n in [4,5,6]:(R/f'chain{n}.ys').write_text(base+f'sat -seq {n} -prove ok 1 -prove-skip {n-1} -show-inputs -show-outputs\n')
(R/'table.ys').write_text(base+'sat -seq 1 -prove rawzero 1 -verify -show-inputs -show-outputs\n')
(R/'mutant.ys').write_text(base.replace('/out/table_chain.v','/out/table_chain_mutant.v')+'sat -seq 1 -prove rawzero 1 -verify -show-inputs -show-outputs\n')
receipt=dict(source=str(p),source_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),function_sha256=hashlib.sha256(fn.encode()).hexdigest(),actual_entries=254,default='64d0',bit30_zero_all_literal_entries=True,bit126='32*3+30: final D4 delay stage bit30',register_chain_edges=5,arithmetic_reimplemented=False,source_unchanged=True,reset_contract_not_changed=True,scope='Exact actual ln2_nk function and actual ot_hdc_delay.W32/D4/RESET0 plus original registered a_hi/a_lo assignment. nk arbitrary8bits; numericalFP datapath not simulated or replaced.',mutant='real nk130 lowword bit30 B93CBF94->F93CBF94')
(R/'exp_table_source_receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print('PREPARED',len(lows),'real table entries plus default')
