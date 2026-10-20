from pathlib import Path
import subprocess,json,hashlib
p=Path(__file__).resolve().parent
r="/srv/opentallas-scratch2/claude/hbm-r6-epoch-build-only-1019"
subprocess.run(["ssh","-o","BatchMode=yes","ot-epyc5",f"test -f {r}/EPOCH_numeric.exit"],check=True)
files=["positive-EPOCH.log","EPOCH_numeric.time","EPOCH_numeric.exit","EPOCH_numeric.STARTED","EPOCH_numeric.ENDED","EPOCH_numeric_result.sha256"]
for name in files:
 subprocess.run(["scp","-q",f"ot-epyc5:{r}/{name}",str(p/"collected"/name)],check=True)
a={x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in sorted((p/"collected").iterdir()) if x.is_file()}
(p/"COLLECTED_SHA256.json").write_text(json.dumps(a,indent=2)+"\n")
print((p/"collected"/"positive-EPOCH.log").read_text()[-12000:])
