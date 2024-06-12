import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

import time
import pickle as pkl
import re

from dotenv import load_dotenv
load_dotenv()
import os


# Configure the Gemini API
api_key =  os.environ.get("gemini_api_key")
genai.configure(api_key=api_key)


safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}


model = genai.GenerativeModel("gemini-1.5-flash", safety_settings=safety_settings)
person = pkl.load(open("MikoChanHistory/MikoChan.pkl", "rb"))
model = model.start_chat(history=person)

context_messages = []


# Function to get a reply from Gemini API
def get_gemini_reply(message):
    try:
        response = model.send_message("\n".join(context_messages) + "\n.The Message to reply to:" + message, safety_settings=safety_settings)
        return response.text
    except Exception as e:
        return f"Sorry, I couldn't understand that. Error: {str(e)}"
    
# Function to get a reply from Gemini API for image messages
def get_image_gemini_reply(message):
    try:
        response = model.send_message([f"{"\n".join(context_messages)}\n- The Message to reply to is the image.", message], safety_settings=safety_settings)
        response.resolve()
        return response.text
    except Exception as e:
        return f"Sorry, I couldn't understand that. Error: {str(e)}"
