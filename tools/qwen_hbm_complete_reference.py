#!/usr/bin/env python3
"""Independent post-execution TP2 oracle using shipped Torch golden primitives.

Its activations/KV are private. Values are compared after execution and never
returned to the executable provider. Weight codes share the admitted recipe.
"""
import numpy as np
import torch
import qwen3_deployment_quality as G

class PostExecutionReference:
    def __init__(self,program,weights):
        self.program=program;self.weights=weights;self.cache={};self.x=None
        self.position=None;self.comparisons=[];self.next_token=None
    def start_token(self,token,position):
        self.position=position
        self.x=torch.from_numpy(self.weights.embedding(token).copy())[None,:]
    def raw_matrix(self,key,x):
        descriptor=self.program['weight_descriptors'][key]
        codes,_=self.weights.matrix(key);outputs=[]
        xb=G.to_bf16(x)
        for start in range(0,len(codes),256):
            w=torch.from_numpy(codes[start:start+256].copy())
            outputs.append(G._chunk_tree_dot_ref(xb,w,descriptor['split']))
        return torch.cat(outputs,-1)
    def scaled_matrix(self,key,x):
        _,scale=self.weights.matrix(key)
        return G.mul(self.raw_matrix(key,x),torch.from_numpy(scale.copy())[None,:])
    def compare(self,name,actual,expected):
        a=np.asarray(actual,dtype=np.float32);b=expected.detach().numpy().astype(np.float32)
        if a.shape!=b.shape:raise ValueError(f'comparison shape {name}: {a.shape} != {b.shape}')
        mismatch=int(np.count_nonzero(a.view(np.uint32)!=b.view(np.uint32)))
        result=dict(register=name,values=a.size,bit_mismatches=mismatch,
                    actual_nonfinite=int(np.count_nonzero(~np.isfinite(a))),
                    reference_nonfinite=int(np.count_nonzero(~np.isfinite(b))))
        self.comparisons.append(result)
        if mismatch or result['actual_nonfinite'] or result['reference_nonfinite']:
            raise ValueError(f'post-execution exactness failure {result}')
    def interleaved(self,x,w,split):
        indexes,_=G.interleave_perm(x.shape[-1],split,'cpu')
        xp=G.gather_pad(x,indexes,x.shape[-1],1)
        wp=G.gather_pad(w,indexes,w.shape[-1],1)
        return G._chunk_tree_dot_ref(xp,wp,split)
    def layer(self,layer,actual):
        c=self.program['config'];hd=c['head_dim'];nh=c['num_attention_heads']//2
        kv=c['num_key_value_heads']//2;ff=c['intermediate_size']//2;groups=nh//kv
        r=G.rstd_g(self.x,c['rms_norm_eps'])[:,None];oparts=[]
        cos,sin=G.rope_tables_g([self.position],hd,c['rope_theta'],'cpu')
        for die in range(2):
            prefix=f'L{layer}.d{die}'
            qkv=G.mul(self.scaled_matrix(f'L{layer}.qkv.d{die}',self.x),r)
            q,k,v=qkv.split([nh*hd,kv*hd,kv*hd],-1)
            q=G.rmsnorm_g(q.reshape(nh,hd),torch.from_numpy(self.weights.constant(layer,'q').copy()),c['rms_norm_eps'])
            k=G.rmsnorm_g(k.reshape(kv,hd),torch.from_numpy(self.weights.constant(layer,'k').copy()),c['rms_norm_eps'])
            q=G.rope_g(q,cos,sin);k=G.to_fp8(G.rope_g(k,cos,sin));v=G.to_fp8(v.reshape(kv,hd))
            key=(layer,die)
            previous=self.cache.get(key)
            if previous is None:
                if self.position:raise ValueError('reference previous KV missing')
                kc,vc=k[:,None,:],v[:,None,:]
            else:
                if previous[0].shape[1]!=self.position:raise ValueError('reference persistent position mismatch')
                kc=torch.cat([previous[0],k[:,None,:]],1);vc=torch.cat([previous[1],v[:,None,:]],1)
            self.cache[key]=(kc,vc)
            ops=self.program['instructions']
            score_split=next(o['attributes']['split'] for o in ops if o['outputs']==[prefix+'.scores'])
            pv_split=next(o['attributes']['split'] for o in ops if o['outputs']==[prefix+'.pv'])
            attention=[]
            for head in range(nh):
                scores=G.mul(self.interleaved(G.to_bf16(q[head:head+1]),kc[head//groups],score_split),G.f32c(1/np.sqrt(hd)))
                exponent=G.exp_g(G.add(scores,-scores.max(-1,keepdim=True).values))
                denominator=G.reduce_chunked(exponent)
                value=self.interleaved(G.to_bf16(exponent),vc[head//groups].t(),pv_split)
                attention.append(G.mul(value,G.reciprocal_g(denominator)[:,None]))
            att=torch.cat(attention,-1)
            oparts.append(self.raw_matrix(f'L{layer}.o.d{die}',att))
        _,scale=self.weights.matrix(f'L{layer}.o.d0')
        residual=G.add(self.x,G.mul(G.add(oparts[0],oparts[1]),torch.from_numpy(scale.copy())[None,:]))
        r=G.rstd_g(residual,c['rms_norm_eps'])[:,None];down=[]
        for die in range(2):
            gu=G.mul(self.scaled_matrix(f'L{layer}.gu.d{die}',residual),r)
            gate,up=gu.split([ff,ff],-1)
            act=G.mul(G.silu_g(gate),up)
            down.append(self.raw_matrix(f'L{layer}.down.d{die}',act))
        _,scale=self.weights.matrix(f'L{layer}.down.d0')
        self.x=G.add(residual,G.mul(G.add(down[0],down[1]),torch.from_numpy(scale.copy())[None,:]))
        self.compare(f'L{layer}.X',actual,self.x[0])
    def final_norm(self,actual):
        c=self.program['config']
        self.x=G.rmsnorm_g(self.x,torch.from_numpy(self.weights.constant(None,'final').copy()),c['rms_norm_eps'])
        self.compare('head.norm',actual,self.x[0])
    def head(self,die,actual):
        expected=self.scaled_matrix(f'head.d{die}',self.x)[0]
        self.compare(f'head.d{die}.scaled',actual,expected)
        winner=(float(expected.max()),int(torch.argmax(expected))+die*(self.program['config']['vocab_size']//2))
        if die==0:self.winner=winner
        elif (-winner[0],winner[1])<(-self.winner[0],self.winner[1]):self.winner=winner
        if die==1:self.next_token=self.winner[1]
