import json,pathlib,shutil,sys
k=pathlib.Path(sys.argv[1]);tools=pathlib.Path(sys.argv[2])
p=k/"sdc_lint.json"; d=json.loads(p.read_text()); note=d.pop("io_hold_note")
(k/"sdc_lint_notes.json").write_text(json.dumps({"io_hold_note":note,"packaging_repair":"Metadata moved unchanged out of strict lint kwargs; timing values unchanged; original failed package preserved."},indent=2)+"\n")
p.write_text(json.dumps(d,indent=2)+"\n")
shutil.copy2(tools/"rtl_lint.py",k/"rtl_lint.py")
