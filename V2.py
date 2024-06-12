import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
import pickle as pkl
import os
import logging
from PIL import Image


# Configure the Gemini API
api_key =  "AIzaSyDORIRmb1YW2SZcXwvbiCZzTVWUinPw418"
genai.configure(api_key=api_key)

safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
}

model = genai.GenerativeModel("gemini-1.5-flash", safety_settings=safety_settings)
history_file_path = "MikoChanHistory/MikoChan.pkl"

# Ensure the history directory exists
os.makedirs(os.path.dirname(history_file_path), exist_ok=True)

if os.path.exists(history_file_path):
    person = pkl.load(open(history_file_path, "rb"))
else:
    person = [
        {"role": "user", "parts": ["Never mention that you are a bot or AI."]},
        {"role": "model", "parts": ["Got it."]}
    ]
model = model.start_chat(history=person)

context_messages = [message["parts"][0] for message in person]

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

# Telegram bot configuration
telegram_api_key = '7424009300:AAF0DGaRSWXrI3Z4JExNHx5P4pyyq65HGIc'
bot = Bot(token=telegram_api_key)
updater = Updater(token=telegram_api_key, use_context=True)
dispatcher = updater.dispatcher

# Command handler to start the bot
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hi! I'm Miko Chan, your anime guide and friend. How can I assist you today?")

# Message handler to process text messages
def handle_message(update: Update, context: CallbackContext):
    user_message = update.message.text
    context_messages.append(user_message)
    
    # Get reply from Gemini
    reply = get_gemini_reply(user_message)
    
    # Send reply to the user
    update.message.reply_text(reply)
    
    # Update the conversation history
    person.append({"role": "user", "parts": [user_message]})
    person.append({"role": "model", "parts": [reply]})
    
    # Save the updated context messages
    with open(history_file_path, "wb") as file:
        pkl.dump(person, file)

# Message handler to process image messages
def handle_image(update: Update, context: CallbackContext):
    logging.info("Message is an image")
    # Extract file information
    photo = update.message.photo[-1]
    file_id = photo.file_id
    new_file = bot.get_file(file_id)
    file_path = new_file.download('last_message.png')
    
    # Process the image
    img = Image.open(file_path)
    
    # You can pass the image object to your image processing function here, if needed
    current_message = img
    
    # Get reply from Gemini for the image message
    gemini_reply = get_image_gemini_reply(current_message)
    
    # Send reply to the user
    update.message.reply_text(gemini_reply)
    
    # Update the conversation history
    person.append({"role": "user", "parts": ["Image received."]})
    person.append({"role": "model", "parts": [gemini_reply]})
    
    # Save the updated context messages
    with open(history_file_path, "wb") as file:
        pkl.dump(person, file)

# Function to handle errors
def error(update: Update, context: CallbackContext):
    logging.error(f"Update {update} caused error {context.error}")

# Add command and message handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
dispatcher.add_handler(MessageHandler(Filters.photo, handle_image))

# Add error handler
dispatcher.add_error_handler(error)

# Start the bot
updater.start_polling()
updater.idle()
