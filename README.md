# HL7-bar2xml
Transform HL7 V2.x Vertical Bar messages into HL7 V2.xml XML tagged message

The two Python scripts in this reprository allow you to transform HL7 messages
from the standard vertical bar format, to the HL7 v2.xml XML tagged format,
and back again.
## Requirements
bar2xml.py uses an XML Schema definition for the HL7 v2.xml message format.
HL7 v2.xml XML Schema definitions, for various HL7 v2.x versions, can be obtained from [HL7 International](https://www.hl7.org/).

You will also need a list of Message structures and the applicable Trigger Event(s) for the applicable HL7 v2.x version
This is the HL7 Defined table 0354 which you will find in Appendix A of the relevant HL7 version 2.x standard,
which is also available from [HL7 International](https://www.hl7.org/).
This needs to be formatted into a CSV file called 'hl7Table0354.csv' (with \<tab\> as the column separator) being two columns.
1. the first column is the message structure (e.g. ADT_A01)
2. the second column is the trigger event(s), possibly as a comma separated list of trigger events (A01,A04,A08,A13), possibly as a range of trigger events (M01-M06).

These scripts will transform a single message from stdin, or a message from a file in a folder, or all the messages(files) in a folder.
## Usage
bar2xml.py can accept a message wrapped in the HL7 MLLP encoding characters or the message can start with 'MSH'. The output will **not** be wrapped with the HL7 MLLP encoding characters.  
If the message is from stdin, then
  * the output will be written to stdout

If the message is from one or more files, then
  * There must be only one message in each file
  * the output will be written to a file with the same basename as the input file
    * bar2xml.py will create a file with the extension of '.xml'.
    * xml2bar.py will create a file with the extension of '.hl7'.

