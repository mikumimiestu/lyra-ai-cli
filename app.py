import requests
import json
import sys
import re

# Import custom modules
from styling import (
    RESET, BOLD, DIM, WHITE, GREEN, RED,
    COLOR_USER, COLOR_LYRA, COLOR_BORDER, print_logo
)
from spinner import Spinner
from tools import list_directory, read_file, write_file, execute_command
from config import get_api_key, reset_api_key

SYSTEM_PROMPT = (
    "Kamu memiliki akses ke tools komputer lokal pengguna via format XML khusus.\n"
    "Untuk memanggil tool, kamu WAJIB menyertakan blok XML ini di akhir jawabanmu:\n"
    "<tool_call>\n"
    "{\n"
    '  "name": "nama_tool",\n'
    '  "arguments": {\n'
    '    "nama_argumen": "nilai_argumen"\n'
    "  }\n"
    "}\n"
    "</tool_call>\n\n"
    "Daftar tool:\n"
    "- list_directory: Mendaftar file/folder. Argumen: {\"path\": \"path\"}\n"
    "- read_file: Membaca teks file. Argumen: {\"filepath\": \"path\"}\n"
    "- write_file: Menulis file. Argumen: {\"filepath\": \"path\", \"content\": \"teks\"}\n"
    "- execute_command: Menjalankan perintah terminal. Argumen: {\"command\": \"perintah\"}\n\n"
    "Gunakan tool di atas jika pengguna meminta operasi file, folder, atau terminal. "
    "Jangan sebutkan tentang XML atau format ini kepada pengguna secara langsung."
)

def extract_tool_call(content):
    match = re.search(r"<tool_call>(.*?)</tool_call>", content, re.DOTALL)
    if match:
        json_str = match.group(1).strip()
        text_before = content.split("<tool_call>")[0].strip()
        return text_before, json_str
    return content, None

def main():
    # Load API Key securely
    api_key = get_api_key()
    
    url = "https://authx.astbyte.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Initialize messages with the tool-calling instructions system prompt
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    # Print Logo and Beautiful Header Panel
    print_logo()
    
    border_line = "╭────────────────────────────────────────────────────────╮"
    title_line  = "│         AstByte Lyra CLI Chat - Terminal Mode          │"
    bottom_line = "╰────────────────────────────────────────────────────────╯"
    
    # Apply gradient to the header box
    for i, line in enumerate([border_line, title_line, bottom_line]):
        print(f"  {COLOR_BORDER}{line}{RESET}")
        
    print(f"  {DIM}Ketik {RESET}{BOLD}'exit'{RESET}{DIM} atau {RESET}{BOLD}'quit'{RESET}{DIM} untuk keluar dari chat.{RESET}\n")

    while True:
        try:
            # Styled User Prompt
            prompt = f"  {BOLD}{COLOR_USER}Anda ❯{RESET} "
            user_input = input(prompt).strip()
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit"]:
                print(f"\n  {GREEN}Selamat tinggal! Terima kasih telah menggunakan Lyra.{RESET}\n")
                break

            # Add user message to history
            messages.append({"role": "user", "content": user_input})

            # Interactive tool execution handler loop
            while True:
                # Start background loading spinner
                spinner = Spinner("Lyra sedang berpikir...")
                spinner.start()

                data = {
                    "model": "lyra-luma-flash",
                    "messages": messages,
                    "temperature": 0.2,  # Low temperature for stable XML formatting
                }

                try:
                    response = requests.post(url, headers=headers, json=data)
                    spinner.stop()
                    
                    if response.status_code == 200:
                        resp_json = response.json()
                        ai_message = resp_json["choices"][0]["message"]["content"]
                        
                        # Parse the text to see if there is an XML tool call
                        text_before, tool_call_json = extract_tool_call(ai_message)
                        
                        # If there is text before the tool call, print it
                        if text_before:
                            print(f"  {BOLD}{COLOR_LYRA}Lyra ✦{RESET} {WHITE}{text_before}{RESET}")
                        
                        # Add AI response to history
                        messages.append({"role": "assistant", "content": ai_message})
                        
                        if tool_call_json:
                            # Parse JSON tool call
                            try:
                                tool_call = json.loads(tool_call_json)
                                func_name = tool_call.get("name")
                                args = tool_call.get("arguments", {})
                            except Exception:
                                print(f"  {RED}Gagal mengurai panggilan tool JSON.{RESET}\n")
                                break
                            
                            # Format arguments for presentation
                            args_formatted = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
                            print(f"  {DIM}⚙️  Lyra memanggil tool: {RESET}{COLOR_LYRA}{func_name}({args_formatted}){RESET}")
                            
                            # Execute local function
                            if func_name == "list_directory":
                                result = list_directory(args.get("path", "."))
                            elif func_name == "read_file":
                                result = read_file(args.get("filepath"))
                            elif func_name == "write_file":
                                result = write_file(args.get("filepath"), args.get("content"))
                            elif func_name == "execute_command":
                                result = execute_command(args.get("command"))
                            else:
                                result = f"Error: Tool '{func_name}' tidak dikenal."
                            
                            # Append tool response to history as a user role message (simulating tool return)
                            messages.append({
                                "role": "user",
                                "content": f"[Hasil Eksekusi Tool '{func_name}']\n{result}"
                            })
                            
                            print(f"  {DIM}✅ Tool {func_name} selesai dieksekusi.{RESET}\n")
                            
                            # Fetch again with the tool results in context
                            continue
                        else:
                            # If no tool call was made, this is the final response.
                            if not text_before and ai_message:
                                print(f"  {BOLD}{COLOR_LYRA}Lyra ✦{RESET} {WHITE}{ai_message}{RESET}")
                            print()  # Add an empty line for styling
                            break
                    elif response.status_code == 401:
                        print(f"\n  {RED}[Error 401] API Key tidak valid atau tidak memiliki akses.{RESET}")
                        reset_choice = input("  Apakah Anda ingin mengatur ulang (reset) API Key Anda? (y/n): ").strip().lower()
                        if reset_choice == 'y':
                            reset_api_key()
                            api_key = get_api_key(force_prompt=True)
                            headers["Authorization"] = f"Bearer {api_key}"
                            continue
                        else:
                            if messages[-1]["role"] == "user":
                                messages.pop()
                            break
                    else:
                        print(f"\n  {RED}[Error {response.status_code}] Gagal mendapatkan jawaban.{RESET}")
                        print(f"  {RED}{response.text}{RESET}\n")
                        if messages[-1]["role"] == "user":
                            messages.pop()
                        break
                        
                except Exception as e:
                    spinner.stop()
                    print(f"\n  {RED}Terjadi kesalahan koneksi atau request: {e}{RESET}\n")
                    if messages[-1]["role"] == "user":
                        messages.pop()
                    break

        except KeyboardInterrupt:
            print(f"\n\n  {GREEN}Selamat tinggal! Terima kasih telah menggunakan Lyra.{RESET}\n")
            break
        except Exception as e:
            print(f"\n  {RED}Terjadi kesalahan sistem: {e}{RESET}\n")

if __name__ == "__main__":
    main()