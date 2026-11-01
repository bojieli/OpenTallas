"""Reviewed native clock contracts must preserve per-register input-root identity."""
from pathlib import Path
import subprocess

SOURCE=Path(__file__).with_name('f4_chain_leaf.tcl')

def run(extra):
    source=SOURCE.read_text().split('\nf4::run\n')[0]
    mock=r'''
proc bp_a {m} {if {$m eq "getIoType"} {return INPUT};return clk_a}
proc bp_b {m} {if {$m eq "getIoType"} {return INPUT};return clk_b}
proc a {m} {if {$m eq "getBTerms"} {return bp_a};return {}}
proc b {m} {if {$m eq "getBTerms"} {return bp_b};return {}}
proc leaf_a {m} {return {}}
proc leaf_b {m} {return {}}
proc unknown {m} {return {}}
proc loop_net {m} {return {}}
proc leaf_buf_a {m} {if {$m eq "getMaster"} {return buf_master};return in_a}
proc leaf_buf_b {m} {if {$m eq "getMaster"} {return buf_master};return in_b}
proc loop_buf {m} {if {$m eq "getMaster"} {return buf_master};return in_loop}
proc in_a {m} {if {$m eq "isInputSignal"} {return 1};return a}
proc in_b {m} {if {$m eq "isInputSignal"} {return 1};return b}
proc in_loop {m} {if {$m eq "isInputSignal"} {return 1};return loop_net}
proc buf_master {m} {return BUFx12_ASAP7_75t_R}
proc f4::drv {n} {switch $n {leaf_a {return leaf_buf_a} leaf_b {return leaf_buf_b} loop_net {return loop_buf} default {return {}}}}
'''
    p=subprocess.run(['tclsh'],input=source+'\n'+mock+'\n'+extra,text=True,capture_output=True)
    assert p.returncode==0 and not p.stderr,p.stderr

def test_native_ancestry_preserves_roots_and_rejects_unknown_or_cyclic_trees():
    run(r'''
set ::env(OT_DTAP_PORTS) {clk_a clk_b}
if {![f4::same_native_root leaf_a a]} {error "same-root co-leafing rejected"}
if {[f4::same_native_root leaf_a leaf_b]} {error "cross-native-root co-leafing allowed"}
if {[f4::same_native_root unknown unknown]} {error "unknown root accepted"}
if {[f4::same_native_root loop_net loop_net]} {error "cyclic root accepted"}
set ::env(OT_DTAP_PORTS) {clk_b}
if {[f4::same_native_root leaf_a a]} {error "root outside reviewed contract accepted"}
''')

def test_legacy_behavior_and_both_mutation_sites_remain_explicit():
    run('unset -nocomplain ::env(OT_DTAP_PORTS)\nif {![f4::same_native_root leaf_a leaf_b]} {error "legacy default changed"}\n')
    text=SOURCE.read_text()
    assert text.count('if {![f4::same_native_root')==2
    for prior in text.split('$cc disconnect')[:-1]:
        assert prior.rfind('f4::same_native_root')>prior.rfind('$cc connect')
