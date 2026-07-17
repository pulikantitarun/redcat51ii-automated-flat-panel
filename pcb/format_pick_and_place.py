from pathlib import Path
import csv
source=Path(__file__).resolve().parent/"positions_raw.csv"
target=Path(__file__).resolve().parent/"PickAndPlace.csv"
with source.open(newline="",encoding="utf-8-sig") as f: rows=list(csv.DictReader(f))
written=0
with target.open("w",newline="",encoding="utf-8") as f:
    names=["Designator","Mid X","Mid Y","Layer","Rotation","Value","Package"]
    w=csv.DictWriter(f,fieldnames=names); w.writeheader()
    for r in rows:
        if r["Ref"].startswith(("H","TP")): continue
        w.writerow({"Designator":r["Ref"],"Mid X":r["PosX"]+"mm","Mid Y":r["PosY"]+"mm","Layer":"Top" if r["Side"]=="top" else "Bottom","Rotation":r["Rot"],"Value":r["Val"],"Package":r["Package"]})
        written+=1
print(f"{written} assembly rows written; mounting holes and test pads removed")
