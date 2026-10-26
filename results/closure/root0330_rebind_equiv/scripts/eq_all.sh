#!/bin/bash
cd "$(dirname "$0")"
python3 -c "import json;print('\n'.join(json.load(open('index.json'))))" | xargs -P 12 -n 1 ./equiv_one.sh
echo DONE
