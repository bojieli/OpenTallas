#include <cuda_runtime.h>
#include <cooperative_groups.h>
#include <cstdio>
namespace cg=cooperative_groups;
__device__ unsigned long long gt(){unsigned long long t; asm volatile("mov.u64 %0, %%globaltimer;":"=l"(t)); return t;}
__global__ void gsync(int iters, unsigned long long* out){ cg::grid_group g=cg::this_grid(); unsigned long long t0=gt(); for(int i=0;i<iters;i++) g.sync(); unsigned long long t1=gt(); if(blockIdx.x==0&&threadIdx.x==0) out[0]=t1-t0; }
__global__ void empty(){}
int main(){ int sms; cudaDeviceGetAttribute(&sms,cudaDevAttrMultiProcessorCount,0); unsigned long long* d; cudaMalloc(&d,8); int it=20000;
  void* args[]={&it,&d}; cudaLaunchCooperativeKernel((void*)gsync,sms,256,args); cudaDeviceSynchronize(); cudaLaunchCooperativeKernel((void*)gsync,sms,256,args); cudaDeviceSynchronize();
  unsigned long long h; cudaMemcpy(&h,d,8,cudaMemcpyDeviceToHost); printf("RESULT grid_sync_%dSMs_ns %.1f\n",sms,(double)h/it);
  cudaStream_t s; cudaStreamCreate(&s); for(int i=0;i<1000;i++) empty<<<1,32,0,s>>>(); cudaStreamSynchronize(s);
  cudaEvent_t a,b; cudaEventCreate(&a); cudaEventCreate(&b); int N=20000; cudaEventRecord(a,s); for(int i=0;i<N;i++) empty<<<sms,256,0,s>>>(); cudaEventRecord(b,s); cudaEventSynchronize(b); float ms; cudaEventElapsedTime(&ms,a,b); printf("RESULT back_to_back_kernel_launch_ns %.1f\n",ms*1e6/N);
  cudaGraph_t g; cudaGraphExec_t ge; cudaStreamBeginCapture(s,cudaStreamCaptureModeGlobal); for(int i=0;i<1000;i++) empty<<<sms,256,0,s>>>(); cudaStreamEndCapture(s,&g); cudaGraphInstantiate(&ge,g,0);
  cudaGraphLaunch(ge,s); cudaStreamSynchronize(s); cudaEventRecord(a,s); for(int r=0;r<20;r++) cudaGraphLaunch(ge,s); cudaEventRecord(b,s); cudaEventSynchronize(b); cudaEventElapsedTime(&ms,a,b); printf("RESULT graph_kernel_node_ns %.1f\n",ms*1e6/20000);
  return 0; }
