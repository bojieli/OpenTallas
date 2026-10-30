"""DIE-HEAD-33: Codex reset_fit.py (codex-head-start-0828) applied to the src25m leaf stages: move only START body r91_3 to the
same native-grid rect Codex chose (+8.631,+0.013 um); same clock/source/RTL/cycles; overlap-checked against every other body."""
import json,shutil,sys
from pathlib import Path
R=Path(sys.argv[1]); src=R/"stages"; dst=R/"stages_resetfit"
if dst.exists(): shutil.rmtree(dst)
shutil.copytree(src,dst)
st=json.load(open(dst/"start_stages.json"))
s=next(s for s in st["stages"] if s["id"]=="r91_3"); old=s["rect_um"][:]
assert old==[8469.855,3869.897,8474.175,3870.167], old
rect=[8478.486,3869.91,8482.806,3870.18]
for o in st["stages"]:
  if o["id"]==s["id"]: continue
  b=o["rect_um"]; assert min(rect[2],b[2])-max(rect[0],b[0])<=1e-6 or min(rect[3],b[3])-max(rect[1],b[1])<=1e-6, o["id"]
s["rect_um"]=rect; s["clock_pin_xy_um"]=rect[:2]
(dst/"start_stages.json").write_text(json.dumps(st,indent=1)+"\n")
print("r91_3",old,"->",rect)
