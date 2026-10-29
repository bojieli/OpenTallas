import json,sys,collections
def errs(p):
    d=json.load(open(p)); return d, [(x['check'],x['msg']) for x in d['findings'] if x['level']=='ERROR']
_,b=errs(sys.argv[1])
for v in sys.argv[2:]:
    d,e=errs(v)
    new=[x for x in e if x not in b]; gone=[x for x in b if x not in e]
    print('==',v,d['verdict'],d['mode'],'errors',d['errors'],'warn',d['warnings'],'new',len(new),'gone',len(gone))
    for x in new: print('  NEW',x[0],x[1][:330])
    for x in gone: print('  GONE',x[0],x[1][:160])
