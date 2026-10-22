#!/usr/bin/env python3
"""Evaluate the actual two tail source localparams; no receipt age constants."""
import ast
import hashlib
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def age(path):
    raw=(ROOT/path).read_text();s=re.sub(r'//[^\n]*|/\*[\s\S]*?\*/','',raw)
    env={}
    for n,v in re.findall(r'parameter\s+integer\s+(SK|ITERS)\s*=\s*(\d+)',s):env[n]=int(v)
    exprs={}
    for decl in re.findall(r'localparam\s+integer\s+([^;]+);',s):
        for part in decl.split(','):
            n,expr=map(str.strip,part.split('=',1))
            expr=expr.replace('((LMe > LAe) ? LMe : LAe)','max(LMe,LAe)')
            tree=ast.parse(expr,mode='eval')
            for node in ast.walk(tree):
                if not isinstance(node,(ast.Expression,ast.BinOp,ast.Add,ast.Sub,ast.Mult,ast.Constant,ast.Name,ast.Load,ast.Call)):
                    raise ValueError('unsupported source expression '+expr)
                if isinstance(node,ast.Call) and not(isinstance(node.func,ast.Name) and node.func.id=='max'):raise ValueError(expr)
            env[n]=eval(compile(tree,'<source-param>','eval'),{'__builtins__':{},'max':max},env)
            exprs[n]=expr
            if n=='L':return {'path':path,'sha256':hashlib.sha256(raw.encode()).hexdigest(),'expressions':exprs,'values':env,'tail_L':env['L']}
    raise ValueError('no L')
a=age('rtl/dsrom_sys/s81_dv/unit/dsdv_gunit_tail.sv')
b=age('rtl/dsrom_sys/s81_dv/unit/guarded_1019/dsdv_gunit_tail_fs.sv')
result={'main':a,'private':b,'delta':b['tail_L']-a['tail_L'],'launch_pin_to_first_CTL_edges':{'main':a['tail_L']+3,'private':b['tail_L']+3},'launch_pin_to_first_L2_return_edges':{'main':a['tail_L']+9,'private':b['tail_L']+9},'whole_HP_HOP':'OPEN: upstream composition not simulated here'}
out=Path(sys.argv[1]);out.mkdir(parents=True,exist_ok=True)
(out/'source_age.json').write_text(json.dumps(result,indent=2)+'\n')
(out/'source_age.svh').write_text(f"`define GUARDED_MAIN_TAIL_L {a['tail_L']}\n`define GUARDED_PRIVATE_TAIL_L {b['tail_L']}\n")
print('SOURCE_AGE main='+str(a['tail_L'])+' private='+str(b['tail_L'])+' delta='+str(result['delta']))
