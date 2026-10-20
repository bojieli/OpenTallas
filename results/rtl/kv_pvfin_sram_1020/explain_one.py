import sys,json
from pathlib import Path
sys.path.insert(0,"tools")
import textbook_lint as TL
base=Path("results/rtl/kv_pvfin_sram_1020")
d=json.loads((base/"native_qkd_pv_fin_s32_census.json").read_text())
g,top=TL.flatten(TL.parse_verilog(Path(d["netlist"]["path"].replace("/work/","")).read_text()),d["top"])
for x in sorted(d["violations"],key=lambda x:x["loads"],reverse=True)[:1]:
 print("VIOL",x["driver"],x["net"],x["loads"])
 for ci,pn,b in x["endpoints"][:40]:
  typ,name,pins=g.cells[ci]
  print(" LOAD",name,typ,pn)
