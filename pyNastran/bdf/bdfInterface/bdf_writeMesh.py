# pylint: disable=E1101,C0103,R0902,R0904,R0914
from __future__ import (nested_scopes, generators, division, absolute_import,
                        print_function, unicode_literals)

from pyNastran.bdf.fieldWriter import printCard

class WriteMesh(object):
    def __init__(self):
        pass

    def echoBDF(self, infileName):
        """
        This method removes all comment lines from the bdf
        A write method is stil required.
        @todo maybe add the write method
        """
        self.cardsToRead = set([])
        return self.readBDF(infileName)

    def autoRejectBDF(self, infileName):
        """
        This method parses supported cards, but does not group them into nodes,
        elements, properties, etc.
        @todo maybe add the write method
        """
        self.autoReject = True
        return self.readBDF(infileName)

    def writeElementsAsCTRIA3(self):
        """
        takes the cquad4 elements and splits them
        @retval msg  string representation of the elements
        """
        eids = self.elementIDs()
        #print "eids = ",eids
        nextEID = max(eids)+1  # set the new ID
        msg = '$ELEMENTS\n'
        for element in sorted(self.elements.itervalues()):
            if element.Is('CQUAD4'):
                msg += element.writeAsCTRIA3(nextEID)
                nextEID += 1
            else:
                msg += str(element)
            ###
        ###
        return msg

    def writeDMIGs(self):
        msg = ''
        for (name, dmig) in sorted(self.dmigs.iteritems()):
            msg += str(dmig)
        for (name, dmi) in sorted(self.dmis.iteritems()):
            msg += str(dmi)
        for (name, dmij) in sorted(self.dmijs.iteritems()):
            msg += str(dmij)
        for (name, dmiji) in sorted(self.dmijis.iteritems()):
            msg += str(dmiji)
        for (name, dmik) in sorted(self.dmiks.iteritems()):
            msg += str(dmik)
        return msg

    def writeCommon(self):
        """
        method to write the common outputs so none get missed...
        @param self the object pointer
        @retval msg part of the bdf
        """
        msg = ''
        msg += self.writeRigidElements()
        msg += self.writeDMIGs()
        msg += self.writeLoads()
        msg += self.writeDynamic()
        msg += self.writeAero()
        msg += self.writeAeroControl()
        msg += self.writeFlutter()
        msg += self.writeThermal()
        msg += self.writeThermalMaterials()

        msg += self.writeConstraints()
        msg += self.writeOptimization()
        msg += self.writeTables()
        msg += self.writeSets()
        msg += self.writeRejects()
        msg += self.writeCoords()
        return msg

    def writeBDFAsPatran(self, outFileName='fem.out.bdf', debug=False):
        """
        Writes a bdf with properties & elements interspersed like how
        Patran writes the bdf.  This takes longer than the write method
        but makes it easier to compare to a Patran-formatted bdf.
        @param self the object pointer
        @param outFileName the name to call the output bdf
        @param debug developer debug (unused)
        """
        msg  = self.writeHeader()
        msg += self.writeParams()
        msg += self.writeNodes()

        msg += self.writeElementsProperties()
        msg += self.writeMaterials()

        msg += self.writeCommon()
        msg += 'ENDDATA\n'

        fname = self.print_filename(outFileName)
        self.log.debug("***writing %s" %(fname))
        
        outfile = open(outFileName,'wb')
        outfile.write(msg)
        outfile.close()
    
    def writeBDF(self, outFileName='fem.out.bdf', debug=False):
        """
        Writes the bdf.  It groups the various sections together to make it
        easy to find cards.  This method is slightly more stable than 
        writeAsPatran due to the properties sometimes being a little funny.
        @param self the object pointer
        @param outFileName the name to call the output bdf
        @param debug developer debug (unused)
        """
        msg  = self.writeHeader()
        msg += self.writeParams()
        msg += self.writeNodes()

        msg += self.writeElements()
        msg += self.writeProperties()
        msg += self.writeMaterials()

        msg += self.writeCommon()
        msg += 'ENDDATA\n'

        fname = self.print_filename(outFileName)
        self.log.debug("***writing %s" %(fname))

        outfile = open(outFileName,'wb')
        outfile.write(msg)
        outfile.close()

    def writeAsCTRIA3(self, outFileName='fem.out.bdf', debug=False):
        """
        Writes a series of CQUAD4s as CTRIA3s.  All other cards are echoed.
        @param self the object pointer
        @param outFileName the name to call the output bdf
        @param debug developer debug (unused)
        @warning not tested in a long time
        """
        msg  = self.writeHeader()
        msg += self.writeParams()
        msg += self.writeNodes()
        msg += self.writeElementsAsCTRIA3()
        msg += self.writeProperties()
        msg += self.writeMaterials()

        msg += self.writeCommon()
        msg += 'ENDDATA\n'

        fname = self.print_filename(outFileName)
        self.log.debug("***writing %s" % (fname))

        outfile = open(outFileName, 'wb')
        outfile.write(msg)
        outfile.close()

    def writeHeader(self):
        """
        Writes the executive and case control decks.
        @param self the object pointer
        """
        msg  = self.writeExecutiveControlDeck()
        msg += self.writeCaseControlDeck()
        return msg

    def writeExecutiveControlDeck(self):
        """
        Writes the executive control deck.
        @param self the object pointer
        """
        msg = '$EXECUTIVE CONTROL DECK\n'
        
        if self.sol == 600:
            newSol = 'SOL 600,%s' %(self.solMethod)
        else:
            newSol = 'SOL %s' %(self.sol)
        
        if self.iSolLine is not None:
            self.executiveControlLines[self.iSolLine] = newSol

        for line in self.executiveControlLines:
            msg += line+'\n'
        return msg

    def writeCaseControlDeck(self):
        """
        Writes the Case Control Deck.
        @param self the object pointer
        """
        msg = ''
        if self.caseControlDeck:
            msg += '$CASE CONTROL DECK\n'
            msg += str(self.caseControlDeck)
        assert 'BEGIN BULK' in msg, msg

        return msg

    def writeParams(self):
        """writes the PARAM cards"""
        msg = ''
        if self.params:
            msg += '$PARAMS\n'
        #print "self.nodes = ",self.nodes
        for (key, param) in sorted(self.params.iteritems()):
            #print "param = ",param
            msg += str(param)
        return msg

    def writeNodes(self):
        """writes the NODE-type cards"""
        msg = []
        if self.nodes:
            msg = ['$NODES\n']
            if self.gridSet:
                msg.append(str(self.gridSet))
            for (nid,node) in sorted(self.nodes.iteritems()):
                msg.append(str(node))

        if 0:
            self.writeNodes_Associated()

        if self.spoints:
            msg.append('$SPOINTS\n')
            msg.append(str(self.spoints))
        ###
        return ''.join(msg)

    def writeNodes_Associated(self):
        """
        Writes the NODE-type in associated and unassociated groups.
        @warning Sometimes crashes, probably on invalid BDFs.
        """
        msg = ''

        associatedNodes = set([])
        for (eid, element) in self.elements.iteritems():
            print(element)
            associatedNodes = associatedNodes.union(set(element.nodeIDs()))

        allNodes = set(self.nodes.keys())
        unassociatedNodes = list(allNodes.difference(associatedNodes))
        #missingNodes = allNodes.difference(
        associatedNodes = list(associatedNodes)


        if associatedNodes:
            msg += '$ASSOCIATED NODES\n'
            if self.gridSet:
                msg += str(self.gridSet)
            for key in sorted(associatedNodes):
                msg += str(self.nodes[key])

        if unassociatedNodes:
            msg += '$UNASSOCIATED NODES\n'
            if self.gridSet and not associatedNodes:
                msg += str(self.gridSet)
            for key in sorted(unassociatedNodes):
                if key in self.nodes:
                    msg += str(self.nodes[key])
                else:
                    msg += '$ Missing NodeID=%s' %(key)
        return msg

    def writeElements(self):
        """writes the elements in a sorted order"""
        msg = []
        if self.elements:
            msg = ['$ELEMENTS\n']
            for (eid, element) in sorted(self.elements.iteritems()):
                try:
                    msg.append(str(element))
                except:
                    print('failed printing element...'
                          'type=%s eid=%s' %(element.type,eid))
                    raise
                ###
        return ''.join(msg)

    def writeRigidElements(self):
        """writes the rigid elements in a sorted order"""
        msg = []
        if self.rigidElements:
            msg += '$RIGID ELEMENTS\n'
            for (eid, element) in sorted(self.rigidElements.iteritems()):
                try:
                    msg.append(str(element))
                except:
                    print('failed printing element...'
                          'type=%s eid=%s' %(element.type,eid))
                    raise
                ###
        return ''.join(msg)

    def writeProperties(self):
        """writes the properties in a sorted order"""
        msg = ''
        if self.properties:
            msg += '$PROPERTIES\n'
            for (pid, prop) in sorted(self.properties.iteritems()):
                msg += str(prop)
        return msg

    def writeElementsProperties(self):
        """writes the elements and properties in and interspersed order"""
        msg = []
        missingProperties = []
        if self.properties:
            msg = ['$ELEMENTS_WITH_PROPERTIES\n']

        eidsWritten = []
        for (pid, prop) in sorted(self.properties.iteritems()):
            eids = self.getElementIDsWithPID(pid)

            if eids:
                msg.append(str(prop))
                eids.sort()
                for eid in eids:
                    element = self.Element(eid)
                    try:
                        msg.append(str(element))
                    except:
                        print('failed printing element...'
                              'type=%s eid=%s' %(element.type,eid))
                        raise
                ###
                eidsWritten += eids
            else:
                missingProperties.append(str(prop))
            ###
        ###

        eidsMissing = set(self.elements.keys()).difference(set(eidsWritten))
        if eidsMissing:
            msg.append('$ELEMENTS_WITH_NO_PROPERTIES '
                       '(PID=0 and unanalyzed properties)\n')
            for eid in sorted(eidsMissing):
                element = self.Element(eid)
                try:
                    msg.append(str(element))
                except:
                    print('failed printing element...'
                          'type=%s eid=%s' %(element.type, eid))
                    raise
                ###
            ###

        if missingProperties:
            msg.append('$UNASSOCIATED_PROPERTIES\n')
            for missingProperty in missingProperties:
                msg.append(str(missingProperty))
        return ''.join(msg)

    def writeMaterials(self):
        """writes the materials in a sorted order"""
        msg = ''
        if self.materials:
            msg += '$MATERIALS\n'
            for (mid, material) in sorted(self.materials.iteritems()):
                msg += str(material)
            for (mid, material) in sorted(self.creepMaterials.iteritems()):
                msg += str(material)
            for (mid, material) in sorted(self.materialDeps.iteritems()):
                msg += str(material)
        return msg

    def writeThermalMaterials(self):
        """writes the thermal materials in a sorted order"""
        msg = ''
        if self.thermalMaterials:
            msg += '$THERMAL MATERIALS\n'
            for (mid, material) in sorted(self.thermalMaterials.iteritems()):
                msg += str(material)
        return msg

    def writeConstraints(self):
        """writes the constraint cards sorted by ID"""
        msg = ''
        if self.suports:
            msg += '$CONSTRAINTS\n'
            for suport in self.suports:
                msg += str(suport)
            ###

        if self.spcs or self.spcadds:
            msg += '$SPCs\n'
            strSPC = str(self.spcObject2)
            if strSPC:
                msg += strSPC
            else:
                for (spcID, spcadd) in sorted(self.spcadds.iteritems()):
                    msg += str(spcadd)
                for (spcID, spcs) in sorted(self.spcs.iteritems()):
                    for spc in spcs:
                        msg += str(spc)
                    ###
                ###
            ###
        ###
        
        if self.mpcs or self.mpcadds:
            msg += '$MPCs\n'
            strMPC = str(self.mpcObject2)
            if strMPC:
                msg += strMPC
            else:
                for (mpcID, mpcadd) in sorted(self.mpcadds.iteritems()):
                    msg += str(mpcadd)
                for (mpcID, mpcs) in sorted(self.mpcs.iteritems()):
                    for mpc in mpcs:
                        msg += str(mpc)
                    ###
                ###
            ###
        ###
        return msg
        #msg += '$ where are my constraints...\n'
        if self.constraints or self.suports:
            msg += '$CONSTRAINTS\n'
            for (key, loadcase) in sorted(self.constraints.iteritems()):
                for constraint in loadcase:
                    msg += str(constraint)
            for suport in self.suports:
                msg += str(suport)
            ###
        ###

    def writeLoads(self):
        """writes the load cards sorted by ID"""
        msg = ''
        if self.loads:
            msg += '$LOADS\n'
            for (key, loadcase) in sorted(self.loads.iteritems()):
                for load in loadcase:
                    try:
                        msg += str(load)
                    except:
                        print('failed printing load...type=%s key=%s'
                            %(load.type, key))
                        raise
                    ###
                ###
            ###
        ###
        return msg

    def writeOptimization(self):
        msg = ''
        if (self.dconstrs or self.desvars or self.ddvals or self.dresps 
          or self.dvprels or self.dvmrels or self.doptprm or self.dlinks):
            msg += '$OPTIMIZATION\n'
            for (ID, dconstr) in sorted(self.dconstrs.iteritems()):
                msg += str(dconstr)
            for (ID, desvar) in sorted(self.desvars.iteritems()):
                msg += str(desvar)
            for (ID, ddval) in sorted(self.ddvals.iteritems()):
                msg += str(ddval)
            for (ID, dlink) in sorted(self.dlinks.iteritems()):
                msg += str(dlink)
            for (ID, dresp) in sorted(self.dresps.iteritems()):
                msg += str(dresp)
            for (ID, dvmrel) in sorted(self.dvmrels.iteritems()):
                msg += str(dvmrel)
            for (ID, dvprel) in sorted(self.dvprels.iteritems()):
                msg += str(dvprel)
            for (ID, equation) in sorted(self.dequations.iteritems()):
                msg += str(equation)
            if self.doptprm is not None:
                msg += str(self.doptprm)
        return msg

    def writeTables(self):
        msg = ''
        if self.tables:
            msg += '$TABLES\n'
            for (ID, table) in sorted(self.tables.iteritems()):
                msg += str(table)
        if self.randomTables:
            msg += '$RANDOM TABLES\n'
            for (ID, table) in sorted(self.randomTables.iteritems()):
                msg += str(table)
        return msg

    def writeSets(self):
        msg = ''
        if (self.sets or self.setsSuper or self.asets or self.bsets or
            self.csets or self.qsets):
            msg += '$SETS\n'
            for (ID, setObj) in sorted(self.sets.iteritems()):
                msg += str(setObj)
            for (setObj) in sorted(self.asets):
                msg += str(setObj)
            for (setObj) in sorted(self.bsets):
                msg += str(setObj)
            for (setObj) in sorted(self.csets):
                msg += str(setObj)
            for (setObj) in sorted(self.qsets):
                msg += str(setObj)
            for (ID, setObj) in sorted(self.setsSuper.iteritems()):
                msg += str(setObj)
        return msg

    def writeDynamic(self):
        msg = ''
        if (self.dareas or self.nlparms or self.frequencies or self.methods or
            self.cMethods or self.tsteps or self.tstepnls):
            msg += '$DYNAMIC\n'
            for (ID, method) in sorted(self.methods.iteritems()):
                msg += str(method)
            for (ID, cMethod) in sorted(self.cMethods.iteritems()):
                msg += str(cMethod)
            for (ID, darea) in sorted(self.dareas.iteritems()):
                msg += str(darea)
            for (ID, nlparm) in sorted(self.nlparms.iteritems()):
                msg += str(nlparm)
            for (ID, tstep) in sorted(self.tsteps.iteritems()):
                msg += str(tstep)
            for (ID, tstepnl) in sorted(self.tstepnls.iteritems()):
                msg += str(tstepnl)
            for (ID, freq) in sorted(self.frequencies.iteritems()):
                msg += str(freq)
        return msg
        
    def writeAero(self):
        """writes the aero cards"""
        #print "output aero cards..."
        msg = ''
        if (self.aero or self.aeros or self.gusts or self.caeros 
        or self.paeros or self.trims):
            msg = '$AERO\n'
            for (ID, caero) in sorted(self.caeros.iteritems()):
                msg += str(caero)
            for (ID, paero) in sorted(self.paeros.iteritems()):
                msg += str(paero)
            for (ID, spline) in sorted(self.splines.iteritems()):
                msg += str(spline)
            for (ID, trim) in sorted(self.trims.iteritems()):
                msg += str(trim)

            for (ID, aero) in sorted(self.aero.iteritems()):
                msg += str(aero)
            for (ID, aero) in sorted(self.aeros.iteritems()):
                msg += str(aero)

            for (ID, gust) in sorted(self.gusts.iteritems()):
                msg += str(gust)
        return msg

    def writeAeroControl(self):
        """writes the aero control surface cards"""
        msg = ''
        if (self.aefacts or self.aeparams or self.aelinks or self.aelists or
            self.aestats or self.aesurfs):
            msg = '$AERO CONTROL SURFACES\n'
            for (ID, aelinks) in sorted(self.aelinks.iteritems()):
                for aelink in aelinks:
                    msg += str(aelink)
            for (ID, aeparam) in sorted(self.aeparams.iteritems()):
                msg += str(aeparam)
            for (ID, aestat) in sorted(self.aestats.iteritems()):
                msg += str(aestat)

            for (ID, aelist) in sorted(self.aelists.iteritems()):
                msg += str(aelist)
            for (ID, aesurf) in sorted(self.aesurfs.iteritems()):
                msg += str(aesurf)
            for (ID, aefact) in sorted(self.aefacts.iteritems()):
                msg += str(aefact)
        return msg

    def writeFlutter(self):
        """writes the flutter cards"""
        msg = []
        if (self.flfacts or self.flutters or self.mkaeros):
            msg = ['$FLUTTER\n']
            for (ID, flfact) in sorted(self.flfacts.iteritems()):
                #if ID!=0:
                msg.append(str(flfact))
            for (ID, flutter) in sorted(self.flutters.iteritems()):
                msg.append(str(flutter))
            for mkaero in self.mkaeros:
                msg.append(str(mkaero))
        return ''.join(msg)

    def writeThermal(self):
        """writes the thermal cards"""
        msg = ''
        # PHBDY
        if self.phbdys or self.convectionProperties or self.bcs:  # self.thermalProperties or
            msg = '$THERMAL\n'

            for (key, phbdy) in sorted(self.phbdys.iteritems()):
                msg += str(phbdy)

            #for key,prop in sorted(self.thermalProperties.iteritems()):
            #    msg += str(prop)
            for (key, prop) in sorted(self.convectionProperties.iteritems()):
                msg += str(prop)

            # BCs
            for (key, bcs) in sorted(self.bcs.iteritems()):
                for bc in bcs: # list
                    msg += str(bc)
                ###
            ###
        return msg

    def writeCoords(self):
        """writes the coordinate cards in a sorted order"""
        #print "output coords..."
        msg = ''
        if len(self.coords) > 1:
            msg += '$COORDS\n'
        #coordKeys = self.coords.keys()
        #self.log.info("coordKeys = %s" %(coordKeys))
        for (ID, coord) in sorted(self.coords.iteritems()):
            if ID != 0:
                msg += str(coord)
        return msg

    def writeRejects(self):
        """
        writes the rejected (processed) cards and the rejected unprocessed
        cardLines
        """
        msg = ''
        if self.rejectCards:
            msg += '$REJECTS\n'
            for rejectCard in self.rejectCards:
                try:
                    msg += printCard(rejectCard)
                except RuntimeError:
                    for field in rejectCard:
                        if field is not None and '=' in field:
                            raise SyntaxError('cannot reject equal signed '
                                          'cards\ncard=%s\n' %(rejectCard))
                    raise

        if self.rejects:
            msg += '$REJECT_LINES\n'
        for rejectLines in self.rejects:
            if rejectLines[0][0] == ' ':
                continue
            else:
                for reject in rejectLines:
                    reject2 = reject.rstrip()
                    if reject2:
                        msg += str(reject2)+'\n'
        return msg

