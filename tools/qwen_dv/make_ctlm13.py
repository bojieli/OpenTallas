#!/usr/bin/env python3
"""Generate component-only safe13 kits from exact RR2 and placed-copy evidence."""
from pathlib import Path
import json
import re
import tarfile

base = 'qfd_tt_ctlm_dv_safe12c'
src = Path('physical/ref_tile') / base
def read_base(name):
    if (src/name).exists():
        return (src/name).read_text()
    with tarfile.open('results/arch/codex_ctlm13_1021/baseline_kit.tgz') as archive:
        return archive.extractfile(name).read().decode()
record = json.loads(Path('results/arch/codex_ctlm13_1021/placed_replica_record.json').read_text())
owners = {}
for group in record['groups']:
    for name, regions in zip(group['copies'], group['after']):
        assert len(regions) == 1, (name, regions)
        owners[name] = next(iter(regions))
zones = {
    'W0': [2.16, 129.6, 453.6, 410.4],
    'W1': [2.16, 410.4, 453.6, 691.2],
    'E0': [453.6, 367.2, 775.44, 475.2],
    'E1': [453.6, 475.2, 615.6, 691.2],
}
for suffix, leaf in [('a', 16), ('b', 8)]:
    name = 'qfd_tt_ctlm_dv_safe13' + suffix
    dst = Path('physical/ref_tile') / name
    dst.mkdir(parents=True, exist_ok=True)
    for filename in ['assigned_pins.tcl', 'lp_cone_regions.tcl', 'lcr_dissolve_after_gpl.tcl']:
        text = read_base(filename).replace(base, name)
        if filename == 'assigned_pins.tcl':
            for port, first in [('native_tok', 156.54), ('native_pos', 160.38)]:
                for bit in range(18):
                    pattern = r'ot_assigned_pin_exact \{' + port + r'\[' + str(bit) + r'\]\} M3 N [0-9.]+'
                    replacement = f'ot_assigned_pin_exact {{{port}[{bit}]}} M4 E {first + .192 * bit:.6f}'
                    text, count = re.subn(pattern, replacement, text)
                    assert count == 1, (port, bit)
            text = '# safe13: Tok/Pos E face beside actual CLOSED h16c E ports; zero new edges.\n' + text
        (dst / filename).write_text(text)
    spec = json.loads(read_base('spec.json'))
    spec = json.loads(json.dumps(spec).replace(base, name).replace('rtl/qwen_dv/lp9e_rr/', 'rtl/qwen_dv/lp9f_rrloc/'))
    spec['name'] = name
    spec['job']['branch'] = 'codex/q-ctlm-safe13-1021'
    spec['job']['tag'] = 'safe13' + suffix
    spec['job']['owner'] = 'CODEX-Q-CLOSE-1021'
    spec['job']['extra_paths'] = [x for x in spec['job']['extra_paths'] if x != 'rtl/qwen_dv/lp9e_rr']
    spec['job']['extra_paths'] += ['rtl/qwen_dv/lp9f_rrloc', 'results/arch/codex_ctlm13_1021']
    for port, span in [('native_tok', [156.54, 159.804]), ('native_pos', [160.38, 163.644])]:
        spec['pins']['N'].remove(port)
        spec['pins']['E'].append(port)
        spec['pin_ranges'][port] = span
    spec['pin_hook_after_flops'].append(str(dst / 'copy_regions.tcl'))
    spec['pre_cts_extra'] = [str(dst / 'spine.tcl')]
    spec['structural_recut_status'] = (
        'Exact safe12c placed-copy locality:14 groups/1119 repointed pins/+2 identical combinational copies;'
        'no FF/state/clock/data edge added. Helpers byte-identical RR2. Native census required before layout.'
        'Existing core/hr landings unchanged. Actual CLOSED h16c retained until H16ZA closes;'
        'not selected73/HP export.'
    )
    spec['job']['purpose'] = spec['structural_recut_status']
    spec['slot_change_request'] = (
        'Safe13 retains777.6x734.4 and13 hard rectangles from safe12c. Tok/Pos N->E beside actual h16c'
        'at y156.540..163.644 M4pitch0.192. Die GEN must reassign faces/transport from actual abstract.'
        'No opcode/frame/data edge changed.'
    )
    (dst / 'spec.json').write_text(json.dumps(spec, indent=1) + '\n')
    (dst / 'spine.tcl').write_text(f'''# Same clock families/edges; physical local subroots, no new domain boundary.
set ::env(OT_SPINE_PORTS) ck_core,ck_hr
set ::env(OT_SPINE_SYM) 1
set ::env(OT_SPINE_RC_CAL) 0
set ::env(OT_SPINE_ITERS) 10
set ::env(OT_SPINE_BIN) 30
set ::env(OT_SPINE_LEAF_N) {leaf}
source /src/physical/common_flow/clock_spine.tcl
''')
    head = '''# Physical ownership of the exact placed-sink copy recut; no timing exception.
set q13_block [ord::get_db_block]
set q13_dbu [$q13_block getDbUnitsPerMicron]
'''
    head += 'set q13_owners [dict create ' + ' '.join(n + ' ' + z for n, z in owners.items()) + ']\n'
    head += 'set q13_zones [dict create ' + ' '.join(z + ' {' + ' '.join(map(str, b)) + '}' for z, b in zones.items()) + ']\n'
    body = '''set q13_groups {}; set q13_counts {}
dict for {z bx} $q13_zones {
 set region [odb::dbRegion_create $q13_block ot_q13_$z]
 $region setRegionType INCLUSIVE
 lassign $bx x0 y0 x1 y1
 odb::dbBox_create $region [expr {round($x0*$q13_dbu)}] [expr {round($y0*$q13_dbu)}] [expr {round($x1*$q13_dbu)}] [expr {round($y1*$q13_dbu)}]
 dict set q13_groups $z [odb::dbGroup_create $region ot_q13_$z]
 dict set q13_counts $z 0
}
set q13_seen {}
foreach i [$q13_block getInsts] {
 set root [regsub {[/.$].*$} [$i getName] {}]
 if {![dict exists $q13_owners $root]} continue
 if {[$i isFixed] || [[$i getMaster] isBlock]} {error "CTLM13 copy unexpectedly fixed/hard: $root"}
 set old [$i getGroup]
 if {$old ne "NULL" && $old ne ""} {$old removeInst $i}
 set z [dict get $q13_owners $root]
 [dict get $q13_groups $z] addInst $i
 dict incr q13_counts $z
 dict set q13_seen $root 1
}
dict for {n z} $q13_owners {if {![dict exists $q13_seen $n]} {error "CTLM13 actual mapped copy absent: $n"}}
puts "CTLM13_COPY_REGIONS PASS owners=[dict size $q13_seen] cells=$q13_counts"
'''
    (dst / 'copy_regions.tcl').write_text(head + body)
    (dst / 'README.md').write_text(f'''# CTLM safe13{suffix}: actual load-side copies and spatial clocks

Component candidate on exact RR2 base263ad92c3. Same777.6x734.4 outline and13 hard blocks.
Tok/Pos move to E beside actual CLOSED h16c ports. No old-view alias: H16ZA binds only
after its actual view closes and an enlarged parent is generated.

14 actual placed mixed-copy groups,1119 pins,+2 identical combinational copies,0 FF or
state/clock/data edges. Canonical comparison finds0non-identical drivers. Helpers are
byte-identical RR2.82 copy owners are assigned W0/W1/E0/E1 from actual placed sinks;
unknown groups remain explicitly unchanged. Clock spine:existing ck_core/ck_hr,bin30,
leaf{leaf}. Same clock families and existing core/hr landed crossings; no new exception.

Checklist: pinsFIXED Tok/Pos E grants; reachPENDING actual wirelint; fanoutPENDING
mapped32 census; depthUNCHANGED identical operators; storageUNCHANGED macros;
floorplanSAME as actual safe12c GPLRC0; clockPENDING CTSspread; scheduleUNCHANGED0edges.
Not selectedQ73, HP/RR2 integration, physical timing PASS or new H16ZA binding.
''')
    print(name, 'owners', len(owners))
