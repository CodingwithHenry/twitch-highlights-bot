import os
from moviepy.editor import VideoFileClip, ImageClip, CompositeVideoClip, concatenate_videoclips
from PIL import Image, ImageDraw, ImageFont
from project.config import font_clip_name, font_broadcaster, render_settings
from project.utils import safe_filename
class VideoEditor():
    def __init__(self):
        self.clips = []

    def create_intro(self):
        pass

    def create_overlay(self, clip_content):
        title = clip_content.title
        broadcaster_name = clip_content.broadcaster_name
        if len(title) > 40: title = title[:40] + '...'

        # Create a 1980x1080 transparent image
        overlay = Image.new('RGBA', (1920, 1080), color = (255,255,255,0))
 
        fnt_clip_name = ImageFont.truetype(font_clip_name, 62)
        fnt_streamer_name = ImageFont.truetype(font_broadcaster, 50)
        d = ImageDraw.Draw(overlay)

        d.text((100, 930), title, font=fnt_clip_name, stroke_width=3, stroke_fill=(0, 0, 0), fill=(255, 255, 255))
        d.text((100, 1000), broadcaster_name, font=fnt_streamer_name, stroke_width=3, stroke_fill=(0, 0, 0), fill=(255, 255, 255))
        
        if not os.path.exists('files/overlays'): os.makedirs('files/overlays')
        overlay.save(f'files/overlays/{safe_filename(title)}.png')
    
    def create_video(self, clip_content):
        clip = VideoFileClip(clip_content.path, target_resolution=(1080, 1980))
        img_clip = ImageClip(f'files/overlays/{safe_filename(clip_content.title)}.png').set_duration(5)
        video = CompositeVideoClip([clip, img_clip])
        return video

    def create_video_compilation(self, clips, amount):
        for clip in clips[:amount]:
            self.create_overlay(clip)
            self.clips.append(self.create_video(clip))
            
        video = concatenate_videoclips(self.clips, method='compose')
        if not os.path.exists('files/youtube'): os.makedirs('files/youtube')
        video.write_videofile(f'files/youtube/video.mp4', fps = render_settings['fps'], codec = render_settings['codec'], threads = render_settings['threads'], preset = render_settings['preset'], bitrate = render_settings['bitrate'])
        return f'files/youtube/video.mp4'