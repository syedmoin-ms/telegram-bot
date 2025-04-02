from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, filters, CallbackContext
)
import json
import os
import logging
import datetime
import re

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 🔹 Bot Token & Channel Details
TOKEN = "1708811576:AAH83NPPqGkdswHHmK7QC6JxOkwsjIhhu6U"
REQUIRED_CHANNELS = ["@fampayearningapp", "@grassnodepayairdrop"]
CHANNEL_LINKS = {
    "@fampayearningapp": "https://t.me/fampayearningapp",
    "@grassnodepayairdrop": "https://t.me/grassnodepayairdrop"
}
ADMIN_ID = 848533788

# 🔹 File for storing user data
DATA_FILE = "users.json"

# Load user data
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r") as f:
        users = json.load(f)
else:
    users = {}

def save_data():
    with open(DATA_FILE, "w") as f:
        json.dump(users, f, indent=4)

async def check_daily_reward(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    today = str(datetime.date.today())

    if user_id not in users:
        return

    if "last_daily_claim" not in users[user_id]:
        users[user_id]["last_daily_claim"] = ""

    if users[user_id]["last_daily_claim"] != today:
        reward_points = 5  # Changed from 10 to 5
        users[user_id]["points"] += reward_points
        users[user_id]["last_daily_claim"] = today
        save_data()
        await update.message.reply_text(f"🎁 Daily Reward Claimed!\n+{reward_points} points!")
    else:
        await update.message.reply_text("❌ You've already claimed your daily reward today.\nCome back tomorrow!")
async def is_user_in_channel(user_id, app):
    try:
        chat_member = await app.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=int(user_id))
        logger.info(f"User {user_id} membership status: {chat_member.status}")
        return chat_member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking channel membership: {str(e)}")
        return False

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton

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

        # Handle referral
        if context.args and context.args[0]:
            referrer_id = context.args[0]
            if referrer_id in users and referrer_id != user_id:
                if "referral_clicks" not in users[user_id]:
                    users[user_id]["referral_clicks"] = 1
                    users[user_id]["referrer_id"] = referrer_id
                    await update.message.reply_text(
                        "🔄 First click registered! Please click the referral link again to confirm."
                    )
                elif users[user_id]["referral_clicks"] == 1 and users[user_id]["referrer_id"] == referrer_id:
                    # Give points to new user
                    users[user_id]["points"] = users[user_id].get("points", 0) + 5

                    # Update referrer's data
                    if referrer_id not in users:
                        users[referrer_id] = {"points": 10, "referrals": 1, "email": "", "rewards_claimed": 0}
                    else:
                        users[referrer_id]["points"] = users[referrer_id].get("points", 0) + 10
                        users[referrer_id]["referrals"] = users[referrer_id].get("referrals", 0) + 1

                    # Send confirmation to new user
                    referrer_name = (await context.bot.get_chat(referrer_id)).first_name
                    await update.message.reply_text(
                        f"🎉 Congratulations! You've been referred by {referrer_name}!\n\n"
                        f"You received: +5 points 🎁\n"
                        f"Current balance: {users[user_id]['points']} points\n\n"
                        f"Start earning by sharing your referral link! 🔗",
                        parse_mode='Markdown'
                    )

                    # Send confirmation to referrer
                    new_user_name = update.effective_user.first_name
                    await context.bot.send_message(
                        chat_id=referrer_id,
                        text=f"🎉 Congratulations! New Referral Success!\n\n"
                            f"User: {new_user_name}\n"
                            f"You received: +10 points 🎁\n"
                            f"Total referrals: {users[referrer_id]['referrals']}\n"
                            f"Current balance: {users[referrer_id]['points']} points",
                        parse_mode='Markdown'
                    )
                    save_data()

        # Initialize user data if new
        if user_id not in users:
            users[user_id] = {
                "points": 0,
                "referrals": 0,
                "email": "",
                "rewards_claimed": 0,
                "awaiting_email": False
            }
            save_data()

        # Create keyboard with main options
        keyboard = [
            [KeyboardButton("👥 Refer & Earn"), KeyboardButton("💰 My Points")],
            [KeyboardButton("🎁 Claim Reward"), KeyboardButton("🏆 Leaderboard")],
            [KeyboardButton("📅 Daily Reward"), KeyboardButton("🔥 Midas RWA Task")],
            [KeyboardButton("ℹ️ Help")]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        # Send welcome message with buttons
        await update.message.reply_text(
            f"👋 Welcome {user_name}!\n\n"
            f"📊 Points: {users[user_id]['points']}\n"
            f"👥 Referrals: {users[user_id]['referrals']}\n\n"
            "Choose an option from the menu below:",
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error in start command: {str(e)}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def refer_earn(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    bot = await context.bot.get_me()
    referral_link = f"https://t.me/{bot.username}?start={user_id}"
    await update.message.reply_text(
        f"🔗 Your referral link:\n{referral_link}\n\n"
        "Share this link with your friends. You'll get points when they join!"
    )

async def my_points(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    user_data = users.get(user_id, {"points": 0, "referrals": 0})
    await update.message.reply_text(
        f"💰 Your Points: {user_data['points']}\n"
        f"👥 Total Referrals: {user_data['referrals']}"
    )

async def claim_reward(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    user_data = users.get(user_id, {"points": 0})

    if user_data["points"] < 100:
        await update.message.reply_text(
            "❌ You need at least 100 points to claim a reward!\n"
            f"Current points: {user_data['points']}"
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

async def leaderboard(update: Update, context: CallbackContext):
    # Sort users by referrals
    sorted_users = sorted(users.items(), key=lambda x: x[1]['referrals'], reverse=True)

    # Create leaderboard message
    message = "🏆 Top Referrers:\n\n"
    for i, (user_id, data) in enumerate(sorted_users[:10], 1):
        try:
            user = await context.bot.get_chat(user_id)
            name = user.first_name
        except:
            name = f"User{user_id[:4]}"
        message += f"{i}. {name}: {data['referrals']} referrals\n"

    await update.message.reply_text(message)

async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "ℹ️ Bot Help:\n\n"
        "1. Join our channel\n"
        "2. Share your referral link\n"
        "3. Earn points when friends join\n"
        "4. Claim rewards at 100 points\n\n"
        "For support: @admin"
    )

async def handle_text(update: Update, context: CallbackContext):
    text = update.message.text
    user_id = str(update.effective_user.id)

    # Handle Midas RWA referral verification
    if "MidasRWA_bot/app?startapp=ref_" in text:
        if not users.get(user_id, {}).get("midas_referral_clicked", False):
            users[user_id]["midas_referral_clicked"] = True
            save_data()
            await update.message.reply_text(
                "✅ First click on Midas RWA referral registered!\n"
                "Please click the link again to confirm your participation."
            )
        else:
            users[user_id]["points"] += 15  # Reward for completing Midas task
            users[user_id]["midas_referral_completed"] = True
            save_data()
            await update.message.reply_text(
                "🎉 Congratulations! You've completed the Midas RWA task.\n"
                "15 points have been added to your account!"
            )
        return

    if text == "✅ Join Channel":
        await update.message.reply_text(
            "🌟 Welcome to our Earning Community! 🌟\n\n"
            "Join our official channel to:\n"
            "• Get instant earning updates\n"
            "• Access exclusive reward opportunities\n"
            "• Stay informed about special bonuses\n\n"
            "Click '🔄 Check Again' after joining to activate your rewards!\n\n"
            "Join now 👉 @fampayearningapp",
            disable_web_page_preview=True
        )
        return
    elif text == "🔄 Check Again":
        if await check_channel_membership(update, context):
            await start(update, context)
        else:
            await update.message.reply_text(
                f"❌ You haven't joined {CHANNEL_LINK} yet.\n"
                "Please join and try again."
            )
        return

    # Verify channel membership for all commands
    if not await check_channel_membership(update, context):
        await update.message.reply_text(
            f"❗️ Please join our channel {CHANNEL_LINK} to use this bot."
        )
        return

    # Check if user is banned
    if users.get(user_id, {}).get("banned", False):
        await update.message.reply_text("🚫 You are banned from using this bot.")
        return

    # Handle email input for reward claim
    if users.get(user_id, {}).get("awaiting_email", False):
        await claim_reward(update, context)
        return

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

    # Admin panel options
    elif user_id == str(ADMIN_ID):
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

async def error_handler(update: Update, context: CallbackContext) -> None:
    logger.error(f"Exception while handling an update: {context.error}")

def main():
    try:
        # Create application
        app = Application.builder().token(TOKEN).build()

        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
        app.add_handler(CommandHandler("help", help_command))

        # Admin handlers
        app.add_handler(CommandHandler("admin", admin_panel))
        app.add_handler(CommandHandler("broadcast", broadcast_message))
        app.add_handler(CommandHandler("ban", ban_user))
        app.add_handler(CommandHandler("unban", unban_user))
        app.add_handler(CommandHandler("points", edit_points))
        app.add_handler(CommandHandler("stats", user_stats))
