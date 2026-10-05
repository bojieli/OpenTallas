"""Offline LP64 layout of the generated root's pointer prefix/anonymous POD groups.

No compiler, simulator, C++ expression evaluation or executable invocation.
Unknown types fail closed; the parsed prefix is validated against machine-code
anchors before any planned debugger read. This is not a generic C++ ABI parser.
"""
import re


def pod_size(t):
    primitive = {'CData': (1,1), 'SData': (2,2), 'IData': (4,4), 'QData': (8,8)}
    if t in primitive:
        return primitive[t]
    wide = re.fullmatch(r'VlWide<(\d+)>', t)
    if wide:
        n = int(wide[1])
        if n <= 0:
            raise ValueError('nonpositive wide length')
        return n*4, 4
    unpacked = re.fullmatch(r'VlUnpacked<(.+), (\d+)>', t)
    if unpacked:
        n = int(unpacked[2])
        if n <= 0:
            raise ValueError('nonpositive array length')
        size, alignment = pod_size(unpacked[1])
        return n*size, alignment
    raise ValueError('unsupported generated POD type: '+t)


def align(n, a):
    return (n+a-1)//a*a


def parse_layout(header):
    if re.search(r'\bvirtual\b', header):
        raise ValueError('virtual/root-vptr layout is unsupported')
    lines = header.splitlines()
    begin = next(i for i,line in enumerate(lines) if line.strip() == 'struct {')
    prefix = [v.strip() for v in lines[:begin]]
    cell_start = prefix.index('// CELLS')+1
    cell_end = prefix.index('// DESIGN SPECIFIC STATE')
    cells = [v for v in prefix[cell_start:cell_end] if v and not v.startswith('//')]
    if not cells or any(not re.fullmatch(r'\w+\* __PVT__\w+;',v) for v in cells):
        raise ValueError('root pointer-prefix schema differs')
    if not any('___024root final {' in line and ':' not in line for line in prefix):
        raise ValueError('root class must have no base classes')

    def group(i):
        offset, max_alignment, members = 0, 1, {}
        i += 1
        while lines[i].strip() != '};':
            line = lines[i].strip()
            if line == 'struct {':
                i, size, alignment, sub = group(i)
            elif not line or line.startswith('//'):
                i += 1
                continue
            else:
                line = re.sub(r'/\*.*?\*/','',line)
                macro = re.fullmatch(r'VL_OUT\((\w+),31,0\);',line)
                if macro:
                    t,name='IData',macro[1]
                else:
                    if not line.endswith(';') or ' ' not in line[:-1]:
                        raise ValueError('unsupported declaration: '+line)
                    t,name=line[:-1].rsplit(' ',1)
                size,alignment=pod_size(t)
                sub={name:{'offset':0,'bytes':size,'alignment':alignment,
                           'type':t,'line':i+1}}
                i+=1
            offset=align(offset,alignment)
            max_alignment=max(max_alignment,alignment)
            for name,value in sub.items():
                if name in members:
                    raise ValueError('duplicate generated member')
                members[name]={**value,'offset':value['offset']+offset}
            offset+=size
        return i+1,align(offset,max_alignment),max_alignment,members

    fields={}
    offset=len(cells)*8  # source-pinned x86-64 LP64 binary: 8-byte pointer/alignment.
    i=begin
    while i<len(lines):
        if lines[i].strip()=='struct {':
            i,size,alignment,sub=group(i)
            offset=align(offset,alignment)
            for name,value in sub.items():
                if name in fields:
                    raise ValueError('duplicate promoted generated member')
                fields[name]={**value,'offset':value['offset']+offset}
            offset+=size
        elif lines[i].strip() and not lines[i].strip().startswith('//'):
            break  # dynamic/complex trailing members intentionally not mapped.
        else:
            i+=1
    return {'fields':fields,'pointer_cells':len(cells),
            'parsed_prefix_bytes':offset,'first_unparsed_line':i+1}


def check_anchors(fields):
    expected={'tb_D1_scope_core__DOT__probe__DOT__dut__DOT__fault_r':0x28021,
              'tb_D1_scope_core__DOT__dbg_fs':0x5f0fc,
              'tb_D1_scope_core__DOT__probe__DOT__g_D1_current__DOT__violations':0x27fe2}
    for name,offset in expected.items():
        if fields[name]['offset'] != offset:
            raise ValueError('machine-code layout anchor mismatch: '+name)


def validate_plan(plan_path):
    import hashlib
    import json
    from pathlib import Path
    path=Path(plan_path).resolve()
    root=path.parents[3]
    plan=json.loads(path.read_text())
    def digest(p):
        return hashlib.sha256(Path(p).read_bytes()).hexdigest()
    for field in ("binary","program","GDB"):
        item=plan[field]
        if digest(item["path"]) != item["SHA256"]:
            raise ValueError("retained input hash mismatch: "+field)
    for name,expected in plan["source_SHA256"].items():
        if digest(root/name) != expected:
            raise ValueError("pinned original source mismatch: "+name)
    for name,expected in plan["layout"]["ABI_source_SHA256"].items():
        if digest(name) != expected:
            raise ValueError("Verilator ABI header mismatch")
    header=Path(plan["layout"]["header"])
    if digest(header) != plan["layout"]["header_SHA256"]:
        raise ValueError("generated root header mismatch")
    parsed=parse_layout(header.read_text())
    check_anchors(parsed["fields"])
    selected=json.loads((path.parent/"offsets.json").read_text())
    for item in selected.values():
        actual=parsed["fields"][item["member"]]
        if any(actual[key] != item[key] for key in ("offset","bytes","alignment","type","line")):
            raise ValueError("selected member layout mismatch")
    for name,expected in json.loads((path.parent/"artifact_SHA256.json").read_text()).items():
        if digest(path.parent/name) != expected:
            raise ValueError("plan artifact mismatch: "+name)
    return {"status":"PASS_OFFLINE_SOURCE_HASH_AND_LAYOUT_ONLY",
            "selected_fields":len(selected),"compiler_runs":0,"inferior_runs":0,
            "fresh_GO_required":True}


if __name__ == "__main__":
    import argparse
    import json
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan",help="Source-pinned capture-plan JSON; validation only")
    print(json.dumps(validate_plan(parser.parse_args().plan),indent=2))
