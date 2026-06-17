import requests
import json
import sys

# Import custom modules
from styling import (
    RESET, BOLD, DIM, WHITE, GREEN, RED,
    COLOR_USER, COLOR_LYRA, COLOR_BORDER, print_logo
)
from spinner import Spinner
from tools import (
    TOOLS, list_directory, read_file, write_file, execute_command
)
from config import get_api_key, reset_api_key

def main():
    # Load API Key securely
    api_key = get_api_key()
    
    url = "https://authx.astbyte.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    messages = []

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
                    "temperature": 0.7,
                    "tools": TOOLS
                }

                try:
                    response = requests.post(url, headers=headers, json=data)
                    spinner.stop()
                    
                    if response.status_code == 200:
                        resp_json = response.json()
                        message = resp_json["choices"][0]["message"]
                        
                        tool_calls = message.get("tool_calls")
                        if tool_calls:
                            # Append assistant's message call to history
                            messages.append(message)
                            
                            # Process each tool call sequentially
                            for tool_call in tool_calls:
                                func_name = tool_call["function"]["name"]
                                args_str = tool_call["function"]["arguments"]
                                try:
                                    args = json.loads(args_str)
                                except Exception:
                                    args = {}
                                
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
                                
                                # Append tool response to history
                                messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call["id"],
                                    "name": func_name,
                                    "content": result
                                })
                                
                                print(f"  {DIM}✅ Tool {func_name} selesai dieksekusi.{RESET}\n")
                            
                            # Fetch again with the tool results in context
                            continue
                        else:
                            ai_message = message.get("content")
                            if ai_message:
                                # Print stylized AI response
                                print(f"  {BOLD}{COLOR_LYRA}Lyra ✦{RESET} {WHITE}{ai_message}{RESET}\n")
                                # Add AI response to history
                                messages.append({"role": "assistant", "content": ai_message})
                            break
                    elif response.status_code == 401:
                        print(f"\n  {RED}[Error 401] API Key tidak valid atau tidak memiliki akses.{RESET}")
                        reset_choice = input("  Apakah Anda ingin mengatur ulang (reset) API Key Anda? (y/n): ").strip().lower()
                        if reset_choice == 'y':
                            reset_api_key()
                            api_key = get_api_key(force_prompt=True)
                            headers["Authorization"] = f"Bearer {api_key}"
                            # Continue the loop so it retries with the new key
                            continue
                        else:
                            # Pop user message if request failed
                            if messages[-1]["role"] == "user":
                                messages.pop()
                            break
                    else:
                        print(f"\n  {RED}[Error {response.status_code}] Gagal mendapatkan jawaban.{RESET}")
                        print(f"  {RED}{response.text}{RESET}\n")
                        # Pop user message if request failed
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