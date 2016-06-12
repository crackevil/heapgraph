import re
import sys
nodePatt = re.compile ('([a-zA-Z0-9]+) \[(rc=[0-9]+|gc(?:.marked)?)\] (.*)$')


if len(sys.argv) < 3:
	sys.stderr.write('Not enough arguments.\n')
	exit()

def loadLog(fname):
	logp=dict()
	try:
		f = open(fname, 'r')
	except:
		sys.stderr.write('Error opening file ' + fname + '\n')
		exit(-1)
	for line in f:
		m = nodePatt.match(line)
		if m:
			addr=int(m.group(1),16)
			stat=m.group(2)
			desc=m.group(3)
			logp[addr]=(stat, desc)
	f.close()
	return logp

p1=loadLog(sys.argv[1])
p2=loadLog(sys.argv[2])

for key in p2.keys():
	if key in p1:
		del p2[key]

for key in p2.keys():
	print hex(key),p2[key][0],p2[key][1]


