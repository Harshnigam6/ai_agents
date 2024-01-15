import tkinter as tk
from tkinter.simpledialog import askstring
from tkinter import scrolledtext
from PIL import ImageGrab
import os

from openai import OpenAI
import base64
import requests
import time


query = "Move the block T up or down so that it aligned with  other blocks and a reader can read the word. you should output only 'up T' or 'down T"
# query = ""

class ChatGPTInterface:
    def __init__(self, api_key):
        self.api_key = api_key

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def describe_image(self, image_path):
        base64_image = self.encode_image(image_path)

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }

        payload = {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": f"{query}"
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        return response.json()

class DraggableBlock:
    def __init__(self, canvas, x, y, text):
        self.canvas = canvas
        self.text = text
        self.x = x  # Store x coordinate
        self.y = y  # Store y coordinate
        self.shape = canvas.create_rectangle(x, y, x+50, y+50, fill="blue", tags=text)
        self.label = canvas.create_text(x+25, y+25, text=text, tags=text)
        self.drag_data = {"x": 0, "y": 0}
        
        self.canvas.tag_bind(self.text, "<ButtonPress-1>", self.on_start)
        self.canvas.tag_bind(self.text, "<ButtonRelease-1>", self.on_drop)
        self.canvas.tag_bind(self.text, "<B1-Motion>", self.on_drag)

    def on_start(self, event):
        # Record the item and its location
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drag(self, event):
        # Compute how much the mouse has moved
        delta_x = event.x - self.drag_data["x"]
        delta_y = event.y - self.drag_data["y"]
        # Move the object the appropriate amount
        self.canvas.move(self.text, delta_x, delta_y)
        # Record the new position
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drop(self, event):
        # Reset the drag information
        self.drag_data = {"x": 0, "y": 0}

    def move_up(self, distance=20):
        self.canvas.move(self.shape, 0, -distance)
        self.canvas.move(self.label, 0, -distance)

    def move_down(self, distance=20):
        self.canvas.move(self.shape, 0, distance)
        self.canvas.move(self.label, 0, distance)


class DraggableLine:
    def __init__(self, canvas, x1, y1, x2, y2, width, fill, tag):
        self.canvas = canvas
        self.tag = tag
        self.line = canvas.create_line(x1, y1, x2, y2, width=width, fill=fill, tags=tag)
        self.drag_data = {"x": 0, "y": 0}

        self.canvas.tag_bind(self.tag, "<ButtonPress-1>", self.on_start)
        self.canvas.tag_bind(self.tag, "<ButtonRelease-1>", self.on_drop)
        self.canvas.tag_bind(self.tag, "<B1-Motion>", self.on_drag)

    def on_start(self, event):
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drag(self, event):
        delta_x = event.x - self.drag_data["x"]
        delta_y = event.y - self.drag_data["y"]
        self.canvas.move(self.tag, delta_x, delta_y)
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def on_drop(self, event):
        self.drag_data = {"x": 0, "y": 0}



class BlockGenerationPanel:
    def __init__(self, master, generate_callback):
        self.frame = tk.Frame(master, height=30)  # Set a fixed height for the input frame
        self.frame.pack(side=tk.TOP, fill=tk.X)  # Pack to the top of the window

        self.label = tk.Label(self.frame, text="Block Letter:")
        self.label.pack(side=tk.LEFT, padx=5)

        self.entry = tk.Entry(self.frame, width=3)  # Width=3 for a single character
        self.entry.pack(side=tk.LEFT, padx=5)

        self.button = tk.Button(self.frame, text="Generate Block", command=generate_callback)
        self.button.pack(side=tk.LEFT, padx=5)

    def get_block_letter(self):
        # Method to retrieve the block letter from the entry
        return self.entry.get().strip().upper()

    def clear_entry(self):
        # Method to clear the entry widget
        self.entry.delete(0, tk.END)


class ChatPanel:
    def __init__(self, master, submit_callback, generate_callback):
        self.frame = tk.Frame(master, width=100)  # set the width of the chat panel
        self.frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)  # don't allow the panel to expand to fill space

        # Label and entry for the instructions
        self.instruction_frame = tk.Frame(self.frame)
        self.instruction_frame.pack(side=tk.TOP, fill=tk.X)
        self.label = tk.Label(self.instruction_frame, text="Instructions:")
        self.label.pack(side=tk.LEFT)
        self.entry = tk.Entry(self.instruction_frame)
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.entry.bind("<Return>", submit_callback)  # Bind the entry to the submit callback

        # Text area for chat history
        self.text_area = scrolledtext.ScrolledText(self.frame, state='disabled', wrap=tk.WORD)
        self.text_area.pack(expand=True, fill='both')

    def update_chat(self, message):
        # Insert the message to the chat history
        self.text_area.config(state='normal')
        self.text_area.insert(tk.END, message + "\n")
        self.text_area.config(state='disabled')
        self.text_area.yview(tk.END)
        

class BlockApp:
    def __init__(self, master):

        self.counter = 0
        
        self.master = master
        self.master.title("Block Canvas and Chat App")

        # Initialize chat panel with callbacks for processing commands and generating blocks
        self.chat_panel = ChatPanel(self.master, self.process_command, self.generate_block)
        self.block_generation_panel = BlockGenerationPanel(master, self.generate_block)


        self.block_size = 50
        
        # Right panel for canvas
        self.canvas = tk.Canvas(master, width=800, height=400)
        self.canvas.pack(side=tk.LEFT, expand=True, fill='both')

        # Initialize the list to keep track of the current blocks
        self.current_blocks = []
        
        # Calculate blocks per row after canvas has been drawn
        self.canvas.update()
        self.blocks_per_row = self.canvas.winfo_width() // 50

        # self.create_movable_lines()

        self.chatgpt = ChatGPTInterface(api_key="")

        
    def generate_block(self):
        # This method will be called when the "Generate Block" button is clicked
        block_letter = self.block_generation_panel.get_block_letter()
        if block_letter and len(block_letter) == 1 and block_letter.isalpha():
            x, y = self.find_empty_space_for_block()
            new_block = DraggableBlock(self.canvas, x, y, block_letter)  # Create a new block instance
            self.current_blocks.append(new_block) 
            print(self.current_blocks)
            self.chat_panel.update_chat(f"Generated block: {block_letter}")
            self.block_generation_panel.clear_entry()
        else:
            self.chat_panel.update_chat("Enter a single letter to generate a block.")

            

    def process_command(self, event):
        self.counter = self.counter + 1

        # Take screenshot and get description
        self.take_screenshot()
        image_path = rf"C:\Users\HarshNigam\Documents\ai_agents\{self.counter}.png"

        if os.path.exists(image_path):
            chatgpt_response = self.chatgpt.describe_image(image_path)

            # Wait for response or timeout
            start_time = time.time()
            while time.time() - start_time < 5:  # 5 seconds timeout
                if chatgpt_response:
                    break
                time.sleep(0.1)  # Sleep a bit before checking again
        else:
            print(f"File not found: {image_path}")  # Debugging print
            return  # Exit the function if the file is not found

        # Get the text from the chat panel's entry widget
        command = self.chat_panel.entry.get().strip().upper()
        try:
            command = chatgpt_response['choices'][0]['message']['content']
        except:
            pass
        print(command)
        # Parse the command and execute the action
        parts = command.split()
        if len(parts) == 2:
            action, block_letter = parts
            print(self.current_blocks, block_letter, "current")
            # Ensure the block letter is a single character and a letter
            if len(block_letter) == 1 and block_letter.isalpha():
                # Find the corresponding block on the canvas
                for block in self.current_blocks:
                    if block.text == block_letter:
                        if action == 'up':
                            block.move_up()
                            self.chat_panel.update_chat(f"AI Agent: Moved block {block_letter} up.")
                            break
                        elif action == 'down':
                            block.move_down()
                            self.chat_panel.update_chat(f"AI Agent: Moved block {block_letter} down.")
                            break
                else:
                    # Else clause of the for loop, executes if no break was hit, meaning no block was found
                    self.chat_panel.update_chat(f"No block with letter {block_letter} found.")
            else:
                self.chat_panel.update_chat("Block letter must be a single alphabetic character.")
        else:
            self.chat_panel.update_chat("Invalid command. Format is: <ACTION> <BLOCK_LETTER>")

        # Clear the entry widget
        self.chat_panel.entry.delete(0, tk.END)


    def find_empty_space_for_block(self):
        # Calculate the next grid position based on current blocks
        next_block_num = len(self.current_blocks)
        row = next_block_num // self.blocks_per_row
        col = next_block_num % self.blocks_per_row

        # Convert grid position to canvas coordinates
        x = col * self.block_size + 10  # Plus 10 for a small margin
        y = row * self.block_size + 10

        # Return the calculated position
        return x, y
    
    def take_screenshot(self):
        self.canvas.update_idletasks()  # Update the canvas to ensure it is redrawn
        self.capture_canvas()  # Directly capture the canvas

    def capture_canvas(self):
        x = self.canvas.winfo_rootx()
        y = self.canvas.winfo_rooty()
        x1 = x + self.canvas.winfo_width()
        y1 = y + self.canvas.winfo_height()
        path = rf"C:\Users\HarshNigam\Documents\ai_agents\{self.counter}.png"
        ImageGrab.grab(bbox=(950, 80, 1920, 1000)).save(path)

    def create_movable_lines(self):
        # Calculate the middle of the canvas
        canvas_width = self.canvas.winfo_reqwidth()
        middle_x = canvas_width // 2
        line_length = 300  # Length of each line
        line_width = 10  # Width of each line

        # Create two DraggableLine instances
        self.lines = []
        self.lines.append(DraggableLine(self.canvas, middle_x - line_length, middle_x - line_width,
                                        middle_x + line_length, middle_x - line_width,
                                        width=line_width, fill="red", tag="line1"))
        self.lines.append(DraggableLine(self.canvas, middle_x - line_length, middle_x + line_width,
                                        middle_x + line_length, middle_x + line_width,
                                        width=line_width, fill="red", tag="line2"))





root = tk.Tk()
app = BlockApp(root)
root.mainloop()
