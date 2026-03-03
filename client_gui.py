import tkinter as tk
from tkinter import messagebox, filedialog
import socket
import ssl
import os
from threading import Thread, Lock
import time

# --- Configuration ---
HOST = '10.0.14.87' # Change this to Server IP if running on different machines
PORT = 9998
CHUNK_SIZE = 1024 

class FileClientApp:
    def __init__(self, master):
        self.master = master
        master.title("Advanced Secure File Client")
        master.geometry("900x600")
        
        self.secure_sock = None
        self.is_authenticated = False
        
        # --- THREAD SAFETY LOCK ---
        # Only one thread can use the socket for synchronous (request/response) file/log commands
        self.lock = Lock() 
        
        # --- SSL Setup ---
        self.context = ssl.create_default_context()
        self.context.check_hostname = False 
        self.context.verify_mode = ssl.CERT_NONE 

        self.setup_gui()

    def setup_gui(self):
        # --- Main Layout ---
        main_pane = tk.PanedWindow(self.master, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True)

        left_frame = tk.Frame(main_pane)
        right_frame = tk.Frame(main_pane, bg="lightgray", width=300)
        
        main_pane.add(left_frame)
        main_pane.add(right_frame)

        # === LEFT FRAME CONTENT ===
        
        # 1. Connection Section
        conn_frame = tk.LabelFrame(left_frame, text="Connection", padx=10, pady=10)
        conn_frame.pack(fill='x', padx=10, pady=5)

        tk.Label(conn_frame, text="Host:").grid(row=0, column=0)
        self.host_entry = tk.Entry(conn_frame, width=15); self.host_entry.insert(0, HOST)
        self.host_entry.grid(row=0, column=1)

        tk.Label(conn_frame, text="User:").grid(row=0, column=2)
        self.user_entry = tk.Entry(conn_frame, width=10); self.user_entry.insert(0, "admin")
        self.user_entry.grid(row=0, column=3)
        
        tk.Label(conn_frame, text="Pass:").grid(row=0, column=4)
        self.pass_entry = tk.Entry(conn_frame, width=10, show="*"); self.pass_entry.insert(0, "secret123")
        self.pass_entry.grid(row=0, column=5)

        self.login_btn = tk.Button(conn_frame, text="Connect", command=self.start_login, bg="#4CAF50", fg="white")
        self.login_btn.grid(row=0, column=6, padx=10)

        self.status_lbl = tk.Label(conn_frame, text="Disconnected", fg="red")
        self.status_lbl.grid(row=1, columnspan=7, sticky="w")

        # 2. Server Files List
        file_list_frame = tk.LabelFrame(left_frame, text="Server Files", padx=10, pady=10)
        file_list_frame.pack(fill='both', expand=True, padx=10, pady=5)

        self.file_listbox = tk.Listbox(file_list_frame, height=10)
        self.file_listbox.pack(fill='both', expand=True, side=tk.LEFT)
        
        scrollbar = tk.Scrollbar(file_list_frame)
        scrollbar.pack(side=tk.RIGHT, fill='y')
        self.file_listbox.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.file_listbox.yview)

        # File Action Buttons
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill='x', padx=10, pady=5)

        tk.Button(btn_frame, text="🔄 Refresh Files", command=self.req_list_files).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="⬇️ Download Selected", command=self.start_download).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="🗑️ Delete Selected", command=self.start_delete, fg="red").pack(side=tk.LEFT, padx=5)

        # 3. Upload Section
        upload_frame = tk.LabelFrame(left_frame, text="Upload File", padx=10, pady=10)
        upload_frame.pack(fill='x', padx=10, pady=10)

        self.upload_entry = tk.Entry(upload_frame, width=30)
        self.upload_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(upload_frame, text="Browse", command=self.browse_file).pack(side=tk.LEFT)
        tk.Button(upload_frame, text="⬆️ Upload", command=self.start_upload, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=10)

        # === RIGHT FRAME CONTENT (Sidebar) ===
        
        # 4. Activity Log Section
        tk.Label(right_frame, text="Global Activity Log", bg="lightgray", font=("Arial", 10, "bold")).pack(pady=5)
        tk.Button(right_frame, text="🔄 Refresh Logs", command=self.req_logs).pack(pady=2)
        
        self.log_text = tk.Text(right_frame, width=30, height=15, state=tk.DISABLED, bg="#f0f0f0", font=("Consolas", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 5. Chat Section
        chat_frame = tk.LabelFrame(right_frame, text="Secure Chat", padx=5, pady=5)
        chat_frame.pack(fill='x', padx=5, pady=5)

        tk.Label(chat_frame, text="Recipient (Use 'ALL' for broadcast):").pack(fill='x')
        self.recipient_entry = tk.Entry(chat_frame, width=25); self.recipient_entry.insert(0, "ALL")
        self.recipient_entry.pack(fill='x', padx=2)
        
        tk.Label(chat_frame, text="Message:").pack(fill='x')
        self.msg_entry = tk.Entry(chat_frame, width=25)
        self.msg_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=2, pady=2)
        tk.Button(chat_frame, text="Send", command=self.start_send_message, bg="#008CBA", fg="white").pack(side=tk.RIGHT, padx=2, pady=2)

        tk.Label(right_frame, text="Chat History", bg="lightgray", font=("Arial", 10, "bold")).pack(pady=5)
        self.chat_history_text = tk.Text(right_frame, width=30, height=15, state=tk.DISABLED, bg="white", font=("Consolas", 9))
        self.chat_history_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)


    def log_gui(self, message):
        """Updates status label safely"""
        self.status_lbl.config(text=message, fg="blue")

    def log_chat(self, sender, message):
        """Updates chat history safely from any thread"""
        def update_gui():
            self.chat_history_text.config(state=tk.NORMAL)
            timestamp = time.strftime("%H:%M:%S")
            self.chat_history_text.insert(tk.END, f"[{timestamp}] {sender}: {message}\n")
            self.chat_history_text.see(tk.END)
            self.chat_history_text.config(state=tk.DISABLED)
            
        self.master.after(0, update_gui) # Use master.after to safely update GUI from a thread

    def browse_file(self):
        f = filedialog.askopenfilename()
        if f:
            self.upload_entry.delete(0, tk.END)
            self.upload_entry.insert(0, f)

    # --- Networking Logic ---

    def start_login(self):
        t = Thread(target=self.connect)
        t.start()

    def connect(self):
        # We don't need the lock here because we aren't connected yet
        try:
            raw_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            # Make the raw socket non-blocking temporarily for cleaner connection/auth
            # raw_sock.settimeout(10) 
            
            self.secure_sock = self.context.wrap_socket(raw_sock, server_hostname=self.host_entry.get())
            self.secure_sock.connect((self.host_entry.get(), PORT))
            
            # Auth Handshake
            self.secure_sock.recv(1024) # "AUTH_REQUIRED"
            creds = f"LOGIN {self.user_entry.get()} {self.pass_entry.get()}"
            self.secure_sock.send(creds.encode())
            
            resp = self.secure_sock.recv(1024).decode()
            if "200" in resp:
                self.is_authenticated = True
                self.log_gui("Connected & Logged In!")
                self.status_lbl.config(fg="green")
                
                # *** NEW: Start permanent chat listener thread ***
                Thread(target=self.listen_for_chats, daemon=True).start()
                
                # Kick off initial data fetch
                self.req_list_files()
                self.req_logs()
            else:
                self.log_gui("Login Failed")
                self.secure_sock.close()
                self.secure_sock = None
        except Exception as e:
            self.log_gui(f"Connection Error: {e}")
            if self.secure_sock:
                self.secure_sock.close()
            self.secure_sock = None

    def listen_for_chats(self):
        """Dedicated thread to continuously listen for and handle chat messages."""
        # This thread must operate carefully outside the main lock
        try:
            # Set a small timeout so the thread can occasionally check if it should exit
            self.secure_sock.settimeout(0.5) 
            while self.is_authenticated:
                try:
                    # Receive data. Since we're outside the lock, the server must 
                    # ensure chat messages don't interrupt a synchronous file transfer.
                    # We assume 'CHAT' messages are sent with a newline separator.
                    data = self.secure_sock.recv(CHUNK_SIZE).decode()
                    
                    if not data:
                        break # Connection closed by server
                        
                    if data.startswith("CHAT"):
                        # Handle CHAT messages
                        lines = data.strip().split('\n')
                        for line in lines:
                            if line.startswith("CHAT"):
                                parts = line.split(" ", 2)
                                if len(parts) == 3:
                                    sender, message = parts[1], parts[2]
                                    self.log_chat(sender, message)
                                else:
                                    print(f"Malformed CHAT message: {line}")

                except socket.timeout:
                    # Expected if no chat message is pending
                    continue
                except ssl.SSLError as e:
                    if "timed out" in str(e):
                        continue
                    else:
                        raise e # Re-raise other SSL errors
                
            print("Chat listener thread exiting.")
            
        except Exception as e:
            print(f"Chat Listener Error: {e}")
            self.is_authenticated = False
            self.log_gui("Chat Listener Failed")
        finally:
            # Reset timeout for the main socket if it's still open
            if self.secure_sock:
                 self.secure_sock.settimeout(None)
                 
    def start_send_message(self):
        if not self.is_authenticated: return
        recipient = self.recipient_entry.get().strip()
        message = self.msg_entry.get().strip()
        self.msg_entry.delete(0, tk.END)

        if not message or not recipient: return
        
        # Log self-sent message immediately
        user = self.user_entry.get()
        if recipient.upper() == "ALL":
             self.log_chat(f"{user} (to ALL)", message)
        else:
             self.log_chat(f"{user} (to {recipient})", message)
             
        def task():
            try:
                # ACQUIRE LOCK before sending command
                with self.lock:
                    command = f"MSG {recipient} {message}"
                    self.secure_sock.send(command.encode())
                    resp = self.secure_sock.recv(1024).decode()
                
                if "200" in resp:
                    # Successfully sent to server
                    pass
                else:
                    self.log_gui("Message failed to send")
            except Exception as e:
                 self.log_gui(f"Chat Send Error: {e}")
        Thread(target=task).start()

    # --- Existing File/Log Methods (using self.lock) ---

    def req_list_files(self):
        if not self.is_authenticated: return
        def task():
            try:
                # ACQUIRE LOCK BEFORE USING SOCKET
                with self.lock:
                    self.secure_sock.send(b"LIST")
                    resp = self.secure_sock.recv(4096).decode()
                
                # Process data (Lock released)
                if resp.startswith("200 LIST"):
                    files_str = resp[9:]
                    files = files_str.split(",") if files_str != "EMPTY" else []
                    
                    self.file_listbox.delete(0, tk.END)
                    for f in files:
                        self.file_listbox.insert(tk.END, f)
            except Exception as e:
                print(f"List Error: {e}")
        Thread(target=task).start()

    def req_logs(self):
        if not self.is_authenticated: return
        def task():
            try:
                # ACQUIRE LOCK BEFORE USING SOCKET
                with self.lock:
                    self.secure_sock.send(b"LOGS")
                    resp = self.secure_sock.recv(4096).decode()
                
                # Process data (Lock released)
                if resp.startswith("200 LOGS"):
                    logs_raw = resp[9:]
                    logs = logs_raw.split("||")
                    
                    self.log_text.config(state=tk.NORMAL)
                    self.log_text.delete(1.0, tk.END)
                    for l in logs:
                        self.log_text.insert(tk.END, l + "\n")
                    self.log_text.config(state=tk.DISABLED)
            except Exception as e:
                print(f"Log Error: {e}")
        Thread(target=task).start()

    def start_delete(self):
        sel = self.file_listbox.curselection()
        if not sel: return
        filename = self.file_listbox.get(sel[0])
        
        if not messagebox.askyesno("Confirm", f"Delete {filename}?"): return

        def task():
            try:
                # ACQUIRE LOCK
                with self.lock:
                    self.secure_sock.send(f"DELETE {filename}".encode())
                    resp = self.secure_sock.recv(1024).decode()
                
                if "200" in resp:
                    self.log_gui(f"Deleted {filename}")
                    # These will launch their own locked threads, so it's safe
                    self.req_list_files() 
                    self.req_logs()       
                else:
                    self.log_gui("Delete failed")
            except Exception as e:
                self.log_gui(f"Delete Error: {e}")
        Thread(target=task).start()

    def start_upload(self):
        path = self.upload_entry.get()
        if not path or not os.path.exists(path): return
        
        def task():
            filename = os.path.basename(path)
            try:
                # ACQUIRE LOCK - Keep lock for the WHOLE upload process
                with self.lock:
                    self.secure_sock.send(f"PUT {filename}".encode())
                    resp = self.secure_sock.recv(1024).decode()
                    
                    if "200 READY" in resp:
                        with open(path, 'rb') as f:
                            while True:
                                data = f.read(CHUNK_SIZE)
                                if not data: break
                                self.secure_sock.send(data)
                        self.secure_sock.send(b'FILE_END')
                        
                        final_resp = self.secure_sock.recv(1024).decode()
                        self.log_gui(f"Uploaded {filename}")
                    else:
                        self.log_gui("Upload refused by server")
                
                # Refresh UI after lock is released
                self.req_list_files()
                self.req_logs()
            except Exception as e:
                 self.log_gui(f"Upload Error: {e}")
        Thread(target=task).start()

    def start_download(self):
        sel = self.file_listbox.curselection()
        if not sel: return
        filename = self.file_listbox.get(sel[0])

        def task():
            try:
                # ACQUIRE LOCK for WHOLE download
                with self.lock:
                    self.secure_sock.send(f"GET {filename}".encode())
                    resp = self.secure_sock.recv(1024).decode()
                    
                    if "200 READY" in resp:
                        self.secure_sock.send(b"ACK")
                        with open(f"DOWNLOADED_{filename}", 'wb') as f:
                            while True:
                                data = self.secure_sock.recv(CHUNK_SIZE)
                                if data.endswith(b'FILE_END'):
                                    f.write(data[:-8])
                                    break
                                f.write(data)
                        self.log_gui(f"Downloaded {filename}")
                    else:
                        self.log_gui("Download Failed (Not Found?)")
                
                self.req_logs()
            except Exception as e:
                self.log_gui(f"Download Error: {e}")
        Thread(target=task).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = FileClientApp(root)
    root.mainloop()
