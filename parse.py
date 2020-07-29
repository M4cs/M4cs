f = open("wordlist.txt")
new = []
for l in f.readlines():
    if len(l) > 3:
        new.append(l)
with open("newwordlist.txt", "w") as n:
    n.writelines(new)