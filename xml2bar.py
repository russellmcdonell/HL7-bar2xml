# pylint: disable=line-too-long
'''
Script xml2bar.py
A script to convert an HL7 v2.xml XML tagged message into a HL7 v2.x vertical bar message


This script reads an HL7 v2.xml XML tagged bar message from <stdin>, or a file,
or all the message files in a folder.


    SYNOPSIS
    $ python xml2bar.py [-I inputDir|--inputDir=inputDir]
        [-i inputFile|--inputFile=inputFile]
        [-O outputDir|--outputDir=outputDir]
        [-v loggingLevel|--verbose=logingLevel]
        [-L logDir|--logDir=logDir]
        [-l logfile|--logfile=logfile]
        [-|filename]...


    REQUIRED


    OPTIONS
    -I inputDir|--inputDir=inputDir
    The folder containing the HL7 v2.xml XML tagged message(s).

    -i inputFile|--inputFile=inputFile
    The name of the HL7 v2.xml XML tagged message to be converted.

    -O outputDir|--outputDir=outputDir
    The folder where the output file(s) will be created.

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
fieldSep = None         # The field separator character
repSep = None           # The repeat separator
escSep = None           # The escape delimiter
compSep = None          # The component separator
subCompSep = None       # The subcomponent separator
hl7charRef = re.compile(r'&#x(([0-9A-Fa-f][0-9A-Fa-f])+);')
removeNamespace = re.compile(r' xmlns="[^"]+"')



def getDocument(fileName):
    '''
    Get an HL7 v2.xml XML tagged message from a file or standard input
    '''
    thisHL7message = ''
    if fileName == '-':     # Use standard input
        for line in sys.stdin:
            thisHL7message += line.strip()
    else:
        if not os.path.isfile(fileName):
            logging.fatal('No file named %s', fileName)
            logging.shutdown()
            sys.exit(EX_CONFIG)
        with open(fileName, 'rt', encoding='utf-8') as fpin:
            for line in fpin:
                thisHL7message += line.strip()
    thisHL7message = hl7charRef.sub(r'\\X\1\\', thisHL7message)
    thisHL7message = removeNamespace.sub('', thisHL7message)
    try:
        thisHL7xml = et.fromstring(thisHL7message, )
    except:
        logging.critical('Invalid XML input')
        logging.shutdown()
        sys.exit(EX_DATAERR)
    return thisHL7xml


def getSegment(thisSegElement):
    '''
    Construct the fields for this segment
    '''
    thisSegment = thisSegElement.tag
    if len(thisSegment) > 3:
        for segChild in thisSegElement:
            thisSegChild = getSegment(segChild)
            if thisSegChild is not None:
                Segments.append(thisSegChild)
        return None
    lastField = 0
    for field in thisSegElement:        # The field or field group elements
        if field.tag == 'MSH.1':        # Don't need the field separator as a separate field
            lastField = 1
            continue
        fieldNo = int(field.tag[4:])
        if fieldNo == lastField:
            thisSegment += repSep
        else:
            while lastField < fieldNo:
                thisSegment += fieldSep
                lastField += 1
        thisSegment += getField(field)
    return thisSegment


def getField(thisFieldElement):
    '''
    Convert a field element into a HL7 vertical bar structured field
    '''

    thisField = ''
    if (len(thisFieldElement) == 0) or (thisFieldElement[0].tag =='escape'):
        thisField += thisFieldElement.text
        if len(thisFieldElement) > 0:
            for fieldEsc in thisFieldElement:
                if fieldEsc.tag != 'escape':
                    logging.critical('Illegal XML - field(%s) - "<escape>" and other tags in field', thisFieldElement.tag)
                    logging.shutdown()
                    sys.exit(EX_DATAERR)
                if 'V' not in fieldEsc.attrib:
                    logging.critical('Malformed "<escape>" tag in field(%s)', thisFieldElement.tag)
                    logging.shutdown()
                    sys.exit(EX_DATAERR)
                if escSep is None:
                    logging.critical('Malformed XML - "<escape>" element in field(%s), but no Escape Delimiter defined in MSH', thisFieldElement.tag)
                    logging.shutdown()
                    sys.exit(EX_DATAERR)
                thisField += escSep + fieldEsc.attrib['V'] + escSep
                if fieldEsc.tail is not None:
                    thisField += fieldEsc.tail
        return thisField
    lastCompNo = 1
    for thisComponent in thisFieldElement:
        thisComponentTag = thisComponent.tag
        dotAt = thisComponentTag.find('.')
        thisCompNo = int(thisComponentTag[dotAt + 1:])
        while lastCompNo < thisCompNo:
            thisField += compSep
            lastCompNo += 1
        if len(thisComponent) is None:
            thisField += thisComponent.text
        else:
            thisField += getComponent(thisComponent)
    return thisField


def getComponent(component):
    '''
    Get a compond component
    '''

    thisComp = ''
    if (len(component) == 0) or (component[0].tag =='escape'):
        thisComp += component.text
        if len(component) > 0:
            if thisComp.tag != 'escape':
                logging.critical('Illegal XML - component(%s) - "<escape>" and other tags in component', component.tag)
                logging.shutdown()
                sys.exit(EX_DATAERR)
            if 'V' not in thisComp.attrib:
                logging.critical('Malformed "<escape>" tag in component(%s)', component.tag)
                logging.shutdown()
                sys.exit(EX_DATAERR)
            if escSep is None:
                logging.critical('Malformed XML - "<escape>" element in component(%s), but no Escape Delimiter defined in MSH', component.tag)
                logging.shutdown()
                sys.exit(EX_DATAERR)
            for compEsc in component:
                thisComp += escSep + compEsc.attrib['V'] + escSep
                if compEsc.tail is not None:
                    thisComp += compEsc.tail
        return thisComp
    lastSubCompNo = 1
    for subComp in component:
        subCompTag = subComp.tag
        subCompDotAt = subCompTag.find('.')
        thisSubCompNo = int(subCompTag[subCompDotAt + 1:])
        while lastSubCompNo < thisSubCompNo:
            thisComp += subCompSep
            lastSubCompNo += 1
        thisComp += subComp.text
        if len(subComp) > 0:
            for subCompEsc in subComp:
                if subComp.tag != 'escape':
                    logging.critical('Illegal XML - component(%s) - "<escape>" and other tags in subcomponent', subComp.tag)
                    logging.shutdown()
                    sys.exit(EX_DATAERR)
                if 'V' not in subComp.attrib:
                    logging.critical('Malformed "<escape>" tag in subcomponent(%s)', subComp.tag)
                    logging.shutdown()
                    sys.exit(EX_DATAERR)
                if escSep is None:
                    logging.critical('Malformed XML - "<escape>" element in suncomponent(%s), but no Escape Delimiter defined in MSH', subComp.tag)
                    logging.shutdown()
                    sys.exit(EX_DATAERR)
                thisComp += escSep + subCompEsc.attrib['V'] + escSep
                if subCompEsc.tail is not None:
                    thisComp += subCompEsc.tail
    return thisComp


if __name__ == '__main__':
    '''
    The main code
    Start by parsing the command line arguements and setting up logging.
    Then process each file name in the command line - read the HL7 v2.xml XML tagged message
    and convert it an HL7 v2.x vertical bar message
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
        hl7xml = getDocument(messageFile)
        MSH = hl7xml[0]
        if MSH.tag != 'MSH':
            logging.critical('Message missing MSH segment')
            logging.shutdown()
            sys.exit(EX_DATAERR)
        if MSH[0].tag != 'MSH.1':
            logging.critical('Message missing MSH.1 [Field Separator] field')
            logging.shutdown()
            sys.exit(EX_DATAERR)
        fieldSep = MSH[0].text
        if MSH[1].tag != 'MSH.2':
            logging.critical('Messing missing MSH.2 [Encoding Characters] field')
            logging.shutdown()
            sys.exit(EX_DATAERR)
        delimiterCharacters = MSH[1].text
        if len(delimiterCharacters) < 2:
            logging.critical('Insufficient message delimiter characters')
            logging.shutdown()
            sys.exit(EX_DATAERR)
        compSep = delimiterCharacters[0:1]
        repSep = delimiterCharacters[1:2]
        if len(delimiterCharacters) > 2:
            escSep = delimiterCharacters[2:3]
        else:
            escSep = None
        if len(delimiterCharacters) > 3:
            subCompSep = delimiterCharacters[3:4]
        else:
            subCompSep = None

        # Now assemble the Segments
        Segments = []
        for child in hl7xml:
            thisSeg = getSegment(child)
            if thisSeg is not None:
                Segments.append(thisSeg)

        # Save the HL7 V2.x vertical bar message
        if messageFile == '-':
            hl7Message = '\r'.join(Segments) + '\r'
            print(hl7Message)
        else:
            basename = os.path.basename(messageFile)
            name, ext = os.path.splitext(basename)
            outputFile = name + '.hl7'
            if outputDir is not None:
                outputFile = os.path.join(outputDir, outputFile)
            elif outputFile == messageFile:
                outputFile = 'HL7_' + outputFile
            with open(outputFile, 'wt', encoding='utf-8', newline='\r') as fpout:
                for seg in Segments:
                    logging.info(seg)
                    print(seg, file=fpout)
