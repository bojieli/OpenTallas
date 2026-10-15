#!/usr/bin/env python3
"""Emit immutable source preflight before building the HC source component."""
import ast, hashlib, json, pathlib, sys
ROOT=pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools'))
# Extract the pure unified-model row without importing unrelated physical artifacts.
tree=ast.parse((ROOT/'tools/uarch_model.py').read_text())
row=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='s81_static_hc_source_model')
ns={}
exec(compile(ast.Module(body=[row],type_ignores=[]),'uarch_model.py','exec'),ns)
m=ns['s81_static_hc_source_model']()
m['inputs_sha256']={p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in (
    'tools/uarch_model.py','rtl/dsrom_sys/s81_ph/ot_s81ph_fp32_add_rne_preexp.sv',
    'rtl/rom/ot_w15_rom_oneshot_px_acceptedpop.sv','rtl/dsrom_sys/s81_ph/coll/dsfd_coll_xc.sv')}
print(json.dumps(m,indent=2,sort_keys=True))
