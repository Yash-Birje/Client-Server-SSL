Here is a **clean, professional, ATS-friendly README.md** for your project.

You can copy this directly into `README.md`.

---

# 🔐 Secure Multi-Threaded File Sharing & Chat System

A TLS-encrypted client–server application built in Python that supports:

* Secure authentication
* Encrypted file upload/download/delete
* Multi-client support (multi-threaded server)
* Real-time secure chat (broadcast & private)
* Global activity logging
* GUI-based client interface (Tkinter)

---

## 🏗 Architecture Overview

### Server

* Multi-threaded TCP server
* TLS encryption using SSL certificates
* Handles authentication and command processing
* Maintains active user connections
* Thread-safe global chat system
* File storage directory management

### Client

* GUI built using Tkinter
* Secure TLS connection to server
* Supports file management operations
* Real-time chat listener thread
* Thread-safe socket usage

---

## 🔧 Tech Stack

* Python 3.10+
* `socket`
* `ssl` (TLS encryption)
* `threading`
* `tkinter`
* OpenSSL (for certificate generation)

---

## 📂 Project Structure

```
project/
│
├── server.py
├── client.py
├── server.crt
├── server.key
├── server_files/
└── README.md
```

---

## 🔐 Security Features

* TLS-encrypted communication
* Username/password authentication
* Thread-safe shared connection mapping
* Controlled file access within server directory
* Custom application-layer protocol
* Chunk-based file transfer

---

## 🚀 How to Run

### 1️⃣ Install Python

Ensure Python 3.10+ is installed.

Check:

```bash
python --version
```

---

### 2️⃣ Install OpenSSL (If Not Installed)

Check:

```bash
openssl version
```

If not installed, download OpenSSL for Windows/Linux.

---

### 3️⃣ Generate SSL Certificates

Run inside project directory:

```bash
openssl req -newkey rsa:2048 -nodes -keyout server.key -x509 -days 365 -out server.crt
```

Important:

* For Common Name (CN), enter your server IP

  * `127.0.0.1` (local testing)
  * or your LAN IP

This generates:

* `server.key`
* `server.crt`

Place them in same folder as `server.py`.

---

### 4️⃣ Start Server

```bash
python server.py
```

Expected output:

```
[INFO] Secure Server running on 0.0.0.0:9998
```

---

### 5️⃣ Start Client

Open a new terminal:

```bash
python client.py
```

Login using:

```
Username: admin
Password: secret123
```

---

## 📡 Supported Commands (Protocol Design)

| Command                 | Description                       |
| ----------------------- | --------------------------------- |
| LOGIN username password | Authenticate user                 |
| MSG recipient message   | Send private or broadcast message |
| LIST                    | List server files                 |
| LOGS                    | Fetch activity logs               |
| PUT filename            | Upload file                       |
| GET filename            | Download file                     |
| DELETE filename         | Delete file                       |
| LOGOUT                  | Disconnect                        |

All commands are newline-terminated (`\n`) for proper TCP framing.

---

## 🧠 Concurrency Design

* Each client runs in its own thread
* Global dictionary maps username → secure socket
* `threading.Lock()` ensures thread-safe access
* Dedicated chat listener thread on client
* File transfers use chunk-based streaming

---

## ⚠ Known Limitations

* Self-signed certificate (not production-ready)
* Basic username/password authentication
* No persistent database (in-memory logs)
* Custom protocol instead of standardized JSON

---

## 🔮 Future Improvements

* JSON-based protocol framing
* Mutual TLS authentication
* AsyncIO-based scalable server
* Database-backed user management
* Rate limiting & DoS protection
* File integrity hashing (SHA-256)
* Role-based access control

---

## 📌 Learning Outcomes

This project demonstrates understanding of:

* TCP socket programming
* TLS handshake & certificate management
* Multi-threaded server design
* Thread synchronization
* Application-layer protocol design
* GUI client networking integration
* Secure file streaming over encrypted channels

---

## 📜 License

Educational use only.

---