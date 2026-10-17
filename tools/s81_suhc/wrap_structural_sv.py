#!/usr/bin/env python3
"""Split generated oversized concatenations only at comma tokens, preserving code."""
import argparse,hashlib,json,re
from pathlib import Path

def main():
 p=argparse.ArgumentParser();p.add_argument('--input',required=True);p.add_argument('--output',required=True);a=p.parse_args();source=Path(a.input).read_text();lines=source.splitlines(keepends=True);result=[];changed=0
 for line in lines:
  if len(line)>16384:
   assert not any(',' in s for s in re.findall(r'"(?:\\.|[^"\\])*"',line)), 'Quoted comma on oversized line: require token-aware wrapping'
   # Escaped Verilog names terminate with whitespace. Never split a name.
   assert not any(',' in s for s in re.findall(r'\\\S+',line)), 'Comma inside escaped identifier'
   new=line.replace(', ', ',\n').replace(',{', ',\n{');assert re.sub(r'\s+','',line)==re.sub(r'\s+','',new);line=new;changed+=1
  result.append(line)
 output=''.join(result);target=Path(a.output);target.write_text(output);receipt=dict(scope='format-only emitted SV correction; no semantic/functional/timing qualification',input_sha256=hashlib.sha256(source.encode()).hexdigest(),output_sha256=hashlib.sha256(output.encode()).hexdigest(),oversized_lines_wrapped=changed,max_output_line_chars=max(map(len,output.splitlines())),nonwhitespace_bytes_identical=True);target.with_suffix(target.suffix+'.format.json').write_text(json.dumps(receipt,indent=1)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
