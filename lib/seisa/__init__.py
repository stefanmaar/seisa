# LICENSE
#
# This file is part of seisa.
#
# If you use seisa in any program or publication, please inform and
# acknowledge its author Stefan Mertl (stefan@mertl-research.at).
#
# seisa is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

__version__ = "0.0.1"
__author__ = "Stefan Mertl"
__author_mail__ = "stefan@mertl-research.at"
__description__ = "A toolbox for audification and sonification of seismic data."
__long_escription__ = "A toolbox for audification and sonification of seismic data."
__website__ = "https://github.com/stefanmaar/seisa"
__download_url__ = "https://github.com/stefanmaar/seisa"
__license__ = "GNU General Public Licence version 3"
__keywords__ = "seismological seismic audification sonification audio"

import logging
import sys

log_config = {}
log_config['level'] = 'INFO'

# The matplotlib plot style.
plot_style = 'seaborn-paper'


class MultilineMessagesFormatter(logging.Formatter):
    '''
    The MultilineMessagesFormatter is taken from https://github.com/peterlauri/python-multiline-log-formatter
    written by Peter Lauri and published under the following license.

    ----
    Copyright (c) 2016, Peter Lauri
    All rights reserved.

    Redistribution and use in source and binary forms, with or without modification, are permitted provided that the
    following conditions are met:

    1. Redistributions of source code must retain the above copyright notice, this list of conditions and the following
    disclaimer.

    2. Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following
    disclaimer in the documentation and/or other materials provided with the distribution.

    THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
    INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
    DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
    SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
    SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
    WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
    THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
    ----

    The class has been modified to use the format passed to the formatter for the
    multiline markers.
    '''

    def format(self, record):
        """
        This is mostly the same as logging.Formatter.format except for the splitlines() thing.
        This is done so (copied the code) to not make logging a bottleneck. It's not lots of code
        after all, and it's pretty straightforward.
        """
        multiline_fmt = self._fmt.replace('#LOG#', '#DET#')
        record.message = record.getMessage()
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        if '\n' in record.message:
            splitted = record.message.splitlines()
            output = self._fmt % dict(record.__dict__, message=splitted.pop(0)) + '\n'
            output += '\n'.join(
                multiline_fmt % dict(record.__dict__, message=line)
                for line in splitted
            )
        else:
            output = self._fmt % record.__dict__

        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            #output += ' ' + multiline_fmt % record.__dict__ + '\n'
            output += '\n'
            try:
                output += '\n'.join(
                    multiline_fmt % dict(record.__dict__, message=line)
                    for index, line in enumerate(record.exc_text.splitlines())
                )
            except UnicodeError:
                output += '\n'.join(
                    multiline_fmt % dict(record.__dict__, message=line)
                    for index, line
                    in enumerate(record.exc_text.decode(sys.getfilesystemencoding(), 'replace').splitlines())
                )
        return output


class LoggingMainProcessFilter(logging.Filter):

    def filter(self, rec):
        return rec.processName == 'MainProcess'

    
def get_logger(inst):
    ''' Get a logger for the passed instance.
    '''
    mod_name = inst.__module__

    if not mod_name.startswith('seisa'):
        log_prefix = 'seisa.unknown'
        loggerName = log_prefix + '.' + inst.__module__ + "." + inst.__class__.__name__
    else:
        loggerName = inst.__module__ + "." + inst.__class__.__name__

    return logging.getLogger(loggerName)


def get_logger_handler(mode='console', log_level = None):
    ch = logging.StreamHandler()
    if log_level is None:
        log_level = log_config['level']
    ch.setLevel(log_level)
    formatter = logging.Formatter("#LOG# - %(asctime)s - %(process)d - %(levelname)s - %(name)s: %(message)s")
    ch.setFormatter(formatter)

    return ch


def get_logger_filehandler(filename=None, log_level = None):
    if not filename:
        return

    if log_level is None:
        log_level = log_config['level']

    ch = logging.FileHandler(filename)
    ch.setLevel(log_level)
    formatter = MultilineMessagesFormatter("#LOG# - %(asctime)s - %(levelname)s - %(name)s: %(message)s")
    ch.setFormatter(formatter)

    return ch
