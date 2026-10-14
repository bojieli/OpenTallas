import pathlib,subprocess,json,hashlib,os
p=pathlib.Path.cwd();source=(p/'ot_qwen_numeric_stream_queue.sv').read_text();vlt='/home/ubuntu/.local/opentallas-tools/verilator-5.050/bin/verilator';records=[]
cases={'positive':source,'late_tag':source.replace('reg output_step;', 'reg output_step; reg [47:0] old_identity; always @(posedge base_clk) old_identity<=numeric_identity;').replace('numeric_identity,numeric_query_seq','old_identity,numeric_query_seq'),'forced_query':source.replace('numeric_word,numeric_has_query,numeric_identity','numeric_word,1\'b1,numeric_identity'),'truncated_seq':source.replace('numeric_identity,numeric_query_seq','numeric_identity,{8\'d0,numeric_query_seq[31:0]}'),'post_as_pop':source.replace('wire pop=consume_v&&consume_ready;','wire pop=pending_post;'),'unreserved_post':source.replace("{1'b0,count}+pending_post<DEPTH","{1'b0,count}<DEPTH")}
for name,text in cases.items():
 if os.environ.get("ONLY_CASE") and name!=os.environ["ONLY_CASE"]:continue
 f=p/(name+'.sv');f.write_text(text);obj=p/('obj_'+name)
 cmd=[vlt,'--binary','--timing','-j','1','-Wno-fatal','--top-module','tb_qwen_numeric_stream_queue','--Mdir',str(obj),str(f),str(p/'tb_qwen_numeric_stream_queue.sv')]
 with(p/(name+'_build.log')).open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
 with(p/(name+'.log')).open('w')as log:r=subprocess.run([str(obj/'Vtb_qwen_numeric_stream_queue')],stdout=log,stderr=subprocess.STDOUT)
 records.append({'case':name,'source_sha256':hashlib.sha256(text.encode()).hexdigest(),'exit_code':r.returncode,'command':cmd})
 print(name,r.returncode,(p/(name+'.log')).read_text(),flush=True)
 if (name=='positive') != (r.returncode==0):raise RuntimeError('unexpected gate '+name)
(p/('receipt_'+os.environ.get('ONLY_CASE','all')+'.json')).write_text(json.dumps({'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'fixture_sha256':hashlib.sha256((p/'tb_qwen_numeric_stream_queue.sv').read_bytes()).hexdigest(),'cases':records},indent=2)+'\n')
