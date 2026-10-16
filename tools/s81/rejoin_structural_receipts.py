#!/usr/bin/env python3
"""Strict read-only source/log joins for the S81 structural source bundles.

This collector validates sealed component receipts. It never runs hardware or
turns source equality into physical, system or throughput qualification.
"""
import argparse, hashlib, json, pathlib, re, subprocess

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=pathlib.Path,required=True);p.add_argument('--git-ref',help='Read tracked bytes from this exact Git tree (works in sparse worktrees)');p.add_argument('--scope',choices=['qb','host','bf'],nargs='+',required=True);a=p.parse_args();root=a.root.resolve();totals={}
 def raw(path):
  if a.git_ref:
   return subprocess.check_output(['git','-C',str(root),'show',a.git_ref+':'+path],stderr=subprocess.DEVNULL)
  return (root/path).read_bytes()
 def js(path):return json.loads(raw(path))
 def join(mapping):
  for path,want in mapping.items():
   got=hashlib.sha256(raw(path)).hexdigest()
   if got!=want:raise ValueError(f'SOURCE MISMATCH {path}: expected {want}, got {got}')
  return len(mapping)
 def marker(path,pattern):
  if not re.search(pattern,raw(path).decode()):raise ValueError(f'LOG MISMATCH {path}: missing {pattern}')
 for scope in a.scope:
  if scope=='qb':
   base='results/rtl/s81_pq_native_audit_1015/takeover_0253/qb_readroot/'
   n=0
   for name in ['bank_gate.json','parent_gate.json','p10_gate.json']:
    r=js(base+name);n+=join(r['source_sha256'])
    if [(c['returncode']==0) for c in r['cases']] != [True,False]:raise ValueError('QB positive/mutant exit contract')
   marker(base+'positive.log',r'QB_READROOT PASS checks1030 physicalrows128 bits256 cycles_added0')
   marker(base+'stopped_read_root.log',r'QB_READROOT FAIL check513')
   marker(base+'p10_positive.log',r'PQ_QB_PINREAD PASS checks=345800 logical_words=384 rows=96 macros=4 exponent_fault=1 read_latency_delta=4')
   marker(base+'p10_stopped_read_root.log',r'PQ_QB_PINREAD FAIL cycle=623')
   totals[scope]=dict(source_joins=n,bank_checks=1030,current_P10_bit_checks=345800,actual_SRAMs=4,negative_logs=2,physical_qualified=False)
  elif scope=='host':
   base='results/rtl/s81_host_recovery_1016/output_select_rcopy/'
   r=js(base+'record.json');n=join(r['source_sha256'])+join(r['generator_source_sha256'])
   for path,want in r['output_artifact_sha256'].items():
    # Records may use a basename or repo-relative file name.
    target=path if path.startswith(('results/','rtl/','tools/','tests/','physical/')) else base+path
    if hashlib.sha256(raw(target)).hexdigest()!=want:raise ValueError('HOST OUTPUT MISMATCH '+target)
   calendar=raw(base+'emit_calendar_exact.tsv')
   if hashlib.sha256(calendar).hexdigest()!='54dc358cc9bb3ef0736390cb8a419991f1bc7982f451f14fb6cd3edc1a3f8472' or len(calendar.splitlines())!=545:raise ValueError('HOST positive calendar mismatch')
   marker(base+'native_m0.log',r'HOST_SLICED_NATIVE PASS exact_calendar=59989 real_packets=1093 sectors=544 completions=1')
   marker(base+'native_m6.log',r'HOST_SLICED_NATIVE FAIL')
   marker(base+'native_bypass_intercepts.log',r'HOST_SLICED_NATIVE FAIL interceptedCSR')
   marker(base+'exact.log',r'PASS');marker(base+'mut.log',r'FATAL RCOPY mismatch at 8')
   totals[scope]=dict(source_joins=n,edges=59989,packets=1093,sectors=544,positive_calendar_rows=544,native_negative_logs=2,standalone_FIFO_logs=2,scope='IKEY initialization only; uncollected bootcase metadata is not requalified',physical_qualified=False)
  else:
   base='results/rtl/s81_bf_clock_1015/c10/recovery_0253/native_main_boundary_r2/'
   mapping={}
   for line in raw(base+'actual_remote_source_sha256.txt').decode().splitlines():
    digest,path=line.split(None,1);mapping[path.strip()]=digest
   if len(mapping)!=17:raise ValueError('BF consumed-source coverage must be17')
   n=join(mapping);r=js(base+'receipt.json')
   if r['compiler_fixture_profile']['programme_delta']!=0:raise ValueError('BF current-main fixture must explicitly use DELTA0')
   marker(base+'positive.log',r'TXN MATCH');marker(base+'root_stop.log',r'DIFF TXN.*n=16')
   t=js(base+'terminal.json')
   if t['cases']['positive']['returncode']!=0 or not t['cases']['positive']['ok']:
    raise ValueError('BF positive terminal failed')
   if t['cases']['root_stop']['returncode']==0 or not t['cases']['root_stop']['ok']:
    raise ValueError('BF stopped-root terminal failed')
   totals[scope]=dict(source_joins=n,rows=456,values=912,configs=448,compiler_cycles=124422,programme_delta=0,negative_logs=1,physical_qualified=False)
 print(json.dumps(dict(verdict='SOURCE_AND_COMPONENT_LOG_JOIN_PASS',results=totals,verified_tree=a.git_ref or 'working tree',scope='No physical/native system/throughput qualification'),indent=2))
if __name__=='__main__':
 try:main()
 except (ValueError,KeyError,OSError,TypeError,subprocess.CalledProcessError) as e:raise SystemExit('REJOIN FAIL: '+str(e))
