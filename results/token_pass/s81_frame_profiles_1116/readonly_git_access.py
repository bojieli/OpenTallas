#!/usr/bin/python3
"""Read-only Git access to the inherited token source; never invent local history."""
import os,shlex,sys
args=sys.argv[1:]
if len(args)>=2 and args[0]=='-C':
 if args[1]!='/tmp/token_ds_followthrough1116/source':
  sys.exit('refuse foreign source directory')
 args=args[2:]
if not args or args[0] not in ('log','show','archive','rev-parse'):
 sys.exit('refuse non-read-only Git operation')
cmd=['git','-C','/srv/opentallas-scratch2/claude/tok-verify-2/repo',*args]
os.execvp('ssh',['ssh','epyc9',shlex.join(cmd)])
