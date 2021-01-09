# TODO: Make into a stand-alone executable. Reference: https://www.pyinstaller.org/
import math
import heapq
import tkinter as tk
from tkinter.filedialog import askopenfilename, asksaveasfilename
from PIL import Image
from PIL import ImageDraw
from PIL import ImageChops

# How many times the image's size should the iterations cover?
num_iterations = 1.0
target_large_logic_display = None #Initilized when Tk is created
instruction_count = 1000
draws_per_flush = 10
redraw_timer_seconds = 10

LARGE_DISPLAY_DIMENSIONS = (176, 176)
SMALL_DISPLAY_DIMENSIONS = (80, 80)

def to_int_rgb(rgb):
    return (int(rgb[0]), int(rgb[1]), int(rgb[2]))

# Returns sum of all pixel values in the image
# If the provided image is the difference between two other images, this
# computes a reasonable value for how different they are
def compute_sum(img, quad):
    # TODO: Compute the average difference by component (ie. +/-rgb value)
    sum = 0
    for x in range(quad[0], quad[2]):
        for y in range(quad[1], quad[3]):
            pixel = img.getpixel((x, y))
            for c in pixel:
                sum += c
    return sum

# Returns the average (r,g,b) value of the quad in the image
def compute_average(img, quad):
    count = 0
    rgb_sum = [0, 0, 0]
    for x in range(quad[0], quad[2]):
        for y in range(quad[1], quad[3]):
            pixel = img.getpixel((x, y))
            rgb_sum[0] += pixel[0]
            rgb_sum[1] += pixel[1]
            rgb_sum[2] += pixel[2]
            count += 1

    avg_rgb = (
        rgb_sum[0] / count,
        rgb_sum[1] / count,
        rgb_sum[2] / count
    )
    return avg_rgb

# Input
# - Image to process at
# - Sub-rect of image to process
# - (rgb) color to compare to
# Output
# - Sum of abs delta of image to passed in rgb value
def compute_delta_from_value(img, rect, rgb):
    rgb_sum = [0, 0, 0]
    for x in range(rect[0], rect[2]):
        for y in range(rect[1], rect[3]):
            pixel = img.getpixel((x, y))
            rgb_sum[0] += abs(pixel[0] - rgb[0])
            rgb_sum[1] += abs(pixel[1] - rgb[1])
            rgb_sum[2] += abs(pixel[2] - rgb[2])

    return rgb_sum[0] + rgb_sum[1] + rgb_sum[2]


# Input
# - two rects (x1, y1, x2, y2)
def rects_overlap(r1, r2):
    # If one rectangle is on left side of other 
    if(r1[2] <= r2[0] or r2[2] <= r1[0]):
        return False
  
    # If one rectangle is above other
    if(r1[3] <= r2[1] or r2[3] <= r1[1]):
        return False

    return True

# Input
# - test_rect (improvement, (rect), (rgb))
# - List of (improvement, (rect), (rgb)) to compare to
def test_rect_options_for_overlap(test_rect, rect_list):
    for r in rect_list:
        if rects_overlap(test_rect[1], r[1]):
            return True
    return False

# Inputs
# - Ground truth image
# - In-progress image
# Outputs
# - Next rectangle to draw (improvment, rect, rgb)
def get_next_best_rects(ground_img, progress_img, rect_size, iterations, max_rects_to_return):
    # Compute difference between images
    delta_img = ImageChops.difference(ground_img, progress_img)
    h = ground_img.height
    w = ground_img.width

    # Evaluate different rects to see where the most improvement can happen
    # List of (improvement, (rect), (rgb))
    potential_options = []
    iters = max(iterations, 1)
    x_slices = math.ceil(iters * w / rect_size[0])
    y_slices = math.ceil(iters * h / rect_size[1])
    for y in range(0, y_slices):
        for x in range(0, x_slices):
            x1 = min(x * rect_size[0] / iters, w - rect_size[0] - 1)
            y1 = min(y * rect_size[1] / iters, h - rect_size[1] - 1)
            x2 = x1 + rect_size[0]
            y2 = y1 + rect_size[1]
            
            rect = (int(x1), int(y1), int(x2), int(y2))

            avg_rgb = to_int_rgb(compute_average(ground_img, rect))
            current_delta = compute_sum(delta_img, rect)
            delta_from_avg = compute_delta_from_value(ground_img, rect, avg_rgb)
            improvement = current_delta - delta_from_avg
            potential_options.append((improvement, rect, avg_rgb))
    
    best_options = []
    potential_options.sort()
    while len(potential_options) > 0 and len(best_options) < max_rects_to_return:
        rect = potential_options.pop()
        if (test_rect_options_for_overlap(rect, best_options) == False):
            best_options.append(rect)
    
    return best_options

# Inputs
# - Ground truth image
# - Max number of rectangles to use
# Outputs
# - Ordered list of rectangles (x1,y1,x2,y2) and colors (r,b,g,a)
def build_rectangle_list_from_image(img, max_num_rects):
    out_rects = []

    # New, empty image to be our canvas
    out_img = Image.new('RGB', (img.width, img.height))
    # ImageDraw object to facilitate drawing onto out_img
    out_draw = ImageDraw.Draw(out_img)

    while (len(out_rects) < max_num_rects):
        percent_done = len(out_rects) / max_num_rects
        t = math.pow(percent_done, 2.0)
        denom = 3.0 * (1 - t) + (img.width / 1.5) * (t)
        s = int(img.width / denom)
        size = (s, s)

        max_rects_to_return = min(20, max_num_rects - len(out_rects))
        next_rects = get_next_best_rects(img, out_img, size, num_iterations, max_rects_to_return)
        
        out_rects.extend(next_rects)
        for r in next_rects:
            out_draw.rectangle(xy=r[1], fill=r[2])
            print(s, r)
    
    out_img.save('out_img.png')

    return out_rects

# Returns array of strings
def get_mindustry_commands(rect_list, img, flush_frequency = 0):
    out_commands = []
    if redraw_timer_seconds == 0:
        out_commands.append("jump 2 equal done false")
        out_commands.append("end")
    out_commands.append("draw clear 0 0 0 0 0 0")

    height = img.height
    for i, r in enumerate(rect_list):
        out_commands.append("draw color {0} {1} {2} 255 0 0".format(r[2][0], r[2][1], r[2][2]))
        x = r[1][0]
        y = (height - 1) - r[1][3]
        # Add 1 to width and height because Mindustry addressing things in slightly different way than pillow
        w = abs(r[1][2] - x) + 1
        h = abs(r[1][1] - r[1][3]) + 1
        out_commands.append("draw rect {0} {1} {2} {3} 0 0".format(x, y, w, h))
        if (flush_frequency > 0) and ((i + 1) % flush_frequency == 0):
            out_commands.append("drawflush display1")
    out_commands.append("drawflush display1")
    if redraw_timer_seconds == 0:
        out_commands.append("set done true")
    else:
        out_commands.append("set countdown {0}".format(int(redraw_timer_seconds * 150 / 2)))
        out_commands.append("op sub countdown countdown 1")
        out_commands.append("jump {0} notEqual countdown 0".format(len(out_commands) - 1))

    return out_commands

def process_image(src):
    val = target_large_logic_display.get()
    if val == 0:
        dimensions = SMALL_DISPLAY_DIMENSIONS
    else:
        dimensions = LARGE_DISPLAY_DIMENSIONS

    max_rects = int((instruction_count - 5) / 2)
    if (draws_per_flush > 0):
        # Each flush takes up only half as many instructions as a rectangle
        max_rects -= int(max_rects / (draws_per_flush * 2.0))
    
    image = src.convert('RGB')
    base_img = image.resize(dimensions, resample = Image.BOX)

    rect_list = build_rectangle_list_from_image(base_img, max_rects)

    commands = get_mindustry_commands(rect_list, base_img, draws_per_flush)
    return commands


source_image = None

def open_file():
    """Open an image for processing."""
    filepath = askopenfilename(
        filetypes=[("Image Files", "*.jpg *.png *.bmp *.tga"), ("All Files", "*.*")]
    )
    if not filepath:
        return
    global source_image
    source_image = Image.open(filepath)
    window.title(f"img2min - {filepath}")

def convert_image():
    """Process the image."""
    global instruction_count
    instruction_count = int(frm_instruction_count.get())
    global num_iterations
    num_iterations = float(frm_iterations.get())
    commands = process_image(source_image)

    txt_edit.delete(1.0, tk.END)
    for s in commands:
        txt_edit.insert(tk.END, s + '\n')

window = tk.Tk()
window.title("Image to Mindustry Converter")
window.rowconfigure(0, minsize=400, weight=1)
window.columnconfigure(1, minsize=400, weight=1)

txt_edit = tk.Text(window)
fr_buttons = tk.Frame(window, relief=tk.RAISED, bd=2)
btn_open = tk.Button(fr_buttons, text="Open Image", command=open_file)
btn_save = tk.Button(fr_buttons, text="Convert", command=convert_image)

# Instruction Count
lbl_instruction_count = tk.Label(fr_buttons, text="Num Instructions")
frm_instruction_count = tk.Entry(fr_buttons, width=6)
frm_instruction_count.insert(0, instruction_count)

# Num Iterations
lbl_iterations = tk.Label(fr_buttons, text="Iterations")
frm_iterations = tk.Entry(fr_buttons, width=6)
frm_iterations.insert(0, num_iterations)

# Output Size
target_large_logic_display = tk.IntVar(window, value=0, name="Large Display")
chk_large_logic_display = tk.Checkbutton(
    master=fr_buttons,
    text="Large Logic Display (176x176)",
    variable=target_large_logic_display,
    onvalue=True,
    offvalue=False
)

btn_open.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
btn_save.grid(row=1, column=0, sticky="ew", padx=5)
lbl_instruction_count.grid(row=2, column=0)
frm_instruction_count.grid(row=2, column=1, sticky="ew", padx=5, pady=5)
lbl_iterations.grid(row=3, column=0)
frm_iterations.grid(row=3, column=1, sticky="ew", padx=5, pady=5)
chk_large_logic_display.grid(row=4)

fr_buttons.grid(row=0, column=0, sticky="ns")
txt_edit.grid(row=0, column=1, sticky="nsew")

window.mainloop()
