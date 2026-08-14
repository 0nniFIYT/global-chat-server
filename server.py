import asyncio
import os
import json
import websockets

# Store active websocket connections
CLIENTS = set()

# HTML & CSS & JavaScript frontend served directly to the browser
HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Global Web Chat</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #1e1e2e;
            color: #cdd6f4;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .chat-container {
            width: 100%;
            max-width: 600px;
            height: 90vh;
            background: #181825;
            border-radius: 12px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            box-shadow: 0 8px 24px rgba(0,0,0,0.5);
        }
        .header {
            padding: 15px 20px;
            background: #11111b;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid #313244;
        }
        .header h2 { color: #cba6f7; font-size: 1.2rem; }
        .status { font-size: 0.85rem; color: #f38ba8; }
        .status.connected { color: #a6e3a1; }
        .config-bar {
            padding: 10px 20px;
            background: #1e1e2e;
            display: flex;
            gap: 10px;
            border-bottom: 1px solid #313244;
        }
        input {
            background: #313244;
            border: 1px solid #45475a;
            color: #cdd6f4;
            padding: 8px 12px;
            border-radius: 6px;
            outline: none;
        }
        input:focus { border-color: #89b4fa; }
        .username-input { flex: 1; }
        .chat-box {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            display: flex;
            flex-direction: column;
            gap: 10px;
        }
        .message {
            background: #313244;
            padding: 8px 12px;
            border-radius: 8px;
            max-width: 80%;
            word-wrap: break-word;
        }
        .message.system {
            background: transparent;
            color: #a6adc8;
            font-style: italic;
            font-size: 0.85rem;
            align-self: center;
        }
        .message .sender {
            font-size: 0.75rem;
            color: #89b4fa;
            margin-bottom: 2px;
            font-weight: bold;
        }
        .message .time {
            font-size: 0.65rem;
            color: #6c7086;
            margin-left: 8px;
        }
        .input-area {
            padding: 15px 20px;
            background: #11111b;
            display: flex;
            gap: 10px;
        }
        .msg-input { flex: 1; }
        button {
            background: #89b4fa;
            color: #11111b;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-weight: bold;
            cursor: pointer;
            transition: background 0.2s;
        }
        button:hover { background: #b4befe; }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="header">
            <h2>🌍 Global Web Chat</h2>
            <div id="status" class="status">Disconnected</div>
        </div>
        <div class="config-bar">
            <input type="text" id="username" class="username-input" placeholder="Your Name">
            <button id="connect-btn" onclick="toggleConnect()">Connect</button>
        </div>
        <div id="chat-box" class="chat-box"></div>
        <div class="input-area">
            <input type="text" id="msg-input" class="msg-input" placeholder="Type a message..." disabled onkeydown="if(event.key==='Enter') sendMessage()">
            <button id="send-btn" onclick="sendMessage()" disabled>Send</button>
        </div>
    </div>

    <script>
        let ws = null;
        const statusEl = document.getElementById('status');
        const chatBox = document.getElementById('chat-box');
        const msgInput = document.getElementById('msg-input');
        const sendBtn = document.getElementById('send-btn');
        const connectBtn = document.getElementById('connect-btn');
        const usernameInput = document.getElementById('username');

        usernameInput.value = "User_" + Math.floor(Math.random() * 1000);

        function addMessage(sender, text, isSystem = false) {
            const msgDiv = document.createElement('div');
            const timeStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

            if (isSystem) {
                msgDiv.className = 'message system';
                msgDiv.textContent = `[${timeStr}] ⚙️ ${text}`;
            } else {
                msgDiv.className = 'message';
                msgDiv.innerHTML = `<div class="sender">${sender}<span class="time">${timeStr}</span></div><div>${text}</div>`;
            }

            chatBox.appendChild(msgDiv);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function toggleConnect() {
            if (ws) {
                ws.close();
                return;
            }

            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws`;

            ws = new WebSocket(wsUrl);

            ws.onopen = () => {
                statusEl.textContent = "Connected";
                statusEl.classList.add("connected");
                connectBtn.textContent = "Disconnect";
                msgInput.disabled = false;
                sendBtn.disabled = false;
                usernameInput.disabled = true;
                addMessage(null, "Connected to the global room!", true);
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                addMessage(data.sender, data.text, data.isSystem);
            };

            ws.onclose = () => {
                statusEl.textContent = "Disconnected";
                statusEl.classList.remove("connected");
                connectBtn.textContent = "Connect";
                msgInput.disabled = true;
                sendBtn.disabled = true;
                usernameInput.disabled = false;
                addMessage(null, "Disconnected from server.", true);
                ws = null;
            };
        }

        function sendMessage() {
            const text = msgInput.value.trim();
            const sender = usernameInput.value.trim() || "Anonymous";

            if (text && ws) {
                const payload = JSON.stringify({ sender, text });
                ws.send(payload);
                addMessage(sender, text);
                msgInput.value = '';
            }
        }
    </script>
</body>
</html>
"""

async def handle_websocket(websocket, path):
    CLIENTS.add(websocket)
    try:
        async for message in websocket:
            # Broadcast message to all other connected browsers
            data = json.loads(message)
            broadcast_data = json.dumps({"sender": data["sender"], "text": data["text"], "isSystem": False})
            
            disconnected = set()
            for client in CLIENTS:
                if client != websocket:
                    try:
                        await client.send(broadcast_data)
                    except Exception:
                        disconnected.add(client)
            
            for client in disconnected:
                CLIENTS.discard(client)
    except Exception:
        pass
    finally:
        CLIENTS.discard(websocket)

async def http_handler(reader, writer):
    # Basic HTTP response serving the webpage
    request = await reader.read(1024)
    response = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n" + HTML_CONTENT
    writer.write(response.encode('utf-8'))
    await writer.drain()
    writer.close()

async def main():
    port = int(os.environ.get("PORT", 10000))
    
    # Start WebSockets server
    async with websockets.serve(handle_websocket, "0.0.0.0", port):
        print(f"🚀 Web Chat Server live on port {port}")
        await asyncio.Future()  # run forever

if __name__ == "__main__":
    asyncio.run(main())
