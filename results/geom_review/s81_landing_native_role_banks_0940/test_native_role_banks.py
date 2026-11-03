"""Pinned native membership/cone guards; no OpenDB/physical/model replay."""
import copy
import gzip
import hashlib
import importlib.util
import json
import re
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parents[2] / 'tools' / 'die_plan'
SPEC = importlib.util.spec_from_file_location('role_lp', TOOLS / 'landing_place.py')
LP = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(LP)
TCL = (TOOLS / 'landing_placement.tcl').read_text()
FIX = json.load(gzip.open(HERE / 't51_native_roles.json.gz', 'rt'))


def atom(x):
    text = str(x)
    assert not any(c in text for c in '\n\r\0') and text.count('{') == text.count('}')
    return '{' + text + '}'


def seq(xs):
    return ' '.join(atom(x) for x in xs)


def typ(config=True):
    t = json.load(gzip.open(HERE / 'source_type.json.gz', 'rt'))
    if config:
        t['clock']['landing_contract']['bands']['ft2_i']['native_role_banks'] = copy.deepcopy(FIX['config'])
    return t


def proc(name):
    return re.search(r'^proc ' + re.escape(name) + r' .*?^}\n', TCL, re.M | re.S).group(0)


def native_setup(fix):
    """Actual native nonPG cone; omitted foreign sinks are never queried by these helpers."""
    lines = ['namespace eval F {}', 'set ff_blk B', 'set ff_dbu 1000', 'set ff_sw 54',
             'set cland_ff_fill .9', 'set cland_multi {}', 'set cland_done {}',
             'set cland_role_lib_cache {}', 'set cland_role_seen {}',
             'set cland_cursor {}', 'set cland_col_cursor {}', 'set ::placed {}',
             'set ::env(OT_CLAND_PINSLOT) 0']
    cells = fix['cells']
    ids = {c[0]: f'I{k}' for k, c in enumerate(cells)}
    mids = {m: f'M{k}' for k, m in enumerate(fix['masters'])}
    nids = {r[1]: f'N{r[0]}' for r in fix['nets']}
    for master, m in fix['masters'].items():
        mid = mids[master]
        lines += [f'set F::master({mid},name) {atom(master)}',
                  f'set F::master({mid},width) {m["width_dbu"]}',
                  f'set F::master({mid},height) {m["height_dbu"]}',
                  f'set F::master({mid},clocks) {atom(seq(m["clock_pins"]))}',
                  f'proc {mid} {{method args}} {{return [F::master_call {mid} $method {{*}}$args]}}']
        lp = []
        for k, (pin, io, sig) in enumerate(m['pins']):
            obj = f'L{mid}_{k}'
            lp.append(obj)
            lines += [f'set F::libpin({obj},name) {atom(pin)}', f'set F::libpin({obj},clock) {int(pin in m["clock_pins"])}']
        lines.append(f'set F::master({mid},libpins) {atom(seq(lp))}')
    for c in cells:
        n, master, bb, loc, orient, status, dnt = c
        iid = ids[n]
        lines += [f'set F::cell({iid},name) {atom(n)}', f'set F::cell({iid},master) {mids[master]}',
                  f'set F::cell({iid},bbox) {atom(seq(bb))}', f'set F::cell({iid},status) {atom(status)}',
                  f'set F::cell({iid},terms) {{}}', f'dict set F::names {atom(n)} {iid}',
                  f'proc {iid} {{method args}} {{return [F::cell_call {iid} $method {{*}}$args]}}',
                  f'proc X{iid} {{method}} {{return [lindex $F::cell({iid},bbox) [lsearch {{xMin yMin xMax yMax}} $method]]}}']
    for k, name, sig, terms, bterms in fix['nets']:
        nid = f'N{k}'
        lines += [f'set F::net({nid},name) {atom(name)}', f'set F::net({nid},terms) {{}}', f'set F::net({nid},ports) {{}}',
                  f'proc {nid} {{method}} {{return [F::net_call {nid} $method]}}']
        for z, (inst, pin, io, psig) in enumerate(terms):
            iid = ids[inst]
            obj = f'J{k}_{z}'
            lines += [f'set F::term({obj},inst) {iid}', f'set F::term({obj},name) {atom(pin)}',
                      f'set F::term({obj},io) {atom(io)}', f'set F::term({obj},sig) {atom(psig)}',
                      f'set F::term({obj},net) {nid}', f'lappend F::net({nid},terms) {obj}',
                      f'lappend F::cell({iid},terms) {obj}', f'set F::cell({iid},pin,{pin}) {obj}',
                      f'proc {obj} {{method}} {{return [F::term_call {obj} $method]}}',
                      f'proc T{obj} {{method}} {{return [F::mterm_call {obj} $method]}}']
    ports = []
    for k, (name, io, sig, net, boxes) in enumerate(fix['ports']):
        obj = f'P{k}'; ports.append(obj)
        assert net in nids, (name, net)
        coords = [b for layer, b in boxes]
        bb = [min(b[0] for b in coords), min(b[1] for b in coords), max(b[2] for b in coords), max(b[3] for b in coords)] if coords else [0, 0, 0, 0]
        lines += [f'set F::port({obj},name) {atom(name)}', f'set F::port({obj},io) {atom(io)}',
                  f'set F::port({obj},net) {nids[net]}', f'set F::port({obj},bbox) {atom(seq(bb))}',
                  f'dict set F::ports {atom(name)} {obj}', f'lappend F::net({nids[net]},ports) {obj}',
                  f'proc {obj} {{method}} {{return [F::port_call {obj} $method]}}',
                  f'proc X{obj} {{method}} {{return [lindex $F::port({obj},bbox) [lsearch {{xMin yMin xMax yMax}} $method]]}}']
    lines += [f'set F::insts {atom(seq(ids.values()))}', f'set F::bterms {atom(seq(ports))}']
    lines.append(r'''
proc F::master_call {obj method args} {
 switch $method {getName {return $::F::master($obj,name)} isBlock {return 0} getWidth {return $::F::master($obj,width)} getHeight {return $::F::master($obj,height)} default {error "unexpected master API $method"}}
}
proc F::cell_call {obj method args} {
 switch $method {getName {return $::F::cell($obj,name)} getMaster {return $::F::cell($obj,master)} getITerms {return $::F::cell($obj,terms)} getPlacementStatus {return $::F::cell($obj,status)} getBBox {return X$obj} findITerm {return $::F::cell($obj,pin,[lindex $args 0])} default {error "unexpected cell API $method"}}
}
proc F::term_call {obj method} {
 switch $method {getMTerm {return T$obj} getInst {return $::F::term($obj,inst)} getNet {return $::F::term($obj,net)} default {error "unexpected iterm API $method"}}
}
proc F::mterm_call {obj method} {
 switch $method {getName {return $::F::term($obj,name)} getIoType {return $::F::term($obj,io)} getSigType {return $::F::term($obj,sig)} default {error "unexpected mterm API $method"}}
}
proc F::net_call {obj method} {
 switch $method {getName {return $::F::net($obj,name)} getITerms {return $::F::net($obj,terms)} getBTerms {return $::F::net($obj,ports)} default {error "unexpected net API $method"}}
}
proc F::port_call {obj method} {
 switch $method {getName {return $::F::port($obj,name)} getIoType {return $::F::port($obj,io)} getNet {return $::F::port($obj,net)} getBBox {return X$obj} default {error "unexpected bterm API $method"}}
}
proc B {method args} {
 switch $method {getInsts {return $::F::insts} getBTerms {return $::F::bterms} findBTerm {set name [lindex $args 0];if {[dict exists $::F::ports $name]} {return [dict get $::F::ports $name]};return NULL} default {error "unexpected block API $method"}}
}
proc get_cells {args} {set name [lindex [lindex $args end] 0];if {[dict exists $::F::names $name]} {return [list [dict get $::F::names $name]]};return {}}
proc get_lib_cells {args} {set i [lindex [lindex $args end] 0];return [list [$i getMaster]]}
proc get_lib_pins {args} {set m [lindex [lindex $args end] 0];return $::F::master($m,libpins)}
proc get_property {obj property} {switch $property {name {return $::F::libpin($obj,name)} is_clock {return $::F::libpin($obj,clock)} default {error "unexpected Liberty property $property"}}}
proc cland_occupy {args} {}
proc cland_put {i rect tag sp cur} {lappend ::placed [$i getName];dict set ::cland_done [$i getName] 1}
''')
    return '\n'.join(lines) + '\n'


def run(body):
    result = subprocess.run(['tclsh'], input=body, text=True, capture_output=True)
    assert result.returncode == 0 and not result.stderr, (result.stdout[-2000:], result.stderr[-4000:])
    return result.stdout


def helpers():
    names = ['cland_group_insts', 'cland_ffkey', 'cland_kbit', 'cland_nearest_bit',
             'cland_ctl_rekey', 'cland_dsel_wch', 'cland_start_bterm_name', 'cland_place_ff']
    return '\n'.join(proc(n) for n in names) + '\n'


def support():
    block = re.findall(r'^# BEGIN NATIVE_ROLE_BANKS\n(.*?)^# END NATIVE_ROLE_BANKS\n', TCL, re.M | re.S)
    return next(s for s in block if 'proc cland_role_prepare' in s)


def test_absent_optin_preserves_full_pinned_t51_generated_bytes():
    class P:
        types = {'t': typ(False)}
    old = json.loads((HERE / 'legacy_output.json').read_text())
    assert hashlib.sha256(LP.tcl(P(), 't').encode()).hexdigest() == old['generated_tcl_sha256']
    assert hashlib.sha256(LP._placement_source(False).encode()).hexdigest() == old['template_sha256']
    assert 'cland_native_role_banks' not in LP.tcl(P(), 't')


def test_python_metadata_rejects_duplicate_and_bad_counts():
    t = typ()
    band = t['clock']['landing_contract']['bands']['ft2_i']
    bank = band['native_role_banks']['banks'][0]
    bank['members'][1] = copy.deepcopy(bank['members'][0])
    with pytest.raises(ValueError, match='duplicate'):
        LP._native_role_config('t', t)
    t = typ(); t['clock']['landing_contract']['bands']['ft2_i']['native_role_banks']['banks'][0]['expected_members'] -= 1
    with pytest.raises(ValueError, match='count'):
        LP._native_role_config('t', t)


@pytest.mark.parametrize('reverse', [False, True])
def test_pinned_2679_native_members_counts_and_legacy_mirrored_order(reverse):
    t = typ(); cfg = LP._native_role_config('t', t)
    setup = native_setup(FIX) + helpers()
    tag = 'ring:ft2_i+ffr' if reverse else 'ring:ft2_i+ff'
    held = '\n'.join('dict set cland_done ' + atom(n) + ' 1' for n in FIX['held_status_names']) + '\n'
    body = setup + held + f'cland_place_ff {FIX["prefix"]} {{4.32 1099.44 175 1222.56}} {tag}\nset legacy $::placed\n'
    body += 'set ::placed {};set cland_done {}\n' + held + cfg
    body += 'set cland_groups {{' + FIX['prefix'] + ' {4.32 1209.6 155.52 1222.56} ' + tag + '}}\n'
    body += support() + f"\ncland_role_place {FIX['prefix']} {tag}\n"
    body += r'''
if {[llength $::placed] != 2677} {error "native member coverage count"}
set expected {}
foreach row [dict get $::cland_native_role_banks u_cland_ft2_i banks] {
 lassign $row bank port filter count first rect qualified
 set ordered {};foreach name $legacy {if {[dict exists $qualified $name]} {lappend ordered $name}}
 lappend expected {*}$ordered
}
if {$expected ne $::placed} {error "native bank filtering changed legacy cland_ffkey mirrored/control order"}
foreach name [dict keys [dict get $::cland_role_prepared u_cland_ft2_i members]] {puts "BANK $name [llength [dict get $::cland_role_prepared u_cland_ft2_i members $name]]"}
puts "PINNED_NATIVE_ROLES PASS"
'''
    out = run(body)
    assert 'BANK forwarded_write 2077' in out and 'BANK mission_read 600' in out
    assert 'PINNED_NATIVE_ROLES PASS' in out


@pytest.mark.parametrize('fault', ['missing', 'duplicate', 'unknown_clock', 'duplicate_bit_capture', 'resized_member'])
def test_native_membership_faults_fail_before_any_bank_move(fault):
    fix = FIX
    setup = native_setup(fix) + helpers()
    target = FIX['config']['banks'][0]['members'][0]['name']
    setup += 'set target [dict get $::F::names ' + atom(target) + ']\n'
    if fault == 'missing':
        setup += 'set at [lsearch -exact $::F::insts $target];set ::F::insts [lreplace $::F::insts $at $at]\n'
    elif fault == 'duplicate':
        setup += 'lappend ::F::insts $target\n'
    elif fault == 'unknown_clock':
        setup += 'set it $::F::cell($target,pin,CLK);set ::F::term($it,net) UNKNOWN_CLOCK_NET\n'
    elif fault == 'duplicate_bit_capture':
        names = [m['name'] for m in FIX['config']['banks'][0]['members']]
        first = next(n for n in names if 's_d[0][0]' in n.replace('\\', ''))
        second = next(n for n in names if 's_d[0][1]' in n.replace('\\', ''))
        setup += 'set a [dict get $::F::names ' + atom(first) + '];set b [dict get $::F::names ' + atom(second) + ']\n'
        setup += 'set ai $::F::cell($a,pin,D);set bi $::F::cell($b,pin,D);set ::F::term($ai,net) $::F::term($bi,net)\n'
    else:
        old = next(m['master'] for m in FIX['config']['banks'][0]['members'] if m['name'] == target)
        role = FIX['config']['ff_pin_roles'][old]
        other = next(m for m, r in FIX['config']['ff_pin_roles'].items() if m != old and r == role and m in FIX['masters'])
        setup += 'foreach key [array names ::F::master *,name] {if {$::F::master($key) eq ' + atom(other) + '} {set ::F::cell($target,master) [lindex [split $key ,] 0];break}}\n'
    setup += LP._native_role_config('t', typ())
    setup += 'set cland_groups {{u_cland_ft2_i {4.32 1209.6 155.52 1222.56} ring:ft2_i+ffr}}\n'
    setup += 'set failed [catch {\n' + support() + '\n} why]\n'
    setup += 'if {!$failed || [llength $::placed]} {error "native membership guard did not fail before placement"}\nputs "GUARD_PASS $why"\n'
    out = run(setup)
    assert 'GUARD_PASS OT_CLAND_ROLE' in out
