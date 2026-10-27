import re,sys
# identical, semantics-preserving rewrite for the Yosys Verilog frontend: `x inside {a, b}` -> (x == a || x == b)
s=open(sys.argv[1]).read()
def f(m):
    x=m.group(1); its=[i.strip() for i in m.group(2).split(',')]
    return '(' + ' || '.join(f'{x} == {i}' for i in its) + ')'
s=re.sub(r'\(?(h_type)\s+inside\s+\{([^}]*)\}\)?', lambda m: f(m), s)
open(sys.argv[2],'w').write(s)
