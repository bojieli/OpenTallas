# QW-TTC9: replay a lane's exact construct_parent7.py (bound netlist build) and dump u_<idx> -> source cell names.
# usage: namemap2.py <lane run dir R> <out dir>   (reads R/generic7/parent.json + R/src, writes only to <out dir>)
import sys,os,hashlib,json
from pathlib import Path
R=Path(sys.argv[1]);O=Path(sys.argv[2]);O.mkdir(parents=True,exist_ok=True)
src=(R/'src/tools/qwen_dv/ctlm6_bound_macro.py').read_text()
old=" for idx,(n,c) in enumerate(cells.items()):\n"
assert src.count(old)==1
src=src.replace(old," NAMEMAP.extend(cells.keys())\n"+old)
md=O/'mod';md.mkdir(exist_ok=True)
(md/'ctlm6_bound_macro.py').write_text("NAMEMAP=[]\n"+src)
cp=(R/'src/construct_parent7.py').read_text()
assert cp.count("sys.path.insert(0,'tools/qwen_dv')")==1
cp=cp.replace("sys.path.insert(0,'tools/qwen_dv')",f"sys.path.insert(0,{str(md)!r})")
cp=cp.replace("Path('/work/generic7c')",f"Path({str(O/'g')!r})").replace("Path('/work/generic7/parent.json')",f"Path({str(R/'generic7/parent.json')!r})")
assert '/work/' not in cp, [l for l in cp.splitlines() if '/work/' in l]
os.chdir(R/'src');sys.argv=['construct']
g={'__name__':'__main__'};exec(compile(cp,'construct_parent7','exec'),g)
B=sys.modules['ctlm6_bound_macro']
rtl=(O/'g/qfd_tt_ctlm_dv_np_lp.sv').read_bytes()
ref=(R/'generic7c/qfd_tt_ctlm_dv_np_lp.sv').read_bytes()
print('SAME_RTL',rtl==ref,hashlib.sha256(rtl).hexdigest())
(O/'namemap.json').write_text(json.dumps({'rtl_sha256':hashlib.sha256(rtl).hexdigest(),'same_as_lane':rtl==ref,'names':B.NAMEMAP}))
print('NAMEMAP',len(B.NAMEMAP))
