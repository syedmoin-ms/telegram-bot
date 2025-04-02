import logging
import os
import json
import datetime
import re
import sys
import traceback
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext

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

async def is_admin(user_id: str) -> bool:
    return str(user_id) == str(ADMIN_ID)

async def admin_panel(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        if not await is_admin(user_id):
            await update.message.reply_text("❌ You are not authorized to use admin commands.")
            return

        current_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        user_login = "syedmoin-ms"

        total_users = len(users)
        total_points = sum(user["points"] for user in users.values())
        total_referrals = sum(user["referrals"] for user in users.values())
        total_rewards = sum(user.get("rewards_claimed", 0) for user in users.values())

        message = (
            f"Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): {current_time}\n"
            f"Current User's Login: {user_login}\n\n"
            "👨‍💼 Admin Panel Statistics:\n\n"
            f"📊 Total Users: {total_users}\n"
            f"💰 Total Points: {total_points}\n"
            f"👥 Total Referrals: {total_referrals}\n"
            f"🎁 Total Rewards Claimed: {total_rewards}\n\n"
            "Admin Commands:\n"
            "/broadcast - Send message to all users\n"
            "/points - Modify user points\n"
            "/ban - Ban a user\n"
            "/unban - Unban a user\n"
            "/stats - View user statistics\n"
            "/send - Send message to specific user"
        )
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in admin panel: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

async def broadcast_message(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        if not await is_admin(user_id):
            await update.message.reply_text("❌ You are not authorized to use admin commands.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /broadcast <message>")
            return

        message = " ".join(context.args)
        success = 0
        failed = 0

        for user_id in users:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 Broadcast Message:\n\n{message}"
                )
                success += 1
            except Exception:
                failed += 1

        await update.message.reply_text(
            f"✅ Broadcast completed!\n"
            f"• Success: {success}\n"
            f"• Failed: {failed}"
        )
    except Exception as e:
        logger.error(f"Error in broadcast: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

async def edit_points(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        if not await is_admin(user_id):
            await update.message.reply_text("❌ You are not authorized to use admin commands.")
            return

        if len(context.args) != 2:
            await update.message.reply_text("Usage: /points <user_id> <points>")
            return

        target_id = str(context.args[0])
        points = int(context.args[1])

        if target_id not in users:
            await update.message.reply_text("❌ User not found.")
            return

        users[target_id]["points"] = points
        save_data()

        await update.message.reply_text(
            f"✅ Points updated!\n"
            f"User: {target_id}\n"
            f"New points: {points}"
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid points value.")
    except Exception as e:
        logger.error(f"Error in edit_points: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

async def ban_user(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        if not await is_admin(user_id):
            await update.message.reply_text("❌ You are not authorized to use admin commands.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /ban <user_id>")
            return

        target_id = str(context.args[0])
        if target_id not in users:
            await update.message.reply_text("❌ User not found.")
            return

        users[target_id]["banned"] = True
        save_data()

        await update.message.reply_text(f"✅ User {target_id} has been banned.")
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="❌ You have been banned from using this bot."
            )
        except Exception:
            pass
            
    except Exception as e:
        logger.error(f"Error in ban_user: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

async def unban_user(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        if not await is_admin(user_id):
            await update.message.reply_text("❌ You are not authorized to use admin commands.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /unban <user_id>")
            return

        target_id = str(context.args[0])
        if target_id not in users:
            await update.message.reply_text("❌ User not found.")
            return

        users[target_id]["banned"] = False
        save_data()

        await update.message.reply_text(f"✅ User {target_id} has been unbanned.")
        
        try:
            await context.bot.send_message(
                chat_id=target_id,
                text="✅ You have been unbanned. You can use the bot again."
            )
        except Exception:
            pass
            
    except Exception as e:
        logger.error(f"Error in unban_user: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

async def send_user_message(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        if not await is_admin(user_id):
            await update.message.reply_text("❌ You are not authorized to use admin commands.")
            return

        if len(context.args) < 2:
            await update.message.reply_text("Usage: /send <user_id> <message>")
            return

        target_id = context.args[0]
        message = " ".join(context.args[1:])

        try:
            await context.bot.send_message(
                chat_id=target_id,
                text=f"📬 Message from Admin:\n\n{message}"
            )
            await update.message.reply_text(f"✅ Message sent to user {target_id}")
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to send message to user {target_id}")
            logger.error(f"Error sending message to user {target_id}: {str(e)}")

    except Exception as e:
        logger.error(f"Error in send_user_message: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

async def user_stats(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        if not await is_admin(user_id):
            await update.message.reply_text("❌ You are not authorized to use admin commands.")
            return

        if not context.args:
            await update.message.reply_text("Usage: /stats <user_id>")
            return

        target_id = str(context.args[0])
        if target_id not in users:
            await update.message.reply_text("❌ User not found.")
            return

        user_data = users[target_id]
        try:
            user = await context.bot.get_chat(target_id)
            user_name = user.first_name
        except:
            user_name = f"User{target_id[:4]}"

        message = (
            f"📊 Stats for {user_name}\n\n"
            f"User ID: {target_id}\n"
            f"Points: {user_data.get('points', 0)}\n"
            f"Referrals: {user_data.get('referrals', 0)}\n"
            f"Rewards Claimed: {user_data.get('rewards_claimed', 0)}\n"
            f"Join Date: {user_data.get('join_date', 'Unknown')}\n"
            f"Last Daily Claim: {user_data.get('last_daily_claim', 'Never')}\n"
            f"Email: {user_data.get('email', 'Not set')}\n"
            f"Banned: {user_data.get('banned', False)}"
        )
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in user_stats: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def get_current_time():
    """Get current UTC time in YYYY-MM-DD HH:MM:SS format"""
    return datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

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
        if not await check_channel_membership(update, context):
            await update.message.reply_text("🛑 Please join our channels first!")
            return

        user_id = str(update.effective_user.id)
        bot_info = await context.bot.get_me()
        bot_username = bot_info.username
        referral_link = f"https://t.me/{bot_username}?start={user_id}"

        message = (
            "👥 Refer & Earn Program\n\n"
            "🎁 Rewards:\n"
            "• You get 10 points for each referral\n"
            "• Your referral gets 5 points\n\n"
            "📊 Your Stats:\n"
            f"• Total Referrals: {users[user_id].get('referrals', 0)}\n"
            f"• Points Earned: {users[user_id].get('points', 0)}\n\n"
            "🔗 Your Referral Link:\n"
            f"{referral_link}\n\n"
            "Share this link with your friends to earn points! 🚀"
        )
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in refer_earn: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

async def my_points(update: Update, context: CallbackContext):
    try:
        if not await check_channel_membership(update, context):
            await update.message.reply_text("🛑 Please join our channels first!")
            return

        user_id = str(update.effective_user.id)
        user_data = users.get(user_id, {"points": 0, "referrals": 0})
        
        message = (
            "💰 Points Dashboard\n\n"
            f"📊 Current Balance: {user_data.get('points', 0)} points\n"
            f"👥 Total Referrals: {user_data.get('referrals', 0)}\n"
            f"🎁 Rewards Claimed: {user_data.get('rewards_claimed', 0)}\n\n"
            "📈 Ways to Earn More:\n"
            "• Daily Check-in: +5 points\n"
            "• Referral Bonus: +10 points\n"
            "• Complete Tasks: Various points"
        )
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in my_points: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

async def leaderboard(update: Update, context: CallbackContext):
    try:
        if not await check_channel_membership(update, context):
            await update.message.reply_text("🛑 Please join our channels first!")
            return

        # Sort users by points
        sorted_users = sorted(
            users.items(),
            key=lambda x: x[1].get('points', 0),
            reverse=True
        )[:10]  # Top 10 users

        message = "🏆 Top 10 Leaderboard\n\n"
        
        for idx, (user_id, user_data) in enumerate(sorted_users, 1):
            try:
                user = await context.bot.get_chat(user_id)
                name = user.first_name
            except:
                name = f"User{user_id[:4]}"
            
            message += (
                f"{idx}. {name}\n"
                f"   💰 Points: {user_data.get('points', 0)}\n"
                f"   👥 Referrals: {user_data.get('referrals', 0)}\n\n"
            )
        
        current_user_id = str(update.effective_user.id)
        # Find user's rank
        user_rank = next((idx for idx, (uid, _) in enumerate(sorted_users, 1) 
                         if uid == current_user_id), None)
        
        if user_rank:
            message += f"Your Rank: #{user_rank}"
        else:
            message += "You're not on the leaderboard yet! Keep earning points! 💪"
            
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in leaderboard: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

async def help_command(update: Update, context: CallbackContext):
    try:
        message = (
            "🔰 Bot Commands & Help\n\n"
            "🎯 Available Commands:\n"
            "/start - Start the bot\n"
            "/daily - Claim daily reward\n"
            "/points - Check your points\n"
            "/refer - Get referral link\n"
            "/leaderboard - View top users\n"
            "/help - Show this help message\n\n"
            "💡 Tips:\n"
            "• Join our channels to use the bot\n"
            "• Claim daily rewards every 24h\n"
            "• Refer friends to earn more\n"
            "• Complete tasks for points\n\n"
            "⚠️ Note: Attempting to abuse the system will result in a ban.\n\n"
            "📞 Support: Contact @adminsupport for help"
        )
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

async def handle_message(update: Update, context: CallbackContext):
    try:
        if not update.message or not update.message.text:
            return

        text = update.message.text
        user_id = str(update.effective_user.id)

        if user_id in users and users[user_id].get("banned", False):
            await update.message.reply_text("❌ You are banned from using this bot.")
            return

        if text == "👥 Refer & Earn":
            await refer_earn(update, context)
        elif text == "💰 My Points":
            await my_points(update, context)
        elif text == "🎁 Claim Reward":
            await claim_reward(update, context)
        elif text == "🏆 Leaderboard":
            await leaderboard(update, context)
        elif text == "📅 Daily Reward":
            await check_daily_reward(update, context)
        elif text == "ℹ️ Help":
            await help_command(update, context)
        elif text == "✅ Join Channels" or text == "🔄 Check Again":
            await start(update, context)
        else:
            # Handle email submission if awaiting
            if users[user_id].get("awaiting_email", False):
                if is_valid_email(text):
                    users[user_id]["email"] = text
                    users[user_id]["awaiting_email"] = False
                    users[user_id]["points"] = users[user_id].get("points", 0) + 10
                    save_data()
                    await update.message.reply_text(
                        "✅ Email verified successfully!\n"
                        "+10 points added to your account! 🎁"
                    )
                else:
                    await update.message.reply_text(
                        "❌ Invalid email format.\n"
                        "Please enter a valid email address."
                    )

    except Exception as e:
        logger.error(f"Error in message handler: {str(e)}")
        await update.message.reply_text("❌ An error occurred.")

async def claim_reward(update: Update, context: CallbackContext):
    try:
        if not await check_channel_membership(update, context):
            await update.message.reply_text("🛑 Please join our channels first!")
            return

        user_id = str(update.effective_user.id)
        user_data = users.get(user_id, {})
        points = user_data.get("points", 0)

        # Define rewards with their point costs
        rewards = {
            "1": {"name": "10 USDT", "cost": 1000},
            "2": {"name": "5 USDT", "cost": 500},
            "3": {"name": "2 USDT", "cost": 200},
            "4": {"name": "1 USDT", "cost": 100}
        }

        if not context.args:
            # Show available rewards
            message = "🎁 Available Rewards:\n\n"
            for reward_id, reward in rewards.items():
                message += (
                    f"{reward_id}. {reward['name']}\n"
                    f"   Cost: {reward['cost']} points\n\n"
                )
            message += (
                f"Your Points: {points}\n\n"
                "To claim a reward, use:\n"
                "/claim <reward_number>"
            )
            await update.message.reply_text(message)
            return

        # Handle reward claim
        reward_id = context.args[0]
        if reward_id not in rewards:
            await update.message.reply_text("❌ Invalid reward number!")
            return

        reward = rewards[reward_id]
        if points < reward["cost"]:
            await update.message.reply_text(
                f"❌ Insufficient points!\n"
                f"Required: {reward['cost']}\n"
                f"Your points: {points}"
            )
            return

        # Check if user has email
        if not user_data.get("email"):
            users[user_id]["awaiting_email"] = True
            save_data()
            await update.message.reply_text(
                "📧 Please enter your email address to receive the reward.\n"
                "Your email will be used only for reward distribution."
            )
            return

        # Process reward
        users[user_id]["points"] = points - reward["cost"]
        users[user_id]["rewards_claimed"] = users[user_id].get("rewards_claimed", 0) + 1
        save_data()

        # Notify admin
        if ADMIN_ID:
            admin_message = (
                f"🎁 New Reward Claim!\n\n"
                f"User ID: {user_id}\n"
                f"Reward: {reward['name']}\n"
                f"Email: {users[user_id]['email']}\n"
                f"Current Date and Time (UTC - YYYY-MM-DD HH:MM:SS formatted): {get_current_time()}\n"
                f"Current User's Login: syedmoin-ms"
            )
            try:
                await context.bot.send_message(chat_id=ADMIN_ID, text=admin_message)
            except Exception as e:
                logger.error(f"Failed to notify admin: {e}")

        await update.message.reply_text(
            f"🎉 Congratulations!\n\n"
            f"You've claimed: {reward['name']}\n"
            f"Points spent: {reward['cost']}\n"
            f"Remaining points: {users[user_id]['points']}\n\n"
            f"Reward will be sent to: {users[user_id]['email']}\n"
            "Please allow 24-48 hours for processing."
        )

    except Exception as e:
        logger.error(f"Error in claim_reward: {str(e)}")
        await update.message.reply_text("❌ An error occurred while claiming reward.")

def main():
    try:
        # Initialize application with your bot token
        application = Application.builder().token(TOKEN).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("daily", check_daily_reward))
        application.add_handler(CommandHandler("refer", refer_earn))
        application.add_handler(CommandHandler("points", my_points))
        application.add_handler(CommandHandler("leaderboard", leaderboard))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("claim", claim_reward))

        # Add admin command handlers
        application.add_handler(CommandHandler("admin", admin_panel))
        application.add_handler(CommandHandler("broadcast", broadcast_message))
        application.add_handler(CommandHandler("points", edit_points))
        application.add_handler(CommandHandler("ban", ban_user))
        application.add_handler(CommandHandler("unban", unban_user))
        application.add_handler(CommandHandler("stats", user_stats))
        application.add_handler(CommandHandler("send", send_user_message))

        # Add message handler
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Log startup
        logger.info("Bot started successfully!")
        
        # Start the bot
        application.run_polling(allowed_updates=Update.ALL_TYPES)

    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Critical error: {str(e)}")
        traceback.print_exc()
        sys.exit(1)
