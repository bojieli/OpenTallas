from pathlib import Path
O=Path('results/rtl/qlb_c4b_1018/lmh_cal/closed_equiv');s=Path('rtl/qwen_sys/static_schedule_20261014/ot_qwen_fixed_issue_pw.sv').read_text();ports=s[s.index(')(\n')+3:s.index('\n);')]
for name,mod,extra in [('gold','gold_ot_qwen_fixed_issue_pw',''),('gate','ot_qwen_fixed_issue_pw',',.SEG(0)')]:
 (O/(name+'_focus.sv')).write_text('module '+name+'(\n'+ports+'\n);\n'+mod+' #(.DENSE_IMAGE(1),.OWN(1),.SREG(1),.SLATE(1)'+extra+') u(.*);\nendmodule\n')
src=' '.join('/src/'+str(O/'reset_unit'/('gold_'+n+'.sv')) for n in ['ot_qwen_fixed_issue','ot_qwen_fixed_issue_pw','ot_qwen_fixed_issue_dense_pw'])+' '+' '.join('/src/rtl/qwen_sys/static_schedule_20261014/'+n+'.sv'for n in ['ot_qwen_fixed_issue','ot_qwen_fixed_issue_pw','ot_qwen_fixed_issue_dense_pw'])
ys=[]
for name in ['gold','gate']:
 ys+=['read_verilog -sv -DSYNTHESIS '+src+' /out/'+name+'_focus.sv','hierarchy -check -top '+name,'proc','flatten','memory_map','opt -full','write_json /out/'+name+'_focus.json','design -stash '+name]
(O/'focus_prepare.ys').write_text('\n'.join(ys)+'\n')
