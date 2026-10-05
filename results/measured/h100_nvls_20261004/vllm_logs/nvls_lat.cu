// NVLS (NVSwitch in-switch reduction) latency microbenchmarks, single process, 8 GPUs.
#include <cuda.h>
#include <cuda_runtime.h>
#include <cstdio>
#include <cstdlib>
#include <vector>
#include <cstring>
#define CK(x) do{CUresult r=(x); if(r!=CUDA_SUCCESS){const char*s;cuGetErrorString(r,&s);printf("ERR %s @%d: %s\n",#x,__LINE__,s);exit(1);}}while(0)
#define RK(x) do{cudaError_t r=(x); if(r!=cudaSuccess){printf("RTERR %s @%d: %s\n",#x,__LINE__,cudaGetErrorString(r));exit(1);}}while(0)

__device__ __forceinline__ unsigned long long gtimer(){unsigned long long t; asm volatile("mov.u64 %0, %%globaltimer;":"=l"(t)); return t;}
__device__ __forceinline__ void mc_red_add(unsigned* p, unsigned v){asm volatile("multimem.red.release.sys.global.add.u32 [%0], %1;"::"l"(p),"r"(v):"memory");}
__device__ __forceinline__ unsigned ld_acq(const unsigned* p){unsigned v; asm volatile("ld.acquire.sys.global.u32 %0, [%1];":"=r"(v):"l"(p):"memory"); return v;}
__device__ __forceinline__ float4 mc_ldred(const float* p){float4 v; asm volatile("multimem.ld_reduce.relaxed.sys.global.add.v4.f32 {%0,%1,%2,%3}, [%4];":"=f"(v.x),"=f"(v.y),"=f"(v.z),"=f"(v.w):"l"(p):"memory"); return v;}
__device__ __forceinline__ void mc_st(float* p, float4 v){asm volatile("multimem.st.relaxed.sys.global.v4.f32 [%0], {%1,%2,%3,%4};"::"l"(p),"f"(v.x),"f"(v.y),"f"(v.z),"f"(v.w):"memory");}

__device__ __forceinline__ void barrier(unsigned* mc_flag, const unsigned* uc_flag, unsigned& epoch, int ngpu){
  __syncthreads();
  if(threadIdx.x==0){ __threadfence_system(); mc_red_add(mc_flag,1); epoch++; while(ld_acq(uc_flag) < epoch*(unsigned)ngpu){} }
  __syncthreads();
}
__device__ __forceinline__ void mc_red_add_rlx(unsigned* p, unsigned v){asm volatile("multimem.red.relaxed.sys.global.add.u32 [%0], %1;"::"l"(p),"r"(v):"memory");}
__device__ __forceinline__ unsigned ld_rlx(const unsigned* p){unsigned v; asm volatile("ld.relaxed.sys.global.u32 %0, [%1];":"=r"(v):"l"(p):"memory"); return v;}
__device__ __forceinline__ void barrier_rlx(unsigned* mc_flag, const unsigned* uc_flag, unsigned& epoch, int ngpu){
  __syncthreads();
  if(threadIdx.x==0){ mc_red_add_rlx(mc_flag,1); epoch++; while(ld_rlx(uc_flag) < epoch*(unsigned)ngpu){} }
  __syncthreads();
}
// mode 0: barrier only; mode 1: one-shot NVLS all-reduce (barrier, ld_reduce slice, multimem.st, barrier)
__global__ void coll(int mode,int rank,int ngpu,unsigned* mc_flag,const unsigned* uc_flag,float* mc_in,float* mc_out,int slice_bytes,int iters,unsigned epoch0,unsigned long long* out_ns){
  unsigned epoch=epoch0; int nv=slice_bytes/16; int t=threadIdx.x;
  barrier(mc_flag,uc_flag,epoch,ngpu);
  unsigned long long t0=gtimer();
  for(int i=0;i<iters;i++){
    if(mode==0){ barrier(mc_flag,uc_flag,epoch,ngpu); }
    else if(mode==2){ barrier_rlx(mc_flag,uc_flag,epoch,ngpu); }
    else if(mode==4){ barrier_rlx(mc_flag,uc_flag,epoch,ngpu);
      if(t<nv){ size_t off=(size_t)rank*slice_bytes/4 + (size_t)t*4; float4 v=*(const float4*)((const char*)uc_flag + 65536 + off*4); mc_st(mc_out+off,v);} 
      barrier_rlx(mc_flag,uc_flag,epoch,ngpu); }
    else if(mode==3){ barrier_rlx(mc_flag,uc_flag,epoch,ngpu);
      if(t<nv){ size_t off=(size_t)rank*slice_bytes/4 + (size_t)t*4; float4 v=mc_ldred(mc_in+off); mc_st(mc_out+off,v);} 
      barrier_rlx(mc_flag,uc_flag,epoch,ngpu); }
    else {
      barrier(mc_flag,uc_flag,epoch,ngpu);
      if(t<nv){ size_t off=(size_t)rank*slice_bytes/4 + (size_t)t*4; float4 v=mc_ldred(mc_in+off); mc_st(mc_out+off,v);} 
      barrier(mc_flag,uc_flag,epoch,ngpu);
    }
  }
  unsigned long long t1=gtimer();
  if(t==0){ out_ns[0]=t1-t0; out_ns[1]=epoch; }
}
// single-thread dependent chains (latency of one op), run on GPU 0 only
__global__ void chain_ldred(const float* mc_in,int iters,unsigned long long* out){
  unsigned long long t0=gtimer(); const float* p=mc_in; float acc=0;
  for(int i=0;i<iters;i++){ float4 v=mc_ldred(p); acc+=v.x; p = mc_in + (((int)(v.x*0.0f)+i*4)&1023); }
  unsigned long long t1=gtimer(); out[0]=t1-t0; out[1]=(unsigned long long)acc;
}
__global__ void chain_ld(const unsigned* remote,int iters,unsigned long long* out){ // pointer chase in remote memory
  unsigned long long t0=gtimer(); unsigned idx=0;
  for(int i=0;i<iters;i++){ unsigned v; asm volatile("ld.relaxed.sys.global.u32 %0, [%1];":"=r"(v):"l"(remote+idx):"memory"); idx=v; }
  unsigned long long t1=gtimer(); out[0]=t1-t0; out[1]=idx;
}
// store ping-pong: side 0 writes ping into peer's flag, waits for pong in its own flag
__global__ void pingpong_rlx(int side,unsigned* my_flag,unsigned* peer_flag,int iters,unsigned long long* out){
  unsigned long long t0=gtimer();
  for(unsigned i=1;i<=(unsigned)iters;i++){
    if(side==0){ asm volatile("st.relaxed.sys.global.u32 [%0], %1;"::"l"(peer_flag),"r"(i):"memory"); while(ld_rlx(my_flag)<i){} }
    else { while(ld_rlx(my_flag)<i){} asm volatile("st.relaxed.sys.global.u32 [%0], %1;"::"l"(peer_flag),"r"(i):"memory"); }
  }
  unsigned long long t1=gtimer(); out[0]=t1-t0;
}
__global__ void pingpong(int side,unsigned* my_flag,unsigned* peer_flag,int iters,unsigned long long* out){
  unsigned long long t0=gtimer();
  for(unsigned i=1;i<=(unsigned)iters;i++){
    if(side==0){ asm volatile("st.release.sys.global.u32 [%0], %1;"::"l"(peer_flag),"r"(i):"memory"); while(ld_acq(my_flag)<i){} }
    else { while(ld_acq(my_flag)<i){} asm volatile("st.release.sys.global.u32 [%0], %1;"::"l"(peer_flag),"r"(i):"memory"); }
  }
  unsigned long long t1=gtimer(); out[0]=t1-t0;
}

int main(){
  CK(cuInit(0)); int n; CK(cuDeviceGetCount(&n)); const char* e=getenv("NGPU"); const int NG= e? atoi(e): n; printf("devices %d\n",NG);
  std::vector<CUdevice> dev(NG); std::vector<CUcontext> ctx(NG);
  for(int d=0;d<NG;d++){ CK(cuDeviceGet(&dev[d],d)); int mcs=0; CK(cuDeviceGetAttribute(&mcs,CU_DEVICE_ATTRIBUTE_MULTICAST_SUPPORTED,dev[d])); printf("dev %d multicast_supported=%d\n",d,mcs); if(!mcs){printf("NO MULTICAST\n");return 2;} CK(cuDevicePrimaryCtxRetain(&ctx[d],dev[d])); }
  CK(cuCtxSetCurrent(ctx[0]));
  // layout: [flags 64KB][in 64KB][out 64KB]
  const size_t FLAG=0, IN=65536, OUT=131072, BYTES=196608;
  CUmulticastObjectProp mp; memset(&mp,0,sizeof(mp)); mp.numDevices=NG; mp.handleTypes=CU_MEM_HANDLE_TYPE_POSIX_FILE_DESCRIPTOR; mp.size=BYTES;
  size_t gran; CK(cuMulticastGetGranularity(&gran,&mp,CU_MULTICAST_GRANULARITY_RECOMMENDED)); size_t SZ=((BYTES+gran-1)/gran)*gran; mp.size=SZ;
  CUmemGenericAllocationHandle mch; CK(cuMulticastCreate(&mch,&mp));
  for(int d=0;d<NG;d++) CK(cuMulticastAddDevice(mch,dev[d]));
  std::vector<CUmemGenericAllocationHandle> mh(NG); std::vector<CUdeviceptr> uc(NG);
  std::vector<CUmemAccessDesc> acc(NG); for(int d=0;d<NG;d++){acc[d].location.type=CU_MEM_LOCATION_TYPE_DEVICE; acc[d].location.id=d; acc[d].flags=CU_MEM_ACCESS_FLAGS_PROT_READWRITE;}
  for(int d=0;d<NG;d++){
    CUmemAllocationProp ap; memset(&ap,0,sizeof(ap)); ap.type=CU_MEM_ALLOCATION_TYPE_PINNED; ap.location.type=CU_MEM_LOCATION_TYPE_DEVICE; ap.location.id=d; ap.requestedHandleTypes=CU_MEM_HANDLE_TYPE_POSIX_FILE_DESCRIPTOR;
    CK(cuMemCreate(&mh[d],SZ,&ap,0)); CK(cuMulticastBindMem(mch,0,mh[d],0,SZ,0));
    CK(cuMemAddressReserve(&uc[d],SZ,gran,0,0)); CK(cuMemMap(uc[d],SZ,0,mh[d],0)); CK(cuMemSetAccess(uc[d],SZ,acc.data(),NG));
  }
  CUdeviceptr mc; CK(cuMemAddressReserve(&mc,SZ,gran,0,0)); CK(cuMemMap(mc,SZ,0,mch,0)); CK(cuMemSetAccess(mc,SZ,acc.data(),NG));
  // init: in = rank+1 per GPU (float), zero flags/out
  std::vector<float> h(SZ/4);
  for(int d=0;d<NG;d++){ CK(cuCtxSetCurrent(ctx[d])); for(size_t i=0;i<SZ/4;i++) h[i]=0; for(size_t i=IN/4;i<OUT/4;i++) h[i]=(float)(d+1);
    // remote pointer-chase ring in 'out' region of each GPU: idx -> next (stride 32 words)
    for(int k=0;k<1024;k++) ((unsigned*)h.data())[OUT/4 + k*32] = (unsigned)(((k+1)%1024)*32);
    CK(cuMemcpyHtoD(uc[d],h.data(),SZ)); CK(cuCtxSynchronize()); }
  std::vector<unsigned long long*> res(NG); std::vector<cudaStream_t> st(NG);
  for(int d=0;d<NG;d++){ RK(cudaSetDevice(d)); RK(cudaMalloc(&res[d],16)); RK(cudaStreamCreate(&st[d])); }
  unsigned epoch=0; const int ITERS=20000;
  auto run=[&](int mode,int slice){ 
    for(int d=0;d<NG;d++){ RK(cudaSetDevice(d)); int thr = mode? ((slice/16)<32?32:(slice/16)) : 32;
      coll<<<1,thr,0,st[d]>>>(mode,d,NG,(unsigned*)(mc+FLAG),(const unsigned*)(uc[d]+FLAG),(float*)(mc+IN),(float*)(mc+OUT),slice,ITERS,epoch,res[d]); RK(cudaGetLastError()); }
    unsigned long long worst=0, e=0; for(int d=0;d<NG;d++){ RK(cudaSetDevice(d)); RK(cudaStreamSynchronize(st[d])); unsigned long long hv[2]; RK(cudaMemcpy(hv,res[d],16,cudaMemcpyDeviceToHost)); if(hv[0]>worst)worst=hv[0]; e=hv[1]; }
    epoch=(unsigned)e; return (double)worst/ITERS; };
  for(int w=0;w<2;w++) run(0,0); // warmup
  double tb=run(0,0); printf("RESULT barrier_only_ns %.1f\n",tb);
  double tr=run(2,0);
  for(int sz: {128,2048,32768}){ int slice=sz/NG; if(slice<16) slice=16; run(4,slice); double t=run(4,slice); printf("RESULT allgather_relaxed_total_bytes %d per_iter_ns %.1f minus_2barriers_ns %.1f\n",sz,t,t-2*tr); } printf("RESULT barrier_relaxed_ns %.1f\n",tr);
  int sizes[]={128,512,2048,8192,32768};
  for(int s: sizes){ int slice=s/NG; if(slice<16) slice=16; run(3,slice); double t=run(3,slice);
    float chk[4]; CK(cuCtxSetCurrent(ctx[0])); CK(cuMemcpyDtoH(chk,uc[0]+OUT,16));
    printf("RESULT allreduce_relaxed_bytes %d per_iter_ns %.1f minus_2barriers_ns %.1f check %.1f\n",s,t,t-2*tr,chk[0]); }
  for(int s: sizes){ int slice=s/NG; if(slice<16) slice=16; run(1,slice); double t=run(1,slice);
    // verify out on GPU0 slice of rank0 = sum(1..8)=36
    RK(cudaSetDevice(0)); float chk[4]; CK(cuCtxSetCurrent(ctx[0])); CK(cuMemcpyDtoH(chk,uc[0]+OUT,16));
    printf("RESULT allreduce_bytes %d per_iter_ns %.1f minus_2barriers_ns %.1f check %.1f\n",s,t,t-2*tb,chk[0]); }
  // single op chains on GPU0
  { RK(cudaSetDevice(0)); unsigned long long hv[2];
    chain_ldred<<<1,1,0,st[0]>>>((const float*)(mc+IN),ITERS,res[0]); RK(cudaStreamSynchronize(st[0])); RK(cudaMemcpy(hv,res[0],16,cudaMemcpyDeviceToHost)); printf("RESULT ld_reduce_roundtrip_ns %.1f\n",(double)hv[0]/ITERS);
    for(int p=1;p<NG;p+=3){ chain_ld<<<1,1,0,st[0]>>>((const unsigned*)(uc[p]+OUT),ITERS,res[0]); RK(cudaStreamSynchronize(st[0])); RK(cudaMemcpy(hv,res[0],16,cudaMemcpyDeviceToHost)); printf("RESULT remote_load_roundtrip_gpu0_to_%d_ns %.1f\n",p,(double)hv[0]/ITERS);} 
    chain_ld<<<1,1,0,st[0]>>>((const unsigned*)(uc[0]+OUT),ITERS,res[0]); RK(cudaStreamSynchronize(st[0])); RK(cudaMemcpy(hv,res[0],16,cudaMemcpyDeviceToHost)); printf("RESULT local_load_roundtrip_ns %.1f\n",(double)hv[0]/ITERS); }
  // ping-pong GPU0 <-> GPU1 via unicast flags (word at FLAG+4096)
  { unsigned* f0=(unsigned*)(uc[0]+FLAG+4096); unsigned* f1=(unsigned*)(uc[1]+FLAG+4096);
    RK(cudaSetDevice(1)); pingpong<<<1,1,0,st[1]>>>(1,f1,f0,ITERS,res[1]); RK(cudaSetDevice(0)); pingpong<<<1,1,0,st[0]>>>(0,f0,f1,ITERS,res[0]);
    RK(cudaStreamSynchronize(st[0])); RK(cudaSetDevice(1)); RK(cudaStreamSynchronize(st[1])); RK(cudaSetDevice(0)); unsigned long long hv[2]; RK(cudaMemcpy(hv,res[0],16,cudaMemcpyDeviceToHost));
    printf("RESULT store_pingpong_rtt_ns %.1f one_way_ns %.1f\n",(double)hv[0]/ITERS,(double)hv[0]/ITERS/2); }
  { unsigned* f0=(unsigned*)(uc[0]+FLAG+8192); unsigned* f1=(unsigned*)(uc[1]+FLAG+8192);
    RK(cudaSetDevice(1)); pingpong_rlx<<<1,1,0,st[1]>>>(1,f1,f0,ITERS,res[1]); RK(cudaSetDevice(0)); pingpong_rlx<<<1,1,0,st[0]>>>(0,f0,f1,ITERS,res[0]);
    RK(cudaStreamSynchronize(st[0])); RK(cudaSetDevice(1)); RK(cudaStreamSynchronize(st[1])); RK(cudaSetDevice(0)); unsigned long long hv[2]; RK(cudaMemcpy(hv,res[0],16,cudaMemcpyDeviceToHost));
    printf("RESULT store_pingpong_relaxed_rtt_ns %.1f one_way_ns %.1f\n",(double)hv[0]/ITERS,(double)hv[0]/ITERS/2); }
  // determinism: inputs with catastrophic cancellation, repeated ld_reduce, compare bits across GPUs and repeats
  { std::vector<float> hv2(1024); 
    for(int d=0;d<NG;d++){ CK(cuCtxSetCurrent(ctx[d])); for(int i=0;i<1024;i++){ float big=(d%2? -1.0f:1.0f)*(1e8f+i); float small=(float)(d+1)*0.37f*(i%7+1); hv2[i]= (d<NG-1)? big+small*1e-3f*(float)(d*13%5) : 1.0f+small; } CK(cuMemcpyHtoD(uc[d]+IN,hv2.data(),4096)); CK(cuCtxSynchronize()); }
    unsigned long long h0=0; int mism=0;
    for(int rep=0;rep<5;rep++){ run(3,4096/NG>=16?4096/NG:16);
      for(int d=0;d<NG;d++){ std::vector<unsigned> o(1024); CK(cuCtxSetCurrent(ctx[d])); CK(cuMemcpyDtoH(o.data(),uc[d]+OUT,4096)); unsigned long long h=1469598103934665603ULL; for(unsigned x:o){h^=x;h*=1099511628211ULL;} if(rep==0&&d==0)h0=h; else if(h!=h0) mism++; } }
    printf("RESULT ld_reduce_determinism_hash %llx mismatches_across_gpus_and_reps %d\n",h0,mism); }
  printf("DONE\n"); return 0;
}
