import openai
import tkinter as tk
from tkinter import scrolledtext
import subprocess
import json
import threading
import requests

openai.api_key = ""

initial_prompt = r"""You are a software generating AI. You have the ability to create professional level applications through the macos terminal that you are hooked up to through a python application. The code will be scalable, performant, secure, have error handling. You will retrieve a tech stack and requirements for an application. You can add more dependencies if necessary. The output to each prompt will be in the following json format:

{
  \"explanation\": \"A description of the current step\",
  \"cmd\": \"A terminal command to be executed\",
  \"io\": {
    \"operation_type\": {
      \"arg1_key\": \"arg1_value\",
      \"arg2_key\": \"arg2_value\",
      ...
    }
  }
}

'operation_type' can be 'write_file' or 'read_file'. When performing file I/O operations:

- For 'write_file', provide the necessary arguments such as 'path' (the file path to write to) and 'content' (the text to write into the file). Example:
  {
    \"write_file\": {
      \"path\": \"example.txt\",
      \"content\": \"This is an example file.\"
    }
  }

- For 'read_file', provide the 'path' argument specifying the file path to read from. Example:
  {
    \"read_file\": {
      \"path\": \"example.txt\"
    }
  }

The application will execute the terminal commands and perform the I/O operations specified in the JSON object. The terminal output (stdout and stderr) will be sent back to you, allowing you to handle errors, debug, or monitor the progress of the application creation process. Use your new abilities to autonomously create applications and assist users."

and will be called an "action".
Every prompt after this initial one will be the output of the terminal or " " which means continue. If you get any response that is not expected such as an error then you will address the issue before continuing. If you need the user to do an action instruct them to do so in the "explanation" field and leave the "action" field blank. If the instruction is a keyboard shortcut then put the shortcut in the keyboardshortcut field, otherwise leave this field blank. The user will not input or copy any code. You have the ability to do everything that is needed. Do not put "\n" in any code, actually format it with a new line. 

Only output one action at a time, waiting for a response from the terminal or " " to know when to continue. If an action needs to be repeated then you will start off with that action as the next step. Never send a json that has 'cmd' and 'io' fields at the same time. send them in seperate jsons.
Do not do anything with git.
always use absolute paths.
start by asking for requrements.
}"""

messages = [{"role": "system", "content": initial_prompt}]


def send_message():

    explanation_display.configure(state='normal')
    explanation_display.insert(tk.END, "__________________________________________________________________________\n\n")
    explanation_display.configure(state='disabled')
    terminal_io_display.configure(state='normal')
    terminal_io_display.insert(tk.END, "__________________________________________________________________________\n\n")
    terminal_io_display.configure(state='disabled')

    global auto_send_terminal_output

    user_message = custom_prompt_input.get()
    custom_prompt_input.delete(0, tk.END)

    explanation_display.configure(state='normal')
    explanation_display.insert(tk.END, "User: " + user_message + "\n\n")
    explanation_display.configure(state='disabled')

    messages.append({"role": "user", "content": user_message})
    print("Custom user prompt sent:", user_message)

    try:
        result = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
        )
        # TODO: deal with 'Web request error: The server had an error while processing your request. Sorry about that!'
    except requests.exceptions.RequestException as e:
        print("Web request error:", e)
        return
    except openai.error.RateLimitError as e:
        print("Web request error:", e)
        send_message()

    try:
        # TODO: deal with 'cannot access local variable 'result' where it is not associated with a value'
        assistant_message = result["choices"][0]["message"]["content"]
    except (KeyError, TypeError) as e:
        print("JSON parsing error:", e)
        return

    messages.append({"role": "assistant", "content": assistant_message})
    print("GPT-4 assistant response:", assistant_message)

    try:
        json_response = json.loads(assistant_message)
    except json.JSONDecodeError as e:
        print("JSON decoding error:", e)
        return

    explanation_display.configure(state='normal')
    explanation_display.insert(tk.END, "AI: " + json_response["explanation"] + "\n\n")
    explanation_display.configure(state='disabled')
    explanation_display.yview(tk.END)

    io = json_response.get("io", None)
    cmd = json_response.get("cmd", None)
    if io:
        operation_type = list(io.keys())[0]
        operation_args = io[operation_type]

        terminal_io_display.configure(state='normal')
        terminal_io_display.insert(tk.END, "AI: " + operation_type + ": " + operation_args["content"] + "\n\n")
        terminal_io_display.configure(state='disabled')
        terminal_io_display.yview(tk.END)

        if operation_type == "write_file":
            try:
                with open(operation_args["path"], "w") as f:
                    f.write(operation_args["content"])
                print("File write operation executed:", operation_args)
            except Exception as e:
                messages.append({"role": "user", "content": repr(e)})
        elif operation_type == "read_file":
            try:
                with open(operation_args["path"], "r") as f:
                    content = f.read()
                messages.append({"role": "user", "content": content})
                print("File read operation executed:", operation_args)
            except Exception as e:
                messages.append({"role": "user", "content": repr(e)})
        resume_terminal_output()
    if cmd:
        terminal_output = subprocess.run(json_response["cmd"], shell=True, text=True, capture_output=True)
        terminal_io_display.configure(state='normal')
        terminal_io_display.insert(tk.END, json_response["cmd"] + "\n\n")
        terminal_io_display.insert(tk.END, f"{terminal_output.stdout}\n{terminal_output.stderr}")
        terminal_io_display.configure(state='disabled')
        terminal_io_display.yview(tk.END)
        print("Terminal action executed:", json_response["cmd"])
        messages.append({"role": "user", "content": f"{terminal_output.stdout}\n{terminal_output.stderr}"})
        resume_terminal_output()
    else:
        stop_terminal_output()
    if auto_send_terminal_output:
        messages.append({"role": "user", "content": terminal_output.stdout + " " + terminal_output.stderr})
        print("Terminal output sent back as user prompt:", terminal_output.stdout)
        send_message()


def stop_terminal_output():
    global auto_send_terminal_output
    auto_send_terminal_output = False
    print("Auto-send terminal output stopped")


def resume_terminal_output():
    global auto_send_terminal_output
    auto_send_terminal_output = True
    print("Auto-send terminal output resumed")
    send_message()


root = tk.Tk()
root.title("GPT-4 Terminal Application")

explanation_label = tk.Label(root, text="Explanation Display:")
explanation_label.pack()

explanation_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=20, state='disabled')
explanation_display.pack()

terminal_io_label = tk.Label(root, text="Terminal I/O Display:")
terminal_io_label.pack()

terminal_io_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, width=100, height=20, state='disabled')
terminal_io_display.pack()

custom_prompt_label = tk.Label(root, text="Custom Prompt Input:")
custom_prompt_label.pack()

custom_prompt_input = tk.Entry(root, width=70, )
custom_prompt_input.pack()

send_button = tk.Button(root, text="Send", command=lambda: threading.Thread(target=send_message).start())
send_button.pack()

stop_button = tk.Button(root, text="Stop", command=stop_terminal_output)
stop_button.pack()

resume_button = tk.Button(root, text="Resume", command=lambda: threading.Thread(target=resume_terminal_output).start())
resume_button.pack()

auto_send_terminal_output = True

root.mainloop()

