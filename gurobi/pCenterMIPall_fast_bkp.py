# Copyright 2019 Antonio Medrano
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Author: Antonio Medrano

import sys
import time
import numpy as np
import readDataFiles
import plot
from scipy.spatial.distance import cdist
from gurobipy import *

def Run_pCenter():
    
    """Example of complete p-Center program with the OR-Tools C++ style API"""
    m = Model()
    
    start_time = time.time()
    
    distMatrix = computeDistanceMatrix()

    solution = np.empty([numSites, 2])
    solution[:,0] = range(1, numSites+1)

    # p = 1 is a trivial solution min(max(dist))
    p = 1
    SDmin = np.amin(np.amax(distMatrix,0))
    solution[p-1,1] = SDmin
        
    computeCoverageMatrix(distMatrix, SDmin)
    BuildModel(m, distMatrix)

    print '  p, SD'
    displaySolution(p, SDmin)


    for i in range(2, numSites):
        p = i

        computeCoverageMatrix(distMatrix, SDmin+.000001)
        UpdateModel(m, p, distMatrix)
        SolveModel(m)
        SDmin = m.objVal
        solution[p-1,1] = SDmin

        displaySolution(p, SDmin)

    # solution for p = numSites is SDmin = 0
    solution[numSites-1,1] = 0
    displaySolution(numSites, 0)
        
    total_time = time.time()-start_time
    
    print
    print 'Total problem solved in %f seconds' % total_time
    print
    #displaySolution(Y, p, SDmin, total_time)
    
    
def computeDistanceMatrix():
        
    #declare a couple variables
    global siteIDs
    
    # Pull out just the site/demand IDs from the data
    siteIDs = sites[:,0]
    
    # Pull out just the coordinates from the data
    xyPointArray = sites[:,[1,2]]
    #A = [xyPointArray[i][:] for i in demandIDs]
    #B = [xyPointArray[j][:] for j in siteIDs]
    A = xyPointArray
    B = A
    #print A
    
    # Compute the distance matrix, using the euclidean distance
    distMatrix = cdist(A, B,'euclidean')

    return distMatrix
    
    
def computeCoverageMatrix(distMatrix, SD_UB):
    
    global cover_rows

    # Determine neighborhood of demands within SD of sites
    C = (distMatrix <= SD_UB).astype(int)

    # Convert coverage to sparse matrix
    cover_rows = [np.nonzero(t)[0] for t in C]
    
    return 0


def BuildModel(m, d):
    
    global X
    global Z
    
    # DECLARE VARIABLES:
    # Assignment variables X
    # =1 if demand i is assigned to facility j
    sitesRange = range(numSites)
    demandsRange = range(numDemands)
    
    X = m.addVars(numDemands, numSites,
                  vtype=GRB.BINARY,
                  name="X")
    # Facility Site binary decision variables Y
    # =1 if facility is located at site j
    Y = m.addVars(sitesRange,
                  vtype=GRB.BINARY,
                  name="Y")

    # Cover distance variable Z
    # continuous variable to be minimized
    Z = m.addVar(vtype=GRB.CONTINUOUS, obj = 1.0, name="Z")
    
    # Define Facility Constraint (c1):
    m.addConstr(quicksum(Y[j] for j in range(numSites)) <= 0, "c1")

    # Define Assignment Constraints (c2)
    # Define Z to be the largest distance from any demand to any facility (c4)
    for i in range(numDemands):
        for j in range(numSites):
            # add the balinsky assignment constraints (c3)
            # Yj - Xij >= 0 <--- canonical form of the assignment constraint
            m.addConstr(X[i,j] <= Y[j], "c3[%d,%d]" % (i,j))
            
    for i in range(numDemands):
        m.addConstr(quicksum(X[i,j] for j in cover_rows[i]) == 1, "c2[%d]" % i)
        m.addConstr(quicksum(X[i,j]*d[i,j] for j in cover_rows[i]) - Z <= 0, "c4[%d]" % i)
        
    # The objective is to minimize the number of located facilities
    m.modelSense = GRB.MINIMIZE
    #m.setObjective(Z, GRB.MINIMIZE)
    m.update()
    
    print 'Number of variables = %d' % m.numvars
    print 'Number of constraints = %d' % m.numconstrs
    #m.printStats()
    
    print
    return 0


def UpdateModel(m, p, d):
    
    # update the right hand side of the facility constraint
    m.getConstrByName("c1").setAttr(GRB.Attr.RHS, p)

    m.remove(m.getConstrs()[(numDemands*numSites+1):])

    # Define Assignment Constraints (c2)
    # Define Z to be the largest distance from any demand to any facility (c4)
    for i in range(numDemands):
        m.addConstr(quicksum(X[i,j] for j in cover_rows[i]) == 1, "c2[%d]" % i)
        m.addConstr(quicksum(X[i,j]*d[i,j] for j in cover_rows[i]) - Z <= 0, "c4[%d]" % i)

    m.update()
    
    #print 'Number of variables = %d' % m.numvars
    #print 'Number of constraints = %d' % m.numconstrs
    return 0
    

def SolveModel(m):
    """Solve the problem and print the solution."""
    m.Params.OutputFlag = 0
    m.Params.ResultFile = "output.sol"
    m.optimize()
    
    
def displaySolution(p, SDmin):
    # The objective value and the minimum service distance
    print '%3d, %f' % (p, SDmin)
    

def read_problem(file):
    global numSites
    global numDemands
    global sites
        
    try:
        if (file[-3:].lower() == "dat"):
            sites = readDataFiles.readDat(file)
        elif (file[-3:].lower() == "tsp"):
            sites = readDataFiles.readTSP(file)
    except IOError:
        print 'Error reading file'
        raise
        
    numSites = sites.shape[0]    
    numDemands = numSites
    
    #plot.plotData(sites)
    
    print '%d locations' % numSites
    print 


def main(unused_argv):
    print ('---- Complete P-Center with Gurobi -----')
    Run_pCenter()


""" Main will take in 3 arguments: p-Facilities; ServiceDistance; Data to Use  """
if __name__ == '__main__':
  if len(sys.argv) > 1 and len(sys.argv) <= 2:
    file = '../data/' + sys.argv[1]
    print "Problem instance from: ", file
    read_problem(file)
    main(None)
  elif len(sys.argv) > 0 and len(sys.argv) <= 1:
    file = '../data/swain.dat'
    print "Problem instance from: ", file
    read_problem(file)
    main(None)
  else:
    print "Please Pass: Service Distance; Data to Use"
    print "Problem not executed!"