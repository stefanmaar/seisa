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

    def __init__(self, stream, audio_stream, audio_sps = 44100):
        ''' Initialization of the instance.

        '''
        # The seismic data which should be visualized.
        self.stream = stream

        # The related audio stream.
        self.audio_stream = audio_stream

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
        self.spectrogram(tr = tr,
                         starttime = tr.stats.starttime,
                         endtime = tr.stats.endtime,
                         spec_win_length = spec_win_length,
                         spec_win_overlap = spec_win_overlap,
                         db_lim = db_lim,
                         freq_min = freq_min,
                         freq_max = freq_max,
                         log = log_freq_scale,
                         utc_offset = utc_offset,
                         resolution = resolution,
                         units = units)
        self.resolution = resolution

        # Get the size of the axes.
        ax = self.fig.axes[1]
        bbox = ax.get_window_extent().transformed(self.fig.dpi_scale_trans.inverted())
        width = bbox.width
        self.ax_width = width * self.fig.dpi
        
        
    def make_frame(self, t):
        ''' Create a frame for a moviepy video.
        '''
        # Check the animation flag.
        # If no animation is requested return the cached image.
        if not self.animate and self.cache is not None:
            self.framecounter += 1
            return self.cache
        
        k = self.framecounter
        frame_times = self.frame_times
        tr = self.stream[0]

        # Handle eventual n_frames rounding problems.
        if k >= len(frame_times):
            k = len(frame_times) - 1

        # Return the cached image if the playhead didn't move far enough.
        # This speeds up rendering.
        playhead_step = k * (self.ax_width / self.n_frames) - self.last_playhead_pos
        thr = 20
        if self.cache is not None and playhead_step <= thr:
            self.framecounter += 1
            return self.cache
        else:
            self.last_playhead_pos += playhead_step

        if self.animate:
            self.spec_line.set_xdata(frame_times[k].matplotlib_date)
            self.wf_line.set_xdata(frame_times[k].matplotlib_date)
            self.time_box.txt.set_text(frame_times[k].strftime('%H:%M:%S'))
            tr_progress = tr.copy().trim(endtime = frame_times[k])
            self.wf_progress.set_xdata(tr_progress.times('matplotlib'))
            self.wf_progress.set_ydata(tr_progress.data)
            self.last_playhead_pos += playhead_step
        else:
            self.spec_line.set_visible(False)
            self.wf_line.set_visible(False)
            self.time_box.set_visible(False)
            self.wf_progress.set_visible(False)
            self.wf_full.set(color = 'k')
        
        self.framecounter += 1
        ret = mp_bind.mplfig_to_npimage(self.fig)
        self.cache = ret
        
        return ret

    
    def render_moviepy(self, fps = 20, animate = True,
                       duration = None):
        ''' Render the animation using moviepy.
        '''
        self.animate = animate
        tr = self.stream[0]
        tr_audio = self.audio_stream[0]
        
        # Compute the speed up factor.
        seismo_dur = (tr.stats.endtime + tr.stats.delta) - tr.stats.starttime
        audio_dur = (tr_audio.stats.endtime + tr_audio.stats.delta) - tr_audio.stats.starttime
        speed_up_factor = seismo_dur / audio_dur
        
        # Compute the times used for animation.
        n_frames = int(round(audio_dur * fps))
        delta_frame = speed_up_factor / fps
        frame_times = [tr.stats.starttime + x * delta_frame for x in range(n_frames)]
        frame_times = np.array(frame_times)
        self.frame_times = frame_times
        self.n_frames = n_frames

        #print(n_frames)
        #print(len(frame_times))
        #print(frame_times)
        #print(delta_frame)

        # Setup the rendering.
        delta = 1 / fps
        if duration is None:
            duration = n_frames * delta
        #print(audio_dur)
        #print(duration)
        handler = functools.partial(self.make_frame)
        animation = mpe.VideoClip(handler,
                                  duration = duration)
        # Reset the framecounter after the initialization of the clip.
        # The initialization calls the handler function, thus increasing
        # the framecounter.
        self.framecounter = 0

        return animation


    def render_mpl_new(self, out_filepath, fps = 10):
        ''' Render the animation to a video.

        This function is based on code taken from the sonify program licensed 
        under the MIT License (https://github.com/liamtoney/sonify).

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
        tr = self.stream[0]
        tr_audio = self.audio_stream[0]
        sps = tr.stats.sampling_rate

        fig = self.fig
        
        # Compute the speed up factor.
        seismo_dur = (tr.stats.endtime + tr.stats.delta) - tr.stats.starttime
        audio_dur = (tr_audio.stats.endtime + tr_audio.stats.delta) - tr_audio.stats.starttime
        speed_up_factor = seismo_dur / audio_dur

        # Compute the times used for animation.
        n_frames = int(audio_dur * fps)
        delta_frame = speed_up_factor / fps
        frame_times = [tr.stats.starttime + x * delta_frame for x in range(n_frames)]
        frame_times = np.array(frame_times)
           
        # Create animation
        
        # interval = (tr.stats.delta * 1000) / speed_up_factor
        interval = (1 / fps) * 1000
        print(speed_up_factor)

        def _init():
            return (self.spec_line, self.wf_line, self.time_box, self.wf_progress)
        
        def _march_forward(frame):
            ''' The animation update function.
            '''
            k = frame
            spec_line = self.spec_line
            wf_line = self.wf_line
            time_box = self.time_box
            wf_progress = self.wf_progress
            spec_line.set_xdata(frame_times[k].matplotlib_date)
            wf_line.set_xdata(frame_times[k].matplotlib_date)
            time_box.txt.set_text(frame_times[k].strftime('%H:%M:%S'))
            tr_progress = tr.copy().trim(endtime = frame_times[k])
            wf_progress.set_xdata(tr_progress.times('matplotlib'))
            wf_progress.set_ydata(tr_progress.data)
            print('Finished frame ' + str(k))

            return (spec_line, wf_line, time_box, wf_progress)
           
        animation = mpl.animation.FuncAnimation(fig,
                                                func = _march_forward,
                                                init_func = _init,
                                                frames = frame_times.size,
                                                interval = interval,
                                                blit = True)

        print('Saving animation. This may take a while...')
        output_res = self.resolution_dict[self.resolution]
        dpi = output_res[0] / self.fig_width
        animation.save(out_filepath,
                       dpi = dpi,
                       progress_callback = lambda i, n: print(
                        '{:d}/{:d} -- {:.1f}%'.format(i + 1, n, ((i + 1) / n) * 100), end='\r'))

        
        
    def render_mpl(self, out_filepath, spec_win_length = 5, spec_win_overlap = 50, db_lim = 'smart', freq_min = None,
               freq_max = None, log_freq_scale = False, utc_offset = None,
               resolution = '1080p', fps = 1, units = None):
        ''' Render the animation to a video.

        This function is based on code taken from the sonify program licensed 
        under the MIT License (https://github.com/liamtoney/sonify).

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
        tr = self.stream[0]
        tr_audio = self.audio_stream[0]
        sps = tr.stats.sampling_rate
        fig, *fargs = self.spectrogram(tr = tr,
                                       starttime = tr.stats.starttime,
                                       endtime = tr.stats.endtime,
                                       spec_win_length = spec_win_length,
                                       spec_win_overlap = spec_win_overlap,
                                       db_lim = db_lim,
                                       freq_min = freq_min,
                                       freq_max = freq_max,
                                       log = log_freq_scale,
                                       utc_offset = utc_offset,
                                       resolution = resolution,
                                       units = units)
        
        # Compute the speed up factor.
        seismo_dur = (tr.stats.endtime + tr.stats.delta) - tr.stats.starttime
        audio_dur = (tr_audio.stats.endtime + tr_audio.stats.delta) - tr_audio.stats.starttime
        speed_up_factor = seismo_dur / audio_dur

        # Compute the times used for animation.
        n_frames = int(audio_dur * fps)
        delta_frame = speed_up_factor / fps
        frame_times = [tr.stats.starttime + x * delta_frame for x in range(n_frames)]
        frame_times = np.array(frame_times)
        
        
        #frame_trace = tr.copy()
        #print(frame_trace)
        #frame_sps = fps / speed_up_factor
        #frame_trace.resample(frame_sps,
        #                     window = 'hann')
        #frame_times = frame_trace.times('UTCDateTime')[:-1]
        #frame_times = frame_trace.times('UTCDateTime')
        print(frame_times)
        print(len(frame_times))
        
        # Create animation
        
        # interval = (tr.stats.delta * 1000) / speed_up_factor
        interval = (1 / fps) * 1000
        print(speed_up_factor)
        
        def _march_forward(frame, spec_line, wf_line, time_box, wf_progress):
            ''' The animation update function.
            '''
            k = frame
            spec_line.set_xdata(frame_times[k].matplotlib_date)
            wf_line.set_xdata(frame_times[k].matplotlib_date)
            time_box.txt.set_text(frame_times[k].strftime('%H:%M:%S'))
            tr_progress = tr.copy().trim(endtime = frame_times[k])
            wf_progress.set_xdata(tr_progress.times('matplotlib'))
            wf_progress.set_ydata(tr_progress.data)
           
        animation = mpl.animation.FuncAnimation(fig,
                                                func = _march_forward,
                                                frames = frame_times.size,
                                                fargs = fargs,
                                                interval = interval)

        print('Saving animation. This may take a while...')
        output_res = self.resolution_dict[resolution]
        dpi = output_res[0] / self.fig_width
        animation.save(out_filepath,
                       dpi = dpi,
                       progress_callback = lambda i, n: print(
                        '{:d}/{:d} -- {:.1f}%'.format(i + 1, n, ((i + 1) / n) * 100), end='\r'))

        
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
    

    def spectrogram(self, tr, starttime, endtime,
                    spec_win_length = 5, spec_win_overlap = 50, db_lim = 'smart',
                    freq_min = None, freq_max = None, log = False,
                    is_local_time = False, resolution = '4K',
                    utc_offset = None, units = None):
        '''
        This function is based on code taken from the sonify program licensed 
        under the MIT License (https://github.com/liamtoney/sonify).

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
        if freq_min is None:
            freq_min = 0
        if freq_max is None:
            freq_max = tr.stats.sampling_rate / 2
        freq_lim = (freq_min, freq_max)

        units = units.lower().strip()
        if units == 'm/s':
            ylab = 'vel.  [m s$^{-1}$]'
            ref_velocity = 1
            if ref_velocity == 1:
                clab = (f'PSD (dB rel. {ref_velocity:g} [m s$^{{-1}}$]$^2$ Hz$^{{-1}}$)')
            else:
                clab = (f'PSD (dB rel. [{ref_velocity:g} m s$^{{-1}}$]$^2$ Hz$^{{-1}}$)')
            ref_val = ref_velocity
        elif units == 'pa':
            ylab = 'Pressure [Pa]'
            clab = 'PSD [dB]'
            ref_val = 1
        elif units is None:
            ylab = 'unknown'
            clab = 'PSD [dB]'
            ref_val = 1
        else:
            ylab = units
            clab = 'PSD [dB]'
            ref_val = 1

        sps = tr.stats.sampling_rate
        nperseg = int(spec_win_length * sps)
        noverlap = np.floor(nperseg * spec_win_overlap / 100)
        # Pad fft with zeroes
        nfft = np.power(2, int(np.ceil(np.log2(nperseg))) + 1)

        f, t, sxx = sp.signal.spectrogram(tr.data, sps,
                                          window = 'hann',
                                          nperseg = nperseg,
                                          noverlap = noverlap,
                                          nfft = nfft)

        # [dB rel. (ref_val <ref_val_unit>)^2 Hz^-1]
        sxx_db = 10 * np.log10(sxx / (ref_val**2))

        t_mpl = tr.stats.starttime.matplotlib_date + (t / mdates.SEC_PER_DAY)

        # Ensure a 16:9 aspect ratio
        fig = plt.Figure(figsize = (self.fig_width,
                                    (9 / 16) * self.fig_width))

        # width_ratios effectively controls the colorbar width
        gs = mpl.gridspec.GridSpec(2, 2,
                                   figure = fig,
                                   height_ratios = [2, 1],
                                   width_ratios = [40, 1])
        
        spec_ax = fig.add_subplot(gs[0, 0])
        wf_ax = fig.add_subplot(gs[1, 0], sharex=spec_ax)
        cax = fig.add_subplot(gs[0, 1])

        wf_lw = 0.5
        wf_full = wf_ax.plot(tr.times('matplotlib'), tr.data, '#b0b0b0',
                             linewidth = wf_lw)
        wf_progress = wf_ax.plot(np.nan, np.nan, 'black', linewidth = wf_lw)[0]
        wf_ax.set_ylabel(ylab)
        wf_ax.grid(linestyle = ':')
        max_value = np.abs(tr.copy().trim(starttime, endtime).data).max()
        wf_ax.set_ylim(-max_value, max_value)

        im = spec_ax.pcolormesh(t_mpl, f, sxx_db,
                                cmap = 'viridis',
                                shading = 'nearest',
                                rasterized = True)

        spec_ax.set_ylabel('Frequency [Hz]')
        spec_ax.grid(linestyle=':')
        if log:
            spec_ax.set_yscale('log')
            if freq_lim[0] <= 0:
                freq_lim = (0.0001, freq_lim[1])
        print(freq_lim)
        spec_ax.set_ylim(freq_lim)

        # Tick locating and formatting
        locator = mdates.AutoDateLocator()
        wf_ax.xaxis.set_major_locator(locator)
        wf_ax.xaxis.set_major_formatter(UTCDateFormatter(locator,
                                                         is_local_time))
        fig.autofmt_xdate()

        # "Crop" x-axis!
        wf_ax.set_xlim(starttime.matplotlib_date, endtime.matplotlib_date)

        # Initialize animated stuff
        line_kwargs = dict(x = starttime.matplotlib_date,
                           color = 'forestgreen',
                           linewidth = 1)
        spec_line = spec_ax.axvline(**line_kwargs)
        wf_line = wf_ax.axvline(ymin = 0.01,
                                clip_on = False,
                                zorder = 10,
                                **line_kwargs)
        time_box = mpl.offsetbox.AnchoredText(s = starttime.strftime('%H:%M:%S'),
                                              pad = 0.2,
                                              loc = 'lower right',
                                              bbox_to_anchor = [1, 1],
                                              bbox_transform = wf_ax.transAxes,
                                              borderpad = 0,
                                              prop = dict(color = 'black',
                                                          family = 'monospace'))
        offset_px = -0.0025 * self.resolution_dict[resolution][1]
        # [pixels] Vertically center text
        time_box.txt._text.set_y(offset_px)
        # This should place it on the very top; see below
        time_box.zorder = 12
        time_box.patch.set_linewidth(mpl.rcParams['axes.linewidth'])
        wf_ax.add_artist(time_box)

        # Adjustments to ensure time marker line is zordered properly
        # 9 is below marker; 11 is above marker
        spec_ax.spines['bottom'].set_zorder(9)
        wf_ax.spines['top'].set_zorder(9)
        for side in 'bottom', 'left', 'right':
            wf_ax.spines[side].set_zorder(11)

        # Pick smart limits rounded to nearest 10
        if db_lim == 'smart':
            db_min = np.percentile(sxx_db, 20)
            db_max = sxx_db.max()
            db_lim = (np.ceil(db_min / 10) * 10, np.floor(db_max / 10) * 10)

        # Clip image to db_lim if provided (doesn't clip if db_lim=None)
        im.set_clim(db_lim)

        # Automatically determine whether to show triangle extensions on colorbar
        # (kind of adopted from xarray)
        if db_lim:
            min_extend = sxx_db.min() < db_lim[0]
            max_extend = sxx_db.max() > db_lim[1]
        else:
            min_extend = False
            max_extend = False

        if min_extend and max_extend:
            extend = 'both'
        elif min_extend:
            extend = 'min'
        elif max_extend:
            extend = 'max'
        else:
            extend = 'neither'

        # Colorbar extension triangle height as proportion of colorbar length
        cb_extend_frac = 0.04
        fig.colorbar(im, cax,
                     extend = extend,
                     extendfrac = cb_extend_frac,
                     label = clab)

        spec_ax.set_title(tr.id)

        fig.tight_layout()
        fig.subplots_adjust(hspace=0, wspace=0.05)

        # Finnicky formatting to get extension triangles (if they exist) to extend
        # above and below the vertical extent of the spectrogram axes
        pos = cax.get_position()
        triangle_height = cb_extend_frac * pos.height
        ymin = pos.ymin
        height = pos.height
        if min_extend and max_extend:
            ymin -= triangle_height
            height += 2 * triangle_height
        elif min_extend and not max_extend:
            ymin -= triangle_height
            height += triangle_height
        elif max_extend and not min_extend:
            height += triangle_height
        else:
            pass
        
        cax.set_position([pos.xmin, ymin, pos.width, height])

        # Move offset text around and format it more nicely, see
        # https://github.com/matplotlib/matplotlib/blob/710fce3df95e22701bd68bf6af2c8adbc9d67a79/lib/matplotlib/ticker.py#L677
        magnitude = wf_ax.yaxis.get_major_formatter().orderOfMagnitude
        if magnitude:  # I.e., if offset text is present
            wf_ax.yaxis.get_offset_text().set_visible(False)  # Remove original text
            sf = mpl.ticker.ScalarFormatter(useMathText=True)
            sf.orderOfMagnitude = magnitude  # Formatter needs to know this!
            sf.locs = [47]  # Can't be an empty list
            wf_ax.text(0.002,
                       0.95,
                       sf.get_offset(),  # Let the ScalarFormatter do the formatting work
                       transform=wf_ax.transAxes,
                       ha='left',
                       va='top')

        self.fig = fig
        self.spec_line = spec_line
        self.wf_line = wf_line
        self.time_box = time_box
        self.wf_full = wf_full[0]
        self.wf_progress = wf_progress


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
