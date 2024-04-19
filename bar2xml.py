# pylint: disable=line-too-long
'''
Script bar2xml.py
A script to convert an HL7 v2.x vertical bar message into a HL7 v2.xml XML tagged message


This script reads an HL7 v2.x vertical bar message from <stdin>, or a file,
or all the message files in a folder.


    SYNOPSIS
    $ python bar2xml.py [-I inputDir|--inputDir=inputDir]
        [-i inputFile|--inputFile=inputFile]
        [-O outputDir|--outputDir=outputDir]
        [-S schemaDir|--schemaDir=schemaDir]
        [-v loggingLevel|--verbose=logingLevel]
        [-L logDir|--logDir=logDir]
        [-l logfile|--logfile=logfile]
        [-|filename]...


    REQUIRED


    OPTIONS
    -I inputDir|--inputDir=inputDir
    The folder containing the HL7 vertical bar message(s).

    -i inputFile|--inputFile=inputFile
    The name of the HL7 vertical bar message file to be converted.

    -O outputDir|--outputDir=outputDir
    The folder where the output file(s) will be created.

    -S schemaDir|--schemaDir=schemaDir
    The folder containing the HL7 v2.xml XML Schema files for the relevant version of HL7 v2.x
    (default = 'schema/v2.4')

    -v loggingLevel|--verbose=loggingLevel
    Set the level of logging that you want.

    -L logDir|--logDir=logDir
    The directory where the log file will be created (default=".").

    -l logfile|--logfile=logfile
    The name of a log file where you want all messages captured.
'''

# pylint: disable=invalid-name, bare-except, pointless-string-statement, global-statement; superfluous-parens

import os
import sys
import logging
import argparse
import re
import csv
from xml.etree import ElementTree as et

# This next section is plagurised from /usr/include/sysexits.h
EX_OK = 0               # successful termination
EX_WARN = 1             # non-fatal termination with warnings

EX_USAGE = 64           # command line usage error
EX_DATAERR = 65         # data format error
EX_NOINPUT = 66         # cannot open input
EX_NOUSER = 67          # addressee unknown
EX_NOHOST = 68          # host name unknown
EX_UNAVAILABLE = 69     # service unavailable
EX_SOFTWARE = 70        # internal software error
EX_OSERR = 71           # system error (e.g., can't fork)
EX_OSFILE = 72          # critical OS file missing
EX_CANTCREAT = 73       # can't create (user) output file
EX_IOERR = 74           # input/output error
EX_TEMPFAIL = 75        # temp failure; user is invited to retry
EX_PROTOCOL = 76        # remote error in protocol
EX_NOPERM = 77          # permission denied
EX_CONFIG = 78          # configuration error

Segments = []           # The Segments in the message being converted
segmentNo = 0           # The next segment in the message to be converted
segmentRoot = None      # The XML Schema for the segments
fieldRoot = None        # The XML Schema for the fields
dataTypeRoot = None     # The XML Schema for the data types
messageRoot = None      # The XML Schema for the message being converted
namespaces = None       # The namespaces of the XML Schemas
fieldSep = None         # The field separator character
repSep = None           # The repeat separator
compSep = None          # The component separator
subCompSep = None       # The subcomponent separator
xmlReplacements = [
    re.compile(r'\\(H)\\'),
    re.compile(r'\\(N)\\'),
    re.compile(r'\\(\.br)\\'),
    re.compile(r'\\(\.sp\s*\d+)\\'),
    re.compile(r'\\(\.in\s*[-+]?\d+)\\'),
    re.compile(r'\\(\.ti\s*[-+]?\d+)\\')
]
charXref = re.compile(r'\\X([0-9A-Fa-f][0-9A-Fa-f])+\\')
charZref = re.compile(r'\\Z([0-9A-Fa-f][0-9A-Fa-f])+\\')
hl7charRef = re.compile(r'&amp;(#x([0-9A-Fa-f][0-9A-Fa-f])+;)')



def getDocument(fileName):
    '''
    Get an HL7 vertical bar message from a file or standard input
    '''
    thisHL7message = ''
    if fileName == '-':     # Use standard input
        for line in sys.stdin:
            thisHL7message += line.rstrip() + '\n'
        return thisHL7message
    if not os.path.isfile(fileName):
        logging.fatal('No file named %s', fileName)
        logging.shutdown()
        sys.exit(EX_CONFIG)
    with open(fileName, 'rt', encoding='utf-8') as fpin:
        for line in fpin:
            thisHL7message += line.rstrip() + '\r'
        return thisHL7message


def createXML(sequenceList, tag, optional, isChoice, depth):
    '''
    Output an XML structure for all the elements in the sequence list where we have a matching segment in the Segments.
    PARAMETERS:
        xmlElement - et.Element, the current element we are working on
        sequenceList - et.Element,the XML sequence we are working on, from the message structure XSD
        sequenceAt - int, how far we are through this sequence list
        tag - str, the group tag, if any
        optional - boolean whether no output is valid
        depth - int, the recursion depth
    This is a recursive routine, so we use depth to prevent indifinite recurrsion
    '''

    global segmentNo

    if depth > 200:
        # Treat this segment as unexpected
        comment = et.Comment(Segments[segmentNo])
        newElement = et.Element(tag)
        newElement.append(comment)
        segmentNo += 1
        return newElement
    depth += 1
    sequenceAt = 0
    thisElement = None
    tagged = False
    occurs = 0
    lastSeg = None
    while sequenceAt < len(sequenceList):
        if sequenceList[sequenceAt].attrib['ref'] != Segments[segmentNo][0:3]:
            # Check if this segment is here, after some optional segments
            if len(sequenceList[sequenceAt].attrib['ref']) > 3:     # A group
                groupRef = sequenceList[sequenceAt].attrib['ref']
                groupOptional = False
                if sequenceList[sequenceAt].attrib['minOccurs'] == '0':
                    groupOptional = True
                thisChoice = False
                groupList = messageRoot.find("xsd:complexType[@name='" + groupRef + ".CONTENT']/xsd:sequence", namespaces)
                if groupList is None:
                    groupList = messageRoot.find("xsd:complexType[@name='" + groupRef + ".CONTENT']/xsd:choice", namespaces)
                    thisChoice = True
                    if groupList is None:
                        logging.critical('XML Schema definition missing either xsd:sequence or xsd:choice for %s', groupRef + '.CONTENT')
                        logging.shutdown()
                        sys.exit(EX_CONFIG)
                groupXML = createXML(groupList, groupRef, groupOptional, thisChoice, depth)
                if groupXML is not None:        # At least one segment was found at in this group
                    if not tagged:
                        thisElement = et.Element(tag)
                        tagged = True
                    thisElement.append(groupXML)
                    if segmentNo < len(Segments):       # More to do
                        continue
                    return thisElement
                # Nothing found - make sure group is optional and skip if it is
                if sequenceList[sequenceAt].attrib['minOccurs'] == '0':
                    sequenceAt += 1
                    continue
                return thisElement
            # Check if this segment is optional
            if sequenceList[sequenceAt].attrib['minOccurs'] == '0':
                sequenceAt += 1
                continue
            # This is some sort of failure something, that is this segment isrequire and is not present
            # If this sequence is optional, then return what we have
            if optional:
                return thisElement
            # Otherwise, reat this segment as 'unexpected'
            comment = et.Comment('Unexpected segment: ' + Segments[segmentNo])
            if not tagged:
                thisElement = et.Element(tag)
                tagged = True
            thisElement.append(comment)
            segmentNo += 1
            if segmentNo < len(Segments):
                continue
            return thisElement
        # A matching segment
        seg = Segments[segmentNo][0:3]
        if (lastSeg is None) or (lastSeg != seg):
            lastSeg = seg
            occurs = 0
        if not tagged:
            thisElement = et.Element(tag)
            tagged = True
        segElement = et.Element(seg)
        Fields = Segments[segmentNo].split(fieldSep)
        if Fields[0] == 'MSH':
            Fields.insert(1, fieldSep)
        seg = Fields[0]
        Fields = Fields[1:]
        xmlSeg = segmentRoot.find("xsd:complexType[@name='" + seg + ".CONTENT']/xsd:sequence", namespaces)
        for i, field in enumerate(Fields):
            if field == '':
                continue
            if (seg != 'MSH') and (i != 1):
                fieldReps = field.split(repSep)
            else:
                fieldReps = [field]
            for thisField in fieldReps:
                if (i < len(xmlSeg)) and ('ref' in xmlSeg[i].attrib):
                    fieldRef = xmlSeg[i].attrib['ref']
                    fieldXML = et.Element(fieldRef)
                    fieldType = fieldRoot.find("xsd:attributeGroup[@name='" + fieldRef + ".ATTRIBUTES']/xsd:attribute[@name='Type']", namespaces).attrib['fixed']
                    if fieldType == 'varies':
                        if (seg == 'OBX') and (fieldRef == 'OBX.5'):
                            fieldType = Fields[1]
                        elif (seg == 'MFE') and (fieldRef == 'MFE.4') and (len(Fields) > 4):
                            fieldType = Fields[4]
                    dataTypeBits = dataTypeRoot.find("xsd:complexType[@name='" + fieldType + "']/xsd:sequence", namespaces)
                    if fieldType == 'FT':       # FT has a sequence, but not components
                        dataTypeBits = None
                    if dataTypeBits is not None:
                        Components = thisField.split(compSep)
                        for j, component in enumerate(Components):
                            if component == '':
                                continue
                            componentRef = dataTypeBits[j].attrib['ref']
                            componentType = dataTypeRoot.find("xsd:attributeGroup[@name='" + componentRef + ".ATTRIBUTES']/xsd:attribute[@name='Type']", namespaces).attrib['fixed']
                            componentBits = dataTypeRoot.find("xsd:complexType[@name='" + componentType + "']/xsd:sequence", namespaces)
                            if (componentBits is not None) and (subCompSep != ''):
                                componentXML = et.Element(componentRef)
                                subComponents = component.split(subCompSep)
                                for k, subComponent in enumerate(subComponents):
                                    if subComponent == '':
                                        continue
                                    subCompRef = componentBits[k].attrib['ref']
                                    subCompType = dataTypeRoot.find("xsd:attributeGroup[@name='" + subCompRef + ".ATTRIBUTES']/xsd:attribute[@name='Type']", namespaces).attrib['fixed']
                                    subComponentXML = et.Element(subCompRef)
                                    subComponentXML.text = subComponent
                                    fixElement(subComponentXML, subCompType)
                                    componentXML.append(subComponentXML)
                                fieldXML.append(componentXML)
                            else:
                                componentXML = et.Element(componentRef)
                                componentXML.text = component
                                fixElement(componentXML, componentType)
                                fieldXML.append(componentXML)
                    else:
                        fieldXML.text = thisField
                        fixElement(fieldXML, fieldType)
                    segElement.append(fieldXML)
                else:       # Undefined field
                    fieldCode = f'{seg}.{i + 1:d}'
                    fieldXML = et.Element(fieldCode)
                    fieldXML.text = thisField
                    segElement.append(fieldXML)
        thisElement.append(segElement)
        segmentNo += 1
        if segmentNo == len(Segments):
            return thisElement
        if isChoice:
            return thisElement
        occurs += 1
        maxOccurs = sequenceList[sequenceAt].attrib['maxOccurs']
        if maxOccurs == 'unbounded':
            continue
        if int(occurs) < int(maxOccurs):
            continue
        sequenceAt += 1
        if sequenceAt < len(sequenceList):
            continue
    return thisElement


def fixElement(thisElement, textType):
    '''
    Fix the text associated with thisElement
    We may need to add child element like <escape ... />
    The tail of thisElement will be the text up to the <escape ... />
    and the remaining text will be the tail of the child <escape ... /> tag
    '''
    if textType not in ['TX', 'FT', 'CF']:
        return
    elementText = thisElement.text
    while (charRef := charXref.search(elementText)) is not None:
        chars = charRef.group()[2:-1]
        repChars = ''
        for cp in range(0, len(chars), 2):
            repChars += r'&#x' + chars[cp:cp + 2] + ';'
        elementText = elementText[0:charRef.start()] + repChars + elementText[charRef.end():]
    while (charRef := charZref.search(elementText)) is not None:
        chars = charRef.group()[2:-1]
        repChars = ''
        for cp in range(0, len(chars), 2):
            repChars += r'&#x' + chars[cp:cp + 2] + ';'
        elementText = elementText[0:charRef.start()] + repChars + elementText[charRef.end():]
    thisElement.text = elementText
    firstEscape = None
    for replacement in xmlReplacements:
        if (found := replacement.search(elementText)) is not None:
            if (firstEscape is None) or (found.start() < firstEscape):
                firstEscape = found.start()
                firstEnd = found.end()
                firstGroup = found.group()
    if firstEscape is None:
        return
    thisElement.text = elementText[:firstEscape]
    escapeElement = et.Element('escape')
    escapeElement.attrib['V'] = firstGroup[1:-1]
    escapeElement.tail = elementText[firstEnd:]
    thisElement.append(escapeElement)
    lastEscapeElement = escapeElement
    escapeElementTail = escapeElement.tail
    while True:
        nextEscape = None
        for replacement in xmlReplacements:
            if (found := replacement.search(escapeElementTail)) is not None:
                if (nextEscape is None) or (found.start() < nextEscape):
                    nextEscape = found.start()
                    nextEnd = found.end()
                    nextGroup = found.group()
        if nextEscape is None:
            return
        lastEscapeElement.tail = escapeElementTail[:nextEscape]
        escapeElement = et.Element('escape')
        escapeElement.attrib['V'] = nextGroup[1:-1]
        escapeElement.tail = escapeElementTail[nextEnd:]
        thisElement.append(escapeElement)
        lastEscapeElement = escapeElement
        escapeElementTail = escapeElement.tail


if __name__ == '__main__':
    '''
    The main code
    Start by parsing the command line arguements and setting up logging.
    Then process each file name in the command line - read the HL7 v2.x vertical bar message
    and convert it an HL7 v2.xml XML tagged message
    '''

    # Set the command line options
    progName = sys.argv[0]
    progName = progName[0:-3]        # Strip off the .py ending
    parser = argparse.ArgumentParser(description='bar2xml')
    parser.add_argument('-I', '--inputDir', dest='inputDir',
                        help='The folder containing the HL7 v2.x vertical bar encoded message files')
    parser.add_argument('-i', '--inputFile', dest='inputFile',
                        help='The name of the HL7 v2.x vertical bar encoded message file')
    parser.add_argument('-O', '--outputDir', dest='outputDir', default='.',
                        help='The folder where the HL7 v2.xml XML tagged message(s) will be created (default=".")')
    parser.add_argument('-S', '--schemaDir', dest='schemaDir', required=True, default='schema/v2.4',
                        help='The folder containing the HL7 v2.xml XML schema files (default="schema/v2.4")')
    parser.add_argument ('-v', '--verbose', dest='verbose', type=int, choices=range(0,5),
                         help='The level of logging\n\t0=CRITICAL,1=ERROR,2=WARNING,3=INFO,4=DEBUG')
    parser.add_argument ('-L', '--logDir', dest='logDir', default='.', metavar='logDir',
                         help='The name of the directory where the logging file will be created')
    parser.add_argument ('-l', '--logFile', dest='logFile', metavar='logfile', help='The name of a logging file')

    # Parse the command line
    args = parser.parse_args()
    inputDir = args.inputDir
    inputFile = args.inputFile
    outputDir = args.outputDir
    schemaDir = args.schemaDir
    logDir = args.logDir
    logFile = args.logFile
    loggingLevel = args.verbose

    # Set up logging
    logging_levels = {0:logging.CRITICAL, 1:logging.ERROR, 2:logging.WARNING, 3:logging.INFO, 4:logging.DEBUG}
    logfmt = progName + ' [%(asctime)s]: %(message)s'
    if loggingLevel is not None:    # Change the logging level from "WARN" if the -v vebose option is specified
        if logFile is not None:        # and send it to a file if the -o logfile option is specified
            with open(os.path.join(logDir, logFile), 'wt', encoding='utf-8', newline='') as logOutput:
                pass
            logging.basicConfig(format=logfmt, datefmt='%d/%m/%y %H:%M:%S %p', level=logging_levels[loggingLevel], filename=os.path.join(logDir, logFile))
        else:
            logging.basicConfig(format=logfmt, datefmt='%d/%m/%y %H:%M:%S %p', level=logging_levels[loggingLevel])
    else:
        if logFile is not None:        # send the default (WARN) logging to a file if the -o logfile option is specified
            with open(os.path.join(logDir, logFile), 'wt', encoding='utf-8', newline='') as logOutput:
                pass
            logging.basicConfig(format=logfmt, datefmt='%d/%m/%y %H:%M:%S %p', filename=os.path.join(logDir, logFile))
        else:
            logging.basicConfig(format=logfmt, datefmt='%d/%m/%y %H:%M:%S %p')
    logging.debug('Logging set up')

    # Check that the schemaDir folder exist and read in the segment, fields and datatype schema
    if not os.path.isdir(schemaDir):
        logging.critical('No schemaDir folder named "%s"', schemaDir)
        logging.shutdown()
        sys.exit(EX_CONFIG)
    if not os.path.isdir(os.path.join(schemaDir, 'xsd')):
        logging.critical('No schemaDir folder named "%s/xsd"', schemaDir)
        logging.shutdown()
        sys.exit(EX_CONFIG)
    if not os.path.isfile(os.path.join(schemaDir, 'xsd', 'segments.xsd')):
        logging.critical('No file "segments.xsd" in schemaDir folder(%s/xsd)', schemaDir)
        logging.shutdown()
        sys.exit(EX_CONFIG)
    segmentTree = et.parse(os.path.join(schemaDir, 'xsd', 'segments.xsd'))
    segmentRoot = segmentTree.getroot()
    if not os.path.isfile(os.path.join(schemaDir, 'xsd', 'fields.xsd')):
        logging.critical('No file "fields.xsd" in schemaDir folder(%s/xsd)', schemaDir)
        logging.shutdown()
        sys.exit(EX_CONFIG)
    fieldTree = et.parse(os.path.join(schemaDir, 'xsd', 'fields.xsd'))
    fieldRoot = fieldTree.getroot()
    if not os.path.isfile(os.path.join(schemaDir, 'xsd', 'datatypes.xsd')):
        logging.critical('No file "datatypes.xsd" in schemaDir folder(%s/xsd)', schemaDir)
        logging.shutdown()
        sys.exit(EX_CONFIG)
    dataTypeTree = et.parse(os.path.join(schemaDir, 'xsd', 'datatypes.xsd'))
    dataTypeRoot = dataTypeTree.getroot()
    namespaces={'xsd':'http://www.w3.org/2001/XMLSchema'}

    # Check that the message structure file exists
    if not os.path.isfile(os.path.join(schemaDir, 'hl7Table0354.csv')):
        logging.critical('No file "hl7Table054.csv" in schemaDir folder(%s/xsd)', schemaDir)
        logging.shutdown()
        sys.exit(EX_CONFIG)
    hl7messageStructures = {}
    with open(os.path.join(schemaDir, 'hl7Table0354.csv'), 'rt', encoding='utf-8') as hl7TableFile:
        csvReader = csv.reader(hl7TableFile, delimiter='\t')
        header = True
        for row in csvReader:
            if header:
                header = False
                continue
            msgStructure = row[0]
            msgStruct = msgStructure[0:3]
            if msgStruct not in hl7messageStructures:
                hl7messageStructures[msgStruct] = {}
            msgTriggers = row[1].split(',')
            for trigger in msgTriggers:
                thisTrigger = trigger.strip()
                if len(thisTrigger) == 3:
                    hl7messageStructures[msgStruct][thisTrigger] = msgStructure
                elif (len(thisTrigger) == 7) and (thisTrigger[3:4] == '-'):
                    thisLetter = thisTrigger[0:1]
                    thisStart = int(thisTrigger[1:3])
                    thisEnd = int(thisTrigger[5:7]) + 1
                    for eachTrigger in range(thisStart, thisEnd):
                        oneTrigger = f'{thisLetter}{eachTrigger:02d}'
                        hl7messageStructures[msgStruct][oneTrigger] = msgStructure

    # If inputFile is specified and is '-', then read one HL7 v2.x vertical bar encoded message from standard input
    # If inputFile is specified and is not '-', and inputDir is None then read one HL7 v2.x vertical bar encoded message from ./inputFile.
    # If inputFile is specified and is not '-', and inputDir is not None then read one HL7 v2.x vertical bar encoded message from inputDir/inputFile.
    # If both inputFile and inputDir are not specified, then read one HL7 v2.x vertical bar encoded message from standard input.
    # If inputFile is not specified, but inputDir is specified, then read one HL7 v2.x vertical bar encoded message for every file in inputDir.

    # If one HL7 v2.x vertical bar encoded message is read from standard input, then output one HL7 v2.xml XML tagges message to standard output.
    # Otherwise use the basename of filename, with the extension changed to '.hl7' to create the outputFile filename.
    # If outputDir is specified, then create the file as outputDir/outputFile.
    # If outputDir is not specified, then create the file as inputDir/outputFile.
    hl7MessageFiles = []
    if inputFile is not None:
        if inputFile == '-':
            hl7MessageFiles.append('-')
        elif inputDir is None:
            hl7MessageFiles.append(inputFile)
        else:
            hl7MessageFiles.append(os.path.join(inputDir, inputFile))
    else:
        if inputDir is None:
            hl7MessageFiles.append('-')
        else:
            for thisFile in os.listdir(inputDir):
                hl7MessageFiles.append(os.path.join(inputDir, thisFile))

    # Process each of these HL7 v2.x vertical bar encoded messages
    for messageFile in hl7MessageFiles:
        hl7Message = getDocument(messageFile)

        # Check for MLLP
        if (hl7Message[0:1] == chr(11)) and (hl7Message[-2:] == chr(28) + chr(13)):
            hl7Message = hl7Message[1:-2]

        # Convert this hl7 v2.x vertical bar encoded message
        Segments = hl7Message.rstrip().split('\r')

        # Check that the MSH can at least be partially parsed
        MSH = Segments[0]
        if len(MSH) < 20:
            logging.fatal('First segment too short - less than 20 characters')
            sys.exit(EX_DATAERR)
        if MSH[0:3] != 'MSH':
            logging.fatal('First segment not MSH')
            sys.exit(EX_DATAERR)

        # Now partially parse the first segment (should be MSH)
        # for the field separator and encoding characters
        fieldSep = MSH[3:4]
        MSHfields = MSH.split(fieldSep)
        if len(MSHfields[1]) < 4:
            subCompSep = ''
        else:
            subCompSep = MSHfields[1][3:4]
        if len(MSHfields[1]) < 3:
            escChar = ''
            subCompSep = ''
        else:
            escChar = MSHfields[1][2:3]
            subCompSep = MSHfields[1][3:4]
        if len(MSHfields[1]) < 2:
            logging.fatal('MSH.2 field less then 2 characters long')
            logging.shutdown()
            sys.exit(EX_DATAERR)
        compSep = MSHfields[1][0:1]
        repSep = MSHfields[1][1:2]

        # And check that MSH has enough fields
        if len(MSHfields) < 12:
            logging.fatal('MSH segment too short - no version!')
            logging.shutdown()
            sys.exit(EX_DATAERR)

        # Now we can further parse the MSH segment for the message type, event and structure
        # All we really want is structure (msgStruct)
        struct = MSHfields[8]
        msgStruct = ''
        if struct == '' :
            logging.fatal('Missing MSH.9.1 component [Message Code]')
            logging.shutdown()
            sys.exit(EX_DATAERR)
        if struct == 'ACK':         # |ACK| is legal?
            msgStruct = 'ACK'
        else:
            typeParts = struct.split(compSep)
            if len(typeParts) == 1:     # |TYP| is illegal if TYP is not ACK
                logging.critical('Missing MSH.9.2 component [Trigger Event] and MSH.9.3 component [Message Structure]')
                logging.shutdown()
                sys.exit(EX_DATAERR)
            msgType = typeParts[0]
            msgTrigger = typeParts[1]
            if len(typeParts) == 3:
                msgStruct = typeParts[2]
            if msgStruct == '':           # We don't have structure, so we will have to deduce it
                if msgType == '':           # |^TRG| and |^TRG^| are illegal
                    logging.critical('Missing MSH.9.1 component [Message Type]')
                    logging.shutdown()
                    sys.exit(EX_DATAERR)
                if msgTrigger == '':
                    if msgType == 'ACK':        # |ACK^| and |ACK^^| are legal?
                        msgStruct = 'ACK'
                    else:               # |TYP^| and |TYP^^| are illegal
                        logging.critical('Missing MSH.9.2 component [Trigger Event] and MSH.9.3 component [Message Structure]')
                        logging.shutdown()
                        sys.exit(EX_DATAERR)
                else:       # Try and deduce message structure from type and trigger
                    if msgType not in hl7messageStructures:
                        logging.critical('Unknown MSH.9.1 [Message Type] (%s)', msgType)
                        logging.shutdown()
                        sys.exit(EX_DATAERR)
                    if msgTrigger not in hl7messageStructures[msgType]:
                        logging.critical('Unknown MSH.9.2 [Message Trigger] (%s)', msgTrigger)
                        logging.shutdown()
                        sys.exit(EX_DATAERR)
                    msgStruct = hl7messageStructures[msgType][msgTrigger]

        # Now we need to read in the message structure as defined in the xsd
        if not os.path.isfile(os.path.join(schemaDir, 'xsd', msgStruct + '.xsd')):
            logging.critical('Unknown message structure (%s)', msgStruct)
            logging.shutdown()
            sys.exit(EX_DATAERR)
        messageTree = et.parse(os.path.join(schemaDir, 'xsd', msgStruct + '.xsd'))
        messageRoot = messageTree.getroot()
        segmentList = messageRoot.find("xsd:complexType[@name='" + msgStruct + ".CONTENT']/xsd:sequence", namespaces)

        # Check that the definintion starts with MSH
        if segmentList[0].attrib['ref'] != 'MSH' :
            logging.critical('MSH not defined for messages structure(%s)', msgStruct)
            logging.shutdown()
            sys.exit(EX_CONFIG)

        # Now create the HL7 v2.xml data
        segmentNo = 0
        hl7XML = createXML(segmentList, msgStruct, False, 0)
        hl7XML.attrib['xmlns'] = 'urn:hl7-org:v2xml'
        hl7XML.attrib['xmlns:xsi'] = 'http://www.w3.org/2001/XMLSchema-instance'
        hl7XML.attrib['xsi:schemaLocation'] = 'urn:hl7-org:v2xml ' + msgStruct + '.xsd'
        et.indent(hl7XML, '    ')

        # Save the HL7 V2.xml message
        s = et.tostring(hl7XML, encoding='unicode')
        s = hl7charRef.sub(r'&\1', s)
        if messageFile == '-':
            print(s)
        else:
            logging.info(s)
            basename = os.path.basename(messageFile)
            name, ext = os.path.splitext(basename)
            outputFile = name + '.xml'
            if outputDir is not None:
                outputFile = os.path.join(outputDir, outputFile)
            elif outputFile == messageFile:
                outputFile = 'XML_' + outputFile
            with open(outputFile, 'wt', encoding='utf-8', newline='') as fpout:
                print(s, file=fpout)
