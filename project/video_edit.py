import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont
from project.config import font_clip_name, font_broadcaster, render_settings
from project.utils import safe_filename


class VideoEditor:
    def __init__(self, max_workers=4):
        self.max_workers = max_workers
        self.clips = []

    def create_overlay(self, clip_content):
        """Creates a transparent PNG overlay with title & broadcaster name."""
        title = clip_content.title
        broadcaster_name = clip_content.broadcaster_name
        if len(title) > 40:
            title = title[:40] + '...'

        overlay = Image.new('RGBA', (1920, 1080), color=(255, 255, 255, 0))
        fnt_clip_name = ImageFont.truetype(font_clip_name, 62)
        fnt_streamer_name = ImageFont.truetype(font_broadcaster, 50)

        d = ImageDraw.Draw(overlay)
        d.text((100, 930), title, font=fnt_clip_name,
               stroke_width=3, stroke_fill=(0, 0, 0), fill=(255, 255, 255))
        d.text((100, 1000), broadcaster_name, font=fnt_streamer_name,
               stroke_width=3, stroke_fill=(0, 0, 0), fill=(255, 255, 255))

        os.makedirs('files/overlays', exist_ok=True)
        overlay_path = f'files/overlays/{safe_filename(title)}.png'
        overlay.save(overlay_path)
        return overlay_path

    def overlay_video(self, input_video, overlay_image, output_video):
        """Overlays a PNG onto a video using ffmpeg."""
        cmd = [
            "ffmpeg", "-y",
            "-i", input_video,
            "-i", overlay_image,
            "-filter_complex", "overlay=0:0",
            "-c:v", "libx264",         # re-encode video
            "-preset", render_settings['preset'],
            "-b:v", render_settings['bitrate'],
            "-c:a", "copy",            # keep audio untouched
            output_video
        ]
        subprocess.run(cmd, check=True)


    def process_clip(self, clip):
        """Processes a single clip and returns its output path."""
        overlay_path = self.create_overlay(clip)
        output_path = f"temp_{safe_filename(clip.title)}.mp4"
        self.overlay_video(clip.path, overlay_path, output_path)
        return output_path

    def create_video_compilation(self, clips, amount):
        """Processes clips in parallel, then concatenates them."""
        self.clips = clips[:amount]
        temp_files = []

        # Parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.process_clip, clip): clip for clip in self.clips}
            for future in as_completed(futures):
                temp_files.append(future.result())

        # Create concat list
        concat_list = "concat_list.txt"
        with open(concat_list, "w") as f:
            for file in temp_files:
                f.write(f"file '{os.path.abspath(file)}'\n")

        # Concatenate without re-encoding
        os.makedirs('files/youtube', exist_ok=True)
        final_output = "files/youtube/video.mp4"
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c", "copy", final_output
        ]
        subprocess.run(cmd_concat, check=True)

        # Cleanup
        for file in temp_files:
            try:
                os.remove(file)
            except Exception as e:
                print(f"Error removing file {file}: {e}")
        os.remove(concat_list)

        return final_output
