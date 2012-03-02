#!/usr/bin/python

# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
#
# The contents of this file are subject to the Mozilla Public License Version
# 1.1 (the "License"); you may not use this file except in compliance with
# the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
#
# Software distributed under the License is distributed on an "AS IS" basis,
# WITHOUT WARRANTY OF ANY KIND, either express or implied. See the License
# for the specific language governing rights and limitations under the
# License.
#
# The Original Code is mozilla.org code.
#
# The Initial Developer of the Original Code is
# The Mozilla Foundation.
# Portions created by the Initial Developer are Copyright (C) 2011
# the Initial Developer. All Rights Reserved.
#
# Contributor(s):
#
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
#
# ***** END LICENSE BLOCK *****


# Library for parsing garbage collector log files into a graph data structure.


# This documentation hasn't been updated.

# parseCCEdgeFile (file_name): given the file name of a CC edge file, parse and 
#   return the data.  This function returns a tuple with two components.
#
#   The first component is a multigraph representing the nodes and
#   edges in the graph.  It is implemented as a dictionary of
#   dictionaries.  The domain of the outer dictionary is the nodes of
#   the graphs.  The inner dictionaries map the destinations of the
#   edges in the graph to the number of times they occur.  For
#   instance, if there are two edges from x to y in the multigraph g,
#   then g[x][y] == 2.
#
#   The second component contains various graph attributes in a GraphAttribs
#      - nodeLabels maps node names to their labels, if any
#      - rcNodes maps ref counted nodes to the number of references
#        they have
#      - gcNodes maps gc'd nodes to a boolean, which is True if the
#        node is marked, False otherwise.
#      - edgeLabels maps source nodes to dictionaries.  These inner
#        dictionaries map destination nodes to a list of edge labels.


# toSinglegraph (gm): convert a multigraph into a single graph

# reverseMultigraph (gm): reverse a multigraph

# printGraph(g): print out a graph

# pringAttribs(ga): print out graph attributes


import sys
import re
from collections import namedtuple



GraphAttribs = namedtuple('GraphAttribs', 'edgeLabels nodeLabels roots rootLabels')


####
####  Log parsing
####

nodePatt = re.compile ('((?:0x)?[a-fA-F0-9]+) (?:(B|G) )?([^\r\n]*)\r?$')
edgePatt = re.compile ('> ((?:0x)?[a-fA-F0-9]+) (?:(B|G) )?([^\r\n]*)\r?$')

# A bit of a hack.  I imagine this could fail in bizarre circumstances.

def switchToGreyRoots(l):
  return l == "XPC global object" or l.startswith("XPCWrappedNative") or \
      l.startswith("XPCVariant") or l.startswith("nsXPCWrappedJS")

def parseRoots (f):
  roots = {}
  rootLabels = {}
  blackRoot = True;

  for l in f:
    nm = nodePatt.match(l)
    if nm:
      addr = nm.group(1)
      color = nm.group(2)
      lbl = nm.group(3)
      
      if blackRoot and switchToGreyRoots(lbl):
        blackRoot = False
      roots[addr] = blackRoot
      rootLabels[addr] = lbl
    elif l[:10] == '==========':
      break
    else:
      print "Error: unknown line ", l
      exit(-1)

  return [roots, rootLabels]


# parse CC graph
def parseGraph (f):
  edges = {}
  edgeLabels = {}
  nodeLabels = {}
  rcNodes = {}
  gcNodes = {}

  def addNode (node, nodeLabel):
    assert(not node in edges)
    edges[node] = {}
    assert(not node in edgeLabels)
    edgeLabels[node] = {}
    assert(nodeLabel != None)
    if nodeLabel != '':
      assert (not node in nodeLabels)
      nodeLabels[node] = nodeLabel

  def addEdge (source, target, edgeLabel):
    edges[source][target] = edges[source].get(target, 0) + 1
    if edgeLabel != '':
      edgeLabels[source].setdefault(target, []).append(edgeLabel)

  currNode = None

  for l in f:
    e = edgePatt.match(l)
    if e:
      assert(currNode != None)
      addEdge(currNode, e.group(1), e.group(3))
    else:
      nm = nodePatt.match(l)
      if nm:
        currNode = nm.group(1)
        nodeColor = nm.group(2)
        addNode(currNode, nm.group(3))
      else:
        print 'Error: Unknown line:', l[:-1]

  # yar, should pass the root crud in and wedge it in here, or somewhere
  return [edges, edgeLabels, nodeLabels]


def parseGCEdgeFile (fname):
  try:
    f = open(fname, 'r')
  except:
    print 'Error opening file', fname
    exit(-1)

  [roots, rootLabels] = parseRoots(f)
  [edges, edgeLabels, nodeLabels] = parseGraph(f)
  f.close()

  ga = GraphAttribs (edgeLabels=edgeLabels, nodeLabels=nodeLabels, roots=roots, rootLabels=rootLabels)
  return (edges, ga)


# Some applications may not care about multiple edges.
# They can instead use a single graph, which is represented as a map
# from a source node to a set of its destinations.
def toSinglegraph (gm):
  g = {}
  for src, dsts in gm.iteritems():
    d = set([])
    for dst, k in dsts.iteritems():
      d.add(dst)
    g[src] = d
  return g


def reverseMultigraph (gm):
  gm2 = {}
  for src, dsts in gm.iteritems():
    if not src in gm2:
      gm2[src] = {}
    for dst, k in dsts.iteritems():
      gm2.setdefault(dst, {})[src] = k
  return gm2


def printGraph(g, ga):
  for x, edges in g.iteritems():
    if x in ga.roots:
      sys.stdout.write('R {0}: '.format(x))
    else:
      sys.stdout.write('  {0}: '.format(x))
    for e, k in edges.iteritems():
      for n in range(k):
        sys.stdout.write('{0}, '.format(e))
    print

def printAttribs(ga):
  print 'Roots: ',
  for x in ga.roots:
    sys.stdout.write('{0}, '.format(x))
  print
  return;

  print 'Node labels: ',
  for x, l in ga.nodeLabels.iteritems():
    sys.stdout.write('{0}:{1}, '.format(x, l))
  print

  print 'Edge labels: ',
  for src, edges in ga.edgeLabels.iteritems():
    for dst, l in edges.iteritems():
      sys.stdout.write('{0}->{1}:{2}, '.format(src, dst, l))
  print


if False:
  # A few simple tests

  if len(sys.argv) < 2:
    print 'Not enough arguments.'
    exit()

  #import cProfile
  #cProfile.run('x = parseGCEdgeFile(sys.argv[1])')

  x = parseGCEdgeFile(sys.argv[1])

  #printGraph(x[0], x[1])
  printAttribs(x[1])

  assert (x[0] == reverseMultigraph(reverseMultigraph(x[0])))
