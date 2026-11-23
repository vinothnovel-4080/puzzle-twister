from itertools import permutations, combinations
# Day 1
seq=[n*(n+1) for n in range(1,11)]; print("D1",seq[:6],"next",seq[5],"10th",seq[9])
# Day 2 shapes: 3C=30, C+2T=18, T-S=2 ; ask S+C+T ; bonus S + C*T
for c in range(31):
  for t in range(31):
    for s in range(31):
      if 3*c==30 and c+2*t==18 and t-s==2: print("D2",c,t,s,"main",s+c+t,"bonus",s+c*t)
# Day 4 triangles: big triangle, 2 cevians from apex, 1 horizontal line
# count via combinatorics brute: lines from apex: 4 rays; horizontal segments: 2 (cross line + base)
print("D4", 2*len(list(combinations(range(4),2))), "bonus(no cross line)", len(list(combinations(range(4),2))))
# Day 5 row
P=["Ana","Ben","Cara","Dev"]
def ok5(o,use3=True):
  i={p:k for k,p in enumerate(o)}
  if i["Dev"] not in (0,3): return False
  if i["Cara"]!=i["Ana"]+1: return False
  if use3 and abs(i["Ben"]-i["Dev"])==1: return False
  return True
print("D5",[o for o in permutations(P) if ok5(o)], "without clue3:",sum(ok5(o,False) for o in permutations(P)))
# Day 7 ages
for b in range(1,50):
  if 3*b+5==2*(b+5): print("D7 brother",b,"Rhea",3*b)
# Day 8 magic square
sq=[[2,7,6],[9,5,1],[4,3,8]]
print("D8 rows",[sum(r) for r in sq],"cols",[sum(c) for c in zip(*sq)],"diag",sq[0][0]+sq[1][1]+sq[2][2],sq[0][2]+sq[1][1]+sq[2][0])
# Day 9
L="ABCDEFGHIJKLMNOPQRSTUVWXYZ"; x=0; out=[]
for g in range(0,6): x+=g; out.append(L[x])
print("D9",out); s=[1];
for g in range(1,6): s.append(s[-1]+g)
print("D9 bonus",s)
# Day 10 race
R=["Kiran","Leo","Maya","Noor","Omar"]
def ok10(o,skip=None):
  i={p:k for k,p in enumerate(o)}
  c=[i["Noor"]<i["Maya"]<i["Leo"], i["Omar"]==i["Kiran"]+1, i["Leo"]!=4, i["Noor"]!=0]
  return all(v for k,v in enumerate(c) if k!=skip)
print("D10",[o for o in permutations(R) if ok10(o)])
for k in range(4): print(" without clue",k+1,sum(ok10(o,k) for o in permutations(R)))
print("---fixes")
def ok5b(o,use3=True):
  i={p:k for k,p in enumerate(o)}
  return i["Dev"]==3 and i["Cara"]==i["Ana"]+1 and (not use3 or abs(i["Ben"]-i["Dev"])!=1)
print("D5",[o for o in permutations(P) if ok5b(o)],"without clue3",[o for o in permutations(P) if ok5b(o,False)])
x=0;out=["A"]
for g in range(2,7): x+=g; out.append(L[x])
print("D9",out)
def ok10b(o,use4=True):
  i={p:k for k,p in enumerate(o)}
  return i["Noor"]<i["Maya"]<i["Leo"] and i["Omar"]==i["Kiran"]+1 and (not use4 or i["Noor"]!=0)
print("D10",[o for o in permutations(R) if ok10b(o)],"without clue3:",[o for o in permutations(R) if ok10b(o,False)])
