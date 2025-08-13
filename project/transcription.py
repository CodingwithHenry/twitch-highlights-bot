import whisper
import subprocess
from pathlib import Path

# Load Whisper model (choose small/medium for speed/accuracy)
model = whisper.load_model("medium")

# Go through all mp4 clips in current folder
for clip in Path(".").glob("*.mp4"):
    print(f"Processing {clip}...")

    # Step 1: Transcribe
    result = model.transcribe(str(clip), language="English")
    
    # Step 2: Save as SRT
    srt_file = clip.with_suffix(".srt")
    with open(srt_file, "w", encoding="utf-8") as f:
        for i, seg in enumerate(result["segments"]):
            start = seg["start"]
            end = seg["end"]
            text = seg["text"].strip()
            f.write(f"{i+1}\n")
            f.write(f"{start//3600:02.0f}:{(start%3600)//60:02.0f}:{start%60:06.3f} --> {end//3600:02.0f}:{(end%3600)//60:02.0f}:{end%60:06.3f}\n")
            f.write(f"{text}\n\n")

    # Step 3: Burn into video with style
    output_file = clip.with_name(f"{clip.stem}_subtitled.mp4")
    subprocess.run([
        "ffmpeg",
        "-i", str(clip),
        "-vf", f"subtitles={srt_file}:force_style='FontName=Arial,FontSize=28,PrimaryColour=&H00FFFF&,OutlineColour=&H000000&,BorderStyle=1,Outline=2,Shadow=1'",
        "-c:a", "copy",
        str(output_file)
    ])

print("✅ All clips processed with subtitles burned in!")
