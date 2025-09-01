import os
from PIL import Image, ImageDraw, ImageFont
from project.config import font_thumbnail
from math import floor, sqrt
from project.twitch_ids_box_art import games_name
from project.utils import prev_week_saturday_dBY, prev_week_sunday_dBY,  safe_filename ,getShortNumber
from pathlib import Path
class VideoContent:

    def __init__(self, title, description, tags, category_id, privacy_status, keywords):
        self.title = title
        self.description = description
        self.tags = tags
        self.category_id = category_id
        self.privacy_status = privacy_status
        self.keywords = keywords
        self.categoryId = 20

class VideoContentGenerator:

    def __init__(self, clips_extractor):
        self.clips_extractor = clips_extractor

    def generate_title(self):
        if self.clips_extractor.by_game:
            return f'Top {len(self.clips_extractor.clips_content)} Most Watched {games_name[self.clips_extractor.clips_content[0].game_id]} Twitch Clips of The Week'
        return f'Top {len(self.clips_extractor.clips_content)} {self.clips_extractor.clips_content[0].broadcaster_id}\'s highlights of the week'

    def generate_description(self):
            description = ('')
            

            return description

    def generate_tags(self):
        tags = set([ ])
        for clip in self.clips_extractor.clips_content:
            tags.add(games_name[clip.game_id])
            tags.add(clip.broadcaster_name)
        return list(tags)

    def generate_thumbnail(self):
        overlay = Image.new('RGBA', (1280, 720), color = (255,255,255,0))
        d = ImageDraw.Draw(overlay)

        # Generate background with thumbnail images
        x = floor(sqrt(len(self.clips_extractor.clips_content)))
        for i in range(x):
            for j in range(x):
                img = Image.open(f'files/thumbnails/{safe_filename(self.clips_extractor.clips_content[i * x + j].title)}.jpg')
                img = img.resize((1280 // x, 720 // x))
                overlay.paste(img, (i * (1280 // x), j * (720 // x)))

        # Generate text
        line1 = f'Top {len(self.clips_extractor.clips_content)}'
        line2 = f'{games_name[self.clips_extractor.clips_content[0].game_id]}'
        line3 = 'Twitch Clips'

        # rename games with long names to fit in the thumbnail
        rename = {
            'Counter-Strike: Global Offensive': 'CSGO',
            'League of Legends': 'LOL',
        }

        if line2 in rename: line2 = rename[line2]

        _, _, w, h = d.textbbox((0, 0), line1, font = ImageFont.truetype(font_thumbnail, 100))
        d.text(((1280 - w)/ 2, (720 - h) / 2 - 120), line1, font=ImageFont.truetype(font_thumbnail, 100), stroke_width=3, stroke_fill=(0, 0, 0), fill=(255, 255, 255))
        _, _, w, h = d.textbbox((0, 0), line2, font = ImageFont.truetype(font_thumbnail, 130))
        d.text(((1280 - w)/ 2, (720 - h) / 2), line2, font = ImageFont.truetype(font_thumbnail, 130), stroke_width=4, stroke_fill=(0, 0, 0), fill=(255, 255, 255))
        _, _, w, h = d.textbbox((0, 0), line3, font = ImageFont.truetype(font_thumbnail, 100))
        d.text(((1280 - w)/ 2, (720 - h) / 2 + 140), line3, font = ImageFont.truetype(font_thumbnail, 100), stroke_width=3, stroke_fill=(0, 0, 0), fill=(255, 255, 255))

        if not os.path.exists('files/youtube'): os.makedirs('files/youtube')
        overlay.save(f'files/youtube/thumbnail.png')

def shortthumbnail( output_path,game):
        """
        Adds text to the top half of a short's thumbnail.
        
        :param base_image_path: Path to the original thumbnail
        :param output_path: Path to save the edited thumbnail
        :param short_number: Number of the short (for text like '#5')
        """
        base_image_path = Path("./fonts/shortnail.jpg")
        output_path = Path(output_path)
        
        short_number=getShortNumber(game)
        # Open image
        img = Image.open(base_image_path).convert("RGBA")
        width, height = img.size

        # Create overlay for text
        overlay = Image.new("RGBA", img.size, (255,255,255,0))
        draw = ImageDraw.Draw(overlay)
        
        # Choose font and size
        try:
            font = ImageFont.truetype("arial.ttf", size=int(height*0.08))
        except:
            font = ImageFont.load_default()

        lines = ["Get", "High on", f"League #{short_number}"]

        # Vertical start position (5% from top)
        y = int(height * 0.05)

        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (width - text_width) // 2  # center horizontally

            # Draw outline
            outline_color = "black"
            for dx in [-2, 2]:
                for dy in [-2, 2]:
                    draw.text((x+dx, y+dy), line, font=font, fill=outline_color)
            # Draw main text
            draw.text((x, y), line, font=font, fill="yellow")

            # Move y down for next line
            y += text_height + int(height * 0.01)  # 1% vertical spacing

        # Combine overlay with original
        combined = Image.alpha_composite(img, overlay)
        combined.convert("RGB").save(output_path)
        print(f"✅ Thumbnail saved to {output_path}")