#!/usr/bin/env python3
"""Read existing producer sources/build records/headers; never compile or run."""
import argparse
import hashlib
import json
import re
import shlex
from pathlib import Path


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--lane',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();cases={}
    for directory,top in [('norm_leaf_partials_r1','tb_norm_leaf_source'),('norm_xfin_r1','tb_norm_xfin_source')]:
        run=a.lane/directory;obj=run/'obj';receipt=json.loads((run/'receipt.json').read_text())
        vf=obj/('V'+top+'__verFiles.dat');command=next(l[3:-1] for l in vf.read_text().splitlines() if l.startswith('C "'))
        argv=shlex.split(command)
        assert not any(x in argv for x in ['--bbox-unsup','--bbox-sys','--blackbox-unsup'])
        inputs=[Path(x) for x in argv if x.endswith(('.sv','.v'))]
        assert len(inputs)==43,(directory,len(inputs)) # 42 pinned RTL files + bench
        actual={};bodies={}
        for path in inputs:
            text=path.read_text();h=sha(path)
            if path.name==top+'.sv':
                assert h==receipt['bench_sha256'];bench=dict(path=str(path),sha256=h);continue
            matches=[rel for rel in receipt['source_sha256'] if str(path).endswith('/'+rel)]
            assert len(matches)==1,(path,matches)
            rel,=matches;assert h==receipt['source_sha256'][rel]
            assert 's81_ph/' not in rel
            assert not re.search(r'\bot_s81ph_mem1r1w\b',text),rel
            actual[rel]=h
            # Preserve each actual source body identity, beyond module names.
            bodies[rel]=dict(file_sha256=h,module_declarations=re.findall(r'\bmodule\s+([A-Za-z_]\w*)',re.sub(r'//[^\n]*|/\*.*?\*/','',text,flags=re.S)))
        assert actual==receipt['source_sha256'] and len(actual)==42
        headers={}
        for path in sorted(obj.glob('*.h')):
            text=path.read_text();assert 'ot_s81ph_mem1r1w' not in text
            headers[path.name]=dict(sha256=sha(path),bytes=path.stat().st_size)
        sym=obj/('V'+top+'__Syms.h');symbols=sym.read_text()
        instances=[l.strip() for l in symbols.splitlines() if re.search(r'\bTOP(?:__\w+)?;',l)]
        root=obj/('V'+top+'___024root.h');root_text=root.read_text()
        # Flattened instance state is retained by the existing root header.
        hierarchy=sorted(set(re.findall(top+r'__DOT__([A-Za-z_][A-Za-z_0-9]*)(?:__DOT__|__BRA__)',root_text)))
        build=(run/'build.log').read_text()
        assert not re.search(r'%Error|MODMISSING|PINNOTFOUND',build)
        binary=obj/('V'+top);assert binary.is_file()
        cases[directory]=dict(receipt_sha256=sha(run/'receipt.json'),status=receipt['status'],
            actual_compiler_command=command,compiler_record_sha256=sha(vf),source_count=42,
            source_sha256=actual,source_body_declarations=bodies,bench=bench,
            generated_headers=headers,symbol_table_sha256=sha(sym),actual_module_instance_state=instances,
            flattened_root_header_sha256=sha(root),flattened_instance_roots=hierarchy,
            binary_sha256=sha(binary),build_log_sha256=sha(run/'build.log'),
            unresolved_module_errors=[],mem1r1w_body_present=False,mem1r1w_instance_present=False,
            blackbox_compile_options=[],argument_file_or_implicit_source_glob=False)
    out=dict(schema='opentallas.s81.norm_producer_mem_exclusion.v1',status='EXISTING_COMPILED_SOURCE_AND_GENERATED_CONE_EXCLUSION_PASS',
        cases=cases,excluded_module='ot_s81ph_mem1r1w',excluded_variants=['b3aad03106bbd37ce5a7e670862db615b4283a13dd9318d919b0e01f12ca909c','151ce45020da1396af30fb17f275fcddb3257c4e216ff8b7ae92e5bd9e85a915'],
        new_compile=False,new_simulator_run=False,
        conclusion='Neither memory variant is in either actual 42-file producer compile or generated instance state. Aggregate memory precedence error does not affect sealed VP/VN/VQ/XFIN component numbers.',
        qualification='Exact component sources only; no shipping MU72 transport/global-clock/global-programme continuity claim; entry40 HOST proof and later L0B normalized-SO proof are separate.')
    a.out.write_text(json.dumps(out,indent=1)+'\n');print(out['status'])


if __name__=='__main__':main()
