import asyncio
import os

# Set of active client writers
CLIENTS = set()

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    addr = writer.get_extra_info('peername')
    print(f"[+] Client connected from {addr}")
    CLIENTS.add(writer)

    try:
        while True:
            data = await reader.read(4096)
            if not data:
                break
            
            # Broadcast the message to all other connected clients
            disconnected = set()
            for client in CLIENTS:
                if client != writer:
                    try:
                        client.write(data)
                        await client.drain()
                    except Exception:
                        disconnected.add(client)
            
            # Remove any dead connections
            for client in disconnected:
                CLIENTS.discard(client)

    except Exception as e:
        print(f"[-] Connection error with {addr}: {e}")
    finally:
        print(f"[-] Client {addr} disconnected")
        CLIENTS.discard(writer)
        writer.close()
        await writer.wait_closed()

async def main():
    # Render assigns dynamic ports via the PORT environment variable
    port = int(os.environ.get("PORT", 10000))
    server = await asyncio.start_server(handle_client, "0.0.0.0", port)
    
    print(f"🚀 Render Relay Server running on port {port}...")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
