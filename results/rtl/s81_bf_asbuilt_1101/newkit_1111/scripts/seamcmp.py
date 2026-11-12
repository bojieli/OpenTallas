import sys,json,hashlib,importlib.util
spec=importlib.util.spec_from_file_location('F',sys.argv[1]);src=open(sys.argv[1]).read()
# only bound_seam_depths is needed: exec its definition without the module's imports of repo tools
import re,collections
ns={'re':re,'collections':collections}
m=re.search(r'^def bound_seam_depths.*?(?=^def )',src,re.M|re.S);exec(m[0],ns)
for p in sys.argv[2:]:
    raw=open(p,'rb').read();plan=json.loads(raw)
    out={}
    for mm in ('col_h9','col_h10'):
        try:out[mm]=ns['bound_seam_depths'](plan,mm)
        except Exception as e:out[mm]='ERR '+str(e)[:200]
    print(hashlib.sha256(raw).hexdigest()[:12],p,json.dumps(out))
