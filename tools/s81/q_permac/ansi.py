"""rewrite a yosys write_verilog non-ANSI module header as ANSI (the ref_tile pin gate reads ANSI headers)"""
import re,sys
p,top=sys.argv[1],sys.argv[2]; s=open(p).read()
i=s.index(f'module {top}('); j=s.index(';',i)
names=[n.strip() for n in s[i+len(f'module {top}('):j].rstrip().rstrip(')').split(',') if n.strip()]
body=s[j+1:]; decl={}
for n in names:
    m=re.search(r'\n  (input|output)((?: signed)?(?: \[[^\]]+\])?) '+re.escape(n)+';',body); decl[n]=(m.group(1),m.group(2) or '')
    body=body.replace(m.group(0),'',1)
    w=re.search(r'\n  (wire|reg)((?: signed)?(?: \[[^\]]+\])?) '+re.escape(n)+';',body)
    if w:
        body=body.replace(w.group(0),'',1)
        if w.group(1)=='reg': decl[n]=(decl[n][0]+' reg',decl[n][1])
hdr=f'module {top}(\n'+',\n'.join(f'  {d}{r} {n}' for n,(d,r) in decl.items())+'\n);'
open(p,'w').write(s[:i]+hdr+body)
