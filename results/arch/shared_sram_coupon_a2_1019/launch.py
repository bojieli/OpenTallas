import subprocess,concurrent.futures,sys,tarfile,io
from pathlib import Path
p=Path(__file__).resolve().parent
remote='/srv/opentallas-scratch/claude/sram-coupon-a2-1019/original'
tar=subprocess.check_output(['tar','-czf','-','-C',str(p),'.'])
def stage(h):
 r=subprocess.run(['ssh',h,'mkdir -p '+remote+'; tar -xzf - -C '+remote],input=tar,capture_output=True);return(h,r.returncode,r.stderr.decode())
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
 for r in ex.map(stage,['ot-epyc4','ot-epyc5','ot-epyc6','ot-epyc7','ot-epyc8']):print(r,flush=True);assert r[1]==0
cmd='''set -e
hostname > host.txt
date -u +%FT%TZ > observed_at.txt
free -b > headroom_memory.txt
df -B1 . > headroom_disk.txt
docker image inspect openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 > image_inspect.json
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/work" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -c 'sha256sum /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad > /work/binary_sha256.txt; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -version > /work/version.txt; /usr/bin/time -v -o /work/resources.time /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -python /work/run_native.py' > native.log 2>&1
rc=$?
du -sb . > disk.bytes
cat native.log
cat resources.time
exit "$rc"
'''
r=subprocess.run(['/home/ubuntu/bin/ot-run','--mem','4','--threads','1','--disk','2','--dir',remote,'--','bash','-c',cmd]);sys.exit(r.returncode)
