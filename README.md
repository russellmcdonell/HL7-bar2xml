# HL7-bar2xml
Transform HL7 V2.x Vertical Bar messages into HL7 V2.xml XML tagged message

The two Python scripts in this repository (**bar2xml.py** and **xml2bar.py**) allow you to transform HL7 messages
from the standard vertical bar format, to the HL7 v2.xml XML tagged format, and back again.

## Requirements
### bar2xml.py
**bar2xml.py** uses an XML Schema definition for the HL7 v2.xml message format.
HL7 v2.xml XML Schema definitions, for various HL7 v2.x versions, can be obtained from [HL7 International](https://www.hl7.org/).

You will also need a list of Message structures and the applicable Trigger Event(s) for the applicable HL7 v2.x version.
This is the HL7 Defined table 0354 which you will find in Appendix A of the specification of the relevant HL7 version 2.x standard,
which is also available from [HL7 International](https://www.hl7.org/).
This needs to be formatted into a CSV file called 'hl7Table0354.csv' (with \<tab\> as the column separator) being two columns.
1. the first column is the message structure (e.g. ADT_A01)
2. the second column is the trigger event(s), possibly as a comma separated list of trigger events (A01,A04,A08,A13), possibly as a range of trigger events (M01-M06).


### xml2bar.py
**xml2bar.py** does not use any message definition as it assumes that any HL7 v2.xml message that it is given to transform is a validly constructed HL7 v2.xml message. Messages are not validated [other than the message starts with MSH and correctly defines the field, repeat and component separators] but are transformed into HL7 v2.x vertical bar messages algorithmically. Hence, any invalid HL7 v2.xml formatted message, with repeating fields that shouldn't repeat, or missing required segments, will be transformed into an equally invalid HL7 v2.x vertical bar message.
## Usage
These scripts will transform a single message from stdin, or a message from a file in a folder, or all the messages(files) in a folder.

**bar2xml.py** can accept a message wrapped in the HL7 MLLP encoding characters or the message can start with 'MSH'. The output will **not** be wrapped with the HL7 MLLP encoding characters.

If the message is from stdin, then
  * the output will be written to stdout

If the message is from one or more files, then
  * There must be only one message in each file
  * the output will be written to a file with the same basename as the input file
    * bar2xml.py will create a file with the extension of '.xml'.
    * xml2bar.py will create a file with the extension of '.hl7'.

## Utilities
This folder contains two scripts (**xsd2ams.py** and **xsd2train.py**) for documenting HL7 Message Structures.

**xsd2ams.py** renders the selected HL7 Message structure in the Abstract Message Structure format (the format in the HL7 standard specifications - square and curly brackets for optional and repeating segments/segment structures). These are output as worksheets in an Excel workbook. Multiple HL7 Messages structures can be specified on the command line, each of which will be rendered as a separate Abstract Message structure on separate worksheets in the Excel workbook.

**xsd2train.py** renders a single HL7 Message structure as a '.png' file, where each segment is represented as a box with the segment name inside the box and an arrow from before the box, to after the box, under the bottom of the box, if the segment is optional, and an arrow from after the box, to before the box, over the top of the box if the segment can repeat. For choice structures, the segment name is replaced with the list of the optional segment names, separated by the vertical bar character. Segment groups are rendered using additional optional/repeat lines around all the segments in the group. These segment gouping arrows are nested to show the nested structure of the segment groups (see ORM_O01.png in the testOutput folder).

### Requirements
**xsd2ams.py**, like **bar2xml.py** uses the HL7 v2.xml XML Schema definitions mentioned above. However, you will also need the list of message types and descriptions, for the applicable HL7 v2.x version, which you will find in Appendix A.3 of the specification of the relevant HL7 version of the v2.x standard. You will also need a list of the Event Types and descriptions for the applicable HL7 v2.x version.
This is the HL7 Defined table 0003 which you will find in Appendix A of the specification of relevant HL7 version of the v2.x standard. And finally, you will also need a list of the segment codes, descriptions and chapter numbers, for the applicable HL7 v2.x version, which you will find in Appendix A.4 of the specification of the relevant HL7 version of the v2.x standard. Copies of the specification, for all version of the HL7 v2.x standard are available from [HL7 International](https://www.hl7.org/).

**xsd2train.py** only uses the HL7 v2.xml XML Schema definitions mentioned above.