import socket
import ssl
import threading
import tkinter as tk
from tkinter import simpledialog, scrolledtext
import random

HOST = '127.0.0.1'
PORT = 55553
SERVER_CERT = 'cert.pem'

client = None       # client socket object
username = None     # store input username
running = True      # flag for thread to keep running

# this function adds incoming message to chat window
def append_message(text_widget, message):
    text_widget.config(state='normal')
    text_widget.insert(tk.END, message + '\n')
    text_widget.config(state='disabled')
    text_widget.yview(tk.END)

# this function handle the incoming message
def receive_messages(chat_box):
    global running
    while running:
        try:
            message = client.recv(1024).decode()
            if message and not message.startswith(f"{username}:"):  # it won't show you the msg if it starts with your username
                append_message(chat_box, message)
            else:
                break
        except:
            break

# this function handle sending the message to the server
def send_message(entry, chat_box):
    global running
    message = entry.get().strip()
    if message:
        client.send(message.encode())       # send to server
        if not message.startswith("/@"):    # if it is not private messaging
            append_message(chat_box, f"{username}: {message}")
        if message == '.exit':      # if user wants to exit, quit GUI
            running = False         
            window.quit()           
        entry.delete(0, tk.END)

# this function gracefully shuting down the client side
def on_close():
    global running
    running = False
    try:
        client.send('.exit'.encode())
        client.close()
    except:
        pass
    window.destroy()    

# this function sets up the secure client socket
def connect():
    global client, username

    # SSL
    context = ssl.create_default_context()          
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=SERVER_CERT)

    # client socket, wrap with SSL
    client = context.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname=HOST)
    client.connect((HOST, PORT))

    client.recv(1024)  # receive server prompt for username
    # client username = input username + 4 digits random number
    client.send((username + str(random.randint(1000, 10000))).encode())     # send username
    welcome = client.recv(1024).decode()    # receive welcome message
    append_message(chat_box, welcome)

# Tkinter GUI

# create GUI window
window = tk.Tk()
window.title("Secure Chat Client")
# window.geometry("600x400")
window.geometry("600x400")

#chatbox
chat_box = scrolledtext.ScrolledText(window, state='disabled', wrap=tk.WORD, font=("Times New Roman", 16),fg="#0A192F")
chat_box.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

#enter text
message_entry = tk.Entry(window, font=("Times New Roman", 14), fg="#333333")
message_entry.pack(padx=10, pady=(0,10), fill=tk.X)

# username prompt
username = simpledialog.askstring("Username", "Enter your username:", parent=window)
if not username:
    window.destroy()
    exit()

connect()

# start thread
threading.Thread(target=receive_messages, args=(chat_box,), daemon=True).start()

message_entry.bind("<Return>", lambda event: send_message(message_entry, chat_box))     # "Enter" key triggers sending message
window.protocol("WM_DELETE_WINDOW", on_close)       # "X" triggers shutting down
window.mainloop()
