#!/usr/bin/env python3
"""Reproduce selected-source causal fixtures against the actual parser and proposed guard.
Run: python3 results/arch/kv_gen9_reconcile_0720/check_binding_source_guard.py --root REPO
"""
import argparse
import importlib.util
import json
from pathlib import Path
import tempfile

ap=argparse.ArgumentParser();ap.add_argument('--root',default='.');a=ap.parse_args();root=Path(a.root).resolve()
p=root/'tools/die_port_bind.py';spec=importlib.util.spec_from_file_location('pb',p);pb=importlib.util.module_from_spec(spec);spec.loader.exec_module(pb)
s=(root/'tools/qwen_kv_die/kv_bound_netlist.py').read_text();start=s.index('    for _master in sorted(');end=s.index('    if _expanded is not None:',start)
code=compile('def check():\n'+''.join('    '+line+'\n' for line in s[start:end].splitlines())+'\ncheck()','actual-selected-source-guard','exec')
checks=[]
with tempfile.TemporaryDirectory() as td:
    fixture=Path(td);selected=fixture/'selected.sv';fallback=fixture/'fallback.sv'
    fallback.write_text('module wanted(input wire hck); endmodule\n')
    def run(label,text,indexed_path,expected):
        if text is not None:selected.write_text(text)
        elif selected.exists():selected.unlink()
        # Index entries are actual parsed Module objects, including their actual source path.
        parser_file=indexed_path if indexed_path.exists() else fallback
        indexed=pb.parse_modules(pb.preprocess(pb.strip_comments(parser_file.read_text()),{}),str(indexed_path))
        module=next((m for m in indexed if m.name=='wanted'),None)
        if module is None:module=pb.parse_modules(fallback.read_text(),str(fallback))[0]
        env=dict(ROOT=fixture,PB=pb,Path=Path,insts=[('wrapper','inst',{}, {})],bindings={'wrapper':dict(file='selected.sv',module='wanted')},_expanded=None,idx={'wanted':module})
        try:exec(code,env)
        except SystemExit as e:
            assert expected and expected in str(e),(label,str(e));checks.append(dict(case=label,verdict='EXPECTED_REFUSAL',message=str(e)));return
        assert expected is None,label
        checks.append(dict(case=label,verdict='PASS'))
    run('exact selected source','module wanted(input wire ck); endmodule\n',selected,None)
    run('missing selected file',None,fallback,'source missing')
    run('missing module despite by-name fallback','module different(input wire ck); endmodule\n',fallback,'declares 0 copies')
    run('duplicate selected declarations','module wanted(input wire ck); endmodule\nmodule wanted(input wire hck); endmodule\n',selected,'declares 2 copies')
    run('wrong indexed provenance','module wanted(input wire ck); endmodule\n',fallback,'does not come from selected source')
print(json.dumps(checks,indent=2))
