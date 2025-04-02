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
            "• Referral Bonus (You): +10 points\n"
            "• Referral Bonus (Friend): +5 points\n"
            "• Daily Reward: +5 points\n"
            "• Task Completion: +15 points\n\n"
            "💰 Rewards:\n"
            "• 100 points = 1 Reward claim\n\n"
            "🔥 How to earn more:\n"
            "• Share your referral link\n"
            "• Complete daily check-in\n"
            "• Participate in tasks\n"
            "• Stay active in channels\n\n"
            "For support: @admin"
        )
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

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
    except Exception as e:
        logger.error(f"Error saving data: {str(e)}")

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

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
                "last_daily_claim": ""
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

        # Add admin panel button for admin
        if str(update.effective_user.id) == str(ADMIN_ID):
            keyboard.append([KeyboardButton("🔐 Admin Panel")])

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

async def check_daily_reward(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        today = str(datetime.date.today())

        if user_id not in users:
            users[user_id] = {
                "points": 0,
                "referrals": 0,
                "email": "",
                "rewards_claimed": 0,
                "last_daily_claim": "",
                "awaiting_email": False
            }

        if users[user_id]["last_daily_claim"] != today:
            reward_points = 5
            users[user_id]["points"] = users[user_id].get("points", 0) + reward_points
            users[user_id]["last_daily_claim"] = today
            save_data()
            await update.message.reply_text(f"🎁 Daily Reward Claimed!\n+{reward_points} points!")
        else:
            await update.message.reply_text("❌ You've already claimed your daily reward today.\nCome back tomorrow!")
    except Exception as e:
        logger.error(f"Error in daily reward: {str(e)}")
        await update.message.reply_text("❌ An error occurred while claiming daily reward.")

# Admin Commands
async def admin_panel(update: Update, context: CallbackContext):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ Access denied!")
        return

    keyboard = [
        [KeyboardButton("📢 Broadcast"), KeyboardButton("🚫 Ban User")],
        [KeyboardButton("✅ Unban User"), KeyboardButton("💰 Edit Points")],
        [KeyboardButton("📊 User Stats"), KeyboardButton("👥 View Users")],
        [KeyboardButton("🔙 Back")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("🔐 Admin Panel:", reply_markup=reply_markup)

async def broadcast_message(update: Update, context: CallbackContext):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    message = ' '.join(context.args)
    success_count = 0

    for user_id in users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
            success_count += 1
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {str(e)}")

    await update.message.reply_text(f"✅ Broadcast sent to {success_count} users")

async def ban_user(update: Update, context: CallbackContext):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /ban <user_id>")
        return

    user_id = context.args[0]
    if user_id in users:
        users[user_id]["banned"] = True
        save_data()
        await update.message.reply_text(f"🚫 User {user_id} has been banned")
    else:
        await update.message.reply_text("❌ User not found")

async def unban_user(update: Update, context: CallbackContext):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return

    if len(context.args) == 0:
        await update.message.reply_text("Usage: /unban <user_id>")
        return

    user_id = context.args[0]
    if user_id in users:
        users[user_id]["banned"] = False
        save_data()
        await update.message.reply_text(f"✅ User {user_id} has been unbanned")
    else:
        await update.message.reply_text("❌ User not found")

async def edit_points(update: Update, context: CallbackContext):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return

    if len(context.args) < 2:
        await update.message.reply_text("Usage: /points <user_id> <points>")
        return

    user_id = context.args[0]
    try:
        points = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Points must be a number")
        return

    if user_id in users:
        users[user_id]["points"] = points
        save_data()
        await update.message.reply_text(f"💰 Set {points} points for user {user_id}")
    else:
        await update.message.reply_text("❌ User not found")

async def view_users(update: Update, context: CallbackContext):
    if str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("❌ Access denied!")
        return

    message = "👥 All Users:\n\n"
    for user_id in users:
        user_link = f"[{user_id}](tg://user?id={user_id})"
        points = users[user_id]["points"]
        referrals = users[user_id]["referrals"]
        message += f"• {user_link}\n  Points: {points} | Referrals: {referrals}\n\n"

    await update.message.reply_text(message, parse_mode='Markdown')

async def user_stats(update: Update, context: CallbackContext):
    if str(update.effective_user.id) != str(ADMIN_ID):
        return

    total_users = len(users)
    total_points = sum(user["points"] for user in users.values())
    banned_users = sum(1 for user in users.values() if user.get("banned", False))

    stats = f"📊 Bot Statistics:\n\n" \
           f"👥 Total Users: {total_users}\n" \
           f"💰 Total Points: {total_points}\n" \
           f"🚫 Banned Users: {banned_users}"

    await update.message.reply_text(stats)

async def my_points(update: Update, context: CallbackContext):
    try:
        user_id = str(update.effective_user.id)
        user_data = users.get(user_id, {"points": 0, "referrals": 0})
        
        message = (
            "💰 Your Account Status:\n\n"
            f"• Points Balance: {user_data['points']}\n"
            f"• Total Referrals: {user_data['referrals']}\n"
            f"• Rewards Claimed: {user_data.get('rewards_claimed', 0)}\n\n"
            "🎯 Need more points?\n"
            "• Share your referral link\n"
            "• Complete daily check-in\n"
            "• Participate in tasks"
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
        save_data()

        user_name = update.effective_user.first_name
        user_link = f"[{user_name}](tg://user?id={user_id})"

        # Notify admin
        admin_message = (
            f"🎁 New Reward Claim!\n\n"
            f"User: {user_link}\n"
            f"Email: {email}\n"
            f"Total Claims: {users[user_id]['rewards_claimed']}\n"
            f"Remaining Points: {users[user_id]['points']}"
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
            message += f"{i}. {name}: {data['referrals']} referrals | {data['points']} points\n"

        if len(sorted_users) == 0:
            message += "No users yet!"

        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in leaderboard: {str(e)}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

# Rest of your existing functions (my_points, claim_reward, leaderboard, help_command)
# ... (keep them as they were)

async def handle_text(update: Update, context: CallbackContext):
    try:
        text = update.message.text
        user_id = str(update.effective_user.id)

        # Check if user is banned
        if users.get(user_id, {}).get("banned", False):
            await update.message.reply_text("🚫 You are banned from using this bot.")
            return

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
                save_data()
                await update.message.reply_text(
                    "🎉 Congratulations! You've completed the Midas RWA task.\n"
                    "15 points have been added to your account!"
                )
            return

        # Handle menu options
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
        elif text == "🔄 Check Again":
            if await check_channel_membership(update, context):
                await start(update, context)
            else:
                await update.message.reply_text(
                    "❌ You haven't joined all required channels yet.\n"
                    "Please join and try again."
                )
        elif text == "👥 Refer & Earn":
            await refer_earn(update, context)
        elif text == "💰 My Points":
            await my_points(update, context)
        elif text == "🎁 Claim Reward":
            await claim_reward(update, context)
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
        elif text == "ℹ️ Help":
            await help_command(update, context)
        elif text == "🔐 Admin Panel" and str(user_id) == str(ADMIN_ID):
            await admin_panel(update, context)
        elif text in ["📢 Broadcast", "🚫 Ban User", "✅ Unban User", "💰 Edit Points", "📊 User Stats", "👥 View Users"] and str(user_id) == str(ADMIN_ID):
            if text == "📢 Broadcast":
                await update.message.reply_text("Use /broadcast <message>")
            elif text == "🚫 Ban User":
                await update.message.reply_text("Use /ban <user_id>")
            elif text == "✅ Unban User":
                await update.message.reply_text("Use /unban <user_id>")
            elif text == "💰 Edit Points":
                await update.message.reply_text("Use /points <user_id> <points>")
            elif text == "📊 User Stats":
                await user_stats(update, context)
            elif text == "👥 View Users":
                await view_users(update, context)
        elif text == "🔙 Back":
            await start(update, context)

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
        app.add_handler(CommandHandler("admin", admin_panel))
        app.add_handler(CommandHandler("broadcast", broadcast_message))
        app.add_handler(CommandHandler("ban", ban_user))
        app.add_handler(CommandHandler("unban", unban_user))
        app.add_handler(CommandHandler("points", edit_points))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

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
