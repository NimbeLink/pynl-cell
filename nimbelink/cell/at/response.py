"""
AT interface utilities

(C) NimbeLink Corp. 2021

All rights reserved except as explicitly granted in the license agreement
between NimbeLink Corp. and the designated licensee. No other use or disclosure
of this software is permitted. Portions of this software may be subject to third
party license terms as specified in this software, and such portions are
excluded from the preceding copyright notice of NimbeLink Corp.
"""

import typing

from .result import Result

class Response(object):
    """A response to an AT command
    """

    DefaultNewLine = "\r\n"
    """The default line endings to use"""

    def __init__(self, result, command = None, output = None, newLine = None):
        """Creates a response

        :param self:
            Self
        :param result:
            The result of the response
        :param command:
            The command that led to this response
        :param output:
            Generic output, sans result indicator
        :param newLine:
            The line endings used

        :return none:
        """

        if command is None:
            command = ""

        if output is None:
            output = ""

        if newLine is None:
            newLine = Response.DefaultNewLine

        self.result = result
        self.command = command
        self.output = output

        self._newLine = newLine

    @property
    def lines(self):
        """Gets the individual lines from the output

        A response cannot necessarily know ahead of time if its output contents
        are individual string lines or binary data that might contain line
        endings. A user of a response is responsible for knowing the context of
        the response, and thus can decide to interpret the output as individual
        lines using this property, which will return the output contents as an
        array of lines with their line endings stripped.

        :param self:
            Self

        :return Array of Strings:
            The output contents as lines
        """

        return self.output.split(self._newLine)

    def __bool__(self):
        """Gets a boolean representation of the response

        :param self:
            Self

        :return True:
            Response was a success
        :return False:
            Response was a failure
        """

        if self.result:
            return True

        return False

    def __str__(self):
        """Gets a string representation of the response

        :param self:
            Self

        :return String:
            Us
        """

        string = ""

        if len(self.command) > 0:
            string += self.command + self._newLine

        if len(self.output) > 0:
            string += self.output + self._newLine

        string += f"{self.result}"

        return string

    def __contains__(self, item: typing.Union[str, bytes]) -> bool:
        """Checks if the response contains a string

        :param self:
            Self
        :param item:
            The string to check for

        :return True:
            Response contains the string
        :return False:
            Response does not contain the string
        """

        return item in self.output

    @staticmethod
    def _filterCommand(command, output):
        """Filters out an echoed command from a response's output

        :param command:
            The command
        :param output:
            The output that might contain the command

        :return String:
            The filtered output
        """

        # Try to filter out the command itself, if present
        commandStart = output.find(command)

        # If the command wasn't echoed back, nothing to do
        if commandStart == -1:
            return output

        # Skip over the command and the line endings automatically appended
        # after it
        return output[len(command):].lstrip()

    @staticmethod
    def makeFromString(string, command = None, newLine = None):
        """Creates a new response from output

        :param string:
            The raw string output to parse
        :param command:
            The command this is a response to
        :param newLine:
            The newline style to use

        :return None:
            Failed to parse response
        :return Response:
            The response
        """

        if newLine is None:
            newLine = Response.DefaultNewLine

        # If there is a final \r\n at the very end, discard it
        if string.endswith(newLine):
            string = string[:-2]

        # Find the last occurrence of \r\n, which would come before our result
        resultStart = string.rfind(newLine)

        # If that failed, this isn't a valid response
        if resultStart == -1:
            return None

        # Split the string into generic output and the final result
        output = string[:resultStart]
        result = string[resultStart + 2:]

        # If we're provided a command for context, make sure the output is
        # stripped of any echoed command characters
        if command is not None:
            output = Response._filterCommand(command = command, output = output)

        # Make the result from the last line
        result = Result.makeFromString(string = result)

        # If that failed, this isn't a valid response
        if result is None:
            return None

        return Response(
            command = command,
            output = output,
            result = result
        )
