import whisper
import subprocess
from pathlib import Path

def transcription():
    model = whisper.load_model("medium")

    # Path to your single video
    clip = Path("./files/youtube/video.mp4")
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
            f.write(f"{start//3600:02.0f}:{(start%3600)//60:02.0f}:{start%60:06.3f} --> "
                    f"{end//3600:02.0f}:{(end%3600)//60:02.0f}:{end%60:06.3f}\n")
            f.write(f"{text}\n\n")

    # Step 3: Burn subtitles into the video
    output_file = clip.with_name("video_subtitled.mp4")
    subprocess.run([
        "ffmpeg",
        "-i", str(clip).replace("\\", "/"),
        "-vf", f"subtitles={str(srt_file).replace('\\', '/')}:" +
               "force_style='FontName=Verdana,Fontsize=28,PrimaryColour=&H00FFFF00," +
               "OutlineColour=&H00000000,BorderStyle=1,Outline=3,Shadow=2,MarginV=150'",
        "-c:a", "copy",
        str(output_file).replace("\\", "/")
    ])

    print("✅ Subtitles burned into video!")
    return output_file
