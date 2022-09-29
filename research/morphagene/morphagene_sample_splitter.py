from pydub import AudioSegment
from pydub.utils import make_chunks

song = AudioSegment.from_wav("file.wav")

chunk_length_ms = 1000  # pydub calculates in millisec
chunks = make_chunks(song, chunk_length_ms)  # Make chunks of one sec

# Export all of the individual chunks as wav files

for i, chunk in enumerate(chunks):
    chunk_name = "file.wav".format(i)
    chunk.export(
        chunk_name, format="wav", parameters=["-f", "pcm_f32le", "-ar", "48000"]
    )
