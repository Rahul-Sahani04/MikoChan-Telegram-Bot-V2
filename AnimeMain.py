import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
import pickle as pkl
import os
import logging
from PIL import Image
from dotenv import load_dotenv
import csv
import requests
import random

from keep_alive import keep_alive

# Load environment variables
load_dotenv()
TOKEN = os.environ.get("TOKEN")
api_url = os.environ.get("API_URL")

# ? isUserSearching variable to check if user is searching for anime or not, and not to trigger the Gemini API for normal messages during search process
isUserSearching = False
isUserSelectingAnime = False
isUserSelectingEpisode = False
isUserSelectingPage = False

# Configure the Gemini API and it from the environment variable

api_key = os.environ.get("GEMINI_API_KEY")
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

context_messages = []

# Function to get a reply from Gemini API
def get_gemini_reply(message):
    try:
        response = model.send_message(message, safety_settings=safety_settings)
        return response.text
    except Exception as e:
        return f"Sorry, I couldn't understand that. Error: {str(e)}"

# Function to get a reply from Gemini API for image messages
def get_image_gemini_reply(message):
    try:
        response = model.send_message([f"The Message to reply to is the image.", message], safety_settings=safety_settings)
        response.resolve()
        return response.text
    except Exception as e:
        return f"Sorry, I couldn't understand that. Error: {str(e)}"

# CSV functions
def append_row_to_csv(filename, data):
    with open(filename, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(data)

# Logger configuration
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
RESULTS_PER_PAGE = 5  # Number of search results to display per page

# Random messages
cute_emojis = ['😊', '🥰', '😍', '🐻', '🐼', '🌸', '🌈', '🍩']
messages = ["Enjoy!", "Here you go!", "I hope you enjoy!", "Oo", "let's watch!", "Now you can watch."]

# Helper functions
def send_random_cute_message(update, context):
    random_emoji = random.choice(cute_emojis)
    random_message = random.choice(messages)
    text = f"{random_emoji} {random_message}"
    context.bot.send_message(chat_id=update.effective_chat.id, text=text)

def update_bot_chat_id(context, sent_msg):
    context.user_data['prev_bot_chat_id'] = sent_msg.chat_id
    context.user_data['prev_bot_message_id'] = sent_msg.message_id

def update_user_chat_id(update, context):
    context.user_data['prev_user_chat_id'] = update.effective_chat.id
    context.user_data['prev_user_message_id'] = update.message.message_id

# Command handlers
def start(update, context):
    global isUserSearching, isUserSelectingAnime, isUserSelectingEpisode, isUserSelectingPage
    
    print("Starting...")
    print("isUserSearching: ", isUserSearching)
    print("isUserSelectingAnime: ", isUserSelectingAnime)
    print("isUserSelectingEpisode: ", isUserSelectingEpisode)
    print("isUserSelectingPage: ", isUserSelectingPage)
    
    isUserSearching = False
    
    
    
    context.user_data['page'] = 1
    update.message.reply_text("Hi! I'm Miko Chan, your anime guide and friend. How can I assist you today?")

def search(update, context):
    global isUserSearching
    isUserSearching = True
    
    context.user_data['page'] = 1
    print("Entering search function...")
    
    # if /search contains a query, process it immediately without asking the user to enter a query again 
    if len(context.args) > 0:
        query = " ".join(context.args)
        page = 1
        search_results = search_anime(query)
        context.user_data['search_results'] = search_results

        if search_results:
            total_results = len(search_results)
            num_pages = (total_results - 1) // RESULTS_PER_PAGE + 1
            context.user_data['num_pages'] = num_pages
            reply_markup = create_pagination_keyboard(context, page, num_pages)
            message = create_search_results_message(search_results, page, num_pages)
            sent_message = context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
            update_bot_chat_id(context, sent_message)
        return "SELECT_ANIME"
    else:
        update.message.reply_text("Enter anime name to search:", reply_markup=ReplyKeyboardMarkup([['/cancel']], resize_keyboard=True))
        return "SEARCH"
    

def get_anime_info_by_id(update, context):
    global isUserSelectingEpisode
    isUserSelectingEpisode = True
    
    # if /info contains an anime ID, get the anime info immediately without asking the user to enter an ID again
    if len(context.args) > 0:
        anime_id = context.args[0]
        anime_info = get_anime_info(anime_id)
        message, image, total_ep, title_id = get_anime_details(anime_info)
        context.bot.send_photo(chat_id=update.effective_chat.id, photo=image)
        context.bot.send_message(chat_id=update.effective_chat.id, text=message)
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Anime ID: {title_id}", reply_markup=ReplyKeyboardMarkup([['/goback', '/cancel', '/search']]))
        update.message.reply_text(f"Select an episode,  (Total: {total_ep}): ")
        update.message.reply_text(f"or ask me about the anime.")
        update.message.reply_text(f"or try /info {title_id} to get info about this anime again.")
        
        return "SELECT_EPISODE"
    else:
        update.message.reply_text("Enter anime ID to get info:")
        return "SELECT_EPISODE"


def process_search(update, context):
    global isUserSelectingAnime
    global isUserSearching 
  
    isUserSelectingAnime = True
    
    
    query = update.message.text
    
    # Update the conversation history
    # person.append({"role": "user", "parts": ["Can you search for: " + query + "."]})
    
    # # Save the updated context messages
    # with open(history_file_path, "wb") as file:
    #     pkl.dump(person, file)
    
    page = 1
    search_results = search_anime(query)
    context.user_data['search_results'] = search_results

    if search_results:
        total_results = len(search_results)
        num_pages = (total_results - 1) // RESULTS_PER_PAGE + 1
        context.user_data['num_pages'] = num_pages
        reply_markup = create_pagination_keyboard(context, page, num_pages)
        message = create_search_results_message(search_results, page, num_pages)
        sent_message = context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        update_bot_chat_id(context, sent_message)

    isUserSearching = False
    return "SELECT_ANIME"

def create_pagination_keyboard(context, current_page, num_pages):
    buttons = []
    page_number = context.user_data['page']
    if page_number <= num_pages:
        buttons.append("next")
    if page_number <= num_pages and page_number > 1:
        buttons.append("back")
    keyboard = [buttons, ['/cancel', '/goback']]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def create_search_results_message(results, page, num_pages):
    start_index = (page - 1) * RESULTS_PER_PAGE
    end_index = start_index + RESULTS_PER_PAGE

    message = "Search results:\n"
    for i, result in enumerate(results[start_index:end_index], start=start_index):
        titles = result['title']
        title = titles.get("english") or titles.get("userPreferred") or titles.get("romaji") or titles.get("native", "")
        message += f"{i+1}. {title}\n"

    message += f"\nPage {page} of {num_pages}"
    return message

def select_anime(update, context):
    print("Searching for anime...")
    global isUserSelectingAnime
    global isUserSelectingEpisode
    global isUserSelectingPage
    isUserSelectingPage = True
    isUserSelectingEpisode = True

    
    if update.message.text in ["next", "back"]:
        return select_page(update, context, context.user_data['page'])
    elif update.message.text == "/cancel":
        return cancel(update, context)
    elif update.message.text == "/search":
        return "SEARCH"
    elif update.message.text == "/start":
        return "START"

    selected_index = int(update.message.text) - 1
    search_results = context.user_data['search_results']
    selected_anime = search_results[selected_index]
    context.user_data['anime_id'] = selected_anime['id']
    anime_info = get_anime_info(selected_anime['id'])
    message, image, total_ep, title_id = get_anime_details(anime_info)
    context.bot.send_photo(chat_id=update.effective_chat.id, photo=image)
    context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"Anime ID: {title_id}", reply_markup=ReplyKeyboardMarkup([['/goback', '/cancel', '/search']]))
    update.message.reply_text(f"Select an episode,  (Total: {total_ep}): ")
    update.message.reply_text(f"or ask me about the anime.")
    
    isUserSelectingAnime = False
    isUserSelectingPage = False
    return "SELECT_EPISODE"

def select_page(update, context, page):
    
    page_number = context.user_data['page']
    num_pages = context.user_data['num_pages']
    search_results = context.user_data['search_results']

    if update.message.text == "/cancel":
        return cancel(update, context)
    if update.message.text == "next" and page_number < num_pages:
        page_number = page + 1
    if update.message.text == "back" and page_number > 1:
        page_number = page - 1

    if 1 <= page_number <= num_pages:
        page = page_number
        context.user_data['page'] = page
        reply_markup = create_pagination_keyboard(context, page, num_pages)
        message = create_search_results_message(search_results, page, num_pages)

        chat_id = context.user_data.get('prev_bot_chat_id')
        msg_id = context.user_data.get('prev_bot_message_id')
        user_chat_id = context.user_data.get('prev_user_chat_id')
        user_msg_id = context.user_data.get('prev_user_message_id')
        # context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
        # context.bot.delete_message(chat_id=user_chat_id, message_id=user_msg_id)
        
        if chat_id and msg_id:
            try:
                context.bot.delete_message(chat_id=chat_id, message_id=msg_id)
            except Exception as e:
                print(f"Failed to delete message with chat_id={chat_id} and message_id={msg_id}. Error: {e}")

        if user_chat_id and user_msg_id:
            try:
                context.bot.delete_message(chat_id=user_chat_id, message_id=user_msg_id)
            except Exception as e:
                print(f"Failed to delete message with chat_id={user_chat_id} and message_id={user_msg_id}. Error: {e}")
                
        send_msg = context.bot.send_message(chat_id=update.effective_chat.id, text=message, reply_markup=reply_markup)
        update_bot_chat_id(context, send_msg)

    return "SELECT_ANIME"

def get_anime_info(anime_id):
    url = f"{api_url}/meta/anilist/info/{anime_id}"
    response = requests.get(url)
    return response.json()

def get_anime_details(anime_info):
    titles = anime_info['title']
    title = titles.get("english") or titles.get("userPreferred") or titles.get("romaji") or titles.get("native", "")
    title_id = anime_info['id']
    total_episodes = anime_info['totalEpisodes']
    release_date = anime_info['releaseDate']
    description = anime_info['description']
    csv_file = 'Most_Searched.csv'
    new_row = [title, title_id, release_date]
    append_row_to_csv(csv_file, new_row)

    message = f"Title: {title}\nTotal Episodes: {total_episodes}\nRelease Date: {release_date}\nDescription: {description}"
    image_url = anime_info['image']
    
    # # Update the conversation history
    # person.append({"role": "model", "parts": ["Here's, What you asked for:\n" + message]})
    
    # # Save the updated context messages
    # with open(history_file_path, "wb") as file:
    #     pkl.dump(person, file)
      
    model.send_message(f"I searched for an anime called {title}. Heres the description of it:\n" + message)
    
    return message, image_url, total_episodes, title_id

def select_episode(update, context):
    global isUserSearching, isUserSelectingAnime, isUserSelectingEpisode, isUserSelectingPage
    
    selected_episode_number = update.message.text.replace(" ", "")
    anime_id = context.user_data['anime_id']

    # Reset all flags
    isUserSearching = False
    isUserSelectingAnime = False
    isUserSelectingEpisode = False
    isUserSelectingPage = False
    
    if "," in selected_episode_number:
        numbers = [int(n) for n in selected_episode_number.split(",")]
        anime_info = get_anime_info(anime_id)
        for num in numbers:
            episode_after(update, context, anime_info, num)
        send_random_cute_message(update, context)
        return ConversationHandler.END

    elif "-" in selected_episode_number:
        start, end = [int(n) for n in selected_episode_number.split("-")]
        numbers = range(start, end + 1)
        anime_info = get_anime_info(anime_id)
        for num in numbers:
            episode_after(update, context, anime_info, num)
        send_random_cute_message(update, context)
        return ConversationHandler.END

    else:
      try:
        number = int(selected_episode_number)
        anime_info = get_anime_info(anime_id)
        episode_after(update, context, anime_info, number)
        send_random_cute_message(update, context)
      except ValueError:
          reply = get_gemini_reply(selected_episode_number)
          context.bot.send_message(chat_id=update.effective_chat.id, text=reply, parse_mode="MarkdownV2")
      except Exception as e:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid episode number. {e}")
      finally:
        return ConversationHandler.END
      

def episode_after(update, context, anime_info, selected_episode_number):
    episodes = anime_info["episodes"]
    selected_episode_id = None
    for episode in episodes:
        if episode['number'] == selected_episode_number:
            selected_episode_id = episode['id']
            break

    if selected_episode_id:
        context.user_data['episode_id'] = selected_episode_id
        streamlink = get_episode_sources(anime_info["id"], selected_episode_id)
        if streamlink:
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"Stream Link for episode {selected_episode_number}: {streamlink}")
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Episode sources not found.")
    else:
        context.bot.send_message(chat_id=update.effective_chat.id, text="Selected episode not found.")
    return ConversationHandler.END

def get_episode_sources(anime_id, episode_id):
    myWebsiteUrl = f"https://v-anime.vercel.app/watch?query={anime_id}&ep={episode_id}"
    data = myWebsiteUrl
    return data if data and episode_id else None

def cancel(update, context):
    global isUserSearching, isUserSelectingAnime, isUserSelectingEpisode, isUserSelectingPage
    isUserSearching = False
    isUserSelectingAnime = False
    isUserSelectingEpisode = False
    isUserSelectingPage = False
    
    context.bot.send_message(chat_id=update.effective_chat.id, text="Search canceled.")
    return ConversationHandler.END

def search_anime(query):
    results = []
    page = 1
    has_next_page = True

    while has_next_page:
        url = f"{api_url}/meta/anilist/{query}?page={page}"
        response = requests.get(url)
        data = response.json()
        results.extend(data.get("results", []))
        has_next_page = data.get("hasNextPage", False)
        page += 1

    return results
  

# Message handler to process text messages
def handle_message(update: Update, context: CallbackContext):
  if isUserSearching:
      process_search(update, context)
  elif isUserSelectingAnime:
    if update.message.text in ["next", "back"]:
      return select_page(update, context, context.user_data['page'])
    select_anime(update, context)
  elif isUserSelectingEpisode:
    select_episode(update, context)
  else:
    user_message = update.message.text
    context_messages.append(user_message)
    
    # Get reply from Gemini
    reply = get_gemini_reply(user_message)
    
    # Send reply to the user
    update.message.reply_text(reply)
    
    # # Update the conversation history
    # person.append({"role": "user", "parts": [user_message]})
    # person.append({"role": "model", "parts": [reply]})
    
    # Save the updated context messages
    with open(history_file_path, "wb") as file:
        person = model.history
        pkl.dump(person, file)
    
    return ConversationHandler.END


# Message handler to process image messages
def handle_image(update: Update, context: CallbackContext):
  if isUserSearching:
    process_search(update, context)
  elif isUserSelectingAnime:
    if update.message.text in ["next", "back"]:
      return select_page(update, context, context.user_data['page'])
    select_anime(update, context)
  elif isUserSelectingEpisode:
    select_episode(update, context)
  else:
    logging.info("Message is an image")
    # Extract file information
    photo = update.message.photo[-1]
    file_id = photo.file_id
    new_file = context.bot.get_file(file_id)
    file_path = new_file.download('last_message.png')
    
    # Process the image
    img = Image.open(file_path)
    
    # You can pass the image object to your image processing function here, if needed
    current_message = img
    
    # Get reply from Gemini for the image message
    gemini_reply = get_image_gemini_reply(current_message)
    
    # Send reply to the user
    update.message.reply_text(gemini_reply, parse_mode="Markdown")
    
    # Update the conversation history
    # person.append({"role": "user", "parts": ["Image received."]})
    # person.append({"role": "model", "parts": [gemini_reply]})
    
    # Save the updated context messages
    with open(history_file_path, "wb") as file:
        person = model.history
        pkl.dump(person, file)
        
    return ConversationHandler.END


# Function to handle errors
def error(update: Update, context: CallbackContext):
    logging.error(f"Update {update} caused error {context.error}")


# Main function
def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('search', search)],
        states={
            "SEARCH": [MessageHandler(Filters.text & ~Filters.command, process_search)],
            "SELECT_ANIME": [MessageHandler(Filters.text, select_anime)],
            "SELECT_EPISODE": [MessageHandler(Filters.text & ~Filters.command, select_episode)],
        },
        fallbacks=[CommandHandler('cancel', cancel), CommandHandler('start', start), CommandHandler('search', search)],
    )
    
    


    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(conv_handler)
    
    # /info command to get a specific anime info by ID (e.g. /info 1)
    dp.add_handler(CommandHandler('info', get_anime_info_by_id))
    
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.photo, handle_image))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    keep_alive()
    main()
