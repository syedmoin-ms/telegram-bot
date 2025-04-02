import os
import json
import datetime
import logging
import re
import sys
import traceback
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext

async def is_admin(user_id: str) -> bool:
    return str(user_id) == str(ADMIN_ID)

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Token & Channel Details
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TOKEN:
    logger.error("No token found in environment variables!")
    sys.exit(1)
else:
    logger.info(f"Token found with length: {len(TOKEN)}")
    logger.info(f"Token starts with: {TOKEN[:4]}...")

# Channel and admin configuration
REQUIRED_CHANNELS = ["@fampayearningapp", "@grassnodepayairdrop"]
CHANNEL_LINKS = {
    "@fampayearningapp": "https://t.me/fampayearningapp",
    "@grassnodepayairdrop": "https://t.me/grassnodepayairdrop"
}
ADMIN_ID = 848533788

# Initialize data directory and file
DATA_DIR = "data"
DATA_FILE = f"{DATA_DIR}/users.json"

# Create data directory if it doesn't exist
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

async def admin_panel(update: Update, context: CallbackContext):
    """Admin panel command handler"""
    try:
        user_id = str(update.effective_user.id)
        if not await is_admin(user_id):
            logger.warning(f"Unauthorized admin panel access attempt by user {user_id}")
            await update.message.reply_text("❌ You are not authorized to use admin commands.")
            return

        logger.info(f"Admin panel accessed by {user_id}")
        current_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

        # Calculate statistics
        total_users = len(users)
        total_points = sum(user.get("points", 0) for user in users.values())
        total_referrals = sum(user.get("referrals", 0) for user in users.values())
        total_rewards = sum(user.get("rewards_claimed", 0) for user in users.values())

        message = (
            f"Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): {current_time}\n"
            "Current User's Login: syedmoin-ms\n\n"
            "👨‍💼 Admin Panel Statistics:\n\n"
            f"📊 Total Users: {total_users}\n"
            f"💰 Total Points: {total_points}\n"
            f"👥 Total Referrals: {total_referrals}\n"
            f"🎁 Total Rewards Claimed: {total_rewards}\n\n"
            "Admin Commands:\n"
            "📢 /broadcast - Send message to all users\n"
            "💰 /points <user_id> <points> - Modify user points\n"
            "🚫 /ban <user_id> - Ban a user\n"
            "✅ /unban <user_id> - Unban a user\n"
            "📊 /stats <user_id> - View user statistics\n"
            "📨 /send <user_id> <message> - Send message to specific user"
        )
        
        await update.message.reply_text(message)
        logger.info("Admin panel displayed successfully")
        
    except Exception as e:
        logger.error(f"Error in admin panel: {str(e)}")
        await update.message.reply_text(
            "❌ An error occurred while displaying the admin panel.\n"
            "Please try again or contact support."
        )

async def send_user_message(update: Update, context: CallbackContext):
    """Send message to specific user"""
    try:
        user_id = str(update.effective_user.id)
        if not await is_admin(user_id):
            await update.message.reply_text("❌ You are not authorized to use admin commands.")
            return

        if len(context.args) < 2:
            await update.message.reply_text(
                "Usage: /send <user_id> <message>\n\n"
                "Example: /send 123456789 Hello, how are you?"
            )
            return

        target_id = context.args[0]
        message = " ".join(context.args[1:])

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"📬 Message from Admin:\n\n{message}"
            )
            await update.message.reply_text(
                f"✅ Message sent successfully!\n"
                f"To: {target_id}\n"
                f"Message: {message}"
            )
            
            logger.info(f"Admin message sent to {target_id}: {message}")
        except Exception as e:
            await update.message.reply_text(
                f"❌ Failed to send message to user {target_id}\n"
                f"Error: {str(e)}"
            )

    except Exception as e:
        logger.error(f"Error in send_user_message: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

# Initialize users dictionary
def load_data():
    global users
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                users = json.load(f)
        except json.JSONDecodeError:
            users = {}
            logger.error("Error reading users file, starting with empty users dict")
    else:
        users = {}

load_data()

def save_data():
    try:
        # Create backup of existing file
        if os.path.exists(DATA_FILE):
            backup_file = f"{DATA_FILE}.backup"
            try:
                with open(DATA_FILE, 'r') as src, open(backup_file, 'w') as dst:
                    dst.write(src.read())
            except Exception as e:
                logger.error(f"Error creating backup: {str(e)}")

        # Save new data
        with open(DATA_FILE, "w") as f:
            json.dump(users, f, indent=4)
        logger.info("Data saved successfully")
    except Exception as e:
        logger.error(f"Error saving data: {str(e)}")

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_current_time():
    """Get current UTC time in YYYY-MM-DD HH:MM:SS format"""
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

async def check_daily_reward(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        current_date = datetime.datetime.utcnow().strftime('%Y-%m-%d')

        if user_id not in users:
            users[user_id] = {
                "points": 0,
                "referrals": 0,
                "email": "",
                "rewards_claimed": 0,
                "last_daily_claim": "",
                "awaiting_email": False
            }

        if users[user_id].get("last_daily_claim", "") != current_date:
            reward_points = 5
            users[user_id]["points"] = users[user_id].get("points", 0) + reward_points
            users[user_id]["last_daily_claim"] = current_date
            save_data()
            await update.message.reply_text(
                f"🎁 Daily Reward Claimed!\n"
                f"+{reward_points} points!\n"
                f"Current balance: {users[user_id]['points']} points\n"
                f"Come back tomorrow for more rewards!"
            )
        else:
            next_claim = (datetime.datetime.strptime(current_date, '%Y-%m-%d') + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
            await update.message.reply_text(
                "❌ You've already claimed your daily reward today.\n"
                f"Next reward available on: {next_claim} UTC"
            )
    except Exception as e:
        logger.error(f"Error in daily reward: {str(e)}")
        await update.message.reply_text("❌ An error occurred while claiming daily reward.")

async def check_channel_membership(update: Update, context: CallbackContext) -> bool:
    try:
        for channel in REQUIRED_CHANNELS:
            chat_member = await context.bot.get_chat_member(chat_id=channel, user_id=update.effective_user.id)
            if chat_member.status not in ['member', 'administrator', 'creator']:
                return False
        return True
    except Exception as e:
        logger.error(f"Error checking channel membership: {str(e)}")
        return False

async def start(update: Update, context: CallbackContext):
    try:
        if not await check_channel_membership(update, context):
            channels_text = "\n".join([f"{i+1}➡️ {channel}" for i, channel in enumerate(REQUIRED_CHANNELS)])
            keyboard = [
                [KeyboardButton("✅ Join Channels"), KeyboardButton("🔄 Check Again")]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text(
                "🛑 Join Our Channels If You Want To Use The Bot:\n\n"
                f"{channels_text}\n\n"
                "✅ Done Subscribed! Click Check",
                reply_markup=reply_markup
            )
            return

        user_id = str(update.effective_user.id)
        user_name = update.effective_user.first_name

        # Initialize user data if new
        if user_id not in users:
            users[user_id] = {
                "points": 0,
                "referrals": 0,
                "email": "",
                "rewards_claimed": 0,
                "awaiting_email": False,
                "has_been_referred": False,
                "referrer_id": None,
                "last_daily_claim": "",
                "join_date": get_current_time()
            }
            save_data()

        # Handle referral
        if context.args and context.args[0]:
            referrer_id = str(context.args[0])
            logger.info(f"Referral attempt - User: {user_id}, Referrer: {referrer_id}")
            
            # Check if referrer exists and is not the same as user
            if referrer_id in users and referrer_id != user_id:
                # Check if user has already been referred
                if not users[user_id].get("has_been_referred", False):
                    # Update new user's data
                    users[user_id]["points"] = users[user_id].get("points", 0) + 5
                    users[user_id]["has_been_referred"] = True
                    users[user_id]["referrer_id"] = referrer_id

                    # Update referrer's data
                    users[referrer_id]["points"] = users[referrer_id].get("points", 0) + 10
                    users[referrer_id]["referrals"] = users[referrer_id].get("referrals", 0) + 1

                    save_data()

                    # Send confirmation to new user
                    await update.message.reply_text(
                        f"🎉 Congratulations!\n\n"
                        f"You've earned: +5 points 🎁\n"
                        f"Current balance: {users[user_id]['points']} points\n\n"
                        f"Start earning more by sharing your referral link! 🔗"
                    )

                    # Send confirmation to referrer
                    try:
                        await context.bot.send_message(
                            chat_id=referrer_id,
                            text=f"🎉 New Referral Success!\n\n"
                                f"User: {user_name}\n"
                                f"You earned: +10 points 🎁\n"
                                f"Total referrals: {users[referrer_id]['referrals']}\n"
                                f"Current balance: {users[referrer_id]['points']} points"
                        )
                        logger.info(f"Referral success - Referrer: {referrer_id}, User: {user_id}")
                    except Exception as e:
                        logger.error(f"Could not send message to referrer: {e}")

        # Create keyboard with main options
        keyboard = [
            [KeyboardButton("👥 Refer & Earn"), KeyboardButton("💰 My Points")],
            [KeyboardButton("🎁 Claim Reward"), KeyboardButton("🏆 Leaderboard")],
            [KeyboardButton("📅 Daily Reward"), KeyboardButton("🔥 Midas RWA Task")],
            [KeyboardButton("ℹ️ Help")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        # Show welcome message
        await update.message.reply_text(
            f"👋 Welcome {user_name}!\n\n"
            f"📊 Points: {users[user_id]['points']}\n"
            f"👥 Referrals: {users[user_id].get('referrals', 0)}\n\n"
            "Choose an option from the menu below:",
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await update.message.reply_text(
            "❌ An error occurred. Please try again. If the problem persists, contact support."
        )

async def refer_earn(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        bot = await context.bot.get_me()
        referral_link = f"https://t.me/{bot.username}?start={user_id}"
        
        user_data = users.get(user_id, {})
        referrals_count = user_data.get('referrals', 0)
        total_earnings = user_data.get('points', 0)
        
        message = (
            "🔥 Refer & Earn Program:\n\n"
            "Earn points by inviting friends:\n"
            "• You get: 10 points per referral\n"
            "• Friend gets: 5 points for joining\n\n"
            f"Your Stats:\n"
            f"• Total Referrals: {referrals_count}\n"
            f"• Total Points: {total_earnings}\n\n"
            f"Your Referral Link:\n{referral_link}\n\n"
            "Share this link with your friends to earn points! 🎁"
        )
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error in refer_earn: {str(e)}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def my_points(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        user_data = users.get(user_id, {"points": 0, "referrals": 0})
        
        message = (
            "💰 Your Points Summary:\n\n"
            f"• Total Points: {user_data['points']}\n"
            f"• Total Referrals: {user_data['referrals']}\n"
            f"• Rewards Claimed: {user_data.get('rewards_claimed', 0)}\n\n"
            "🎯 Ways to earn more:\n"
            "1. Refer friends (+10 points)\n"
            "2. Daily reward (+5 points)\n"
            "3. Complete tasks (+15 points)\n\n"
            "Need 100 points to claim reward! 🎁"
        )
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in my_points: {str(e)}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def claim_reward(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        user_data = users.get(user_id, {"points": 0})

        if user_data["points"] < 100:
            await update.message.reply_text(
                "❌ You need at least 100 points to claim a reward!\n"
                f"Current points: {user_data['points']}\n"
                f"Points needed: {100 - user_data['points']}"
            )
            return

        if not user_data.get("awaiting_email", False):
            users[user_id]["awaiting_email"] = True
            save_data()
            await update.message.reply_text(
                "🎁 Great! To claim your reward, please enter your Gmail address:"
            )
            return

        email = update.message.text
        if not is_valid_email(email):
            await update.message.reply_text(
                "❌ Invalid email format! Please enter a valid Gmail address."
            )
            return

        users[user_id]["points"] -= 100
        users[user_id]["email"] = email
        users[user_id]["awaiting_email"] = False
        users[user_id]["rewards_claimed"] = users[user_id].get("rewards_claimed", 0) + 1
        users[user_id]["last_reward_claim"] = get_current_time()
        save_data()

        user_name = update.effective_user.first_name
        user_link = f"[{user_name}](tg://user?id={user_id})"

        # Notify admin
        admin_message = (
            f"🎁 New Reward Claim!\n\n"
            f"User: {user_link}\n"
            f"Email: {email}\n"
            f"Total Claims: {users[user_id]['rewards_claimed']}\n"
            f"Remaining Points: {users[user_id]['points']}\n"
            f"Claim Time: {get_current_time()}"
        )

        try:
            await context.bot.send_message(
                chat_id=ADMIN_ID,
                text=admin_message,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"Failed to notify admin: {str(e)}")

        await update.message.reply_text(
            "✅ Reward claimed successfully!\n"
            f"Remaining points: {users[user_id]['points']}\n"
            "An admin will contact you soon."
        )

    except Exception as e:
        logger.error(f"Error in claim_reward: {str(e)}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def leaderboard(update: Update, context: CallbackContext):
    try:
        sorted_users = sorted(users.items(), key=lambda x: x[1]['referrals'], reverse=True)
        message = "🏆 Top Referrers:\n\n"
        
        for i, (user_id, data) in enumerate(sorted_users[:10], 1):
            try:
                user = await context.bot.get_chat(user_id)
                name = user.first_name
            except:
                name = f"User{user_id[:4]}"
            message += f"{i}. {name}: {data['referrals']} referrals ({data['points']} points)\n"

        message += "\n💫 Keep referring to reach the top!"
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in leaderboard: {str(e)}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def help_command(update: Update, context: CallbackContext):
    try:
        await update.message.reply_text(
            "ℹ️ Bot Help:\n\n"
            "1. Join our channels to start earning\n"
            "2. Share your referral link with friends\n"
            "3. Earn points through referrals\n"
            "4. Claim daily rewards\n"
            "5. Complete tasks for extra points\n"
            "6. Claim rewards at 100 points\n\n"
            "📌 Points System:\n"
            "• Referral Bonus: +10 points\n"
            "• Daily Reward: +5 points\n"
            "• Task Completion: +15 points\n\n"
            "For support: @admin"
        )
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def handle_text(update: Update, context: CallbackContext):
    try:
        text = update.message.text
        user_id = str(update.effective_user.id)

        # Handle Midas RWA referral verification
        if "MidasRWA_bot/app?startapp=ref_" in text:
            if not users.get(user_id, {}).get("midas_referral_clicked", False):
                users[user_id] = users.get(user_id, {"points": 0})
                users[user_id]["midas_referral_clicked"] = True
                save_data()
                await update.message.reply_text(
                    "✅ First click on Midas RWA referral registered!\n"
                    "Please click the link again to confirm your participation."
                )
            else:
                users[user_id]["points"] = users[user_id].get("points", 0) + 15
                users[user_id]["midas_referral_completed"] = True
                users[user_id]["midas_completion_time"] = get_current_time()
                save_data()
                await update.message.reply_text(
                    "🎉 Congratulations! You've completed the Midas RWA task.\n"
                    "15 points have been added to your account!"
                )
            return

        if text == "✅ Join Channels":
            channels_text = "\n".join([f"{i+1}➡️ {channel}" for i, channel in enumerate(REQUIRED_CHANNELS)])
            await update.message.reply_text(
                "🌟 Welcome to our Earning Community! 🌟\n\n"
                "Join our official channels to:\n"
                "• Get instant earning updates\n"
                "• Access exclusive reward opportunities\n"
                "• Stay informed about special bonuses\n\n"
                "Click '🔄 Check Again' after joining to activate your rewards!\n\n"
                f"Join now:\n{channels_text}"
            )
            return

        elif text == "🔄 Check Again":
            if await check_channel_membership(update, context):
                await start(update, context)
            else:
                await update.message.reply_text(
                    "❌ You haven't joined all required channels yet.\n"
                    "Please join and try again."
                )
            return

        # Verify channel membership for all commands
        if not await check_channel_membership(update, context):
            channels_text = "\n".join([f"{i+1}➡️ {channel}" for i, channel in enumerate(REQUIRED_CHANNELS)])
            await update.message.reply_text(
                f"❗️ Please join our channels to use this bot:\n\n{channels_text}"
            )
            return

        # Handle email input for reward claim
        if users.get(user_id, {}).get("awaiting_email", False):
            await claim_reward(update, context)
            return

        # Handle main menu options
        if text == "👥 Refer & Earn":
            await refer_earn(update, context)
        elif text == "💰 My Points":
            await my_points(update, context)
        elif text == "🎁 Claim Reward":
            await claim_reward(update, context)
        elif text == "ℹ️ Help":
            await help_command(update, context)
        elif text == "🏆 Leaderboard":
            await leaderboard(update, context)
        elif text == "📅 Daily Reward":
            await check_daily_reward(update, context)
        elif text == "🔥 Midas RWA Task":
            await update.message.reply_text(
                "🎯 Complete Midas RWA Task:\n\n"
                "1. Click this link:\n"
                "https://t.me/MidasRWA_bot/app?startapp=ref_326f2187-d1cb-43ab-bb7f-5ae74e3c93d6\n\n"
                "2. Complete the registration\n"
                "3. Send the link back here to verify\n\n"
                "Earn 15 points upon completion! 🎁"
            )

    except Exception as e:
        logger.error(f"Error in handle_text: {str(e)}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error(f"Exception while handling an update: {context.error}")
    traceback.print_exc()

def main():
    try:
        # Create application
        app = Application.builder().token(TOKEN).build()

        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(CommandHandler("help", help_command))
        
        # Add admin command handlers
        app.add_handler(CommandHandler("admin", admin_panel))
        app.add_handler(CommandHandler("broadcast", broadcast_message))
        app.add_handler(CommandHandler("ban", ban_user))
        app.add_handler(CommandHandler("unban", unban_user))
        app.add_handler(CommandHandler("points", edit_points))
        app.add_handler(CommandHandler("stats", user_stats))
        app.add_handler(CommandHandler("send", send_user_message))

        # Add error handler
        app.add_error_handler(error_handler)

        # Start the bot
        logger.info("Starting bot...")
        app.run_polling()

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        traceback.print_exc()
        raise e


if __name__ == "__main__":
    main()
