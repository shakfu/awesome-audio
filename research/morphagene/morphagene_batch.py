# -*- coding: utf-8 -*-
"""
Created on Sun Nov 25 21:15:52 2018

@author: ferri

updated version of mor.py with wavio functions

Reads 8, 16 bit wav or aiff files, mono or stereo.
    
Allows for the compilation of multiple wav samples in one folder,
    either mono or stereo of any bit depth (rate ideally 48000Hz to avoid
    change in pitch), to be written as one 32-bit float 48000Hz wav, directly
    compatible with the Make Noise Morphagene.
     
See the Morphagene manual for naming conventions of output files:    
    http://www.makenoisemusic.com/content/manuals/morphagene-manual.pdf
"""
# see http://stackoverflow.com/questions/15576798/create-32bit-float-wav-file-in-python
# see... http://blog.theroyweb.com/extracting-wav-file-header-information-using-a-python-script
# marker code from Joseph Basquin [https://gist.github.com/josephernest/3f22c5ed5dabf1815f16efa8fa53d476]

from __future__ import division, print_function, absolute_import
import os, getopt, sys
import struct
import warnings
import collections
from scipy import interpolate
import numpy as np
import aifc

class WavFileWarning(UserWarning):
    pass
    
_ieee = False
    
def read(file, readmarkers=False, readmarkerlabels=False, 
         readmarkerslist=False, readloops=False, readpitch=False, 
         normalized=False, forcestereo=False):
    """
    Return the sample rate (in samples/sec) and data from a WAV file
    Parameters
    ----------
    file : file
        Input wav file.
    Returns
    -------
    rate : int
        Sample rate of wav file
    data : np array
        Data read from wav file
    Notes
    -----
    * The file can be an open file or a filename.
    * The returned sample rate is a Python integer
    * The data is returned as a np array with a
      data-type determined from the file.
    """
    ################
    ## READ SUBFUNCTIONS
    ## assumes file pointer is immediately
    ##  after the 'fmt ' id
    def _read_fmt_chunk(fid):
        res = struct.unpack('<ihHIIHH',fid.read(20))
        size, comp, noc, rate, sbytes, ba, bits = res
        if (comp != 1 or size > 16):
            if (comp == 3):
              global _ieee
              _ieee = True
              #warnings.warn("IEEE format not supported", WavFileWarning)        
            else: 
              warnings.warn("Unfamiliar format bytes", WavFileWarning)
            if (size>16):
                fid.read(size-16)
        return size, comp, noc, rate, sbytes, ba, bits
    # assumes file pointer is immediately
    #   after the 'data' id
    def _read_data_chunk(fid, noc, bits, normalized=False):
        size = struct.unpack('<i',fid.read(4))[0]
        if bits == 8 or bits == 24:
            dtype = 'u1'
            bytes = 1
        else:
            bytes = bits//8
            dtype = '<i%d' % bytes
        if bits == 32 and _ieee:
           dtype = 'float32'
        data = np.fromfile(fid, dtype=dtype, count=size//bytes)
        if bits == 24:
            # handle 24 bit file by using samplewidth=3, no native 24-bit type
            a = np.empty((len(data) // 3, 4), dtype='u1')
            a[:, :3] = data.reshape((-1, 3))
            a[:, 3:] = (a[:, 3 - 1:3] >> 7) * 255
            data = a.view('<i4').reshape(a.shape[:-1])
        if noc > 1: 
            # handle stereo
            data = data.reshape(-1,noc)
        if bool(size & 1):     
          # if odd number of bytes, move 1 byte further (data chunk is word-aligned)
          fid.seek(1,1)    
        if normalized:
            if bits == 16 or bits == 24 or bits == 32: 
                normfactor = 2 ** (bits-1)
                data = np.float32(data) * 1.0 / normfactor
            elif bits == 8:
                if isinstance(data[0], (int, np.uint8)):
                    # handle uint8 data by shifting to center at 0
                    normfactor = 2 ** (bits-1)
                    data = (np.float32(data) * 1.0 / normfactor) -\
                                    ((normfactor)/(normfactor-1))
        return data
    def _skip_unknown_chunk(fid):
        data = fid.read(4)
        size = struct.unpack('<i', data)[0]
        if bool(size & 1):     
          # if odd number of bytes, move 1 byte further (data chunk is word-aligned)
          size += 1 
        fid.seek(size, 1)
    def _read_riff_chunk(fid):
        str1 = fid.read(4)
        if str1 != b'RIFF':
            raise ValueError("Not a WAV file.")
        fsize = struct.unpack('<I', fid.read(4))[0] + 8
        str2 = fid.read(4)
        if (str2 != b'WAVE'):
            raise ValueError("Not a WAV file.")
        return fsize
    ##################
    if hasattr(file,'read'):
        fid = file
    else:
        fid = open(file, 'rb')
    fsize = _read_riff_chunk(fid)
    noc = 1
    bits = 8
    #_cue = []
    #_cuelabels = []
    _markersdict = collections.defaultdict(lambda: {'position': -1, 'label': ''})
    loops = []
    pitch = 0.0
    while (fid.tell() < fsize):
        # read the next chunk
        chunk_id = fid.read(4)
        if chunk_id == b'fmt ':
            size, comp, noc, rate, sbytes, ba, bits = _read_fmt_chunk(fid)
        elif chunk_id == b'data':
            data = _read_data_chunk(fid, noc, bits, normalized)
        elif chunk_id == b'cue ':
            str1 = fid.read(8)
            size, numcue = struct.unpack('<ii',str1)
            for c in range(numcue):
                str1 = fid.read(24)
                id, position, datachunkid, chunkstart, blockstart, \
                    sampleoffset = struct.unpack('<iiiiii', str1)
                #_cue.append(position)
                # needed to match labels and markers
                _markersdict[id]['position'] = position                    
        elif chunk_id == b'LIST':
            str1 = fid.read(8)
            size, type = struct.unpack('<ii', str1)
        elif chunk_id in [b'ICRD', b'IENG', b'ISFT', b'ISTJ']:   
             # see http://www.pjb.com.au/midi/sfspec21.html#i5
            _skip_unknown_chunk(fid)
        elif chunk_id == b'labl':
            str1 = fid.read(8)
            size, id = struct.unpack('<ii',str1)
            # the size should be even, see WAV specfication, e.g. 16=>16, 23=>24
            size = size + (size % 2)      
            # remove the trailing null characters                        
            label = fid.read(size-4).rstrip('\x00')               
            #_cuelabels.append(label)
            # needed to match labels and markers
            _markersdict[id]['label'] = label                          
        elif chunk_id == b'smpl':
            str1 = fid.read(40)
            size, manuf, prod, sampleperiod, midiunitynote,\
            midipitchfraction, smptefmt, smpteoffs, numsampleloops, \
                samplerdata = struct.unpack('<iiiiiIiiii', str1)
            cents = midipitchfraction * 1./(2**32-1)
            pitch = 440. * 2 ** ((midiunitynote + cents - 69.)/12)
            for i in range(numsampleloops):
                str1 = fid.read(24)
                cuepointid, type, start, end, \
                fraction, playcount = struct.unpack('<iiiiii', str1) 
                loops.append([start, end])
        else:
            warnings.warn("Chunk " + chunk_id + " skipped", WavFileWarning)
            _skip_unknown_chunk(fid)
    fid.close()
    if data.ndim == 1 and forcestereo:
        data = np.column_stack((data, data))
    _markerslist = sorted([_markersdict[l] for l in _markersdict], key=lambda k: k['position'])  # sort by position
    _cue = [m['position'] for m in _markerslist]
    _cuelabels = [m['label'] for m in _markerslist]
    return (rate, data, bits, ) \
        + ((_cue,) if readmarkers else ()) \
        + ((_cuelabels,) if readmarkerlabels else ()) \
        + ((_markerslist,) if readmarkerslist else ()) \
        + ((loops,) if readloops else ()) \
        + ((pitch,) if readpitch else ())
        
def read_aiff_norm(filename,read_params=False):
    '''
    Read and normalize aif/aiff/aifc files
    '''
    s = aifc.open(filename, 'r')
    strsig = s.readframes(s.getnframes())
    try: # int16 short
        array = np.frombuffer(strsig, np.short)/np.float(32767)
    except: # int8
        array = np.frombuffer(strsig, np.int8)/np.float(127)
    if read_params:
        nchan,samp_wid,frame_rate,n_frames,comp_type,comp_name = s.getparams()
        return array,nchan,samp_wid,frame_rate,\
                n_frames,comp_type,comp_name
    else:
        return array
        
def get_list_of_files(dir_name,file_type):
    '''
    See:
    https://thispointer.com/python-how-to-get-list-of-files-in-directory-and-sub-directories/
    Create a list of files within a directory and it's subdirectories
    Modified to filter so that full filname has to match fileType, and to 
        ignore case of extension
    '''
    list_of_files = os.listdir(dir_name)
    all_files = list()
    # Iterate over all the entries
    for entry in list_of_files:
        # Create full path
        full_path = os.path.join(dir_name, entry)
        # If entry is a directory then get the list of files in this directory 
        if os.path.isdir(full_path):
            all_files = all_files + get_list_of_files(full_path,file_type)
        else:
            if file_type.upper() in full_path or file_type.lower() in full_path:
                all_files.append(full_path)
    return all_files

def change_samplerate_interp(old_audio,old_rate,new_rate):
    '''
    Change sample rate to new sample rate by simple interpolation.
    If old_rate > new_rate, there may be aliasing / data loss,
    Input should be in column format, as the interpolation will be completed
        on each channel this way.
    Modified from:
    https://stackoverflow.com/questions/33682490/
        how-to-read-a-wav-file-using-scipy-at-a-different-sampling-rate
    '''    
    if old_rate != new_rate:
        # duration of audio
        duration = old_audio.shape[0] / old_rate
        # length of old and new audio
        time_old  = np.linspace(0, duration, old_audio.shape[0])
        time_new  = np.linspace(0, duration, 
                                int(old_audio.shape[0] * new_rate / old_rate))
        # fit old_audio into new_audio length by interpolation
        interpolator = interpolate.interp1d(time_old, old_audio.T)
        new_audio = interpolator(time_new).T
        return new_audio
    else:
        return old_audio # conversion not needed

def float32_wav_file(file_name, sample_array, sample_rate, 
                     markers=None, verbose=False):
    '''
    Write 32-bit WAV at specified sample rate
    '''
    (M,N)=sample_array.shape
    #print "len sample_array=(%d,%d)" % (M,N)
    byte_count = M * N * 4 # (len(sample_array)) * 4  # 32-bit floats
    wav_file = ""
    # write the header
    wav_file += struct.pack('<ccccIccccccccIHHIIHH',
        'R', 'I', 'F', 'F',
        byte_count + 0x2c - 8,  # header size
        'W', 'A', 'V', 'E', 'f', 'm', 't', ' ',
        0x10,  # size of 'fmt ' header
        3,  # format 3 = floating-point PCM
        M,  # channels
        sample_rate,  # samples / second
        sample_rate * 4,  # bytes / second
        4,  # block alignment
        32)  # bits / sample
    wav_file += struct.pack('<ccccI',
        'd', 'a', 't', 'a', byte_count)
    if verbose:
        print("packing data...")
    # flatten data in an alternating fashion 
    # see: http://soundfile.sapp.org/doc/WaveFormat/
    reordered_wav = [sample_array[k,j] for j in range(N) for k in range(M)]
    wav_file += struct.pack('<%df' % len(reordered_wav), *reordered_wav)
    if verbose:
        print("saving audio...")
    fid=open(file_name,'wb')
    for value in wav_file:
        fid.write(value)
    if markers:    # != None and != []
        if verbose:
            print("saving cue markers...")
        if isinstance(markers[0], dict):       
            # then we have [{'position': 100, 'label': 'marker1'}, ...]
            labels = [m['label'] for m in markers]
            markers = [m['position'] for m in markers]
        else:
            labels = ['' for m in markers]
        fid.write(b'cue ')
        size = 4 + len(markers) * 24
        fid.write(struct.pack('<ii', size, len(markers)))
        for i, c in enumerate(markers):
            # 1635017060 is struct.unpack('<i',b'data')
            s = struct.pack('<iiiiii', i + 1, c, 1635017060, 0, 0, c)           
            fid.write(s)
        lbls = ''
        for i, lbl in enumerate(labels):
            lbls += b'labl'
            label = lbl + ('\x00' if len(lbl) % 2 == 1 else '\x00\x00')
            size = len(lbl) + 1 + 4 # because \x00
            lbls += struct.pack('<ii', size, i + 1)
            lbls += label
        fid.write(b'LIST')
        size = len(lbls) + 4
        fid.write(struct.pack('<i', size))   
        # https://web.archive.org/web/20141226210234/...
        #   http://www.sonicspot.com/guide/wavefiles.html#list                      
        fid.write(b'adtl') 
        fid.write(lbls) 
    fid.close()
    return wav_file

def write_audacity_labels(filename,labels,files):
    '''
    Write an Audacity-compatible label file, with labels AFTER every file,
        and with the last label indicating the final two labels
    '''
    r = open(filename,'w')
    for i,l in enumerate(labels):
        if i == (len(labels)-1):
            end_label = '<-%s~%s->'%(os.path.basename(files[-2]),os.path.basename(files[-1]))
            r.write('%3.6f\t%3.6f\t%s\n'%(l,l,end_label))
        else:
            r.write('%3.6f\t%3.6f\t%s\n'%(l,l,os.path.basename(files[i])))
    r.close()
    
def main(argv):
    directory = ''
    filetype = ''
    speedmultiplier = ''
    attenuation = ''
    outputfile = ''
    try:
        opts, args = getopt.getopt(argv,"hd:f:s:a:o:",["directory=",\
                                                       "filetype=",\
                                                       "speedmultiplier=",\
                                                       "attenuation=",\
                                                       "outputfile="])
    except getopt.GetoptError:
        raise ValueError('Error in usage, correct format:\n'+\
            'morphagene_batch.py -d <directory> -f <filetype> -s <speedmultiplier> -a <attenuation_dB> -o <outputfile>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('morphagene_batch.py -d <directory> -f <filetype> -s <speedmultiplier> -a <attenuation_dB> -o <outputfile>')
            sys.exit(2)
        elif opt in ("-d", "--directory"):
            directory = arg
        elif opt in ("-f", "--filetype"):
            filetype = arg
        elif opt in ("-s", "--speedmultiplier"):
            speedmultiplier = arg
        elif opt in ("-a", "--attenuation"):
            attenuation = arg
        elif opt in ("-o", "--outputfile"):
            outputfile = arg
    print('Input directory: %s'%directory)
    print('Input file type: %s'%filetype)
    print('Speed multiplied by %2.2f for output file'%float(speedmultiplier))
    print('Volume attenuated by %2.2fdB for output file'%float(attenuation))
    print('Output Morphagene reel: %s'%outputfile)
    # morphagene settings
    morph_samplerate = 48000 # required sample rate for Morphagene
    # speed and attenuation
    volscale = 10**(float(attenuation)/10.)
    # read/write options
    write_label_file = True # write labels to a file compatible with Audacity
    ###########################################################################
    '''
    Write drum samples to one stereo Morphagene 32bit WAV file with scaled 
        volume sampled at 48000Hz
    '''
    ###########################################################################
    # load each sample name
    extension = '.'+filetype
    files = get_list_of_files(directory,extension)
    files.sort()
    # volume of each repeated sample, leave as [1] to have one repeat of each
    #   sample at full volume
    scale = [volscale]
    # preallocate
    arrays, labs_comp, lab_tot = [],[], 0.
    # loop over files
    for fi in files:
        # repeat each sample at each volume
        for s in scale:
            # read rate, data, and bitdepth, normalized
            try:
                if 'aif' in extension:
                    array,_,_,rate,_,_,_ = read_aiff_norm(fi,read_params=True)
                else:
                    rate, array, _ = read(fi, normalized=True)
            except:
                raise ValueError('Input audio file %s is poorly formatted, exiting'%os.path.basename(fi))
            # scale volume
            array = array*s
            # convert to Morphagene rate if not already that rate
            # do this to avoid pitch change upon rate mismatch
            if rate != morph_samplerate: 
                print('Correcting input sample rate %iHz'%(rate) + \
                      ' to Morphagene rate %iHz'%(morph_samplerate)+ \
                      ' and multiplying speed by %2.2f'%float(speedmultiplier))
                new_rate = float(morph_samplerate) * (1 / float(speedmultiplier))
                array = change_samplerate_interp(array,float(rate),
                                 new_rate)   
            # warn (not error) if old rate is greater than Morphagene rate
            if rate > morph_samplerate: 
                print('Input sample rate greater than Morphagene, aliasing possible')
            if array.ndim == 1: # mono
                # make mono sample stereo
                stereo = np.tile(array,(2,1))
                # append samples
                arrays.append(stereo)
                # calculate new splice location [in frames] and append to list
                lab_tot += stereo.shape[1]
                labs_comp.append(lab_tot)
            elif array.ndim == 2: #stereo
                # append samples
                arrays.append(array.T) # transpose to orientation of other arrays
                # calculate new splice location [in frames] and append to list
                lab_tot += array.T.shape[1]
                labs_comp.append(lab_tot)
            else:
                raise ValueError('File must be either mono or stereo')
    # concatenate samples into long array
    arrays = np.hstack(arrays)
    # convert splice location to int for correct format and make dict
    # ignore last splice point as there is no audio after it
    frame_labs = np.array(labs_comp)[:-1].astype('int')
    frame_dict = [{'position': l, 'label': 'marker%i'%(i+1)} for i,l in enumerate(frame_labs)]
    # test if resultant file exceeds the splice and
    #   file length limitations of the Morphagene
    if len(frame_dict) > 300 or (arrays.shape[1]/morph_samplerate)/60. > 2.9:
        raise ValueError('Number of splices (%i) and/or audio'%len(frame_dict) + \
            ' length (%2.1f minutes)'%((arrays.shape[1]/morph_samplerate)/60.) + \
            ' exceed Morphagene limits')
    else:
        # write concatenated sample arrays and labels to single morphagene wav file
        # also optionally write text file of Audacity-compatible labels
        float32_wav_file(outputfile,arrays,morph_samplerate,
                         markers=frame_dict,verbose=True)
        print('Saved Morphagene reel with %i splices: %s'%(len(frame_labs),outputfile))
        if write_label_file:
            fn = os.path.splitext(os.path.basename(outputfile))[0]
            write_audacity_labels('%s.txt'%fn,frame_labs/float(morph_samplerate),files)
if __name__ == "__main__":
    main(sys.argv[1:])

