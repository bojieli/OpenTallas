import sys
p=sys.argv[1]; s=open(p).read()
i=s.index('if {[catch {set _df'); j=s.index('\n',i)
s=s[:i]+'if {[catch {set _df [open "/work/ckdump_${corner}_${name}.txt" w]; dict for {_k _v} $measured {puts $_df "$_k $_v"}; close $_df} _e]} {puts "CKDUMP err $_e"}'+s[j:]
open(p,'w').write(s)
