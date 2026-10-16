#!/usr/bin/env python3
"""Stage independent remaining archives; original verified remover stays live."""
import concurrent.futures,hashlib,json,os,shlex,subprocess,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
HOST='ot-epyc3';DEST='/srv/opentallas-scratch/codex-takeover-20261010/local-archive-preserve/h1v'
# The existing first archive rsync remains the sole producer for that archive.
FIRST='fb_hbm_stn_r38_88136dcd2_bud2.tar'
files=sorted(p for p in Path('/tmp/h1v').glob('*.tar') if p.stat().st_size>2**30 and p.name!=FIRST)
def one(p):
    s=p.stat();h=hashlib.sha256()
    with p.open('rb') as f:
        while b:=f.read(8*2**20):h.update(b)
    original_hash=h.hexdigest();gz=DEST+'/'+p.name+'.gz';tar=DEST+'/'+p.name
    # Verify decompressed original bytes before making the ordinary tar visible.
    verify="import hashlib,os\np="+repr(tar+'.prestage')+"\nh=hashlib.sha256()\nwith open(p,'rb') as f:\n while b:=f.read(8*2**20):h.update(b)\nassert h.hexdigest()=="+repr(original_hash)+"\nos.utime(p,ns="+repr((s.st_atime_ns,s.st_mtime_ns))+")\nos.replace(p,"+repr(tar)+")\n"
    cmd='set -e; cat > '+shlex.quote(gz+'.part')+'; mv -- '+shlex.quote(gz+'.part')+' '+shlex.quote(gz)+'; gzip -dc -- '+shlex.quote(gz)+' > '+shlex.quote(tar+'.prestage')+'; python3 -c '+shlex.quote(verify)
    producer=subprocess.Popen(['gzip','-1','-c','--',str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    consumer=subprocess.Popen(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8',HOST,cmd],stdin=producer.stdout,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    producer.stdout.close();out,err=consumer.communicate();producer_err=producer.stderr.read();prc=producer.wait()
    if consumer.returncode or prc:raise RuntimeError(p.name+' compressed stream failed')
    assert p.stat().st_size==s.st_size and p.stat().st_mtime_ns==s.st_mtime_ns
    row={'original':str(p),'bytes':s.st_size,'original_sha256':original_hash,'compressed_home':HOST+':'+gz,'ordinary_tar_home':HOST+':'+tar,'remote_decompressed_verified':True,'local_deletion_owner':'preserve_h1v.py (existing unchanged verifier/remover)','restore_command':'ssh '+HOST+' '+shlex.quote('gzip -dc -- '+shlex.quote(gz))+' > '+shlex.quote(str(p))}
    (HERE/('compressed-'+p.name+'.json')).write_text(json.dumps(row,indent=2)+'\n')
    receipt=DEST+'/compressed-'+p.name+'.json'
    subprocess.run(['ssh','-o','BatchMode=yes',HOST,'cat > '+shlex.quote(receipt)],input=json.dumps(row,indent=2)+'\n',text=True,check=True)
    print('COMPRESSED_PRESTAGED '+p.name,flush=True)
    return row
with concurrent.futures.ThreadPoolExecutor(max_workers=len(files)) as pool:
    rows=list(pool.map(one,files))
(HERE/'h1v_compressed_prestage.json').write_text(json.dumps({'completed_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),'files':rows},indent=2)+'\n')
