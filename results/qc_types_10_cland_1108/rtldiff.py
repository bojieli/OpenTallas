"""diff bound RTL old vs new bind dir: per file, changed lines classified; any changed line outside the landing raw
reset layer is reported as OTHER. usage: rtldiff.py OLD NEW OUT.json"""
import sys,os,difflib,json,re,glob,collections
A,B=sys.argv[1],sys.argv[2]
ok=re.compile(r"cland_reset_|u_cland_rst_|u_cland_collect_|\.rst_n\(|^\s*\.clk\(clk\), \.rst_n\(")
res={};other=collections.Counter();files=collections.Counter()
na=set(os.listdir(A+'/rtl'));nb=set(os.listdir(B+'/rtl'))
print('only old',sorted(na-nb)[:10],'only new',sorted(nb-na)[:10])
for f in sorted(na&nb):
    a=open(f'{A}/rtl/{f}','rb').read();b=open(f'{B}/rtl/{f}','rb').read()
    if a==b: files['same']+=1; continue
    files['changed']+=1
    if not f.endswith('.sv'): res[f]=dict(kind='nonsv'); continue
    al=a.decode(errors='replace').splitlines();bl=b.decode(errors='replace').splitlines()
    ch=[l for l in difflib.unified_diff(al,bl,lineterm='',n=0) if l[:1] in '+-' and not l.startswith(('+++','---'))]
    bad=[l for l in ch if not ok.search(l) and l[1:].strip() not in ('',) and not re.match(r"[+-]\s*wire cland_reset_",l)]
    res[f]=dict(changed=len(ch),other=len(bad),sample=bad[:5])
    if bad: other[f]=len(bad)
print(dict(files)); print('files with OTHER lines',len(other),list(other.items())[:10])
json.dump(res,open(sys.argv[3],'w'),indent=1)
