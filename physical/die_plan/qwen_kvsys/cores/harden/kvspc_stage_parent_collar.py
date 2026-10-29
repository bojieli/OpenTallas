#!/usr/bin/env python3
"""Stage an opt-in actual-provider source/recipe delta; never edit the parent.

The emitted recipe first selects the patched native definitions, then composes
the existing param_regen with their explicit per-instance collar enable. The
normal binder and provider source closure consume these definitions directly.
No latency model or physical result can substitute for this source selection.
"""
import argparse
import json
from pathlib import Path
from kvspc_native_collar import TARGETS, transform


def stage(recipe, normal_source, hhp_source, out):
    recipe, out = Path(recipe).resolve(), Path(out).resolve()
    old = json.loads(recipe.read_text())
    if old.get("kvspc_native_input_collar"):
        raise ValueError("recipe already stages native PC collar")
    base = (recipe.parent / old.get("base", ".")).resolve()
    original_hook = Path(old["param_regen"]["file"])
    if not original_hook.is_absolute():
        original_hook = base / original_hook
    if not original_hook.is_file():
        raise ValueError("existing parameter hook is missing")
    out.mkdir(parents=True, exist_ok=False)
    receipts, providers, replacement = [], [], {}
    for module, source in zip(TARGETS, [normal_source, hhp_source]):
        source = Path(source).resolve()
        text, receipt = transform(source.read_text(), module)
        dest = out / (module + "_native_provider.sv")
        dest.write_text(text)
        receipts.append(dict(receipt, original_source=str(source), provider=str(dest)))
        providers.append(str(dest))
        replacement[str(source)] = str(dest)
    helper = Path(__file__).with_name("kvspc_native_collar.py").resolve()
    hook = out / "regen_with_pc_input_collar.py"
    hook.write_text('''# Generated opt-in composition; all existing parameter rules execute first.
import importlib.util
def load(name, path):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module
def regen(ctx):
    original=load("original_kv_param_regen", ORIGINAL).regen(ctx)
    event=load("native_pc_collar", HELPER).regen_parameters(ctx)
    params={path:dict(values) for path,values in original["params"].items()}
    for path,values in event["params"].items():
        target=params.setdefault(path,{})
        for name,value in values.items():
            if name in target:raise ValueError("PC collar parameter already set by another hook")
            target[name]=value
    return dict(params=params,record=dict(existing=original.get("record",{}),pc_input_collar=event["record"]))
'''.replace("ORIGINAL", repr(str(original_hook))).replace("HELPER", repr(str(helper))))
    new = dict(old)
    # Absolute base preserves every existing repository-relative input, including
    # compose tables and netlists. Only the two explicitly preferred providers and
    # composed parameter hook differ from the owner's current recipe.
    new["base"] = str(base)
    for key in ("files", "prefer"):
        entries=[]
        for value in old.get(key, []):
            resolved=Path(value) if Path(value).is_absolute() else base / value
            target=replacement.get(str(resolved.resolve()),value)
            if target not in entries:entries.append(target)
        new[key]=providers+[value for value in entries if value not in providers]
    new["param_regen"] = dict(old["param_regen"], file=str(hook))
    event = dict(schema="opentallas.kvspc.parent_input_collar.v1", enabled=True,
                 input_cycles=1, boot_cycles=1, throughput_cycles=0,
                 default_enabled=False, source_recipe=str(recipe), providers=receipts,
                 adoption="candidate only; requires current source/physical qualification and coherent R8/compiler event")
    new["kvspc_native_input_collar"] = event
    (out / "recipe_pc_input_collar.json").write_text(json.dumps(new, indent=2)+"\n")
    (out / "event.json").write_text(json.dumps(event, indent=2)+"\n")
    return event


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recipe",required=True)
    ap.add_argument("--normal-source",required=True)
    ap.add_argument("--hhp-source",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    print(json.dumps(stage(a.recipe,a.normal_source,a.hhp_source,a.out),indent=2))


if __name__=="__main__":main()
