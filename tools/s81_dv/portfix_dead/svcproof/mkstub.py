# blackbox stub of the FIRST module of a file: its header (params + ports) up to the port list ');', then endmodule
import re, sys
src, mod, out = sys.argv[1], sys.argv[2], sys.argv[3]
s = open(src).read()
s = re.sub(r"//[^\n]*", "", s)
i = s.index("module " + mod)
depth = 0; j = i; seen = False
while True:
    c = s[j]
    if c == "(": depth += 1; seen = True
    elif c == ")": depth -= 1
    j += 1
    if seen and depth == 0:
        # skip over "#( ... )" then the port list: stop after the ")" that is followed by ";"
        rest = s[j:].lstrip()
        if rest.startswith(";"): break
open(out, "a").write("(* blackbox *)\n" + s[i:j] + ";\nendmodule\n")
