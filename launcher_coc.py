from tkinter import *
import os
import urllib.request

launcher = Tk()
launcher.geometry('250x250')
launcher.title("CoC [1.4.22]")
version = "0.beta"

# запуск с дебагом
def start_with_debug():
    os.system('start Stalker-CoC.exe -skip_reg -dbg')
    launcher.quit()


# фаст запуск
def start_low_cpu():
    os.system('start CoC_1.4_02coreCPU.cmd')
    launcher.quit()


# запуск менеджера модов от стасона
def start_manager():
    os.system('start Autorun.exe')


# запуск игры без ничего
def start_game():
    os.system('start Stalker-CoC.exe -skip_reg')
    launcher.quit()


# запуск настроек (options.exe)
def start_options():
    os.system('start options.exe')

def exit():
    launcher.quit()

def update_launcher():
    os.system('start msg.vbs')

but1 = Button(text='ЗАПУСК (Debug)', font=("Arial", 12), command=start_with_debug)
but2 = Button(text='ЗАПУСК', font=("Arial", 12), command=start_game)
but3 = Button(text='Менеджер модов', font=("Arial", 12), command=start_manager)
but4 = Button(text='ФАСТ ЗАПУСК', font=("Arial", 12), command=start_low_cpu)
but5 = Button(text="НАСТРОЙКИ", font=("Arial", 12), command=start_options)
but6 = Button(text="ВЫХОД", font=("Arial", 12), command=exit)
but7 = Button(text="Обновление", font=("Arial", 12), command=update_launcher)
but1.place(x=50, y=30)
but2.place(x=50, y=60)
but4.place(x=50, y=90)
but3.place(x=50, y=120)
but5.place(x=50, y=150)
but6.place(x=0, y=220)
but7.place(x=100, y=220)

launcher.mainloop()
