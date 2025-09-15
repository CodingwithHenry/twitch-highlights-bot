import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image, ImageDraw, ImageFont
from project.config import font_clip_name, font_broadcaster, render_settings
from project.utils import safe_filename
from project.youtube import upload_short
from project.clipSelector import rankClips
import glob
import cv2
from collections import deque
import tempfile
import numpy as np
from pydub import AudioSegment
import random
from project.utils import UPLOADS
from datetime import datetime, timedelta ,timezone
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
        subprocess.run(cmd, check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT)
        return output_file

    def lol_to_vertical(self, input_video, output_video, smooth_frames=75, min_contour_area=1000, max_shift=5):
        """
        Converts a 16:9 League of Legends video to 9:16 vertical,
        tracking main action robustly with weighted centroid, max pan speed, and smoothing.

        Args:
            input_video (str): Path to input 16:9 video.
            output_video (str): Path to save final 9:16 video.
            smooth_frames (int): Number of past frames to average for smoothing.
            min_contour_area (int): Minimum contour area to consider as main action.
            max_shift (int): Maximum horizontal shift per frame in pixels.

        Returns:
            str: Path to the final vertical video.
        """
        cap = cv2.VideoCapture(input_video)
        width  = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps    = cap.get(cv2.CAP_PROP_FPS)

        target_w = int(height * 9 / 16)

        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        temp_file = os.path.join(tempfile.gettempdir(), "lol_crop.mp4")
        out = cv2.VideoWriter(temp_file, fourcc, fps, (target_w, height))

        fgbg = cv2.createBackgroundSubtractorMOG2(history=200, varThreshold=50, detectShadows=False)

        current_center_x = width // 2
        center_history = deque([current_center_x]*smooth_frames, maxlen=smooth_frames)

        while True:
            ret, frame = cap.read()
            if not ret: break

            fgmask = fgbg.apply(frame)
            contours, _ = cv2.findContours(fgmask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            # Filter contours by area
            valid_contours = [c for c in contours if cv2.contourArea(c) >= min_contour_area]

            # Optional: ignore contours too far from current center (reduce distraction)
            valid_contours = [
                c for c in valid_contours
                if abs((cv2.boundingRect(c)[0] + cv2.boundingRect(c)[2]//2) - current_center_x) < width * 0.4
            ]

            if valid_contours:
                # Weighted centroid of all valid contours
                xs, areas = [], []
                for c in valid_contours:
                    x, y, w, h = cv2.boundingRect(c)
                    xs.append(x + w//2)
                    areas.append(cv2.contourArea(c))
                target_center_x = int(np.average(xs, weights=areas))
            else:
                target_center_x = current_center_x  # no relevant movement

            # Smooth with moving average
            center_history.append(target_center_x)
            target_center_x = int(np.mean(center_history))

            # Limit maximum horizontal shift
            shift = np.clip(target_center_x - current_center_x, -max_shift, max_shift)
            current_center_x += shift

            # Define crop boundaries
            left = max(0, current_center_x - target_w // 2)
            right = left + target_w
            if right > width:
                right = width
                left = width - target_w

            cropped = frame[:, left:right]

            # Ensure exact size and 3 channels
            if cropped.shape[1] != target_w:
                cropped = cv2.resize(cropped, (target_w, height))
            if len(cropped.shape) == 2:
                cropped = cv2.cvtColor(cropped, cv2.COLOR_GRAY2BGR)
            elif cropped.shape[2] != 3:
                cropped = cv2.cvtColor(cropped, cv2.COLOR_BGRA2BGR)

            try:
                out.write(cropped)
            except cv2.error as e:
                print("⚠️ Skipped frame due to OpenCV error:", e)
                continue

        cap.release()
        out.release()

        # Merge original audio
        subprocess.run([
            "ffmpeg", "-y", "-i", temp_file, "-i", input_video,
            "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-c:a", "aac",
            output_video
        ], check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT)

        return output_video

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

    def add_background_music(self, video_file, output_file, music_volume_reduction=-20):
        """
        Adds background music to a video with reduced volume.
        
        Args:
            video_file (str): Path to input video.
            music_file (str): Path to background music file (mp3, wav, etc.).
            output_file (str): Path for saving the final video.
            music_volume_reduction (int): dB reduction applied to music.
            
        Returns:
            str: Path to final video with mixed audio.
        """
        music_folder = "./fonts/"

        # Get a list of all MP3 files in the folder
        music_files = [f for f in os.listdir(music_folder) if f.endswith(".mp3")]

        # Randomly select one
        music_file = os.path.join(music_folder, random.choice(music_files))
        
        # --- Step 1: Extract original audio from video ---
        temp_audio_file = os.path.join(tempfile.gettempdir(), "video_audio.wav")
        subprocess.run([
            "ffmpeg", "-y", "-i", video_file, "-vn",
            "-acodec", "pcm_s16le", "-ar", "44100", "-ac", "2",
            temp_audio_file
        ], check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT)

        # --- Step 2: Load audio files ---
        video_audio = AudioSegment.from_wav(temp_audio_file)
        music = AudioSegment.from_file(music_file)

        # Extend/trim music to match video length
        if len(music) < len(video_audio):
            music = music * (len(video_audio) // len(music) + 1)
        music = music[:len(video_audio)]

        # Lower music volume
        music = music + music_volume_reduction

        # --- Step 3: Mix music with video audio ---
        final_audio = video_audio.overlay(music)

        # --- Step 4: Export combined audio ---
        combined_audio_file = os.path.join(tempfile.gettempdir(), "combined_audio.wav")
        final_audio.export(combined_audio_file, format="wav")

        # --- Step 5: Merge combined audio back with video ---
        subprocess.run([
            "ffmpeg", "-y", "-i", video_file, "-i", combined_audio_file,
            "-c:v", "copy", "-map", "0:v:0", "-map", "1:a:0",
            output_file
        ], check=True)

        return output_file
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
        subprocess.run(cmd, check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT)

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
        try:
            subprocess.run(cmd, check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print(f"Error fixing clip {input_file}: {e}")
        return output_file

    def process_clip(self, clip):
        """Processes a single clip and returns its output path."""
        overlay_path = self.create_overlay(clip)
        output_path = f"temp_{safe_filename(clip.title)}.mp4"
        try:
            self.overlay_video(clip.path, overlay_path, output_path)
        except Exception as e:
            return clip.path  # fallback to original if overlay fails
            print(f"Error processing clip {clip.title}: {e}")
        return output_path

    def add_cta_animation(self, input_video, output_video, start_time=15, cta_mp4="./fonts/cta_subscribe1.mp4", scale_factor=0.45):
        """
        Overlays a CTA .webm animation onto a video using FFmpeg.

        Args:
            input_video (str): Path to input video.
            cta_webm (str): Path to the CTA .webm animation (must have transparency).
            output_video (str): Path to save the video with CTA.
            start_time (int/float): Seconds when the CTA should appear.
        """
        # FFmpeg command to overlay
        cmd = [
        "ffmpeg", "-y",
        "-i", input_video,
        "-itsoffset", str(start_time), "-i", cta_mp4,
        "-filter_complex",
        f"[1:v]scale=iw*{scale_factor}:ih*{scale_factor},colorkey=0x00FF00:0.3:0.1[cta];"
        f"[0:v][cta]overlay=(main_w-overlay_w)/2:(main_h-overlay_h)/2",
        "-c:a", "copy",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        output_video
    ]

        subprocess.run(cmd, check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT)
        return output_video
    def create_video_compilation(self, clips, amount, gameTitle):
        """Processes clips in parallel, then concatenates them."""
        start_time_utc = datetime.now(timezone.utc)
        # Shift to UTC+2
        start_time_utc2 = start_time_utc + timedelta(hours=2)
        num_clips = 4
        interval_minutes = 15
        timestamps = []
        for i in range(num_clips):
            clip_time = start_time_utc2 + timedelta(minutes=i*interval_minutes)
            iso_time = clip_time.isoformat(timespec='seconds')
            timestamps.append(iso_time)
        
        
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
        TOPNCLIPS=4
        #Top n clips based on ranking logic are getting uploaded as short's
        topClips = rankClips(processed_clips, min_len=20, max_len=60, top_n=TOPNCLIPS)
        #Create timestamps for upload timing
        start_time_utc = datetime.now(timezone.utc)
        # Shift to UTC+2
        start_time_utc2 = start_time_utc + timedelta(hours=2)
        num_clips = TOPNCLIPS
        interval_minutes = 15
        timestamps = []
        for i in range(num_clips):
            clip_time = start_time_utc2 + timedelta(minutes=i*interval_minutes)
            iso_time = clip_time.isoformat(timespec='seconds')
            timestamps.append(iso_time)
            
        print( "Anzahl Top Clips",len(topClips))
        for (clip, path),scheduleTime in zip(topClips,timestamps):

            short_file = path.replace(".mp4", "_short.mp4")
            vertical_short = short_file.replace(".mp4", "_vertical.mp4")
            vertical_lol_short = short_file.replace(".mp4", "_vertical_lol.mp4")

            # Step 1: Add background music
            self.add_background_music(path, short_file)


            #Still testing what format has better "stay to watch" ratio

            # Step 2: Convert to letterboxed vertical format
            self.convert_to_vertical(short_file, vertical_short)

            # Step 3: Apply action crop on ORIGINAL 16:9 video
            self.lol_to_vertical(short_file, vertical_lol_short)
            
            
            vertical_short_cta = vertical_short.replace(".mp4", "_cta.mp4")
            vertical_lol_short_cta = vertical_lol_short.replace(".mp4", "_cta.mp4")
            
            self.add_cta_animation(vertical_short, vertical_short_cta, start_time=clip.duration/2)
            self.add_cta_animation(vertical_lol_short, vertical_lol_short_cta, start_time=clip.duration/2)
            print(f"Uploading short for clip: {clip.title} by {clip.broadcaster_name}")
            description = (
            f"Daily League of Legends highlights! 🎮🔥\n"
            f"Featuring: {clip.broadcaster_name}\n"
            f"Clip: \"{clip.title}\"\n\n"
            f"👉 Subscribe for your daily League dose!\n"
            f"#LeagueOfLegends #Shorts #DailyLeague"
    )       
            title = f"{clip.title} by {clip.broadcaster_name}"
            if len(title) > 95:  # leave room for hashtags
                title = title[:]
            title += " #LeagueofLegends #highlight #twitch #Shorts #lec"
            try:
               if UPLOADS:
                    upload_short(
                    vertical_lol_short_cta,
                    game=gameTitle,
                    title=title,
                    tags="league of Legends, GamingShort,LeagueGameplay,ff20,arcane,riotgames ",
                    description=description,
                    video_file=vertical_lol_short_cta,
                    publishtime=scheduleTime
                    )
               else:
                   print("Uploads are disabled on Windows for testing purposes.")

            except Exception as e:
                print("Error during upload:", e)

        
        # Concatenate without re-encoding
        os.makedirs('files/youtube', exist_ok=True)
        final_output = "files/youtube/video.mp4"
        cmd_concat = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", concat_list,
            "-c", "copy", final_output
        ]
        subprocess.run(cmd_concat, check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.STDOUT)
        # Cleanup folder
        for file in glob.glob("*.mp4"):
            try:
                os.remove(file)
            except Exception as e:
                print(f"Error removing file {file}: {e}")

        return final_output
