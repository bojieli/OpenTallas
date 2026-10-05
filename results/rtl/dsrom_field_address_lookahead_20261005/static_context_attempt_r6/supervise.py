import subprocess,json,sys
from pathlib import Path
r=Path(__file__).resolve().parent
a=json.loads((r/"driver_args.json").read_text())
c=subprocess.call(["/srv/opentallas-scratch/admit.sh","16","--",sys.executable,"tools/run_abi3_physical_persistent.py","--persistent-workdir",str(r/"work"),"--launch-receipt",str(r/"launch.json"),*a],cwd=r/"src",stdout=(r/"route.log").open("xb"),stderr=subprocess.STDOUT)
(r/"terminal.exit").write_text(str(c)+"\n")
sys.exit(c)
