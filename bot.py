# - *- coding: utf- 8 - *-

import os
import re
import shutil
import telebot
import urllib.request
from PIL import Image, ImageFilter

TOKEN = '1153877647:AAHGv4z9mbyKAGadNZCrMNY_oodLq4Y7WQA'
bot = telebot.TeleBot(TOKEN)

RESULT_STORAGE_DIR = 'temp'
PARAMS = dict()


def get_image_id_from_message(message):
    return message.photo[len(message.photo) - 1].file_id


def save_image_from_message(message):
    image_id = get_image_id_from_message(message)

    file_path = bot.get_file(image_id).file_path

    image_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"

    image_name = f"{image_id}.png"
    urllib.request.urlretrieve(image_url, f"{RESULT_STORAGE_DIR}/{image_name}")
    return image_name


def cleanup_remove_images(image_name, image_name_new):
    os.remove(f'{RESULT_STORAGE_DIR}/{image_name}')
    os.remove(f'{RESULT_STORAGE_DIR}/{image_name_new}')


def clear_chat_info(chat_id):
    PARAMS[chat_id] = None


def get_image_capture_params(message):
    caption = message.caption

    if caption is not None:
        parsed_params = [param.strip() for param in re.split(r'\W+', caption.strip())]

        if len(parsed_params) == 2:
            params = dict()
            params['rgbmax'] = int(parsed_params[0]) if parsed_params[0].isdigit() and 0 <= int(
                parsed_params[0]) <= 255 else None
            params['rgbmin'] = int(parsed_params[-1]) if parsed_params[-1].isdigit() and 0 <= int(
                parsed_params[-1]) <= 255 else None
            if not None in [params['rgbmax'], params['rgbmin']]:
                return params

        bot.send_message(chat_id=message.chat.id, text=f'Извини, но я не знаю такого'
                                                       f'\nИспользуй комманду /help, чтобы узнать как работаю я')
    return None


def filter_image(image_name, params):
    content_image = Image.open(f"{RESULT_STORAGE_DIR}/{image_name}")

    rgbmax = params['rgbmax']
    rgbmin = params['rgbmin']

    R, G, B = content_image.split()

    rout = R.point(lambda i: (i - rgbmin) / (rgbmax - rgbmin) * 255)
    gout = G.point(lambda i: (i - rgbmin) / (rgbmax - rgbmin) * 255)
    bout = B.point(lambda i: (i - rgbmin) / (rgbmax - rgbmin) * 255)

    result_img_pillow = Image.merge("RGB", (rout, gout, bout))
    image_name_new = "handled_image_" + image_name
    result_img_pillow.save(f"{RESULT_STORAGE_DIR}/{image_name_new}")
    return image_name_new


def process_image(message, image_name, params):
    contrast_image_filename = filter_image(image_name, params=params)

    bot.send_message(chat_id=message.chat.id, text='Я почти закончил, скоро будет готово! 🤔')
    bot.send_photo(message.chat.id, open(f'{RESULT_STORAGE_DIR}/{contrast_image_filename}', 'rb'),
                   caption=f'✅ Я успешно обработал изображение по значениям:\nПервое: {params["rgbmax"]}'
                           f'\nВторое: {params["rgbmin"]}')
    bot.send_message(chat_id=message.chat.id,
                     text='''Мне понравилось с тобой работать! Отправь мне еще фото, чтобы обработать его. 👍
                           \nКстати, в следующий раз можешь с фото сразу прикрепить желаемые тобой значения.
                           \nК примеру, в формате <b>240 10</b>''', parse_mode='html')

    cleanup_remove_images(image_name, contrast_image_filename)


@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, '''<b>Я тебя приветствую!</b> 
    \nЯ бот, который обрабатывает изображения! 🎆
    \nЕсли хочешь, чтобы я работал - отправь мне изображение.
    \nОбязательно воспользуйся командой /help, чтобы понять как работаю я''', parse_mode='html')


@bot.message_handler(commands=['help'])
def help_handler(message):
    bot.send_message(message.chat.id, '''<b>Как я работаю?</b>
    \n💪 У меня есть уже навыки в обработки фотографий, поэтому я тебе предлагаю выбрать вариант контраста. Следуя
    подсказкам, я тебя попрошу после загрузки фото выбрать число <b>от 1 до 10</b>. 1 - это самый слабый контраст, а 10 
    - наиболее сильный.
    \nПоэтому пробуй и выбирай то, что тебе понравится! Загружай изображение, мне уже не терпится начать работать!''',
                     parse_mode='html')
    bot.send_message(message.chat.id, '''Кстати, если ты уже опытный пользователь, то могу тебе предложить 
    самостоятельно выбрать значения, с помощью которых я обработаю твое изображение! 
    \nДля этого тебе необходимо, при отправке фотографии, в подписи к ней указать желаемые значения. К примеру, это
    должно быть в виде "<b>240 15</b>" (без кавычек). 
    \n❗️Помни, что чем больше разница между 1-м и 2-м значением, тем слабее контраст! И первое значение должно быть
    больше, чем второе! 
    \nВот тебе пример введенных значений и какой от них эффект:''', parse_mode='html')
    bot.send_photo(message.chat.id, 'http://i.piccy.info/i9/9e05fca3c86c85f20404e6bc3c21d7f9/1590874914/170052/1381121/gaid_1.jpg')


@bot.message_handler(content_types=['text'])
def handle_text(message):
    cid = message.chat.id

    if PARAMS.get(cid) is not None:
        if message.text.isdigit():
            number = int(message.text)
            if number == 1:
                if PARAMS[cid].get('rgbmax') is None:
                    if PARAMS[cid].get('rgbmin') is None:
                        PARAMS[cid]['rgbmax'] = 240
                        PARAMS[cid]['rgbmin'] = 15
                        bot.send_message(chat_id=cid, text='Хорошо, выбираю первый фильтр. ✅')
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    else:
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                        clear_chat_info(cid)
                else:
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
            elif number == 2:
                if PARAMS[cid].get('rgbmax') is None:
                    if PARAMS[cid].get('rgbmin') is None:
                        PARAMS[cid]['rgbmax'] = 230
                        PARAMS[cid]['rgbmin'] = 25
                        bot.send_message(chat_id=cid, text='Хорошо, выбираю второй фильтр. ✅')
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    else:
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                        clear_chat_info(cid)
                else:
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
            elif number == 3:
                if PARAMS[cid].get('rgbmax') is None:
                    if PARAMS[cid].get('rgbmin') is None:
                        PARAMS[cid]['rgbmax'] = 220
                        PARAMS[cid]['rgbmin'] = 35
                        bot.send_message(chat_id=cid, text='Хорошо, выбираю третий фильтр. ✅')
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    else:
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                        clear_chat_info(cid)
                else:
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
            elif number == 4:
                if PARAMS[cid].get('rgbmax') is None:
                    if PARAMS[cid].get('rgbmin') is None:
                        PARAMS[cid]['rgbmax'] = 210
                        PARAMS[cid]['rgbmin'] = 45
                        bot.send_message(chat_id=cid, text='Хорошо, выбираю четвертый фильтр. ✅')
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    else:
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                        clear_chat_info(cid)
                else:
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
            elif number == 5:
                if PARAMS[cid].get('rgbmax') is None:
                    if PARAMS[cid].get('rgbmin') is None:
                        PARAMS[cid]['rgbmax'] = 200
                        PARAMS[cid]['rgbmin'] = 55
                        bot.send_message(chat_id=cid, text='ЗХорошо, выбираю пятый фильтр. ✅')
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    else:
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                        clear_chat_info(cid)
                else:
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
            elif number == 6:
                if PARAMS[cid].get('rgbmax') is None:
                    if PARAMS[cid].get('rgbmin') is None:
                        PARAMS[cid]['rgbmax'] = 190
                        PARAMS[cid]['rgbmin'] = 65
                        bot.send_message(chat_id=cid, text='Хорошо, выбираю шестой фильтр. ✅')
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    else:
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                        clear_chat_info(cid)
                else:
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
            elif number == 7:
                if PARAMS[cid].get('rgbmax') is None:
                    if PARAMS[cid].get('rgbmin') is None:
                        PARAMS[cid]['rgbmax'] = 180
                        PARAMS[cid]['rgbmin'] = 75
                        bot.send_message(chat_id=cid, text='Хорошо, выбираю седьмой фильтр. ✅')
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    else:
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                        clear_chat_info(cid)
                else:
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
            elif number == 8:
                if PARAMS[cid].get('rgbmax') is None:
                    if PARAMS[cid].get('rgbmin') is None:
                        PARAMS[cid]['rgbmax'] = 170
                        PARAMS[cid]['rgbmin'] = 85
                        bot.send_message(chat_id=cid, text='Хорошо, выбираю восьмой фильтр. ✅')
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    else:
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                        clear_chat_info(cid)
                else:
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
            elif number == 9:
                if PARAMS[cid].get('rgbmax') is None:
                    if PARAMS[cid].get('rgbmin') is None:
                        PARAMS[cid]['rgbmax'] = 160
                        PARAMS[cid]['rgbmin'] = 95
                        bot.send_message(chat_id=cid, text='Хорошо, выбираю девятый фильтр. ✅')
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    else:
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                        clear_chat_info(cid)
                else:
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
            elif number == 10:
                if PARAMS[cid].get('rgbmax') is None:
                    if PARAMS[cid].get('rgbmin') is None:
                        PARAMS[cid]['rgbmax'] = 150
                        PARAMS[cid]['rgbmin'] = 100
                        bot.send_message(chat_id=cid, text='Хорошо, выбираю десятый фильтр. ✅')
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    else:
                        process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                        clear_chat_info(cid)
                else:
                    process_image(message, image_name=PARAMS[cid]['image'], params=PARAMS[cid])
                    clear_chat_info(cid)
            else:
                bot.send_message(chat_id=cid, text='Немного неправильно, от 1 до 10, будь добр.')
        else:
            bot.send_message(chat_id=cid, text='Извини, но эти символы неизвестны мне. Введи значение, пожалуйста.')
    else:
        bot.send_message(chat_id=cid, text='Прости, но загрузи любое изображение, я с удовольствием обработаю его')


@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    cid = message.chat.id

    image_name = save_image_from_message(message)
    bot.send_message(chat_id=cid, text='Отлично, сохранил я изображение твоё!')

    params = get_image_capture_params(message)

    if params is not None:
        bot.send_message(chat_id=message.chat.id, text='Получена информация.\nОбрабатываю... 🤔')
        params['image'] = image_name

        process_image(message, image_name, params)
    else:
        PARAMS[cid] = {
            'image': image_name
        }
        bot.send_photo(message.chat.id, 'http://i.piccy.info/i9/d615b19399a0268a7aa26bc7e9fbf6ac/1590928883/222137/1381121/gaid_2.jpg',
                       'Хорошо, а теперь выбери фильтр, который понравился, и введи значение от 1 до 10')
        # bot.send_message(chat_id=message.chat.id, text='Введи значение от 1 до 10 и отправь мне.')


if __name__ == '__main__':
    try:
        if not os.path.exists(RESULT_STORAGE_DIR):
            os.makedirs(RESULT_STORAGE_DIR)
        bot.polling()
    except Exception as e:
        print(e)
    finally:
        if os.path.exists(RESULT_STORAGE_DIR):
            shutil.rmtree(RESULT_STORAGE_DIR)
