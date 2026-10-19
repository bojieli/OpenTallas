# helper (MU-KV-PEER): build a _mu drop-in skeleton from an original module: g_plain instantiates the original
# (output regs copied through always @*), g_mu = the original body with edits applied (each edit must apply once).
import re,sys
def parse(src,mod):
    i=src.index('module '+mod)
    # header up to ');' that closes the port list
    depth=0;k=src.index('(',i)
    # skip parameter list
    hdr_start=i
    m=re.match(r'module\s+\w+\s*(#\s*\()?',src[i:])
    pos=i+m.end()
    params=''
    if m.group(1):
        d=1;p0=pos
        while d:
            c=src[pos];d+= (c=='(')-(c==')');pos+=1
        params=src[p0:pos-1]
    pos=src.index('(',pos)
    d=1;p0=pos+1;pos+=1
    while d:
        c=src[pos];d+=(c=='(')-(c==')');pos+=1
    ports=src[p0:pos-1]
    end=src.index(';',pos)+1
    body=src[end:src.rindex('endmodule')]
    return params,ports,body
def port_list(ports):
    out=[];cur_dir=None;cur_reg=False;cur_w=''
    txt=re.sub(r'//[^\n]*','',ports)
    for tok in re.split(r',',txt):
        t=tok.strip()
        if not t: continue
        m=re.match(r'(input|output)\s*(wire|reg)?\s*(\[[^\]]*\])?\s*(\w+)$',t)
        if m:
            cur_dir=m.group(1);cur_reg=(m.group(2)=='reg');cur_w=m.group(3) or '';name=m.group(4)
        else:
            m2=re.match(r'(\[[^\]]*\])?\s*(\w+)$',t)
            assert m2,t
            if m2.group(1): cur_w=m2.group(1)
            name=m2.group(2)
        out.append((cur_dir,cur_reg,cur_w,name))
    return out
def param_names(params):
    return re.findall(r'(\w+)\s*=',re.sub(r'\[[^\]]*\]','',params))
def build(src,mod,head,edits,extra_param='parameter integer MU=1',body_prefix=''):
    params,ports,body=parse(src,mod)
    pl=port_list(ports);pn=param_names(params)
    for e in edits:
        a,b=e[0],e[1];n=e[2] if len(e)>2 else 1
        assert body.count(a)==n,(mod,a,body.count(a),n)
        body=body.replace(a,b)
    # the body is placed inside a generate branch: drop its own generate/endgenerate keywords (regions nest implicitly)
    body=re.sub(r'\bendgenerate\b','',body);body=re.sub(r'\bgenerate\b','',body)
    np=(params+','+extra_param) if params.strip() else extra_param
    s=head+'module '+mod+'_mu #('+np+')('+ports+');\n'
    s+='generate if(MU==0)begin:g_plain\n'
    regs=[p for p in pl if p[0]=='output' and p[1]]
    for d,r,w,n in regs: s+=f' wire{w} w_{n};\n'
    conn=','.join(f'.{n}({"w_"+n if (d=="output" and r) else n})' for d,r,w,n in pl)
    pa=('#('+','.join(f'.{n}({n})' for n in pn)+')') if pn else ''
    s+=f' {mod} {pa} u_plain({conn});\n'
    if regs:
        s+=' always @*begin '+''.join(f'{n}=w_{n};' for d,r,w,n in regs)+'end\n'
    s+='end else begin:g_mu\n'+body_prefix+body+'end endgenerate\nendmodule\n'
    return s
