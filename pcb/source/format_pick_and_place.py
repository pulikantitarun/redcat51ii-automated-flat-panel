from pathlib import Path
import csv
p=Path(__file__).resolve().parent/"PickAndPlace.csv"
with p.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
with p.open("w",newline="",encoding="utf-8") as f:
    names=["Designator","Mid X","Mid Y","Layer","Rotation","Value","Package"]
    w=csv.DictWriter(f,fieldnames=names); w.writeheader()
    for r in rows:
        if r["Ref"].startswith("H"): continue
        w.writerow({"Designator":r["Ref"],"Mid X":r["PosX"]+"mm","Mid Y":r["PosY"]+"mm","Layer":"Top" if r["Side"]=="top" else "Bottom","Rotation":r["Rot"],"Value":r["Val"],"Package":r["Package"]})
print(f"{len(rows)} input rows; mounting holes removed")
