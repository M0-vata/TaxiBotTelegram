import telebot
from telebot import types
import sqlite3
from geocoder_coords import coords_to_address, addess_to_coords


token = "1796160355:AAGcBwsAitQtxHiNnRPDkmRq_v8GmlZSu3U"
bot = telebot.TeleBot(token)


@bot.message_handler(commands=["start"])
def start(message):
    name = message.text
    bot.send_message(message.chat.id, "Привет <b>{first_name}</b>, рад тебя видеть. Пожалуйста, отправьте мне свой номер для этого есть команда /phone".format(first_name=message.from_user.first_name), parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove())

@bot.message_handler(commands=["phone"])
def phone(message):
    user_markup = types.ReplyKeyboardMarkup(row_width=1, resize_keyboard=True, one_time_keyboard=True)
    button_phone = types.KeyboardButton(text="Отправить номер телефона", request_contact=True)   
    user_markup.add(button_phone)
    msg = bot.send_message(message.chat.id, "Согласны ли вы предоставить ваш номер телефона для регистрации в системе?", reply_markup=user_markup)
    bot.register_next_step_handler(msg, reg_or_auth)

@bot.message_handler('text')
def reg_or_auth(message):
    # user phone
    input_phone = message.contact.phone_number    

    # connect to base
    mydb = sqlite3.connect('base.db')
    mycursor = mydb.cursor()
    
    # find phone in passengers table
    mycursor.execute('SELECT * FROM passengers')      
    passengers = mycursor.fetchall()
    for user in passengers:
        table_phone = user[1]
        if table_phone == input_phone:   # if user_phone in passengers
            print(1)
    mycursor.execute('SELECT * FROM taxi_drivers')      
    drivers = mycursor.fetchall()
    for user in drivers:
        table_phone = user[1]
        if table_phone == input_phone:   # if user_phone in taxi_drivers
            print(2)
    
    # if table is empty
    buttons_characters = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button_taxi_driver = types.KeyboardButton(text="Таксист")
    button_passenger = types.KeyboardButton(text="Пассажир")
    buttons_characters.add(button_taxi_driver)
    buttons_characters.add(button_passenger)
    mess = bot.send_message(message.chat.id, "Выберите кем вы являетесь?", reply_markup=buttons_characters)
    bot.register_next_step_handler(mess, choose_character, input_phone)      
        
        
@bot.message_handler('text')
def choose_character(message, user_phone):      # choose taxi_drivers or passenger
    if message.text == 'Таксист':
        mess = bot.send_message(message.chat.id, "Введите марку машины.", reply_markup=types.ReplyKeyboardRemove())
        bot.register_next_step_handler(mess, machine_firm, user_phone)
        
        
    elif message.text == 'Пассажир':
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        button_loca = types.KeyboardButton(text="🌐 Определить местоположение", request_location=True)
        keyboard.add(button_loca)
        mess = bot.send_message(message.chat.id, "Отправьте вашу геолокацию.🌐", reply_markup=keyboard)
        bot.register_next_step_handler(mess, geo_location, user_phone, 'Пассажир')

        
@bot.message_handler('text')              # machine_firm
def machine_firm(message, phone):
    firm = message.text
    mess = bot.send_message(message.chat.id, "Введите номера машины.", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(mess, car_numbers, phone, firm)

    
@bot.message_handler('text')             # car_numbers
def car_numbers(message, phone, machine_firm):          
    car_numbers = message.text
    
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_loca = types.KeyboardButton(text="🌐 Определить местоположение", request_location=True)
    keyboard.add(button_loca)
    mess = bot.send_message(message.chat.id, "Отправьте вашу геолокацию.🌐", reply_markup=keyboard)
    bot.register_next_step_handler(mess, geo_location, phone, 'Таксист', firm=machine_firm, car_numbers=car_numbers)


@bot.message_handler('text')
def geo_location(message, phone, job, firm=None, car_numbers=None):   # firm and car_numbers if taxi, default passenger
        latitude = message.location.latitude
        longitude = message.location.longitude
        
        address_location = coords_to_address(longitude, latitude)     # get address from coords, function file geocoder.py
        bot.send_message(message.chat.id, address_location, reply_markup=types.ReplyKeyboardRemove())
                         
        mydb = sqlite3.connect('base.db')
        mycursor = mydb.cursor()
        if job == 'Таксист':
            sqlFormula = "INSERT INTO taxi_drivers ('phone', 'machine_firm', 'car_numbers', 'longitude', 'latitude') VALUES (?,?,?,?,?)"
            mycursor.execute(sqlFormula, (phone, firm, car_numbers, longitude, latitude))
            mydb.commit()
            
            users = mycursor.execute('SELECT * FROM passengers')
            list_users = []                   
            for user in users:
                user_address = coords_to_address(user[2], user[3])    # find address from coords
                list_users.append(f"<b>Пассажир №{user[0]}</b>\nАдрес: {user_address}")  # add address user to list_users
                
            message_list = '\n'.join(list_users)              # list users for send
            bot.send_message(message.chat.id, "Список пассажиров:", parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove())
            bot.send_message(message.chat.id, message_list, parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove())
         
        elif job == 'Пассажир':
            mess = bot.send_message(message.chat.id, "<b>Куда едем?</b>", parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove())
            bot.register_next_step_handler(mess, where_go, phone, longitude, latitude)
            

@bot.message_handler('text')
def where_go(message, phone, longitude_start, latitude_start):   # end address for passenger
    address_go = message.text
    longitude_end, latitude_end = addess_to_coords(address_go).split(' ')
    
    mess = bot.send_message(message.chat.id, "<b>Укажите желаемую цену в ₽.</b>", parse_mode='HTML', reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(mess, price_way, phone, longitude_start, latitude_start, longitude_end, latitude_end)

    
@bot.message_handler('text')
def price_way(message, phone, longitude_start, latitude_start, longitude_end, latitude_end):   # end address for passenger
    price_way = int(message.text)
    
    mydb = sqlite3.connect('base.db')
    mycursor = mydb.cursor()
    sqlFormula = "INSERT INTO passengers ('phone', 'longitude_start', 'latitude_start', 'longitude_end', 'latitude_end', 'price') VALUES (?,?,?,?,?,?)"
    mycursor.execute(sqlFormula, (phone, longitude_start, latitude_start, longitude_end, latitude_end, price_way))
    mydb.commit()
    
            
            
if __name__ == '__main__':
    bot.polling(none_stop=True)