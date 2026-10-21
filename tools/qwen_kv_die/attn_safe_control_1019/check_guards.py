import pathlib,subprocess,sys,re
r=pathlib.Path('.');p=r/'candidate/qkd_kvs_attn_safe_control.v';s=p.read_text();guard=r/'guards';guard.mkdir(exist_ok=True)
checks=[('wrong_D',re.sub(r'\.D\(n\d+\)',".D(1'b0)",s,count=1)),('wrong_master',s.replace('XOR2x1_ASAP7_75t_R','OR2x2_ASAP7_75t_R',1)),('missing_cell',re.sub(r'^.* c0 \(.*\);\n','',s,count=1,flags=re.M)),('wrong_port',s.replace('assign n4 = ck;', 'assign n4 = rst_n;',1))]
source='synth/results/asap7/opentallas_qkd_kvs_attn_fl_ba5_asap7_ref_gate/base/1_2_yosys.v'
for name,text in checks:
 assert text!=s,name;f=guard/(name+'.v');f.write_text(text)
 cmd=[sys.executable,'tools/qwen_kv_die/attn_safe_control_1019/check_emitted.py',source,str(f),'candidate/correspondence.json'];v=subprocess.run(cmd,capture_output=True,text=True);(guard/(name+'.log')).write_text(v.stdout+v.stderr);assert v.returncode!=0,name
 print('GUARD_REJECT',name)
f=guard/'unsupported_source.v';f.write_text(pathlib.Path(source).read_text()+'\n');v=subprocess.run([sys.executable,'tools/qwen_kv_die/attn_safe_control_1019/fork.py',str(f),'--out',str(guard/'unexpected')],capture_output=True,text=True);(guard/'unsupported_source.log').write_text(v.stdout+v.stderr);assert v.returncode!=0 and 'unsupported source hash' in v.stderr
print('GUARD_REJECT unsupported_source')
