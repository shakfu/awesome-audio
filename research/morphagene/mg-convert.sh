#!/bin/bash
set -e

INPUTDIR=$(pwd)
if [ "$#" -eq 1 ]; then
    INPUTDIR=$1
    if [ ! -d $INPUTDIR ];then
        echo "The directory you provided does not exist."
        exit 1
    fi
fi
echo -e "Processing files in: $INPUTDIR\n"

mkdir -p $INPUTDIR/converted

names="123456789abcdefghijklmnopqrstuvw"
function suffix() {
    echo ${names:$1:1}
}

COUNTER=0
for filename in $INPUTDIR/*.wav; do
    if [ "$COUNTER" -eq 32 ]; then
        echo "WARNING: Too many files. Morphagene's max is 32. Exiting without processing the rest."
        exit 0
    fi

    echo -e "Converting: $filename...\n"
    outfile=mg$(suffix $COUNTER).wav
    # this is where the magic happens
    
    # somehow couldn't get ffmpeg to work :(
    # ffmpeg  -i "$filename" -ar 48000 -c:a pcm_f32le -ac 2 -y "$INPUTDIR/converted/$outfile"
    
    # VLC worked, but can't normalize during conversion :(
    # eval /Applications/VLC.app/Contents/MacOS/VLC -I dummy -vvv \""$filename"\" --audio-filter normvol --norm-max-level 5 --sout \''#transcode{vcodec=none,acodec=fl33,ab=128,channels=2,samplerate=48000,scodec=none,soverlay}:standard{mux=wav,access=file{no-overwrite},dst='"$INPUTDIR/converted/$outfile"'}'\' vlc://quit
    
    # sox FTW!
    sox --norm "$filename" -c 2 -r 48k -e float -b 32 "$INPUTDIR/converted/$outfile"
    echo -e "\nDone!\n\n"
    let COUNTER=COUNTER+1
done

echo "All converted files are located in: $INPUTDIR/converted"

