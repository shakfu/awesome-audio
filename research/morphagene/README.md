# Make Noise Morphagene Support

## Information

- [Lines Forum: Morphagene Patch & System Ideas](https://llllllll.co/t/morphagene-patch-system-ideas/8197)

- [signal flux / Morphagene Guide](https://signalflux.org/morphagene)

- [reddit / Tips for prepping morphagene reels](https://www.reddit.com/r/modular/comments/s1he2j/tips_for_prepping_morphagene_reels/)

- [reddit / Using audacity and python to make morphagene reels](https://www.reddit.com/r/modular/comments/a5mvzk/using_audacity_and_python_to_make_morphagene_reels/) -- also has a [visual guide](https://imgur.com/a/XocUesN)

- [search topic on github](https://github.com/search?q=morphagene)


## Webapps

- [morphweb](https://knandersen.github.io/morphaweb/) -- Based on the python2 [morphagen_ableton.py](https://gist.github.com/knandersen/a1da6859e3ef84f3c0ce1979536d85c8) script. Allows you to use Ableton projects and exports as reels for the Make Noise Morphagene eurorack module. 

- [morphagene web-editor](https://www.lorenzostanco.com/lab/morphagene/) -- provides A web editor for the SD card options and a reel assembler to convert one or more WAV files to a single morphagene reel.


## Splitter Scripts

Generally have not included python2 scripts if a python3 script is available.

- [Morphagene-sample-splitter](https://github.com/podusmonens/Morphagene-sample-splitter) -- Morphagene sample splitter is a Python script which takes a wav file as an input, splits it into chunks of a designated length and then outputs them as individual 32bit/48khz/stereo wav files. It was made to create reels for the Make Noise Morphagene Eurorack module. Once exported, the files can be combined into a reel using this [Reel Assembler web app]( https://www.lorenzostanco.com/lab/morphagene/)

- [mgreel](https://github.com/olt/mgreel) -- mgreel.js is a JavaScript/Node script to convert one or more Wave files to a single Make Noise Morphagene reel (Wave file 32bit/48khz/stereo). All files are concatenated and splice markers are set at the end of each input files. Mono Wave files are converted to stereo. For example: `mgreel --out out.wav mywav/*.wav`
	
- [mg-convert](https://gist.github.com/sym3tri/636befdaae22f0c4b1f7f4b448dad113) -- This simple shell script (depends on `sox`) converts all audio files in a provided directory into Morphagene compatible files (48KHz, floating-point, 32-bit, stereo WAV). It automatically names the files in the proper format too.

- [morphagene_ableton3.py](https://gist.github.com/ferrihydrite/3830e66b8b90a998adeddd5f693296cf) -- [A [ferrihydrite](https://gist.github.com/ferrihydrite) fork of knandersen's `morphagene_ableton.py` script. Allows you to use Ableton projects and exports as reels for the Make Noise Morphagene eurorack module. Here’s the basic process:

	1. In arrangement view, put locators 4 where you want your splices.
	2. Export as a 48 kHz 32 bit WAV
	3. In a terminal, run the following:
	`python morphagene_ableton3.py -w wav_exported_from_ableton.wav -l my_ableton_session.als -o mg1.wav`

	Change the output filename to be whatever entry in the reel list you want.

- [morphagene_audacity3](https://gist.github.com/ferrihydrite/562ee8926e66e0c1af753f28f69b34ab) -- A [ferrihydrite](https://gist.github.com/ferrihydrite) script used to convert Audacity labels in `.txt` form on `.wav` files into single 32-bit float `.wav` with CUE markers within the file, directly compatible with the Make Noise Morphagene.

- [morphagene_onset3.py](https://gist.github.com/ferrihydrite/4eecdb4cfc2d08c582064bd7b58c79f5) -- A [ferrihydrite](https://gist.github.com/ferrihydrite) script which uses an onset detection algorithm with backtracking to generate splice locations. Use these splice locations with a converted WAV (to 32-bit float / 48000Hz) to make Morphagene reels.

- [morphagene_batch.py](https://gist.github.com/ferrihydrite/a8fc9b2b2d4cefc362a419d21451d193) -- A [ferrihydrite](https://gist.github.com/ferrihydrite) script which allows for the compilation of multiple wav samples in one folder, either mono or stereo of any bit depth (rate ideally 48000Hz to avoid change in pitch), to be written as one 32-bit float 48000Hz wav, directly compatible with the Make Noise Morphagene.

- [morphagene_logic.py](https://gist.github.com/ferrihydrite/290f4874711f99456e542c71b893df75) -- A [ferrihydrite](https://gist.github.com/ferrihydrite) script which reads 24 bit WAV files with markers from Logic Pro, extract markers, and resave file as a 32 bit float file with cue markers, directly compatible with the Make Noise Morphagene.


