import socket
import threading
import signal
import sys
import ssl

HOST = '127.0.0.1'
PORT = 55553


# List to keep track of connected clients
clients = {}
usernames = {}

#SSL required info
SERVER_CERT = 'cert.pem'
SERVER_KEY = 'key.pem'


# Function to handle client communication
def handle_client(client_socket, client_address):
    # Sending the list of active users
    welcome_msg = [
        "Welcome to the chat room!\n",
        "=" * 50,
        "Instructions:",
        '1. Press "/u" to show all users online',
        "2. Use '/@ <username> <message>' to send a private message",
        "3. Type your message normally to send to everyone",
        "4. Enter '.exit' to leave the chat",
        "=" * 50
    ]
    
    for msg in welcome_msg:
        client_socket.send(msg.encode())
    send_active_users(client_socket)

    while True:
        try:
            # Receiving the message from the client
            message = client_socket.recv(1024).decode()
            if message:
                # If the user types .exit, disconnect them
                if message.strip() == '.exit':
                    remove_client(client_socket)
                    break
                
                # Check if it's a private message
                if message.startswith("/@"):
                    handle_private_message(message, client_socket)

                elif message.startswith("/u"):
                    send_active_users(client_socket)
                else:
                    # Broadcasting the message to all clients
                    full_message = f"{usernames.get(client_socket, 'Unknown')}: {message}"
                    broadcast(full_message, client_socket)
            else:
                break
        except:
            break

    remove_client(client_socket)

# Function to handle private messages
def handle_private_message(message, sender_socket):
    try:
        # Split the message into /@ <username> <message>
        parts = message.split(" ", 2)
        if len(parts) < 3: #Invalid format, need three 
            sender_socket.send("Invalid private message format. Use: /@ <username> <message>\n".encode())
            return

        target_username = parts[1]
        private_message = parts[2]

        # Find the recipient socket
        recipient_socket = None
        for socket, username in usernames.items():
            if username == target_username:
                recipient_socket = socket
                break

        if recipient_socket:
            sender_username = usernames[sender_socket]
            recipient_socket.send(f"Private message from {sender_username}: {private_message}\n".encode())
            sender_socket.send(f"Private message to {target_username}: {private_message}\n".encode())
        else:
            sender_socket.send(f"User {target_username} not found.\n".encode())
    except Exception as e:
        print(f"Error handling private message: {e}")

# Function to broadcast message to all clients
def broadcast(message, sender_socket):
    for client_socket in list(clients.keys()):
        if client_socket != sender_socket:
            try:
                client_socket.send(message.encode())
            except (BrokenPipeError, ConnectionResetError):
                print(f"[!] Removing dead socket: {client_socket}")
                client_socket.close()
                clients.pop(client_socket, None)
                usernames.pop(client_socket, None)

# Send the list of active users to the new client
def send_active_users(client_socket):
    client_socket.send("Users currently online:\n".encode())
    users_list = "\n".join(usernames.values()) 
    client_socket.send((users_list + "\n").encode())

# Remove a client from the server
def remove_client(client_socket):
    username = usernames.pop(client_socket, None)
    if username:
        clients.pop(client_socket, None)
        broadcast(f"{username} has left the chat.\n", client_socket)
        client_socket.close()

#Close the server 
def stop_server(signal_num, frame):
    print("Shutting down the server...")
    #Remove all clients first
    for client_socket in list(clients.keys()):
        remove_client(client_socket)
    print("All connections closed")
    sys.exit(0) #Close

# Main server function
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))  # Host on all interfaces at port 
    server.listen(5)
    print("Server started... Waiting for clients to connect.")

    #Wrap socket in SSL for encryption
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(certfile=SERVER_CERT, keyfile=SERVER_KEY)
    server = context.wrap_socket(server, server_side=True)

    #When Control + C signal is received, run the stop_server
    signal.signal(signal.SIGINT, stop_server)

    
    while True:
        client_socket, client_address = server.accept()
        print(f"New connection from {client_address}")
        
        # Ask for the username
        client_socket.send("Enter your username: ".encode())
        username = client_socket.recv(1024).decode().strip()
        
        # Save the client and username
        clients[client_socket] = client_address
        usernames[client_socket] = username
        
        # Send welcome message and the list of active users
        
        client_socket.send(f"Hello {username}! You are now connected.\n".encode())
        
        # Start a new thread to handle this client
        client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_thread.start()


start_server()