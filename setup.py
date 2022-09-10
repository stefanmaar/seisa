#!/usr/bin/env python

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

'''
The seisa setup script.

:copyright:
    Stefan Mertl

:license:
    GNU General Public License, Version 3 
    (http://www.gnu.org/licenses/gpl-3.0.html)
'''
import sys
from setup_ext import printStatus, printMessage, printLine, printRaw

# Check for mandatory modules.
try:
    import numpy  # @UnusedImport # NOQA
    from numpy.distutils.core import setup
    from numpy.distutils.misc_util import Configuration
except ImportError:
    printLine()
    printRaw("MISSING REQUIREMENT")
    printStatus('numpy', 'Missing module')
    msg = ('Numpy is needed to run the seisa setup script. '
           'Please install it first.')
    printMessage(msg)
    msg = ('Numpy is needed to run the seisa setup script. '
           'Please install it first.')
    raise ImportError(msg)

# Set the current seisa version, author and description.
__version__ = "0.0.1"
__author__ = "Stefan Mertl"
__author_email__ = "stefan@mertl-research.at"
__description__ = ("A toolbox for audification and sonification "
                   "of seismic data.")
__long_escription__ = ("A toolbox for audification and sonification "
                       "of seismic data.")
__website__ = "https://github.com/stefanmaar/seisa"
__download_url__ = "https://github.com/stefanmaar/seisa"
__license__ = "GNU General Public Licence version 3"
__keywords__ = "seismological seismic audification sonification audio"

# Set the directories of the packages.
package_dir = {'': 'lib'}

# Define the packages to be processed.
packages = ['seisa',
            'seisa.audification']

# Define the scripts to be processed.
scripts = []

# Define some package data.
package_data = {}

# Define the package requirements.
install_requires = ['matplotlib>=3.2.0',
                    'obspy>=1.1.1',
                    'pedalboard>=0.5.9']

# Let the user know what's going on.
printLine()
printRaw("BUILDING SEISA")
printStatus('seisa', __version__)
printStatus('python', sys.version)
printStatus('platform', sys.platform)
if sys.platform == 'win32':
    printStatus('Windows version', sys.getwindowsversion())
printRaw("")
printRaw("")


def configuration(parent_package = '', top_path = None):
    '''

    '''
    config = Configuration('', parent_package, top_path,
                           package_dir = package_dir)
    return config


long_description = ('seisa is a toolbox for the audification '
                    'and sonfication of seismic data.')
setup(name = 'seisa',
      version = __version__,
      description = __description__,
      long_description = long_description,
      author = __author__,
      author_email = __author_email__,
      url = __website__,
      download_url = __download_url__,
      license = __license__,
      keywords = __keywords__,
      packages = packages,
      platforms = 'any',
      scripts = scripts,
      package_data = package_data,
      ext_package = 'seisa.lib',
      install_requires = install_requires,
      configuration = configuration)
