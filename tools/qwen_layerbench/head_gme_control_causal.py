import re,sys
s=open(sys.argv[1]).read();cmd={int(i):int(e)for i,e in re.findall(r'GME_CMD index=(\d+) edge=(\d+)',s)};m=re.search(r'GME_SUMMARY .*first=(-?\d+)',s)
assert m and len(cmd)==4,(m,cmd)
if sys.argv[2]!='none':assert int(m[1])==cmd[int(sys.argv[2])],(m[1],cmd,sys.argv[2])
print('PASS_CAUSAL_FAULT_AT_GO',sys.argv[2],m[1])
