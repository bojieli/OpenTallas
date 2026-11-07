import json,sys
d=json.load(open(sys.argv[1])); m=d['modules']['ot_hgi_sfu_split3_ctl_core']
nn=m['netnames']; new={}
for k,v in nn.items():
    s=k
    for p in ('u_pipe.u_pipe.','u_rest.'):
        if s.startswith(p): s=s[len(p):]
    if s in new or (s!=k and s in nn): s=k  # keep original on conflict
    new[s]=v
m['netnames']=new
d['modules']={'gate':m}
json.dump(d,open(sys.argv[2],'w'))
print(len(nn),len(new))
