import socket
import ssl
import os
import threading
import datetime
import logging

# ================== CONFIG ==================
HOST = '0.0.0.0'
PORT = 9998
USERS = {"admin": "secret123", "guest": "welcome"}
SERVER_FILES_DIR = "server_files"
CHUNK_SIZE = 1024

# ================== LOGGING ==================
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)

# ================== GLOBAL STATE ==================
ACTIVE_CONNECTIONS = {}
CONNECTIONS_LOCK = threading.Lock()
activity_logs = []

if not os.path.exists(SERVER_FILES_DIR):
    os.makedirs(SERVER_FILES_DIR)

# ================== SSL ==================
context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
context.load_cert_chain(certfile="server.crt", keyfile="server.key")

# ================== HELPERS ==================
def log_action(user, action):
    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
    entry = f"[{timestamp}] {user}: {action}"
    activity_logs.append(entry)

    if len(activity_logs) > 50:
        activity_logs.pop(0)

    logging.info(entry)

def send_chat_message(sender, recipient, message):
    formatted = f"CHAT {sender} {message}\n".encode()

    with CONNECTIONS_LOCK:
        if recipient.upper() == "ALL":
            for user, sock in ACTIVE_CONNECTIONS.items():
                if user != sender:
                    try:
                        sock.sendall(formatted)
                    except:
                        pass
        elif recipient in ACTIVE_CONNECTIONS:
            try:
                ACTIVE_CONNECTIONS[recipient].sendall(formatted)
            except:
                pass

def safe_recv(sock):
    try:
        data = sock.recv(1024)
        if not data:
            raise ConnectionResetError()
        return data
    except:
        raise

# ================== CLIENT HANDLER ==================
def handle_client(client_sock, addr):
    user = None
    secure_sock = None

    try:
        secure_sock = context.wrap_socket(client_sock, server_side=True)
        logging.info(f"Secure connection from {addr}")

        secure_sock.send(b"AUTH_REQUIRED\n")
        raw = safe_recv(secure_sock).decode().strip()

        if raw.startswith("LOGIN"):
            try:
                _, u, p = raw.split()
                if USERS.get(u) == p:
                    user = u
                    secure_sock.send(b"200 OK")
                    log_action("System", f"{user} logged in")

                    with CONNECTIONS_LOCK:
                        if user in ACTIVE_CONNECTIONS:
                            logging.warning(f"{user} already logged in. Overwriting.")
                        ACTIVE_CONNECTIONS[user] = secure_sock
                else:
                    secure_sock.send(b"401 ERROR")
                    return
            except:
                secure_sock.send(b"400 ERROR")
                return
        else:
            return

        while True:
            header = safe_recv(secure_sock).decode().strip()
            parts = header.split()
            command = parts[0].upper()

            if command == "MSG":
                recipient = parts[1]
                message = " ".join(parts[2:])
                send_chat_message(user, recipient, message)
                secure_sock.send(b"200 MSG SENT")

            elif command == "LIST":
                files = os.listdir(SERVER_FILES_DIR)
                file_str = ",".join(files) if files else "EMPTY"
                secure_sock.send(f"200 LIST {file_str}".encode())

            elif command == "LOGS":
                logs_str = "||".join(activity_logs) if activity_logs else "No activity yet."
                secure_sock.send(f"200 LOGS {logs_str}".encode())

            elif command == "DELETE":
                filename = parts[1]
                filepath = os.path.join(SERVER_FILES_DIR, filename)
                if os.path.exists(filepath):
                    os.remove(filepath)
                    log_action(user, f"Deleted {filename}")
                    secure_sock.send(b"200 DELETED")
                else:
                    secure_sock.send(b"404 NOT FOUND")

            elif command == "PUT":
                filename = parts[1]
                filepath = os.path.join(SERVER_FILES_DIR, filename)
                secure_sock.send(b"200 READY")

                with open(filepath, "wb") as f:
                    while True:
                        data = secure_sock.recv(CHUNK_SIZE)
                        if data.endswith(b"FILE_END"):
                            f.write(data[:-8])
                            break
                        f.write(data)

                log_action(user, f"Uploaded {filename}")
                secure_sock.send(b"200 UPLOADED")

            elif command == "GET":
                filename = parts[1]
                filepath = os.path.join(SERVER_FILES_DIR, filename)

                if os.path.exists(filepath):
                    secure_sock.send(b"200 READY")
                    secure_sock.recv(1024)

                    with open(filepath, "rb") as f:
                        while chunk := f.read(CHUNK_SIZE):
                            secure_sock.send(chunk)

                    secure_sock.send(b"FILE_END")
                    log_action(user, f"Downloaded {filename}")
                else:
                    secure_sock.send(b"404 NOT FOUND")

    except Exception as e:
        logging.error(f"Client error {addr}: {e}")

    finally:
        if user:
            with CONNECTIONS_LOCK:
                ACTIVE_CONNECTIONS.pop(user, None)

        if secure_sock:
            secure_sock.close()

        logging.info(f"Connection closed for {user}")

# ================== SERVER START ==================
def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)

    logging.info(f"Secure Server running on {HOST}:{PORT}")

    while True:
        client_sock, addr = server_socket.accept()
        thread = threading.Thread(target=handle_client, args=(client_sock, addr), daemon=True)
        thread.start()

if __name__ == "__main__":
    start_server()