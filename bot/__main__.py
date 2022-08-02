from signal import signal, SIGINT
from os import path as ospath, remove as osremove, execl as osexecl
from subprocess import run as srun, check_output
from psutil import disk_usage, cpu_percent, swap_memory, cpu_count, virtual_memory, net_io_counters, boot_time
from time import time
from datetime import datetime
import pytz
from sys import executable
from telegram import InlineKeyboardMarkup
from telegram.ext import CommandHandler

from bot import bot, dispatcher, updater, botStartTime, IGNORE_PENDING_REQUESTS, LOGGER, Interval, INCOMPLETE_TASK_NOTIFIER, DB_URI, alive, app, main_loop, AUTHORIZED_CHATS
from .helper.ext_utils.fs_utils import start_cleanup, clean_all, exit_clean_up
from .helper.ext_utils.telegraph_helper import telegraph
from .helper.ext_utils.bot_utils import get_readable_file_size, get_readable_time
from .helper.ext_utils.db_handler import DbManger
from .helper.telegram_helper.bot_commands import BotCommands
from .helper.telegram_helper.message_utils import sendMessage, sendMarkup, editMessage, sendLogFile
from .helper.telegram_helper.filters import CustomFilters
from .helper.telegram_helper.button_build import ButtonMaker

from .modules import authorize, list, cancel_mirror, mirror_status, mirror, clone, watch, shell, eval, delete, count, leech_settings, search, rss, qbselect


def stats(update, context):
    currentTime = get_readable_time(time() - botStartTime)
    osUptime = get_readable_time(time() - boot_time())
    total, used, free, disk= disk_usage('/')
    total = get_readable_file_size(total)
    used = get_readable_file_size(used)
    free = get_readable_file_size(free)
    sent = get_readable_file_size(net_io_counters().bytes_sent)
    recv = get_readable_file_size(net_io_counters().bytes_recv)
    cpuUsage = cpu_percent(interval=0.5)
    p_core = cpu_count(logical=False)
    t_core = cpu_count(logical=True)
    swap = swap_memory()
    swap_p = swap.percent
    swap_t = get_readable_file_size(swap.total)
    memory = virtual_memory()
    mem_p = memory.percent
    mem_t = get_readable_file_size(memory.total)
    mem_a = get_readable_file_size(memory.available)
    mem_u = get_readable_file_size(memory.used)
    stats = f'<b>╭──《 𝗕ᴏᴛ 𝗦ᴛᴀᴛɪ𝘀ᴛɪᴄ𝘀 》</b>\n' \
            f'<b>│</b>\n' \
            f'<b>|--𝗕𝗼𝘁 𝗨𝗽𝘁𝗶𝗺𝗲:</b> {currentTime}\n'\
            f'<b>|--𝗢𝗦 𝗨𝗽𝘁𝗶𝗺𝗲:</b> {osUptime}\n\n'\
            f'<b>|--𝗧𝗼𝘁𝗮𝗹 𝗗𝗶𝘀𝗸 𝗦𝗽𝗮𝗰𝗲:</b> {total}\n'\
            f'<b>|--𝗨𝘀𝗲𝗱:</b> {used} | <b>𝗙𝗿𝗲𝗲:</b> {free}\n\n'\
            f'<b>|--𝗨𝗽𝗹𝗼𝗮𝗱:</b> {sent}\n'\
            f'<b>|--𝗗𝗼𝘄𝗻𝗹𝗼𝗮𝗱:</b> {recv}\n\n'\
            f'<b>|--𝗖𝗣𝗨:</b> {cpuUsage}%\n'\
            f'<b>|--𝗥𝗔𝗠:</b> {mem_p}%\n'\
            f'<b>|--𝗗𝗜𝗦𝗞:</b> {disk}%\n\n'\
            f'<b>|--𝗣𝗵𝘆𝘀𝗶𝗰𝗮𝗹 𝗖𝗼𝗿𝗲𝘀:</b> {p_core}\n'\
            f'<b>|--𝗧𝗼𝘁𝗮𝗹 𝗖𝗼𝗿𝗲𝘀:</b> {t_core}\n\n'\
            f'<b>|--𝗦𝗪𝗔𝗣:</b> {swap_t} | <b>𝗨𝘀𝗲𝗱:</b> {swap_p}%\n'\
            f'<b>|--𝗠𝗲𝗺𝗼𝗿𝘆 𝗧𝗼𝘁𝗮𝗹:</b> {mem_t}\n'\
            f'<b>|--𝗠𝗲𝗺𝗼𝗿𝘆 𝗙𝗿𝗲𝗲:</b> {mem_a}\n'\
            f'<b>|--𝗠𝗲𝗺𝗼𝗿𝘆 𝗨𝘀𝗲𝗱:</b> {mem_u}\n'
    sendMessage(stats, context.bot, update.message)


def start(update, context):
    buttons = ButtonMaker()
    buttons.buildbutton("PublicLeechCloneGroup", "t.me/PublicLeechCloneGroup")
    reply_markup = InlineKeyboardMarkup(buttons.build_menu(2))
    if CustomFilters.authorized_user(update) or CustomFilters.authorized_chat(update):
        start_string = f'''
This bot can be used only in group!
Type /{BotCommands.HelpCommand} to get a list of available commands
'''
        sendMarkup(start_string, context.bot, update.message, reply_markup)
    else:
        sendMarkup('Not an Authorized User', context.bot, update.message, reply_markup)

def restart(update, context):
    restart_message = sendMessage("Restarting...", context.bot, update.message)
    if Interval:
        Interval[0].cancel()
        Interval.clear()
    alive.kill()
    clean_all()
    srun(["pkill", "-9", "-f", "gunicorn|extra-api|last-api|megasdkrest|new-api"])
    srun(["python3", "update.py"])
    with open(".restartmsg", "w") as f:
        f.truncate(0)
        f.write(f"{restart_message.chat.id}\n{restart_message.message_id}\n")
    osexecl(executable, executable, "-m", "bot")


def ping(update, context):
    start_time = int(round(time() * 1000))
    reply = sendMessage("Starting Ping", context.bot, update.message)
    end_time = int(round(time() * 1000))
    editMessage(f'{end_time - start_time} ms', reply)


def log(update, context):
    sendLogFile(context.bot, update.message)


help_string_telegraph = f'''<br>
<br><br>
<b>/{BotCommands.LeechZipWatchCommand}</b> 𝐋𝐞𝐞𝐜𝐡 𝐭𝐡𝐫𝐨𝐮𝐠𝐡 𝐲𝐭-𝐝𝐥𝐩 𝐚𝐧𝐝 𝐳𝐢𝐩 𝐛𝐞𝐟𝐨𝐫𝐞 𝐮𝐩𝐥𝐨𝐚𝐝𝐢𝐧𝐠
<br><br>
<b>/{BotCommands.LeechSetCommand}</b> 𝐓𝐨 𝐂𝐡𝐞𝐜𝐤 𝐘𝐨𝐮𝐫 𝐂𝐮𝐫𝐫𝐞𝐧𝐭 𝐋𝐞𝐞𝐜𝐡 𝐒𝐞𝐭𝐭𝐢𝐧𝐠𝐬
<br><br>
<b>/{BotCommands.SetThumbCommand}</b> 𝐑𝐞𝐩𝐥𝐲 𝐭𝐨 𝐩𝐡𝐨𝐭𝐨 𝐭𝐨 𝐬𝐞𝐭 𝐢𝐭 𝐚𝐬 𝐭𝐡𝐮𝐦𝐛𝐧𝐚𝐢𝐥 𝐟𝐨𝐫 𝐧𝐞𝐱𝐭 𝐮𝐩𝐥𝐨𝐚𝐝𝐬
<br><br>
<b>/{BotCommands.StatusCommand}</b>: 𝐒𝐡𝐨𝐰𝐬 𝐚 𝐬𝐭𝐚𝐭𝐮𝐬 𝐨𝐟 𝐚𝐥𝐥 𝐭𝐡𝐞 𝐝𝐨𝐰𝐧𝐥𝐨𝐚𝐝𝐬
<br><br>
<b>/{BotCommands.StatsCommand}</b>: 𝐒𝐡𝐨𝐰 𝐒𝐭𝐚𝐭𝐬 𝐨𝐟 𝐭𝐡𝐞 𝐦𝐚𝐜𝐡𝐢𝐧𝐞 𝐭𝐡𝐞 𝐛𝐨𝐭 𝐢𝐬 𝐡𝐨𝐬𝐭𝐞𝐝 𝐨𝐧
'''


help = telegraph.create_page(
        title='PublicLeechCloneGroup',
        content=help_string_telegraph,
    )["path"]

help_string = f'''
/{BotCommands.LeechCommand}: 𝐋𝐞𝐞𝐜𝐡 𝐓𝐨𝐫𝐫𝐞𝐧𝐭/𝐃𝐢𝐫𝐞𝐜𝐭 𝐥𝐢𝐧𝐤

/{BotCommands.ZipLeechCommand}: 𝐋𝐞𝐞𝐜𝐡 𝐓𝐨𝐫𝐫𝐞𝐧𝐭/𝐃𝐢𝐫𝐞𝐜𝐭 𝐥𝐢𝐧𝐤 𝐚𝐧𝐝 𝐮𝐩𝐥𝐨𝐚𝐝 𝐚𝐬 .𝐳𝐢𝐩

/{BotCommands.UnzipLeechCommand}: 𝐋𝐞𝐞𝐜𝐡 𝐓𝐨𝐫𝐫𝐞𝐧𝐭/𝐃𝐢𝐫𝐞𝐜𝐭 𝐥𝐢𝐧𝐤 𝐚𝐧𝐝 𝐞𝐱𝐭𝐫𝐚𝐜𝐭

/{BotCommands.QbLeechCommand}: 𝐋𝐞𝐞𝐜𝐡  𝐓𝐨𝐫𝐫𝐞𝐧𝐭/𝐌𝐚𝐠𝐧𝐞𝐭 𝐮𝐬𝐢𝐧𝐠 𝐪𝐁𝐢𝐭𝐭𝐨𝐫𝐫𝐞𝐧𝐭

/{BotCommands.QbZipLeechCommand}: 𝐋𝐞𝐞𝐜𝐡 𝐓𝐨𝐫𝐫𝐞𝐧𝐭/𝐌𝐚𝐠𝐧𝐞𝐭 𝐚𝐧𝐝 𝐮𝐩𝐥𝐨𝐚𝐝 𝐚𝐬 .𝐳𝐢𝐩 𝐮𝐬𝐢𝐧𝐠 𝐪𝐁𝐭𝐨𝐫𝐫𝐞𝐧𝐭

/{BotCommands.QbUnzipLeechCommand}: 𝐋𝐞𝐞𝐜𝐡 𝐓𝐨𝐫𝐫𝐞𝐧𝐭/𝐃𝐢𝐫𝐞𝐜𝐭 𝐥𝐢𝐧𝐤 𝐚𝐧𝐝 𝐞𝐱𝐭𝐫𝐚𝐜𝐭 𝐮𝐬𝐢𝐧𝐠 𝐪𝐁𝐭𝐨𝐫𝐫𝐞𝐧𝐭

/{BotCommands.LeechWatchCommand}: 𝐋𝐞𝐞𝐜𝐡 𝐭𝐡𝐫𝐨𝐮𝐠𝐡 𝐲𝐭-𝐝𝐥𝐩 𝐬𝐮𝐩𝐩𝐨𝐫𝐭𝐞𝐝 𝐥𝐢𝐧𝐤 𝐚𝐧𝐝 𝐔𝐩𝐥𝐨𝐚𝐝 𝐭𝐨 𝐓𝐞𝐥𝐞𝐠𝐫𝐚𝐦

/{BotCommands.CancelMirror}: 𝐑𝐞𝐩𝐥𝐲 𝐭𝐨 𝐭𝐡𝐞 𝐦𝐞𝐬𝐬𝐚𝐠𝐞 𝐛𝐲 𝐰𝐡𝐢𝐜𝐡 𝐭𝐡𝐞 𝐝𝐨𝐰𝐧𝐥𝐨𝐚𝐝 𝐰𝐚𝐬 𝐢𝐧𝐢𝐭𝐢𝐚𝐭𝐞𝐝 𝐚𝐧𝐝 𝐭𝐡𝐚𝐭 𝐝𝐨𝐰𝐧𝐥𝐨𝐚𝐝 𝐰𝐢𝐥𝐥 𝐛𝐞 𝐜𝐚𝐧𝐜𝐞𝐥𝐥𝐞𝐝
'''

def bot_help(update, context):
    button = ButtonMaker()
    button.buildbutton("Other Commands", f"https://telegra.ph/{help}")
    reply_markup = InlineKeyboardMarkup(button.build_menu(1))
    sendMarkup(help_string, context.bot, update.message, reply_markup)

def main():
    start_cleanup()
    notifier_dict = None
    if INCOMPLETE_TASK_NOTIFIER and DB_URI is not None:
        notifier_dict = DbManger().get_incomplete_tasks()
        if notifier_dict:
            for cid, data in notifier_dict.items():
                if ospath.isfile(".restartmsg"):
                    with open(".restartmsg") as f:
                        chat_id, msg_id = map(int, f)
                    msg = 'Restarted Successfully!'
                else:
                    kek = datetime.now(pytz.timezone(f'Asia/Kolkata'))
                    vro = kek.strftime('\n 𝗗𝗮𝘁𝗲 : %d/%m/%Y\n 𝗧𝗶𝗺𝗲: %I:%M%P')
                    msg = f" 𝐁𝐎𝐓 𝐑𝐄𝐒𝐓𝐀𝐑𝐓𝐄𝐃 \n{vro}\n\n#Restarted"
                    msg2 = f" 𝐁𝐎𝐓 𝐑𝐄𝐒𝐓𝐀𝐑𝐓𝐄𝐃 \n{vro}\n\n#Restarted"
                for tag, links in data.items():
                     msg += f"\n\n💀 {tag}: "
                     for index, link in enumerate(links, start=1):
                         msg += f" <a href='{link}'>{index}</a> |"
                         if len(msg.encode()) > 4000:
                             if 'Restarted Successfully!' in msg and cid == chat_id:
                                 bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTMl', disable_web_page_preview=True)
                                 osremove(".restartmsg")
                             else:
                                 try:
                                     bot.sendMessage(cid, msg, 'HTML', disable_web_page_preview=True)
                                 except Exception as e:
                                     LOGGER.error(e)
                             msg = ''
                if 'Restarted Successfully!' in msg and cid == chat_id:
                     bot.editMessageText(msg, chat_id, msg_id, parse_mode='HTMl', disable_web_page_preview=True)
                     osremove(".restartmsg")
                else:
                    try:
                        bot.sendMessage(cid, msg, 'HTML', disable_web_page_preview=True)
                    except Exception as e:
                        LOGGER.error(e)

    if ospath.isfile(".restartmsg"):
        with open(".restartmsg") as f:
            chat_id, msg_id = map(int, f)
        bot.edit_message_text("Restarted Successfully!", chat_id, msg_id)
        osremove(".restartmsg")
    elif not notifier_dict and AUTHORIZED_CHATS:
        for id_ in AUTHORIZED_CHATS:
            try:
                bot.sendMessage(id_, msg2, 'HTML')
            except Exception as e:
                LOGGER.error(e)

    start_handler = CommandHandler(BotCommands.StartCommand, start, run_async=True)
    ping_handler = CommandHandler(BotCommands.PingCommand, ping,
                                  filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    restart_handler = CommandHandler(BotCommands.RestartCommand, restart,
                                     filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    help_handler = CommandHandler(BotCommands.HelpCommand,
                                  bot_help, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    stats_handler = CommandHandler(BotCommands.StatsCommand,
                                   stats, filters=CustomFilters.authorized_chat | CustomFilters.authorized_user, run_async=True)
    log_handler = CommandHandler(BotCommands.LogCommand, log, filters=CustomFilters.owner_filter | CustomFilters.sudo_user, run_async=True)
    dispatcher.add_handler(start_handler)
    dispatcher.add_handler(ping_handler)
    dispatcher.add_handler(restart_handler)
    dispatcher.add_handler(help_handler)
    dispatcher.add_handler(stats_handler)
    dispatcher.add_handler(log_handler)
    updater.start_polling(drop_pending_updates=IGNORE_PENDING_REQUESTS)
    LOGGER.info("Bot Started!")
    signal(SIGINT, exit_clean_up)

app.start()
main()

main_loop.run_forever()
