import subprocess,concurrent.futures,sys
from pathlib import Path
p=Path(__file__).resolve().parent;remote='/srv/opentallas-scratch/claude/sram-a3-wholemaster-1019/binding_corrected'
tar=subprocess.check_output(['tar','-czf','-','--exclude=__pycache__','-C',str(p),'.'])
def stage(h):
 r=subprocess.run(['ssh',h,'mkdir -p '+remote+'; tar -xzf - -C '+remote],input=tar,capture_output=True);return(h,r.returncode,r.stderr.decode())
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
 for r in ex.map(stage,['ot-epyc4','ot-epyc5','ot-epyc6','ot-epyc7','ot-epyc8']):print(r,flush=True);assert r[1]==0
cmd='''set -eu
hostname > host.txt
date -u +%FT%TZ > observed_at.txt
free -b > headroom_memory.txt
df -B1 . > headroom_disk.txt
docker image inspect openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 > image_inspect.json
sha256sum input/* run_native.py qwen/coupon.json sc2/coupon.json controls/coupon.json > execution_inputs.sha256
for a3_case in qwen sc2 controls; do
 docker run --rm --user "$(id -u):$(id -g)" -e A3_CASE="$a3_case" -v "$PWD:/work" openroad/orfs@sha256:16470cea1d346bfa245e402108995a4f04a1e54fe7c7bb7441774d7f6a2ece29 bash -c 'sha256sum /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad > /work/binary_sha256.txt; /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -version > /work/version.txt; /usr/bin/time -v -o /work/$A3_CASE/resources.time /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -exit -python /work/run_native.py' > "$a3_case/native.log" 2>&1
 cat "$a3_case/native.log"
 cat "$a3_case/resources.time"
done
du -sb . > disk.bytes
'''
r=subprocess.run(['/home/ubuntu/bin/ot-run','--mem','4','--threads','1','--disk','2','--dir',remote,'--','bash','-c',cmd]);sys.exit(r.returncode)
