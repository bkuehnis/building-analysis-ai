from pydantic import BaseModel
from openai import OpenAI
from dotenv import load_dotenv
import os
from typing import List, Optional
import base64


load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


base64_image = encode_image('data/werk/57403/09_Schnitte.jpeg')
# Define your messages with the image
messages = [
    {
        "role": "user",
        "content": [
            {"type": "text", "text": "Classify this image using computer vision skill."},
            {
                "type": "image_url",
                "image_url": {
                #    "url": "https://boneclones.com/images/store-product/product-1530-main-main-big-1531762823.jpg",
                "url": f"data:image/jpeg;base64,{base64_image}",
                }
                
            },
        ]
    }
]



class FirstDetectionData(BaseModel):
    description: str
    Lithotype: List[str]
    Pathology: List[str]
    relative_path: Optional[str] = None


# Use messages
response = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=messages,
    max_tokens=1000,
    response_format=FirstDetectionData  # Use the Pydantic model as the response format
)

# Access the structured response
structured_response = response.choices[0].message.parsed
print(structured_response)