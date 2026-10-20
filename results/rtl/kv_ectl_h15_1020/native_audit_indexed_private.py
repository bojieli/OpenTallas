"""Private spelling adapter only. Original native-audit logic/state/params unchanged.

Not a production receipt authority. ROOT review required before adoption.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys


def signal_table(js, top='gold'):
    table={}
    for wire,n in js['modules'][top]['netnames'].items():
        if wire.startswith('$') or n.get('hide_name'):continue
        if re.search(r'\s',wire) or '\\' in wire:
            raise ValueError('unsupported source wire spelling '+repr(wire))
        bits=n['bits'];off=n.get('offset',0);upto=n.get('upto',0)
        for i,bit in enumerate(bits):
            if not isinstance(bit,int):continue
            idx=off+(len(bits)-1-i if upto else i)
            scalar=len(bits)==1 and off==0 and not upto
            logical=wire if scalar else f'{wire}[{idx}]'
            candidate=dict(wire=wire,index=None if scalar else idx,rtlil_bitindex=i,bit=bit,
                           spelling='\\'+wire+('' if scalar else f'[{i}]'))
            if logical in table and table[logical]['bit']!=bit:
                raise ValueError('ambiguous logical alias '+logical)
            table.setdefault(logical,candidate)
    return table


def rewrite(script, js):
    refs=signal_table(js);context=None;rows=[];out=[]
    for line in script.splitlines():
        if line=='cd':context=None
        elif line.startswith('cd '):context=line[3:]
        if line.startswith('connect -set '):
            fields=line.split()
            if len(fields)!=4:raise ValueError('unsupported connect statement '+line)
            target,name=fields[2:]
            if not re.fullmatch(r'S__[A-Za-z0-9_]+',target):raise ValueError('unsupported observation target '+target)
            if re.fullmatch(r"1'[01]",name):
                out.append(line);continue
            if context!='gold':raise ValueError('non-gold source observation '+line)
            if name not in refs:raise ValueError('missing exact source alias '+name)
            row=refs[name];new=f'connect -set {target} {row["spelling"]}'
            rows.append(dict(original=line,repaired=new,logical=name,**row));line=new
        out.append(line)
    if not rows:raise ValueError('no source observations in script')
    return '\n'.join(out)+'\n',rows


def main():
    tool=Path(__file__).resolve().parents[3]/'tools/qwen_kv_die/kv_param_native_audit.py'
    sys.path.insert(0,str(tool.parent));sys.path.insert(0,str(tool.parent.parent))
    spec=importlib.util.spec_from_file_location('canonical_native_audit',tool)
    a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a);original=a.run
    def run(cmd,work,log,timeout):
        work=Path(work)
        if '-s' in cmd:
            script=work/cmd[cmd.index('-s')+1]
            if script.is_file() and 'connect -set S__' in script.read_text():
                raw=script.read_text();js_path=work/'gold1.json'
                repaired,rows=rewrite(raw,json.loads(js_path.read_text()))
                original_path=script.with_suffix(script.suffix+'.original')
                if original_path.exists():raise ValueError('fresh private proof directory required')
                original_path.write_text(raw);script.write_text(repaired)
                packet=dict(scope='PRIVATE_EXACT_JSON_RESOLVED_RTLIL_BITINDEX_ONLY',
                    original_tool_sha256=hashlib.sha256(tool.read_bytes()).hexdigest(),
                    gold_json_sha256=hashlib.sha256(js_path.read_bytes()).hexdigest(),
                    original_sha256=hashlib.sha256(raw.encode()).hexdigest(),
                    repaired_sha256=hashlib.sha256(repaired.encode()).hexdigest(),
                    observations=len(rows),rows=rows)
                script.with_suffix(script.suffix+'.spelling.json').write_text(json.dumps(packet,indent=2)+'\n')
        return original(cmd,work,log,timeout)
    a.run=run
    return a.main(sys.argv[1:])

if __name__=='__main__':raise SystemExit(main())
