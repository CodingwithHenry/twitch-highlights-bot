import google.generativeai as ai
from google import genai
from dotenv import load_dotenv
import os
import json
import random


def generateTitleAndThumbnail():

    load_dotenv()
    # Configure the API key
    ai.configure(api_key=os.getenv("googleAPI_KEY"))

    # Create the model
    
    with open("./files/youtube/video.srt", "r", encoding="utf-8") as f:
        transcription = f.read()

    # Initialize model
    model = ai.GenerativeModel('gemini-2.5-pro')

    # Prompt for a single title
    prompt = f"""
    You are a YouTube content assistant. Generate **one short, catchy, and clickbait-y title**
    (accurate to the video, not misleading) based on the following video transcription. 
    Keep it under 6 words.

    Transcription:
    {transcription}
    """

    # Generate content
    response = model.generate_content(prompt)

    # Extract the title
    title = response.text.strip()+" - League of Legends Highlight's"
    

    client = genai.Client(api_key=os.getenv("googleAPI_KEY"))
    with open("champion_description.json", "r", encoding="utf-8") as f:
        champions = json.load(f)

    # Pick a random number of champions (between 2 and 4)
    num_champions = random.randint(2, 4)

    # Randomly select that many champion descriptions
    selected_champions = random.sample(list(champions.values()), num_champions)
    result = client.models.generate_images(
        model="models/imagen-4.0-generate-001",
        
        prompt=f'''You are an AI art generator specialized in creating cinematic, fantasy-themed illustrations. 
    Always produce images in a hyper-detailed, watercolor fantasy style with semi-realistic proportions. 
    Focus on dynamic compositions suitable for YouTube thumbnails. 
    Lighting should be dramatic and cinematic, with glowing magical effects where appropriate. 
    Characters should resemble League of Legends champions! 
    Ensure clarity, readability, and visually striking poses, emphasizing action and energy. 
    -Make sure to also consider the title of the video: "{title} - League of Legends Highlight's"
    - ALWAYS!! include the TITLE as text overlay in the image in a way it fit's to the rest of the image
    -“Create a bold, ornate serif fantasy font in a high-fantasy style, with engraved gold letters, dramatic cinematic lighting, subtle shadows, and glowing magical accents, epic heroic typography, reminiscent of League of Legends logo, thumbnail composition”
    - include the following champions:
    {'\n- '.join(selected_champions)}
make the characters stick to their lore and personalities

display them in a epic fight setting against a elemental dragon(erath,fire,air,poison,electric), or just horders of minions/bad guys in summoners rift, alternatively let them fight against each other with their minion armies behind them
-the battleground can be a field, summoners rift, a forest, a castle, near a river, in the ice or any other iconic location from the League of Legends universe.
''',

        config=dict(
            number_of_images=1,
            output_mime_type="image/jpeg",
            person_generation="ALLOW_ADULT",
            aspect_ratio="16:9",
            image_size="1K",
        ),
    )

    if not result.generated_images:
        print("No images generated.")
        return

    if len(result.generated_images) != 1:
        print("Number of images generated does not match the requested number.")

    for n, generated_image in enumerate(result.generated_images):
        generated_image.image.save(f"./files/youtube/thumbnail{n}.png")
    
    return title
