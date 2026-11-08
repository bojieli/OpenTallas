import json,sys,glob,os
A,B=sys.argv[1],sys.argv[2]; d=0;n=0
for f in glob.glob(A+'/rtl/*.reset_tree.json'):
    g=B+'/rtl/'+os.path.basename(f); n+=1
    a=json.load(open(f))['tree_sha256']; b=json.load(open(g))['tree_sha256'] if os.path.exists(g) else None
    if a!=b: d+=1; print('DIFF',os.path.basename(f))
print('reset_tree.json',n,'tree_sha256 differ',d)
