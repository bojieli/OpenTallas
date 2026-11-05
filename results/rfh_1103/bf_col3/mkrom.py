import random,sys
d,seed=sys.argv[1],int(sys.argv[2]); r=random.Random(seed)
for i in (0,1):
    with open(f'{d}/tb_{i}.viamap.hex','w') as f:
        for _ in range(512): f.write('%0548x\n'%r.getrandbits(2192))
