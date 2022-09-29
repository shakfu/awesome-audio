# -*- coding: utf-8 -*-
"""
Read 24 bit WAV files with markers from Logic Pro, extract markers, and resave
    file as a 32 bit float file with cue markers, directly compatible with
    the Make Noise Morphagene.
Does not require input file to be 48000Hz, only that the .WAV file 
    has cue markers correct to its sampling rate, and that the input 
    .WAV is stereo.
    
Usage:
   morphagene_logic.py -w <inputwavfile> -o <outputfile>'
    
See the Morphagene manual for naming conventions of output files:    
    http://www.makenoisemusic.com/content/manuals/morphagene-manual.pdf
    
# see http://stackoverflow.com/questions/15576798/create-32bit-float-wav-file-in-python
# see... http://blog.theroyweb.com/extracting-wav-file-header-information-using-a-python-script
# marker code from Joseph Basquin [https://gist.github.com/josephernest/3f22c5ed5dabf1815f16efa8fa53d476]
"""

import sys, getopt
import struct
import numpy as np
from scipy import interpolate


def float32_wav_file(file_name, sample_array, sample_rate, markers=None, verbose=False):
    (M, N) = sample_array.shape
    # print "len sample_array=(%d,%d)" % (M,N)
    byte_count = M * N * 4  # (len(sample_array)) * 4  # 32-bit floats
    wav_file = ""
    # write the header
    wav_file += struct.pack(
        "<ccccIccccccccIHHIIHH",
        "R",
        "I",
        "F",
        "F",
        byte_count + 0x2C - 8,  # header size
        "W",
        "A",
        "V",
        "E",
        "f",
        "m",
        "t",
        " ",
        0x10,  # size of 'fmt ' header
        3,  # format 3 = floating-point PCM
        M,  # channels
        sample_rate,  # samples / second
        sample_rate * 4,  # bytes / second
        4,  # block alignment
        32,
    )  # bits / sample
    wav_file += struct.pack("<ccccI", "d", "a", "t", "a", byte_count)
    if verbose:
        print("packing data...")
    # flatten data in an alternating fashion
    # see: http://soundfile.sapp.org/doc/WaveFormat/
    reordered_wav = [sample_array[k, j] for j in range(N) for k in range(M)]
    wav_file += struct.pack("<%df" % len(reordered_wav), *reordered_wav)
    if verbose:
        print("saving audio...")
    fid = open(file_name, "wb")
    for value in wav_file:
        fid.write(value)
    if markers:  # != None and != []
        if verbose:
            print("saving cue markers...")
        if isinstance(
            markers[0], dict
        ):  # then we have [{'position': 100, 'label': 'marker1'}, ...]
            labels = [m["label"] for m in markers]
            markers = [m["position"] for m in markers]
        else:
            labels = ["" for m in markers]
        fid.write(b"cue ")
        size = 4 + len(markers) * 24
        fid.write(struct.pack("<ii", size, len(markers)))
        for i, c in enumerate(markers):
            s = struct.pack(
                "<iiiiii", i + 1, c, 1635017060, 0, 0, c
            )  # 1635017060 is struct.unpack('<i',b'data')
            fid.write(s)
        lbls = ""
        for i, lbl in enumerate(labels):
            lbls += b"labl"
            label = lbl + ("\x00" if len(lbl) % 2 == 1 else "\x00\x00")
            size = len(lbl) + 1 + 4  # because \x00
            lbls += struct.pack("<ii", size, i + 1)
            lbls += label
        fid.write(b"LIST")
        size = len(lbls) + 4
        fid.write(struct.pack("<i", size))
        fid.write(
            b"adtl"
        )  # https://web.archive.org/web/20141226210234/http://www.sonicspot.com/guide/wavefiles.html#list
        fid.write(lbls)
    fid.close()


def wav_file_read(filename, verbose=False):
    # read file and close
    fi = open(filename, "rb")
    data = fi.read()
    fi.close()
    # take raw data and read subsections for important format data
    A, B, C, D = struct.unpack("4c", data[0:4])  # 'RIFF'
    ChunkSize = struct.unpack("<l", data[4:8])[
        0
    ]  # 4+(8+SubChunk1Size)+8+SubChunk2Size)
    A, B, C, D = struct.unpack("4c", data[8:12])  # 'WAVE'
    A, B, C, D = struct.unpack("4c", data[12:16])  # 'fmt '
    Subchunk1Size = struct.unpack("<l", data[16:20])[0]  # LITTLE ENDIAN, long, 16
    AudioFormat = struct.unpack("<h", data[20:22])[0]  # LITTLE ENDIAN, short, 1
    NumChannels = struct.unpack("<h", data[22:24])[
        0
    ]  # LITTLE ENDIAN, short, Mono = 1, Stereo = 2
    SampleRate = struct.unpack("<l", data[24:28])[
        0
    ]  # LITTLE ENDIAN, long,  sample rate in samples per second
    ByteRate = struct.unpack("<l", data[28:32])[
        0
    ]  # self.SampleRate * self.NumChannels * self.BitsPerSample/8)) # (ByteRate) LITTLE ENDIAN, long
    BlockAlign = struct.unpack("<h", data[32:34])[
        0
    ]  # self.NumChannels * self.BitsPerSample/8))  # (BlockAlign) LITTLE ENDIAN, short
    BitsPerSample = struct.unpack("<h", data[34:36])[0]  # LITTLE ENDIAN, short
    A, B, C, D = struct.unpack("4c", data[36:40])  # BIG ENDIAN, char*4
    SubChunk2Size = struct.unpack("<l", data[40:44])[0]  # LITTLE ENDIAN, long
    waveData = data[44:]
    (M, N) = (len(waveData), len(waveData[0]))
    if verbose:
        print(
            "ChunkSize     =%d\nSubchunk1Size =%d\nAudioFormat   =%d\nNumChannels   =%d\nSampleRate    =%d\nByteRate      =%d\nBlockAlign    =%d\nBitsPerSample =%d\nA:%c,  B:%c,  C:%c,  D:%c\nSubChunk2Size =%d"
            % (
                ChunkSize,
                Subchunk1Size,
                AudioFormat,
                NumChannels,
                SampleRate,
                ByteRate,
                BlockAlign,
                BitsPerSample,
                A,
                B,
                C,
                D,
                SubChunk2Size,
            )
        )
    # convert audio data to float based on bitdepth
    if BitsPerSample == 8:
        if verbose:
            print("Unpacking 8 bits on len(waveData)=%d" % len(waveData))
        d = np.fromstring(waveData, np.uint8)
        floatdata = d.astype(np.float64) / np.float(127)
    elif BitsPerSample == 16:
        if verbose:
            print("Unpacking 16 bits on len(waveData)=%d" % len(waveData))
        d = np.zeros(SubChunk2Size / 2, dtype=np.int16)
        j = 0
        for k in range(0, SubChunk2Size, 2):
            d[j] = struct.unpack("<h", waveData[k : k + 2])[0]
            j = j + 1
        floatdata = d.astype(np.float64) / np.float(32767)
    elif BitsPerSample == 24:
        if verbose:
            print("Unpacking 24 bits on len(waveData)=%d" % len(waveData))
        d = np.zeros(SubChunk2Size / 3, dtype=np.int32)
        j = 0
        for k in range(0, SubChunk2Size, 3):
            d[j] = struct.unpack(
                "<l", struct.pack("c", waveData[k]) + waveData[k : k + 3]
            )[0]
            j = j + 1
        floatdata = d.astype(np.float64) / np.float(2147483647)
    else:  # anything else will be considered 32 bits
        if verbose:
            print("Unpacking 32 bits on len(waveData)=%d" % len(waveData))
        d = np.fromstring(waveData, np.int32)
        floatdata = d.astype(np.float64) / np.float(2147483647)
    v = floatdata[0::NumChannels]
    for i in range(1, NumChannels):
        v = np.vstack((v, floatdata[i::NumChannels]))
    # return (np.vstack((floatdata[0::2],floatdata[1::2])), SampleRate, NumChannels, BitsPerSample)
    return (v, SampleRate, NumChannels, BitsPerSample)


def readmarkers(file, mmap=False):
    """
    Extract cue markers (in frames) from a WAV file.
    From:
        https://stackoverflow.com/questions/20011239/read-markers-of-wav-file
    """

    def _read_riff_chunk(fid):
        str1 = fid.read(4)
        if str1 != b"RIFF":
            raise ValueError("Not a WAV file.")
        fsize = struct.unpack("<I", fid.read(4))[0] + 8
        str2 = fid.read(4)
        if str2 != b"WAVE":
            raise ValueError("Not a WAV file.")
        return fsize

    def _skip_unknown_chunk(fid):
        data = fid.read(4)
        size = struct.unpack("<i", data)[0]
        if bool(
            size & 1
        ):  # if odd number of bytes, move 1 byte further (data chunk is word-aligned)
            size += 1
        fid.seek(size, 1)

    if hasattr(file, "read"):
        fid = file
    else:
        fid = open(file, "rb")
    fsize = _read_riff_chunk(fid)
    cue = []
    while fid.tell() < fsize:
        chunk_id = fid.read(4)
        if chunk_id == b"cue ":
            size, numcue = struct.unpack("<ii", fid.read(8))
            for c in range(numcue):
                (
                    id,
                    position,
                    datachunkid,
                    chunkstart,
                    blockstart,
                    sampleoffset,
                ) = struct.unpack("<iiiiii", fid.read(24))
                cue.append(position)
        else:
            _skip_unknown_chunk(fid)
    fid.close()
    return cue


def change_samplerate_interp(old_audio, old_rate, new_rate):
    """
    Change sample rate to new sample rate by simple interpolation.
    If old_rate > new_rate, there may be aliasing / data loss.
    Input should be in column format, as the interpolation will be completed
        on each channel this way.
    Modified from:
    https://stackoverflow.com/questions/33682490/how-to-read-a-wav-file-using-scipy-at-a-different-sampling-rate
    """
    if old_rate != new_rate:
        # duration of audio
        duration = old_audio.shape[0] / old_rate

        # length of old and new audio
        time_old = np.linspace(0, duration, old_audio.shape[0])
        time_new = np.linspace(
            0, duration, int(old_audio.shape[0] * new_rate / old_rate)
        )

        # fit old_audio into new_audio length by interpolation
        interpolator = interpolate.interp1d(time_old, old_audio.T)
        new_audio = interpolator(time_new).T
        return new_audio
    else:
        print("Conversion not needed, old and new rates match")
        return old_audio  # conversion not needed


def main(argv):
    inputwavefile = ""
    outputfile = ""
    try:
        opts, args = getopt.getopt(argv, "hw:o:", ["wavfile=", "outputfile="])
    except getopt.GetoptError:
        print(
            "Error in usage, correct format:\n"
            + "morphagene_logic.py -w <inputwavfile> -o <outputfile>"
        )
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            print("morphagene_logic.py -w <inputwavfile> -o <outputfile>")
            sys.exit(2)
        elif opt in ("-w", "--wavfile"):
            inputwavefile = arg
        elif opt in ("-o", "--outputfile"):
            outputfile = arg
    print("Input wave file: %s" % inputwavefile)
    print("Output Morphagene reel: %s" % outputfile)

    ###########################################################################
    """
    Write single 24bit WAV file, edited in Logic with cues, to Morphagene 32bit
        WAV file at 48000hz sample rate.
    """
    ###########################################################################
    morph_srate = 48000  # required samplerate for Morphagene
    morpth_bd = 32
    # read labels from stereo Audacity label file, ignore text, and use one channel
    logic_cues = readmarkers(inputwavefile)
    if logic_cues:  # if not empty
        # skip first tempo element, as well as markers at 0, as there is
        #   no audio before that point
        logic_cues = np.array(logic_cues)[1:]
        logic_cues = logic_cues[np.nonzero(logic_cues)]
    else:
        raise ValueError("WAV file does not contain cue points")
    # read pertinent info from audio file, exit if input wave file is broken
    try:
        (array, sample_rate, num_channels, bits_per_sample) = wav_file_read(
            inputwavefile
        )
    except:
        raise ValueError(
            "Input .wav file %s is poorly formatted, exiting" % inputwavefile
        )
    # check if input wav has a different rate than desired Morphagene rate,
    #   and correct by interpolation
    if sample_rate != morph_srate:
        print(
            "Correcting input sample rate %iHz to Morphagene rate %iHz"
            % (sample_rate, morph_srate)
        )
        # perform interpolation on each channel, then transpose back
        array = change_samplerate_interp(
            array.T, float(sample_rate), float(morph_srate)
        ).T
        # convert labels in seconds to labels in frames, adjusting for change
        #   in rate
        sc = float(morph_srate) / float(sample_rate)
        frame_labs = (logic_cues * sc).astype(np.int)
    else:
        frame_labs = logic_cues.astype(np.int)
    frame_dict = [
        {"position": l, "label": "marker%i" % (i + 1)} for i, l in enumerate(frame_labs)
    ]
    print(
        "Correcting input %i-bit bitdepth to Morphagene %i-bit float bitdepth"
        % (bits_per_sample, morpth_bd)
    )
    # write wav file with additional cue markers from labels
    float32_wav_file(outputfile, array, morph_srate, markers=frame_dict, verbose=True)
    print("Saved Morphagene reel with %i splices: %s" % (len(frame_labs), outputfile))


if __name__ == "__main__":
    main(sys.argv[1:])
