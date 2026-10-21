from pathlib import Path
import subprocess,shlex,time,json
p=Path('/home/ubuntu/scratch/codex-ve-linked-runtime-1021')
run='/srv/opentallas-scratch2/claude/codex-ve-linked-runtime-1021/s81sl_ve_r5-f51f4ec42-linked-eco-1021'
archive='/archive/epyc6-retire-1021/srv/opentallas-scratch/claude/closure-loop/s81sl_ve_r5-s81sl_ve_r5-f51f4ec42'
src='/archive/epyc6-retire-1021/recovered_exact_sources/s81sl_ve_r5-20261020-212201/src'
a=['ssh','-S','none','-o','ConnectTimeout=10','-i','/home/ubuntu/.ssh/agidock_ot','ubuntu@155.103.253.53']
b=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','ot-epyc9']
def transfer(name,source,dest,paths=None):
    start=time.time();print('COPY_START',name,flush=True)
    with (p/(name+'.stderr.log')).open('wb') as log:
        cmd=['tar','-C',source,'-cf','-']+(['--null','-T','-'] if paths is not None else ['.'])
        producer=subprocess.Popen(a+[shlex.join(cmd)],stdin=subprocess.PIPE if paths is not None else subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=log)
        consumer=subprocess.Popen(b+[shlex.join(['tar','--no-same-owner','-xpf','-','-C',dest])],stdin=producer.stdout,stdout=subprocess.DEVNULL,stderr=log)
        producer.stdout.close();producer.stdout=None
        producer.communicate(input=paths);sink=consumer.wait()
        if producer.returncode or sink:raise RuntimeError('%s source=%s destination=%s'%(name,producer.returncode,sink))
    print('COPY_DONE',name,'seconds',round(time.time()-start,2),flush=True)
try:
    transfer('original_289_route_root',archive,run)
    transfer('canonical_13971_gate_source',src,run+'/src',(p/'gate_paths.null').read_bytes())
    raw=subprocess.check_output(a+['cat '+shlex.quote(src+'/SOURCE_COMMIT')])
    subprocess.run(b+['cat > '+shlex.quote(run+'/input_provenance/original_gate_SOURCE_COMMIT')],input=raw,check=True)
    subprocess.run(b+['printf copied > '+shlex.quote(run+'/input_provenance/COPY_DONE')],check=True)
    print('BOTH_COPY_PHASES_PASS; published worker now validates exact inputs; NO APPLY/READY/EDA',flush=True)
except BaseException as error:
    subprocess.run(b+['cat > '+shlex.quote(run+'/input_provenance/COPY_FAILED')],input=str(error).encode())
    raise
