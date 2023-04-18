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

import functools

import matplotlib as mpl
import matplotlib.animation
import matplotlib.dates as mdates
import matplotlib.gridspec
import matplotlib.offsetbox
import matplotlib.pyplot as plt
import matplotlib.ticker
import moviepy.editor as mpe
import moviepy.video.io.bindings as mp_bind
import numpy as np
import scipy as sp
import scipy.signal

import seisa.util as util


class SpectrogramVideo(object):
    ''' Spectrogram animation of a trace.
    '''

    def __init__(self, stream, audio_stream, speed_up, audio_sps = 44100):
        ''' Initialization of the instance.

        '''
        # The seismic data which should be visualized.
        self.stream = stream

        # The related audio stream.
        self.audio_stream = audio_stream

        # The speed-up factor.
        self.speed_up = speed_up

        # The audio sample rate.
        self.audio_sps = audio_sps

        # The output figure width [inch].
        self.fig_width = 7.7

        # [px] Output video resolution options (width, height)
        self.resolution_dict = {'crude': (640, 360),
                                '720p': (1280, 720),
                                '1080p': (1920, 1080),
                                '2K': (2560, 1440),
                                '4K': (3840, 2160)}

        # The animation figure.
        self.fig = None

        # Parameters used for animation.
        self.ax_width = None
        self.n_frames = None
        self.last_playhead_pos = 0

        # The resolution of the figure.
        self.resolution = None

        # The animation artists
        self.spec_line = None
        self.wf_line = None
        self.time_box = None
        self.wf_full = None
        self.wf_progress = None

        # The animation framecounter.
        self.framecounter = 0

        # Flag to indicate if the artists should be animated.
        self.animate = True

        # The rendering frame cache.
        self.cache = None

        # The animation frame times of the original trace.
        self.frame_times = None

        
    def init_figure(self, spec_win_length = 5, spec_win_overlap = 50,
                    db_lim = 'smart', freq_min = None,
                    freq_max = None, log_freq_scale = False, utc_offset = None,
                    resolution = '1080p', units = None):
        ''' Initialize the animation figure.
        '''
        tr = self.stream[0]

        # The figure size
        dpi = 72
        disp_ratio = 16 / 9
        fig_width = 1920 / dpi

        # Global plotting parameters.
        mpl.rcParams['axes.labelsize'] = 30
        mpl.rcParams['axes.linewidth'] = 3

        fig_size = (fig_width,
                    fig_width / disp_ratio)

        fig = plt.figure(figsize = fig_size,
                         dpi = dpi)
        
        # The axes of the plot
        gs = mpl.gridspec.GridSpec(2, 1,
                                   figure = fig,
                                   height_ratios = [2, 1])
        ax_spec = fig.add_subplot(gs[0, 0])
        ax_seismo = fig.add_subplot(gs[1, 0],
                                    sharex = ax_spec)

        # Plot the spectrogram.
        f, t, sxx = self.compute_spectrogram(tr,
                                             win_length = spec_win_length,
                                             win_overlap = spec_win_overlap)
        t = t / self.speed_up
        sxx_db = 20 * np.log10(sxx)

        # Interpolate the spectrogram to a regular grid with 
        # equal spacing in the log-space.
        f_loglin = np.logspace(np.log10(freq_min),
                               np.log10(freq_max),
                               num = 1000)
        f_interp = sp.interpolate.interp2d(t, f, sxx_db, kind = 'linear')
        sxx_interp = f_interp(t, f_loglin)

        y = np.arange(sxx_interp.shape[0])
        ax_spec.pcolormesh(t, y, sxx_interp)

        # Plot the seismogram.
        tr.normalize()
        t = tr.times()
    
        t = t / self.speed_up
        ax_seismo.plot(t, tr.data,
                       color = 'k',
                       linewidth = 2)

        # Add the playhead lines.
        spec_playhead = ax_spec.axvline(1,
                                        color = 'gray',
                                        linewidth = 3)
        seismo_playhead = ax_seismo.axvline(1,
                                            color = 'gray',
                                            linewidth = 3)

        ax_spec.set_xlim(0, t[-1])

        # Style the axes.
        ax_spec.set_xticks([])
        ax_spec.set_yticks([])
        ax_seismo.set_xticks([])
        ax_seismo.set_yticks([])

        # Annotation
        ax_spec.set_ylabel('Frequenz')
        ax_seismo.set_xlabel('Zeit')
        ax_seismo.set_ylabel('Amplitude')

        # Adjust the figure spacings
        fig.tight_layout()
        fig.subplots_adjust(hspace=0, wspace=0.05)

        # Save variables in the instance.
        self.fig = fig
        self.ax_spec = ax_spec
        self.ax_seismo = ax_seismo
        self.spec_playhead = spec_playhead
        self.seismo_playhead = seismo_playhead
        
        
    def make_frame(self, t):
        ''' Create a frame for a moviepy video.
            '''        
        self.spec_playhead.set_xdata(t)
        self.seismo_playhead.set_xdata(t)
        
        ret = mp_bind.mplfig_to_npimage(self.fig)
        return ret

    
    def render_moviepy(self, audio_filepath,
                       fps = 20, animate = True,
                       duration = None):
        ''' Render the animation using moviepy.
        '''
        # Create the animation instance.
        x_lim = self.ax_spec.get_xlim()
        duration = x_lim[1]
        handler = functools.partial(self.make_frame)
        animation = mpe.VideoClip(handler,
                                  duration = duration)
        audioclip = mpe.AudioFileClip(audio_filepath)
        animation = animation.set_audio(audioclip)

        return animation

        
    def compute_spectrogram(self, tr, win_length, win_overlap, nfft = None):
        ''' Compute the spectrogram of the data.
        
        '''
        sps = tr.stats.sampling_rate
        n_perseg = int(win_length * sps)
        n_overlap = np.floor(n_perseg * win_overlap / 100)

        comp_nfft = util.next_power_of_2(int(n_perseg))
        if nfft is None:
            nfft = comp_nfft
        if comp_nfft > nfft:
            print("A larger nfft number would have be needed: {:d}.".format(comp_nfft))

        f, t, sxx = sp.signal.spectrogram(tr.data, sps,
                                          window = 'hann',
                                          nperseg = n_perseg,
                                          noverlap = n_overlap,
                                          nfft = nfft)

        return f, t, sxx


class UTCDateFormatter(mdates.ConciseDateFormatter):
    '''
    This function is based on code taken from the sonify program licensed 
    under the MIT License.
    
    MIT License

    Copyright (c) 2020-2022 Liam Toney

    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction, including without limitation the rights
    to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
    copies of the Software, and to permit persons to whom the Software is
    furnished to do so, subject to the following conditions:
    
    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.
    
    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.
    '''
    
    def __init__(self, locator, is_local_time):
        super().__init__(locator)

        # Determine proper time label (local time or UTC)
        if is_local_time:
            time_type = 'Local'
        else:
            time_type = 'UTC'

        # Re-format datetimes
        self.formats[1] = '%B'
        self.zero_formats[2:4] = ['%B', '%B %d']
        self.offset_formats = [
            f'{time_type} time',
            f'{time_type} time in %Y',
            f'{time_type} time in %B %Y',
            f'{time_type} time on %B %d, %Y',
            f'{time_type} time on %B %d, %Y',
            f'{time_type} time on %B %d, %Y at %H:%M',
        ]

    def set_axis(self, axis):
        self.axis = axis

        # If this is an x-axis (usually is!) then center the offset text
        if self.axis.axis_name == 'x':
            offset = self.axis.get_offset_text()
            offset.set_horizontalalignment('center')
            offset.set_x(0.5)
