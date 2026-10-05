from pathlib import Path
import json,subprocess
r=Path('/srv/opentallas-scratch2/codex/boole-w2-caller-sizing-20261005-r3')
a=json.loads((r/"launch.json").read_text())["argv"]
p=subprocess.run(a)
(r/"exit").write_text(str(p.returncode)+"\n")
raise SystemExit(p.returncode)
