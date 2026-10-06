#!/usr/bin/env python3
"""Read-only LEF/SS/FF ETM extraction; no synth, CTS, placement, or gate rerun.

Final routed inputs must match committed hashes. Input capacitances and actual
clock->output arcs are audited, never filled using arbitrary defaults.
One native OpenROAD thread is sufficient for the 39k-cell FIFO extraction.
"""
import argparse, hashlib, json, re, subprocess
from pathlib import Path

LIBS = {
 'ss': ['asap7sc7p5t_AO_RVT_SS_nldm_211120.lib.gz','asap7sc7p5t_INVBUF_RVT_SS_nldm_220122.lib.gz','asap7sc7p5t_OA_RVT_SS_nldm_211120.lib.gz','asap7sc7p5t_SEQ_RVT_SS_nldm_220123.lib','asap7sc7p5t_SIMPLE_RVT_SS_nldm_211120.lib.gz'],
 'ff': ['asap7sc7p5t_AO_RVT_FF_nldm_211120.lib.gz','asap7sc7p5t_INVBUF_RVT_FF_nldm_220122.lib.gz','asap7sc7p5t_OA_RVT_FF_nldm_211120.lib.gz','asap7sc7p5t_SEQ_RVT_FF_nldm_220123.lib','asap7sc7p5t_SIMPLE_RVT_FF_nldm_211120.lib.gz']}
def sha(p):
 h=hashlib.sha256()
 with Path(p).open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--base',type=Path,required=True);p.add_argument('--libs',type=Path,required=True)
 p.add_argument('--evidence',type=Path,required=True);p.add_argument('--source',type=Path,required=True)
 p.add_argument('--out',type=Path,required=True);p.add_argument('--openroad',default='openroad')
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
 ev=json.loads(a.evidence.read_text());base=a.base.resolve()
 expected=ev['setup_ss']
 pins={n:sha(base/n) for n in ['6_final.odb','6_final.spef','6_final.sdc','6_final.v']}
 for n,k in [('6_final.odb','odb_sha256'),('6_final.spef','spef_sha256'),('6_final.sdc','sdc_sha256')]:
  if pins[n]!=expected[k]:raise ValueError('immutable route hash mismatch: '+n)
 if not ev.get('closes_signoff'):raise ValueError('source route is open')
 if sha(a.source)!='7e05230e70d6113af2da3326e678d86dd0c1e78e6cbf985d06b18c955f4b0ecb':raise ValueError('FIFO RTL differs from closed source')
 rec=dict(schema='opentallas.hbm.links.routed_export.v1',name='ot_meso_fifo',parameters=dict(W=512,DEPTH=4,OFFSET=2,CREDITS=8,ENABLE=1),
  route_source_commit='aec121692cc6c16931d4972501cdceda65459dc7',source_sha256=sha(a.source),
  evidence_sha256=sha(a.evidence),input_hashes=pins,threads=1,tool_sha256=sha(__file__),
  extraction_is_new_signoff=False,parent_closed=False,reader_sha256=sha(subprocess.check_output(['which',a.openroad],text=True).strip()),reader_version=subprocess.check_output([a.openroad,'-version'],text=True).strip(),orientation='original routed pin placement; not a rotated/rerouted variant',corners={})
 (out/'ot_meso_fifo.sdc').write_bytes((base/'6_final.sdc').read_bytes())
 for c in ['ss','ff']:
  files=[(a.libs/f).resolve() for f in LIBS[c]]
  rec['corners'][c]=dict(library_hashes={str(f):sha(f) for f in files})
  # Pin-only receiver sums are exported independently of the ETM's extracted
  # wire+receiver load, so a zero-cap clock root cannot silently pass.
  tcl='\n'.join('read_liberty {'+str(f)+'}' for f in files)+f'''
read_db {{{base}/6_final.odb}}
read_sdc {{{base}/6_final.sdc}}
read_spef {{{base}/6_final.spef}}
set_propagated_clock [all_clocks]
set_units -time ps -capacitance fF
set b [ord::get_db_block]
set f [open {{{out}/pins_{c}.tsv}} w]
puts $f "port\\tdirection\\tnet\\treceiver_pin_cap_fF\\tloads"
foreach bt [$b getBTerms] {{
 set net [$bt getNet];set cap 0;set loads {{}}
 if {{$net ne "NULL"}} {{
  foreach it [$net getITerms] {{
   if {{[$it isOutputSignal] || [[$it getMTerm] getSigType] in {{POWER GROUND}}}} {{continue}}
   set ref [[[$it getInst] getMaster] getName];set pin [[$it getMTerm] getName]
   set lp [get_lib_pins -quiet */$ref/$pin]
   if {{[llength $lp]!=1}} {{error "missing actual sink Liberty $ref/$pin"}}
   set cp [get_property $lp capacitance];set cap [expr {{$cap+$cp}}]
   lappend loads [list [[$it getInst] getName] $ref $pin $cp]
  }}
 }}
 puts $f [join [list [$bt getName] [$bt getIoType] [$net getName] $cap $loads] "\\t"]
}}
close $f
redirect {{{out}/clock_paths_{c}.txt}} {{
 report_checks -path_delay min_max -to [all_outputs] -group_path_count 8 -format full_clock_expanded
}}
write_timing_model -library_name ot_meso_fifo_{c} {{{out}/ot_meso_fifo_{c}.lib}}
'''+(f'write_abstract_lef {{{out}/ot_meso_fifo.lef}}\n' if c=='ss' else '')+'puts OT_EXPORT_DONE\nexit\n'
  script=out/f'export_{c}.tcl';script.write_text(tcl)
  run=subprocess.run([a.openroad,'-no_init','-threads','1','-exit',str(script)],capture_output=True,text=True)
  (out/f'export_{c}.log').write_text(run.stdout+run.stderr)
  rec['corners'][c].update(returncode=run.returncode,done='OT_EXPORT_DONE' in run.stdout)
  if run.returncode or 'OT_EXPORT_DONE' not in run.stdout:
   (out/'export.json').write_text(json.dumps(rec,indent=2)+'\n');raise SystemExit(1)
  lib=(out/f'ot_meso_fifo_{c}.lib').read_text()
  rec['corners'][c]['clock_output_arc_count']=len(re.findall(r'related_pin\s*:\s*"(?:rclk|wclk)"',lib))
  audits={}
  for m in re.finditer(r'\bpin\s*\(\s*([^)]*?)\s*\)\s*\{',lib):
   depth=1;end=m.end()
   while depth and end<len(lib):
    depth+=(lib[end]=='{')-(lib[end]=='}');end+=1
   body=lib[m.end():end-1];name=m.group(1).strip('\"')
   if re.search(r'direction\s*:\s*input\s*;',body):
    cap=re.search(r'(?<!_)\bcapacitance\s*:\s*([0-9.eE+-]+)',body)
    if not cap or float(cap[1])<=0:raise ValueError('missing actual positive input cap '+name)
    audits[name]=float(cap[1])
  rec['corners'][c]['input_capacitance_fF']=audits
  rec['corners'][c]['edge_clockQ_arcs']=len(re.findall(r'timing_type\s*:\s*(?:rising_edge|falling_edge)',lib))
  if not all(k in audits for k in ['wclk','rclk']):raise ValueError('missing actual clock root loads')
  if not rec['corners'][c]['edge_clockQ_arcs']:raise ValueError('no measured edge clockQ')
  if not rec['corners'][c]['clock_output_arc_count']:raise ValueError('no actual clock->output timing arcs')
 rec['files']={f.name:sha(f) for f in out.iterdir() if f.is_file()}
 rec['status']='EXTRACTED_LEAF_ONLY_PARENT_OPEN'
 (out/'export.json').write_text(json.dumps(rec,indent=2)+'\n');print(rec['status'])
if __name__=='__main__':main()
