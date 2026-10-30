#!/usr/bin/env python3
"""Opt-in face capture for qkd_hr_phy_adp's credit RETURN (not ready).

One return edge, same credit capacity, no data pipeline. Default parameter0 preserves
old behavior. Parent schedule/model must price the returned-credit round trip.
Input is the already-proved flattened hr_face_ports output; never applied by default.
"""
import argparse,json,re,hashlib
from pathlib import Path

def transform(src,module='qkd_hr_phy_adp',new_module=None,mutant=False):
 target=new_module or module
 pat=r'(\bmodule\s+)'+re.escape(module)+r'(\s*\()'
 s,n=re.subn(pat,lambda m:m[1]+target+' #(parameter integer CREDIT_RETURN_CAPTURE = 0)'+m[2],src,count=1)
 if n!=1:raise ValueError('expected one unparameterized PHY adapter top')
 # Only RHS occurrences. Aliases and the actual o_cred increment consume the same captured pulse.
 used=0;lines=[]
 for line in s.splitlines():
  if re.match(r'\s*assign\s',line) and '=' in line:
   lhs,rhs=line.split('=',1)
   rhs,n=re.subn(r'(?<![.\\\w])r_cr(?!\w)', '_hr_credit_i', rhs); used+=n;line=lhs+'='+rhs
  lines.append(line)
 if used!=3:raise ValueError(f'expected 3 actual/alias r_cr uses, found {used}')
 s='\n'.join(lines)+'\n'
 # Insert after the top's original port declarations. The generated file has no submodules.
 i=s.index('\n  assign ')
 expr='~r_cr' if mutant else 'r_cr'
 body='''
  wire [0:0] _hr_credit_i;
  generate if (CREDIT_RETURN_CAPTURE != 0) begin: g_hr_credit_capture
    (* keep = 1, dont_touch = 1 *) reg [0:0] credit_q;
    always @(posedge ck or negedge rst_n)
      if (!rst_n) credit_q <= 1'b0; else credit_q <= EXPR;
    assign _hr_credit_i = credit_q;
  end else begin: g_hr_credit_direct
    assign _hr_credit_i = r_cr;
  end endgenerate
'''.replace('EXPR',expr)
 return s[:i]+body+s[i:],dict(schema='opentallas.hr.credit_capture.v1',module=target,default=0,return_latency_edges=1,credit_capacity_delta=0,registered_credit_uses=used,mutant=mutant,source_sha256=hashlib.sha256(src.encode()).hexdigest())
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('out');p.add_argument('--new-module');p.add_argument('--mutant',action='store_true');p.add_argument('--receipt');a=p.parse_args()
 s,r=transform(Path(a.input).read_text(),new_module=a.new_module,mutant=a.mutant);Path(a.out).write_text(s)
 if a.receipt:Path(a.receipt).write_text(json.dumps(r,indent=2)+'\n')

def enabled_wrapper(src, module='qkd_hr_phy_adp'):
    """Explicit active physical-kit form. The reusable implementation remains default0."""
    impl=module+'__credit_impl'
    text,receipt=transform(src,module=module,new_module=impl)
    header=re.search(r'\bmodule\s+'+re.escape(module)+r'\s*\((.*?)\);',src,re.S)
    if not header:raise ValueError('PHY source module header not found')
    ports=[p.strip() for p in header.group(1).split(',')]
    if any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',p) for p in ports):raise ValueError('unsupported header port')
    decl=[]
    for line in src.splitlines():
        if re.match(r'\s*(input|output)\s',line):decl.append(line)
    declared=[]
    for line in decl:
        m=re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*;',line)
        if not m:raise ValueError('unsupported port declaration')
        declared.append(m.group(1))
    if sorted(ports)!=sorted(declared):raise ValueError('wrapper port set mismatch')
    wrapper='module '+module+' ('+', '.join(ports)+');\n'+'\n'.join(decl)+'\n'
    wrapper+=impl+' #(.CREDIT_RETURN_CAPTURE(1)) u_credit_impl (\n'+',\n'.join('    .'+p+'('+p+')' for p in ports)+'\n);\nendmodule\n'
    receipt.update(enabled_by='explicit --hr-credit-return-capture',public_module=module)
    return wrapper+text,receipt

def enabled_vehicle(src, module='qkd_hr_phy_adp'):
    """Explicit kit-only parameter specialization; preserve the original flat face aliases.

    A new hierarchy wrapper turns kept output-reg aliases into internal kept wires,
    which Yosys buffers from the public output and face_guard correctly rejects.
    The generator flag is the opt-in; transform() itself keeps parameter default0.
    """
    text,receipt=transform(src,module=module)
    # The old face export retains two output-only debug aliases as keep wires.
    # They add physical buffer loads to the19 control bits, not functional loads.
    # Keep every actual FF attribute; only these exact wire aliases lose keep.
    clean=text
    removed=[]
    for alias in ('u_slice.tx_flit','u_slice.u_body.tx_flit'):
        pat=r'(?m)^  \(\* keep = [^\n]* \*\)\n(  wire \[146:0\] '+re.escape('\\'+alias)+r' ;)'
        clean,n=re.subn(pat,r'\1',clean)
        if n!=1:raise ValueError(f'expected one output-only kept PHY alias {alias}: {n}')
        removed.append(alias)
    attrs=lambda s:re.sub(r'\(\*.*?\*\)\s*','',s,flags=re.S)
    if attrs(clean)!=attrs(text):raise ValueError('alias keep cleanup changed logic')
    text=clean;receipt['dead_alias_keep_removed']=removed
    receipt['attribute_stripped_identity']=True
    token='parameter integer CREDIT_RETURN_CAPTURE = 0'
    if text.count(token)!=1:raise ValueError('capture parameter specialization is not unique')
    text=text.replace(token,'parameter integer CREDIT_RETURN_CAPTURE = 1',1)
    receipt.update(enabled_by='explicit --hr-credit-return-capture',public_module=module,vehicle_parameter=1,flat_faces_preserved=True)
    return text,receipt
