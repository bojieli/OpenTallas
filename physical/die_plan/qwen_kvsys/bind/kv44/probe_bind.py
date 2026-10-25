import sys, os, json
sys.argv=[sys.argv[0]]
ROOT=os.getcwd()
sys.path.insert(0, ROOT+'/tools'); sys.path.insert(0, ROOT+'/tools/qwen_kv_die')
import kv_die as K
K._set_geometry(True)
masters = [l.split()[1] for l in open(os.environ['MASTERS'])]
out={}
for m in masters:
    b=K.BINDINGS.get(m)
    out[m]= (b['module'], b['file'], sorted((b.get('parameters') or {}).items())) if b else None
for m in masters: print(m, out[m])
