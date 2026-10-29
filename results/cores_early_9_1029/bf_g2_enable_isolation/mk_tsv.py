import json,sys
d=json.load(open(sys.argv[1]))
with open(sys.argv[2],'w') as f:
    f.write('# from %s source_slice %s\n'%(d['schema'],d['source_slice_sha256']))
    for b in d['buffers']:
        f.write('\t'.join([b['name'],b['target'],b['pin'],'%.4f'%b['origin_um'][0],'%.4f'%b['origin_um'][1],b['orient']])+'\n')
print(len(d['buffers']))
