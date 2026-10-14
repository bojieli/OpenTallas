#!/usr/bin/env python3
"""Production HC golden gate using the comb's explicit child clock interface.

Only the build-directory caller is patched. Source hashes and the exact caller
patch are preserved. mode=1 drives 14 separate leaf entries at the ideal common
boundary phase; mode=2 stops the actual sequencer leaf clock and must fail.
No physical insertion or skew closure is claimed by this functional test.
"""
import hashlib
import json
import sys
from pathlib import Path
import hc_gate as gate

mode = int(sys.argv[sys.argv.index('--native-mode')+1])
idx = sys.argv.index('--native-mode')
del sys.argv[idx:idx+2]
assert mode in (1,2)
original = gate.tile_edit


def edit(srcs, obj, probes, tmut):
    srcs = original(srcs,obj,probes,tmut)
    native = gate.ROOT/'rtl/dsrom_sys/s81_suhc/hier/dsfd_sp_hc_comb_native.sv'
    srcs.append(native)
    for i, path in enumerate(srcs):
        if path.name != 'dsfd_sp_hc.sv':
            continue
        text = path.read_text()
        assert text.count('ot_s81_hc_comb #(')==1
        text=text.replace('ot_s81_hc_comb #(', 'dsfd_sp_hc_comb_native #(',1)
        old = '.DW(CSPLIT ? 6 : 5), .RET_EXTRA(CNL_PIN),'
        assert text.count(old)==1
        text=text.replace(old,'.DW(CSPLIT ? 6 : 5), .RET_EXTRA(CNL_PIN), .PHYS_CLK(1),')
        clock = '{14{sk}}' if mode==1 else "{10{sk}, 1'b0, 3{sk}}"
        # SystemVerilog replication inside a concatenation requires braces.
        clock = '{14{sk}}' if mode==1 else "{{10{sk}}, 1'b0, {3{sk}}}"
        pos=text.index(') u_cb (')
        text=text[:pos]+text[pos:].replace(') u_cb (',f') u_cb (\n        .sk_leaf({clock}),',1)
        dest=obj/'native_dsfd_sp_hc.sv';dest.write_text(text);srcs[i]=dest
        manifest=dict(mode=mode, source=str(path), source_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                      actual_parent_master='dsfd_sp_hc_comb_native',
                      actual_parent_source_sha256=hashlib.sha256(native.read_bytes()).hexdigest(),
                      edited_sha256=hashlib.sha256(text.encode()).hexdigest(),
                      clock_connections=clock,actual_comb_parameter_PHYS_CLK=1,
                      scope='functional common ideal boundary phase only; real clocks require phi-R per child',
                      gate_driver_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        (obj/'native_clock_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        break
    else:
        raise AssertionError('native comb caller not found')
    return srcs


gate.tile_edit=edit
raise SystemExit(gate.main())
