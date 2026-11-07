from pathlib import Path
import tarfile,json
k=Path('/srv/opentallas-scratch2/claude/codex-su-1209/group0_vE_ewspread')
with tarfile.open(k/'input.tgz') as t:t.extractall(k,filter='data')
f=k/'face_flops.tcl';s=f.read_text()
a='set ff_n 0; set ff_miss 0';assert s.count(a)==1
s=s.replace(a,a+'\n# CODEX measured W/E hotface packing: spread starts across six legal depth columns.\nset ff_ew_seq [dict create W 0 E 0]')
a='for {set c 0} {$c < 400 && !$placed} {incr c} {';assert s.count(a)==1
s=s.replace(a,'''set ff_ew_phase [expr {[dict get $ff_ew_seq $face] % 6}]
      dict incr ff_ew_seq $face
      for {set c $ff_ew_phase} {$c < 6 && !$placed} {incr c} {''')
f.write_text(s)
(k/'.keep').touch();(k/'preflight').mkdir(exist_ok=True);(k/'preflight'/'.keep').touch()
(k/'preflight.tcl').write_text('''read_db /work/preflight_input.odb
set ::env(RESULTS_DIR) /work/preflight
source /work/face_flops.tcl
write_db /work/preflight/face_pose.odb
puts EW_SPREAD_PREFLIGHT_PASS
''')
(k/'CODEX_FORM.json').write_text(json.dumps({'source':'epyc2 codex-hbm-su-1107/kits/opsa_group0_vC','change':'E/W face flop allocator rotates startcolumn across6columns, capped6; actual gridpitch2.16um and FFwidth1.08um; N/S+stationgrid+RTL+pins+macros+clock unchanged','reason':'W5,215/220 density .849/.875; E750,220 .791. FaceFF plus input buffers clump in first2depthcolumns','geometry_estimate':'faceflop outerbound16.20um < Wmacrohalo17.28; mirrorE same; pin-to-FF reach checked from actual pose;0PINcycles','goal':'ONE PLACE only, preflight/image first'},indent=1)+'\n')
print('PREPARED',k)
