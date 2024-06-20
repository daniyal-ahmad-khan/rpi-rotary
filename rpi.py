from gpiozero import LED, Button
import time
import os
import pygame
from PIL import Image
import json

# Initialize pygame
os.environ['DISPLAY'] = ':0'
os.environ['XDG_RUNTIME_DIR'] = '/run/user/1000'
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption('Slideshow')
clock = pygame.time.Clock()
pygame.mouse.set_visible(False)

# Read configuration from JSON file
def read_gpio_config(json_file_path):
    with open(json_file_path, 'r') as json_file:
        return json.load(json_file)

json_file_path = 'gpio_config.json'
gpio_config = read_gpio_config(json_file_path)

PULSES_PER_360 = 20
screens_directory = gpio_config.get('screens_directory', 'screens')
IDLE_TIMEOUT = gpio_config.get('IDLE_TIMEOUT', 5)
DEGREES_PER_SECTION = gpio_config.get('DEGREES_PER_SECTION', 30)
STEPS_PER_SECTION = int(round((PULSES_PER_360 / 360) * DEGREES_PER_SECTION))

# Initialize components
leds = [LED(pin) for pin in gpio_config['leds']]
dt = Button(gpio_config['dt'], pull_up=True)
clk = Button(gpio_config['clk'], pull_up=True)
sw = Button(gpio_config['sw'], pull_up=True)

# State variables
value = 0
previous_clk_state = clk.is_pressed
encoder_position = 0
image_index = 0  # Track the index of the currently displayed image within the directory

def display_image(pin, index):
    folder_path = os.path.join(screens_directory, str(pin))
    files = [f for f in os.listdir(folder_path) if f.endswith(('png', 'jpg', 'jpeg', 'bmp', 'gif'))]
    if files:
        image_path = os.path.join(folder_path, files[index % len(files)])
        img = Image.open(image_path)
        img_width, img_height = img.size
        screen_width, screen_height = screen.get_size()
        scale = min(screen_width / img_width, screen_height / img_height)
        new_width = int(img_width * scale)
        new_height = int(img_height * scale)
        img = img.resize((new_width, new_height), Image.LANCZOS)
        img_surface = pygame.image.fromstring(img.tobytes(), img.size, img.mode)
        x_pos = (screen_width - new_width) // 2
        y_pos = (screen_height - new_height) // 2
        return img_surface, (x_pos, y_pos)
    return None, (0, 0)
def display_idle_image():
    idle_path = os.path.join(screens_directory, 'idle')
    for file in os.listdir(idle_path):
        if file.endswith(('png', 'jpg', 'jpeg', 'bmp', 'gif')):
            image_path = os.path.join(idle_path, file)
            img = Image.open(image_path)
            img_width, img_height = img.size
            screen_width, screen_height = screen.get_size()

            scale = min(screen_width / img_width, screen_height / img_height)
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            img = img.resize((new_width, new_height), Image.LANCZOS)
            img_surface = pygame.image.fromstring(img.tobytes(), img.size, img.mode)

            x_pos = (screen_width - new_width) // 2
            y_pos = (screen_height - new_height) // 2

            screen.fill((0, 0, 0))
            screen.blit(img_surface, (x_pos, y_pos))
            pygame.display.update()

def turn_on_all_leds():
    for led in leds:
        led.on()

def smooth_transition(new_image, pos):
    for alpha in range(0, 256, 35):  # Increase step size to make the transition faster
        screen.fill((0, 0, 0))
        new_image.set_alpha(alpha)
        screen.blit(new_image, pos)
        pygame.display.update()
        clock.tick(60)


def rotary_changed():
    global value, previous_clk_state, encoder_position, image_index, last_input_time
    current_clk_state = clk.is_pressed
    if current_clk_state != previous_clk_state:
        if not current_clk_state:
            if dt.is_pressed:
                encoder_position += 1
            else:
                encoder_position -= 1
            if abs(encoder_position) >= STEPS_PER_SECTION:
                increment = 1 if encoder_position > 0 else -1
                value = (value + increment) % len(gpio_config['leds'])
                encoder_position = 0
                image_index = 0
                update_display()
                last_input_time = time.time()  # Update the last interaction time
        previous_clk_state = current_clk_state


    if not sw.is_pressed:
        # Handle switch press if needed
        pass
def update_display():
    global last_input_time
    img_surface, pos = display_image(gpio_config['leds'][value], image_index)
    update_leds()  # Ensure this is called to update the LED states
    if img_surface:
        smooth_transition(img_surface, pos)
    last_input_time = time.time()  # Reset the idle timer whenever the display updates
def update_leds():
    # Turn off all LEDs except the currently selected one
    for i, led in enumerate(leds):
        if i != value:
            led.off()
        else:
            led.on()  # Ensure the correct LED is on

def handle_swipe(start_pos, end_pos, screen_size):
    global image_index
    global last_input_time
    start_x, start_y = start_pos
    end_x, end_y = end_pos
    screen_width, screen_height = screen_size
    
    # Scale up the normalized coordinates
    start_x *= screen_width
    start_y *= screen_height
    end_x *= screen_width
    end_y *= screen_height
    
    dx = end_x - start_x
    if abs(dx) > 50:  # Swipe threshold
        if dx > 0:  # Swipe right
            image_index += 1
        else:  # Swipe left
            image_index -= 1
        update_display()
        last_input_time = time.time()

# # Initial LED update to turn on the first LED
# update_leds()

swipe_start_pos = None
display_idle_image()
turn_on_all_leds()
last_input_time = time.time()
while True:
    current_time = time.time()
    if current_time - last_input_time > IDLE_TIMEOUT:
        display_idle_image()
        turn_on_all_leds()
    rotary_changed()
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            exit()
        elif event.type == pygame.FINGERDOWN:
            swipe_start_pos = (event.x, event.y)
        elif event.type == pygame.FINGERUP and swipe_start_pos is not None:
            swipe_end_pos = (event.x, event.y)
            handle_swipe(swipe_start_pos, swipe_end_pos, screen.get_size())
            swipe_start_pos = None
    time.sleep(0.001)