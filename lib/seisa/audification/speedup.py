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

import numpy as np
import pedalboard as pb


class SpeedUpSynth(object):
    ''' Audification using speeding up the playback.
    '''

    def __init__(self, stream, factor = 200, frequ_min = 1,
                 frequ_max = 25, audio_sps = 44100):
        ''' Initialization of the instance.

        Parameters
        ----------
        factor: float
            The factor used to speed up the data.
        '''
        # The seismic data which should be sped up.
        self.stream = stream

        # The audio data stream
        self.audio_stream = None
        
        # The factor to speed up the data.
        self.factor = factor

        # The lower bandpass corner frequency.
        self.frequ_min = frequ_min

        # The upper bandpass corner frequency.
        self.frequ_max = frequ_max

        # The audio sample rate.
        self.audio_sps = audio_sps


    def run(self, comp_ratio = 5, comp_threshold_db = -35):
        ''' Perform the audification.
        '''
        self.audio_stream = self.stream.copy()
        for cur_trace in self.audio_stream:
            self.speed_up(cur_trace)
            self.adjust_dynamic_range(cur_trace,
                                      ratio = comp_ratio,
                                      threshold_db = comp_threshold_db)


    def speed_up(self, trace):
        ''' Speed up the playback rate.
        '''
        trace.detrend('demean')
        trace.filter('bandpass',
                     freqmin = self.frequ_min,
                     freqmax = self.frequ_max,
                     zerophase = True)
        # Speed up by changing the sampling rate.
        speedup_sps = trace.stats.sampling_rate * self.factor
        trace.stats.sampling_rate = speedup_sps

        if speedup_sps <= self.audio_sps:
            # Interpolate to the audio sps.
            trace.interpolate(sampling_rate = self.audio_sps,
                              method = 'lanczos',
                              a = 20)
        else:
            # Resample to the audio sps.
            trace.resample(self.audio_sps,
                           window = 'hann')
        # Normalize
        trace.normalize()
        trace.taper(0.01)


    def adjust_dynamic_range(self, trace, threshold_db = -35,
                             ratio = 9, attack_ms = 5,
                             release_ms = 100):
        ''' Adjust the dynamic range using a compressor.
        '''
        audio = trace.data
        board = pb.Pedalboard([pb.Compressor(threshold_db = threshold_db,
                                             ratio = ratio,
                                             attack_ms = attack_ms,
                                             release_ms = release_ms)])
        effected = board(audio, self.audio_sps)

        # Normalize the amplitude
        effected = effected / np.max(np.abs(effected))
        trace.data = effected
