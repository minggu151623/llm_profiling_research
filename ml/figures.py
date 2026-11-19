"""Plot project-level held-out errors and paired measured changes from published result tables."""
import argparse
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np


def rows(path):
    with path.open() as stream:
        return list(csv.DictReader(stream))


def main(results, output):
    data = rows(results/"project_metrics.csv")
    errors = {(r["project"], r["model"]):float(r["mae"]) for r in data
              if r["workload"]=="normal" and r["setting"]=="unseen"}
    shifts = defaultdict(list)
    for r in rows(results/"workload_shift.csv"):
        shifts[r["project"]].append(float(r["absolute_shift"]))
    names = sorted(shifts)
    figure, (a,b) = plt.subplots(1,2,figsize=(11,4.8),layout="constrained")
    positions = np.arange(len(names))
    for i,name in enumerate(names):
        a.plot([errors[name,"zero_full"],errors[name,"lexical_ridge"]],[i,i],color="#C0C9CF",zorder=1)
    for model,label,marker,color in [
        ("zero_full","Zero-shot", "o","#A04621"),("lexical_ridge","Lexical ridge","s","#1B6872"),
        ("embedding_full","Embedding ridge","D","#4E4A88")]:
        a.scatter([errors[n,model] for n in names],positions,marker=marker,color=color,
                  edgecolors="white",linewidths=.6,s=46,zorder=2,label=label)
    a.set_yticks(positions,names)
    a.invert_yaxis()
    a.set_xlabel("Mean absolute error")
    a.set_title("Held-out project, normal workload",loc="left")
    a.legend(fontsize=8,loc="upper center",bbox_to_anchor=(.5,-.14),ncol=3,frameon=False)
    for i,name in enumerate(names):
        points=sorted(shifts[name])
        b.scatter(points, i+np.linspace(-.18,.18,len(points)), color="#54758A",s=17,alpha=.65)
        b.scatter([np.mean(points)], [i], marker="|",s=140,color="black",linewidths=2)
    b.set_yticks(positions,names)
    b.invert_yaxis()
    b.set_title("Same branch under two workloads",loc="left")
    b.set_xlabel("Absolute change in measured taken probability")
    b.set_xlim(-.025,1.025)
    for ax in (a,b):
        ax.grid(axis="x",alpha=.2)
        ax.spines[["top","right"]].set_visible(False)
    figure.savefig(output,dpi=180)
    plt.close(figure)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evaluation",type=Path)
    parser.add_argument("output",type=Path)
    args=parser.parse_args()
    main(args.evaluation,args.output)
