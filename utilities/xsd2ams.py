# pylint: disable=line-too-long
'''
Script xsd2ams.py
A script to render an HL7 v2.xml XML schema as an HL7 Abstract Message Structure

This script reads an HL7 v2.x message structure from the 'xsd' schema folder
and then renders it a an HL7 Abstract Message Structure which is written to an Excel Workbook


    SYNOPSIS
    $ python bar2xml.py
        [-S schemaDir|--schemaDir=schemaDir]
        [-O outputDir|--outputDir=outputDir]
        [-o outputFilename|--ouputFilename=outputFilename]
        [-v loggingLevel|--verbose=logingLevel]
        [-L logDir|--logDir=logDir]
        [-l logfile|--logfile=logfile]
        messageStructure ...


    REQUIRED
    messageStructure
    One or more message structures

    
    OPTIONS
    -S schemaDir|--schemaDir=schemaDir
    The folder containing the HL7 v2.xml XML Schema files for the relevant version of HL7 v2.x
    (default = 'schema/v2.4')

    -O outputDir|--outputDir=outputDir
    The folder where the output file of the Abstract Message Structure will be created as an Excel Workbook.

    -o outputFilename|--outputFilename=outputFilename
    The name of the Excel Workbook of Abstract Message Structure to be created

    -v loggingLevel|--verbose=loggingLevel
    Set the level of logging that you want.

    -L logDir|--logDir=logDir
    The directory where the log file will be created (default=".").

    -l logfile|--logfile=logfile
    The name of a log file where you want all messages captured.
'''

# pylint: disable=invalid-name, pointless-string-statement, global-statement, superfluous-parens

import os
import sys
import logging
import argparse
import csv
from xml.etree import ElementTree as et
from openpyxl import Workbook

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

hl7messageTypes = {}    # The descriptions of the message types
hl7segments = {}        # The description and chapter for each segment
namespaces={'xsd':'http://www.w3.org/2001/XMLSchema'}   # The namespaces in the XSD message structure definition
messageRoot = None      # The root of the XSD message structure definition
lines = []              # The list of lines that make up this AMS


def render(sequence, indent, isChoice):
    '''
    Render an XML sequence as an Abstract Message Structure
    PARAMETERS:
        sequence, XML Element - an XML Schema sequence definition
    RETURNS:
        lines, list - list of lines for of the AMS
    '''

    firstSeg = True
    for segNo, seg in enumerate(sequence):
        name = seg.attrib['ref']
        if name.startswith('any'):
            continue
        if len(name) == 3:      # A segment
            if name in hl7segments:
                segName, chapter = hl7segments[name]
            else:
                segName = 'Unknown'
                chapter = ''
            if isChoice:
                if firstSeg:
                    firstSeg = False
                    name = '<' + name
                    if segNo == (len(sequence) - 1):
                        name = name + '>'
                    else:
                        name = name + '|'
                elif segNo == (len(sequence) - 1):
                    name = ' ' + name + '>'
                else:
                    name = ' ' + name + '|'
            if seg.attrib['maxOccurs'] == 'unbounded':
                name = '{' + name + '}'
            if seg.attrib['minOccurs'] == '0':
                name = '[' + name + ']'
            lines.append([indent + name, segName, chapter])
        else:
            if seg.attrib['minOccurs'] == '0':
                lines.append([indent + '[', name + ' - begin', ''])
                indent += '   '
                if seg.attrib['maxOccurs'] == 'unbounded':
                    lines.append([indent + '{', '', ''])
                    indent += '   '
            elif seg.attrib['maxOccurs'] == 'unbounded':
                lines.append([indent + '{', name + ' - begin', ''])
                indent += '   '
            thisChoice = False
            newSequence = messageRoot.find("xsd:complexType[@name='" + name + ".CONTENT']/xsd:sequence", namespaces)
            if newSequence is None:
                thisChoice = True
                newSequence = messageRoot.find("xsd:complexType[@name='" + name + ".CONTENT']/xsd:choice", namespaces)
            # logging.debug('newSequence for name(%s) - %s, isChoice(%s)', name, repr(newSequence), isChoice)
            render(newSequence, indent, thisChoice)
            if seg.attrib['minOccurs'] == '0':
                if seg.attrib['maxOccurs'] == 'unbounded':
                    indent = indent[:-3]
                    lines.append([indent + '}', '' ''])
                indent = indent[:-3]
                lines.append([indent + ']', name + ' - end', ''])
            elif seg.attrib['maxOccurs'] == 'unbounded':
                indent = indent[:-3]
                lines.append([indent + '}', name + ' - end' ''])
    return



if __name__ == '__main__':
    '''
    The main code
    Start by parsing the command line arguements and setting up logging.
    Then process the HL7 v2.xml message structure definition.
    '''

    # Set the command line options
    progName = sys.argv[0]
    progName = progName[0:-3]        # Strip off the .py ending
    parser = argparse.ArgumentParser(description='bar2xml')
    parser.add_argument('-S', '--schemaDir', dest='schemaDir', default='schema/v2.4',
                        help='The folder containing the HL7 v2.xml XML schema files (default="schema/v2.4")')
    parser.add_argument('-O', '--outputDir', dest='outputDir', default='.',
                        help='The folder where Excel Workbook containing the HL7 Abstact Message Structure will be created (default=".")')
    parser.add_argument('-o', '--outputFilename', dest='outputFilename',
                        help='The filename of the Excel Workbook containing the HL7 Abstact Message Structure that will be created (default="firstMessageStrucutre.xlsx")')
    parser.add_argument ('-v', '--verbose', dest='verbose', type=int, choices=range(0,5),
                         help='The level of logging\n\t0=CRITICAL,1=ERROR,2=WARNING,3=INFO,4=DEBUG')
    parser.add_argument ('-L', '--logDir', dest='logDir', default='.', metavar='logDir',
                         help='The name of the directory where the logging file will be created')
    parser.add_argument ('-l', '--logFile', dest='logFile', metavar='logfile', help='The name of a logging file')
    parser.add_argument('messageStructures', nargs='*',
                        help='The basename of the HL7 v2.xml message structure file(s)')

    # Parse the command line
    args = parser.parse_args()
    schemaDir = args.schemaDir
    outputDir = args.outputDir
    outputFile = args.outputFilename
    logDir = args.logDir
    logFile = args.logFile
    loggingLevel = args.verbose
    msgStructures = args.messageStructures

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
    logging.debug(msgStructures)

    # Check that the schemaDir folder exist
    if not os.path.isdir(schemaDir):
        logging.critical('No schemaDir folder named "%s"', schemaDir)
        logging.shutdown()
        sys.exit(EX_CONFIG)
    if not os.path.isdir(os.path.join(schemaDir, 'xsd')):
        logging.critical('No schemaDir folder named "%s/xsd"', schemaDir)
        logging.shutdown()
        sys.exit(EX_CONFIG)

    # Check that the message types and segments files exist
    if not os.path.isfile(os.path.join(schemaDir, 'hl7messageTypes.csv')):
        logging.critical('No file "hl7messageTypes.csv" in schemaDir folder(%s/xsd)', schemaDir)
        logging.shutdown()
        sys.exit(EX_CONFIG)
    hl7messageTypes = {}
    with open(os.path.join(schemaDir, 'hl7messageTypes.csv'), 'rt', encoding='utf-8') as hl7TableFile:
        csvReader = csv.reader(hl7TableFile, delimiter='\t')
        header = True
        for row in csvReader:
            if header:
                header = False
                continue
            hl7messageTypes[row[0]] = row[1]
    logging.debug(hl7messageTypes)
    if not os.path.isfile(os.path.join(schemaDir, 'hl7Table0003.csv')):
        logging.critical('No file "hl7Table0003.csv" in schemaDir folder(%s/xsd)', schemaDir)
        logging.shutdown()
        sys.exit(EX_CONFIG)
    hl7messageEvents = {}
    with open(os.path.join(schemaDir, 'hl7Table0003.csv'), 'rt', encoding='utf-8') as hl7TableFile:
        csvReader = csv.reader(hl7TableFile, delimiter='\t')
        header = True
        for row in csvReader:
            if header:
                header = False
                continue
            event = row[1]
            dashAt = event.find('-')
            spaceAt = event.find(' ')
            if dashAt is not None:
                event = event[dashAt + 1:]
            elif spaceAt is not None:
                event = event[spaceAt + 1:]
            event.strip()
            hl7messageEvents[row[0]] = event
    logging.debug(hl7messageEvents)
    if not os.path.isfile(os.path.join(schemaDir, 'hl7segments.csv')):
        logging.critical('No file "hl7segments.csv" in schemaDir folder(%s/xsd)', schemaDir)
        logging.shutdown()
        sys.exit(EX_CONFIG)
    hl7segments = {}
    with open(os.path.join(schemaDir, 'hl7segments.csv'), 'rt', encoding='utf-8') as hl7TableFile:
        csvReader = csv.reader(hl7TableFile, delimiter='\t')
        header = True
        for row in csvReader:
            if header:
                header = False
                continue
            hl7segments[row[0]] = (row[1], row[2])

    # Create the output Excel Workbook
    if outputFile is None:
        outputFile = msgStructures[0] + '.xlsx'
    if outputDir is not None:
        outputFile = os.path.join(outputDir, outputFile)
    wb = Workbook()

    # Process the message structures
    firstMSGstructure = True
    for msgStruct in msgStructures:
        # Check that the message structure file(s) exists and read it in
        if not os.path.isfile(os.path.join(schemaDir, 'xsd', msgStruct + '.xsd')):
            logging.critical('Unknown message structure (%s)', msgStruct)
            logging.shutdown()
            sys.exit(EX_DATAERR)
        messageTree = et.parse(os.path.join(schemaDir, 'xsd', msgStruct + '.xsd'))
        messageRoot = messageTree.getroot()
        segmentList = messageRoot.find("xsd:complexType[@name='" + msgStruct + ".CONTENT']/xsd:sequence", namespaces)
        # logging.debug('message structure(%s), mesasgeRoot(%s), segmentList(%s)', msgStruct, messageRoot, repr(segmentList))

        # Check that the definintion starts with MSH
        if segmentList[0].attrib['ref'] != 'MSH' :
            logging.critical('MSH not defined for messages structure(%s)', msgStruct)
            logging.shutdown()
            sys.exit(EX_CONFIG)

        # Now create the HL7 v2 Abstract Message Structure output
        lines = []
        if msgStruct[0:3] in hl7messageTypes:
            structName = hl7messageTypes[msgStruct[0:3]]
        else:
            structName = 'Unknown'
        if msgStruct[-3:] in hl7messageEvents:
            structName += ' -' + hl7messageEvents[msgStruct[-3:]]
        else:
            structName += ' - Unknown'
        if structName.find('message') == -1:
            structName += ' message'
        lines.append([msgStruct, structName, 'Chapter'])
        render(segmentList, '', False)
        msgAMS = ''
        for line in lines:
            msgAMSline = '\t'.join(line)
            msgAMS += msgAMSline + '\n'

        # Save the HL7 V2 Abstract Message Structure
        logging.info(msgAMS)
        if firstMSGstructure:
            ws = wb.active
            ws.title = msgStruct
            firstMSGstructure = False
        else:
            ws = wb.create_sheet(msgStruct)
        for line in lines:
            ws.append(line)
    wb.save(outputFile)
