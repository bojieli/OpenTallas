#!/usr/bin/env python3
"""Generate actual six-SRAM stream calendar kit from the die owner's literal grant."""
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/ref_tile'))
import ref_tile as RT
GRANT = 'results/arch/hbm_die_v15/su_stream6_grant_1417.json'
AUDIT = '\nset vb [ord::get_db_block]\nset vu [$vb getDbUnitsPerMicron]\nset vt [ord::get_db_tech]\nset vm_pg {}\nforeach bt [$vb getBTerms] {\n if {[$bt getSigType] ni {POWER GROUND}} continue\n foreach bp [$bt getBPins] {foreach box [$bp getBoxes] {\n  lappend vm_pg [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]\n }}\n}\nset vm_bad 0\nset vm_rows [open [file join $::env(RESULTS_DIR) stream6_actual_pins.tsv] w]\nputs $vm_rows "port\\tface\\tlayer\\texpected_um\\tactual_um\\ttrack_ok\\tPG_projection_clear"\nforeach item $vm_expected {\n lassign $item name face layer expected\n set bt [$vb findBTerm $name]\n if {$bt eq "NULL" || $bt eq "" || [llength [$bt getBPins]] != 1} {\n  puts "STREAM6_PIN_ERROR missing/duplicate pin $name";incr vm_bad;continue\n }\n set boxes [[lindex [$bt getBPins] 0] getBoxes]\n if {[llength $boxes] != 1} {puts "STREAM6_PIN_ERROR rectangle count $name";incr vm_bad;continue}\n set box [lindex $boxes 0]\n set actual [expr {$face in {N S}?([$box xMin]+[$box xMax])/2.0:([$box yMin]+[$box yMax])/2.0}]\n set tl [$vt findLayer $layer]\n set grid [$vb findTrackGrid $tl]\n set tracks [expr {$face in {N S}?[$grid getGridX]:[$grid getGridY]}]\n set track_ok [expr {[lsearch -exact $tracks [expr {int(round($actual))}]] >= 0}]\n set pg_clear 1\n set half [expr {$face in {N S}?([$box xMax]-[$box xMin])/2.0:([$box yMax]-[$box yMin])/2.0}]\n set space [$tl getSpacing]\n foreach rect $vm_pg {\n  lassign $rect pl ax ay bx by\n  if {$pl ne $layer} continue\n  set lo [expr {$face in {N S}?$ax:$ay}]\n  set hi [expr {$face in {N S}?$bx:$by}]\n  if {$actual+$half+$space>$lo && $actual-$half-$space<$hi} {set pg_clear 0;break}\n }\n set actual_um [expr {$actual/double($vu)}]\n if {abs($actual_um-$expected)>0.0001 || [[$box getTechLayer] getName] ne $layer || !$track_ok || !$pg_clear} {\n  puts "STREAM6_PIN_ERROR $name expected=$expected actual=$actual_um track=$track_ok PG_clear=$pg_clear"\n  incr vm_bad\n }\n puts $vm_rows "$name\\t$face\\t$layer\\t$expected\\t$actual_um\\t$track_ok\\t$pg_clear"\n}\nclose $vm_rows\nset vm_actual_signal 0\nforeach bt [$vb getBTerms] {if {[$bt getSigType] ni {POWER GROUND}} {incr vm_actual_signal}}\nif {$vm_actual_signal != [llength $vm_expected]} {incr vm_bad;puts "STREAM6_PIN_ERROR signal inventory $vm_actual_signal expected [llength $vm_expected]"}\nsource /src/tools/fp_margin_lint.tcl\not_fp_lint_dump [file join $::env(RESULTS_DIR) stream6_actual_pin_pg.json]\norfs_write_db $::env(RESULTS_DIR)/3_2_place_iop.odb\nputs "STREAM6_PIN_READBACK checked=[llength $vm_expected] PG_shapes=[llength $vm_pg] violations=$vm_bad"\nif {$vm_bad} {error "STREAM6_PIN_READBACK failed: $vm_bad actual coordinate/track/PG errors"}\n'

def make():
    assert (ROOT/'physical/common_flow/assigned_pin_exact.tcl').is_file()
    slot=json.loads((ROOT/GRANT).read_text())['slots'][0]
    for rel,digest in slot['source_dependencies_sha256'].items():
        assert hashlib.sha256((ROOT/rel).read_bytes()).hexdigest()==digest,rel
    s=json.loads((ROOT/'tools/hbm_static/su_stream6_pin_spec.json').read_text())
    s['contract']={'file':GRANT,'slot':slot['name']}
    s['outline']=dict(slot['outline'],exact=True)
    s['pin_ranges']={}
    s['pins']={f:[] for f in 'NSEW'}
    expected=[]
    for p in slot['pins']:
        stem=p['name'].split('[')[0]
        if stem not in s['pins'][p['face']]:s['pins'][p['face']].append(stem)
        expected.append((p['name'],p['face'],p['layer'],p['offset']))
    assert len(expected)==389 and len(set(p[0] for p in expected))==389
    for m,g in zip(s['macros'],slot['macros']):
        assert g['index']==s['macros'].index(m)
        m.update(at=g['origin_um'],orient=g['orient'],at_exact=True)
    hd_rel='physical/hbm_su_stream6_1015'
    hd=ROOT/hd_rel;hd.mkdir(parents=True,exist_ok=True)
    io=['# Literal source-bound H-DIE grant. No pin snapping or PG relocation.',
        'set vm_expected {',*[' {%s %s %s %.9f}'%p for p in expected],'}',
        'set vm_w 369.36;set vm_h 151.2',
        'source /src/physical/common_flow/assigned_pin_exact.tcl',
        'set vm_block [ord::get_db_block]',
        'foreach bt [$vm_block getBTerms] {if {[$bt getSigType] in {POWER GROUND}} continue;foreach bp [$bt getBPins] {odb::dbBPin_destroy $bp}}',
        'foreach item $vm_expected {lassign $item name face layer along;ot_assigned_pin_exact $name $layer $face $along}']
    (hd/'io.tcl').write_text('\n'.join(io)+'\n')
    # The IO hook executes before CTS; failure aborts the run, without relocation.
    (hd/'post_iop.tcl').write_text(f'source /src/{hd_rel}/io.tcl\n'+AUDIT)
    s['io_tcl']=f'{hd_rel}/io.tcl'
    s['orfs_vars'].update(POST_IO_PLACEMENT_TCL=f'{hd_rel}/post_iop.tcl',OT_ASSIGNED_PIN_HELPER='physical/common_flow/assigned_pin_exact.tcl')
    s['job']['extra_paths']=[hd_rel,GRANT,'results/arch/hbm_su_f2_static_1014/programme/stream_packed16_1436/stream_cal.mem']
    s['job']['cycles_added']=1
    s['job']['purpose']+=' Exact389perbit pin grant fbe4906e4 and explicit six macro homes; actual ODB coordinate/track/PG-clear must PASS before CTS. Source clock-to-macro mapping must be audited before any adoption.'
    kd=ROOT/'physical/ref_tile'/s['name'];kd.mkdir(parents=True,exist_ok=True)
    (kd/'spec.json').write_text(json.dumps(s,indent=2)+'\n')
    r=RT.gen(str(kd/'spec.json'));print(json.dumps(r))
if __name__=='__main__':make()
