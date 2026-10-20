"""Only split mixed initialized/uninitialized net declarations rejected by Icarus11.
No equation, register, sensitivity, reset, parameter, or delay transformation.
Verilator benches use original source without this parser workaround.
"""
from pathlib import Path
import hashlib,json
changes={
 "rtl/lib/ot_sram_oldread_wreg.sv": [("wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},wdata},raw;", "wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},wdata}; wire [NB*128-1:0] raw;")],
 "rtl/lib/ot_sram_showahead_1r1w.sv": [("wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},mwd}, raw;", "wire [NB*128-1:0] padded={{(NB*128-W){1'b0}},mwd}; wire [NB*128-1:0] raw;")],
 "rtl/dsrom_sys/s81_dv/slice/ot_s81sl_slice_lep.sv": [("wire [79:0] old_host={3'd0,pd},new_host={3'd0,thq},next_host;", "wire [79:0] old_host={3'd0,pd},new_host={3'd0,thq}; wire [79:0] next_host;"), ("wire [55:0] old_key={2'd0,kd},new_key={2'd0,tkq},next_key;", "wire [55:0] old_key={2'd0,kd},new_key={2'd0,tkq}; wire [55:0] next_key;")]
}
manifest=[]
for source,replacements in changes.items():
 original=Path(source).read_bytes();s=original.decode()
 for old,new in replacements:
  assert s.count(old) in (1,2),(source,old)
  s=s.replace(old,new)
 output=Path("out_fourstate")/Path(source).name;output.write_text(s)
 manifest.append(dict(source=source,original_sha256=hashlib.sha256(original).hexdigest(),portable_sha256=hashlib.sha256(s.encode()).hexdigest(),replacements=replacements))
Path("out_fourstate/portable_manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
