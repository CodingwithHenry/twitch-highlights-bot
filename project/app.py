from project.clips import ClipsExtractor, ClipsDownloader
from project.video_edit import VideoEditor
from project.video_content import VideoContentGenerator, VideoContent
from project.twitch_ids_box_art import games_id
from project.youtube import upload
from project.transcription import transcription
from project.utils import get_description
from project.titleGen import generateTitleAndThumbnail
import os
import glob
class App:
    def __init__(self):
        self.clips_extractor = ClipsExtractor()
        self.clips_downloader = ClipsDownloader()
        self.video_editor = VideoEditor()
        
    def run(self, game, amount, languages = []):
        
        print(f"Creating video compilation with game: {game}, amount: {amount}, languages: {languages}")
        game_id = games_id[game]
        
        # Get clips from Twitch
        self.clips_extractor.get_clips(quantity = amount, game_id = game_id, languages=languages)
        clips = self.clips_extractor.clips_content
            

        # Download clips
        self.clips_downloader.download_top_clips(clips)

        # Create video compilation
        self.video_editor.create_video_compilation(clips, amount, gameTitle=game)

        file =transcription()
        
        #use gemini2.5 and imagin to generate title and thumbnail based of the transcription
        title=generateTitleAndThumbnail()
        # Upload video to Youtube
        self.video_content_generator = VideoContentGenerator(self.clips_extractor)

        description, tags = get_description(game)  # load description from description json
        # Create video content
        video_content = VideoContent(
            title=title,
            description=description,
            tags=tags,
            category_id='20',  # Gaming
            privacy_status='public',
            keywords=None
        )

        

        # Upload video to Youtube
        upload(video_content, file, game)


# delete clips and thumbnails etc.        
        main_folder = "files"


        for subfolder in os.listdir(main_folder):
            subfolder_path = os.path.join(main_folder, subfolder)
            if os.path.isdir(subfolder_path):
                # Find all files in the subfolder
                for file_path in glob.glob(os.path.join(subfolder_path, "*")):
                    if os.path.isfile(file_path):
                        os.remove(file_path)
                        print(f"Deleted: {file_path}")