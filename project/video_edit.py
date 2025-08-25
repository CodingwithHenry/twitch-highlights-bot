import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont
from project.config import font_clip_name, font_broadcaster, render_settings
from project.utils import safe_filename
from project.youtube import upload_short
from project.clipSelector import rankClips
import glob
class VideoEditor:
    def __init__(self, max_workers=4):
        self.max_workers = max_workers
        self.clips = []
    def convert_to_vertical(self, input_file, output_file):
        
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2",
            "-c:a", "copy",
            output_file
        ]
        subprocess.run(cmd, check=True)
        return output_file

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

    def fix_clip(self, input_file, output_file):
        """Normalizes timestamps & framerate to avoid DTS errors."""
        cmd = [
            "ffmpeg", "-y",
            "-i", input_file,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-c:a", "aac", "-ar", "48000", "-ac", "2",
            "-fflags", "+genpts", "-r", "30",
            output_file
        ]
        subprocess.run(cmd, check=True)
        return output_file

    def process_clip(self, clip):
        """Processes a single clip and returns its output path."""
        overlay_path = self.create_overlay(clip)
        output_path = f"temp_{safe_filename(clip.title)}.mp4"
        self.overlay_video(clip.path, overlay_path, output_path)
        return output_path

    def create_video_compilation(self, clips, amount, gameTitle):
        """Processes clips in parallel, then concatenates them."""
        self.clips = clips[:amount]
        temp_files = []
        processed_clips = []
        # Parallel processing
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.process_clip, clip): clip for clip in self.clips}
            
            for i, future in enumerate(as_completed(futures)):
                
                processed = future.result()
                clip = futures[future]
                # Normalize timestamps
                fixed = processed.replace(".mp4", "_fixed.mp4")
                self.fix_clip(processed, fixed)
                # store (clip object, path to processed file)
                processed_clips.append((clip, fixed))
                temp_files.append(fixed)

            # Create concat list
            concat_list = "concat_list.txt"
            with open(concat_list, "w") as f:
                for file in temp_files:
                    f.write(f"file '{os.path.abspath(file)}'\n")

        #Top n clips based on ranking logic are getting uploaded as short's
        topClips = rankClips(processed_clips, min_len=17, max_len=45, top_n=2)

        for clip, path in topClips:
            short_file = path.replace(".mp4", "_short.mp4")
            self.convert_to_vertical(path, short_file)
            description = (
            f"Daily League of Legends highlights! 🎮🔥\n"
            f"Featuring: {clip.broadcaster_name}\n"
            f"Clip: \"{clip.title}\"\n\n"
            f"👉 Subscribe for your daily League dose!\n"
            f"#LeagueOfLegends #Shorts #DailyLeague"
    )
            upload_short(
                short_file,
                game=gameTitle,
                title=f'#Shorts {clip.title} by {clip.broadcaster_name} #LeagueofLegends #highlight #twitch',
                tags="#Shorts,league of Legends, gaming, twitch, highlights ",
                description=description,
                video_file=short_file
    )

        # Concatenate without re-encoding
        os.makedirs('files/youtube', exist_ok=True)
        final_output = "files/youtube/video.mp4"
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c", "copy", final_output
        ]
        subprocess.run(cmd_concat, check=True)
        # Cleanup folder
        for file in glob.glob("*.mp4"):
            try:
                os.remove(file)
            except Exception as e:
                print(f"Error removing file {file}: {e}")

        return final_output
