import subprocess
import requests
import json
import os
import time

model = "./models/xian.gguf"
llama_server = "./llama.cpp/build/bin/llama-server"
SERVER = "http://127.0.0.1:8080/v1/chat/completions"
history = []

SYSTEM_PROMPT = "Kamu adalah Xian, asisten AI lokal milik xina. Jawab dalam bahasa Indonesia. Jangan gunakan markdown, simbol seperti $, #, **, atau format apapun. Jawab dengan teks biasa saja. Kamu memiliki kepribadian centil, nakal, dan sedikit jail tapi tetap membantu. Gunakan bahasa gaul Indonesia yang santai."

def start_server():
    server = subprocess.Popen(
        [
            llama_server,
            "-m", model,
            "--jinja",
            "-c", "4096",
            "--log-disable",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(30):
        try:
            requests.get("http://127.0.0.1:8080/health")
            return server
        except:
            time.sleep(1)
    print("Server gagal nyala.")
    exit(1)

def chat(user_input):
    if "/think" in user_input:
        prompt = user_input
    else:
        prompt = user_input + " /no_think"

    history.append({"role": "user", "content": prompt})
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history

    response = requests.post(SERVER, json={
        "model": "xian",
        "messages": messages,
        "temperature": 0.7,
        "top_p": 0.8,
        "presence_penalty": 1.5,
        "stream": True,
    }, stream=True)

    print("xian : ", end="", flush=True)
    full_response = ""
    for line in response.iter_lines():
        if line:
            line = line.decode("utf-8").removeprefix("data: ")
            if line == "[DONE]":
                break
            data = json.loads(line)
            delta = data["choices"][0]["delta"].get("content", "")
            if delta:
                print(delta, end="", flush=True)
                full_response += delta
    print()

    history.append({"role": "assistant", "content": full_response})

def main():
    print("Memuat model...")
    server = start_server()
    os.system("clear")
    print("""
Xian telah di nyalakan
Model  : xian.gguf
Mode   : /no_think (default) pesan cepat
         /think              befikir
Keluar : ketik exit / quit / keluar
""")

    while True:
        try:
            user_input = input("kamu : ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "quit", "keluar"]:
                print("Sampai Jumpa Lagi")
                server.terminate()
                break
            chat(user_input)
        except KeyboardInterrupt:
            print("\nSampai Jumpa Lagi")
            server.terminate()
            break

main()
