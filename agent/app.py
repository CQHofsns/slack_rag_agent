import os, configparser

from slack_bolt import App
from pathlib import Path
from slack_bolt.adapter.socket_mode import SocketModeHandler
from agent.handler import SlackMessageHandler

BASE_DIR= Path(__file__).resolve().parent # Get the current folder
config_path= BASE_DIR / "../.config/creds.env"
config= configparser.ConfigParser()
config.read(config_path)

SLACK_APP_TOKEN= config["SLACK"]["APP_LEVEL_TOKEN"]
SLACK_BOT_TOKEN= config["SLACK"]["BOT_USER_OAUTH_TOKEN"]

app= App(token= SLACK_BOT_TOKEN)
handler= SlackMessageHandler()

@app.event("app_mention")
def handle_message_events(body, say, logger):
    # Ignore bot messages
    if "bot_id" in body["event"]:
        return
    
    event = body["event"]
    text= event.get("text", "")
    user= event.get("user")
    channel= event.get("channel")

    mentioned_user= f"<@{user}>"

    logger.info(f"[Agent mentioned] Message from {user}: {text}")

    if not text or text== "":
        say(f"Xin lỗi {mentioned_user} tôi không nhận được tin nhắn của bạn :< .")
    else:
        _, llm_response= handler.process(
            text= text
        )

        if llm_response or llm_response!= "":
            response= f"Trả lời câu hỏi của bạn {mentioned_user}:\n-----\n{llm_response}"
            say(response)

if __name__== "__main__":
    print("Khởi động SLACK Bot")
    SocketModeHandler(app= app, app_token= SLACK_APP_TOKEN).start()