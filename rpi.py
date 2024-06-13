from gpiozero import LED, Button
import time
import os
import pygame
from PIL import Image
import json


screens_directory = 'screens'
IDLE_TIMEOUT = 5
json_file_path = 'gpio_config.json'


# Initialize pygame
os.environ['DISPLAY'] = ':0'  # Set the DISPLAY environment variable
os.environ['XDG_RUNTIME_DIR'] = '/run/user/1000'  # Set the XDG_RUNTIME_DIR environment variable
pygame.init()
screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
pygame.display.set_caption('Slideshow')
clock = pygame.time.Clock()

def read_gpio_config(json_file_path):
    with open(json_file_path, 'r') as json_file:
        config = json.load(json_file)
    return config

gpio_config = read_gpio_config(json_file_path)






leds = [LED(pin) for pin in gpio_config['leds']]
dt = Button(gpio_config['dt'], pull_up=True)
clk = Button(gpio_config['clk'], pull_up=True)
sw = Button(gpio_config['sw'], pull_up=True)

value = 0
previous_clk_state = clk.is_pressed

def display_image(pin):
    folder_path = os.path.join(screens_directory, str(pin))
    for file in os.listdir(folder_path):
        if file.endswith(('png', 'jpg', 'jpeg', 'bmp', 'gif')):
            image_path = os.path.join(folder_path, file)
            img = Image.open(image_path)
            img_width, img_height = img.size
            screen_width, screen_height = screen.get_size()

            # Calculate the scaling factor to maintain aspect ratio
            scale = min(screen_width / img_width, screen_height / img_height)

            # Calculate new dimensions while maintaining aspect ratio
            new_width = int(img_width * scale)
            new_height = int(img_height * scale)
            img = img.resize((new_width, new_height), Image.LANCZOS)

            # Convert the image to a pygame surface
            img_surface = pygame.image.fromstring(img.tobytes(), img.size, img.mode)

            # Calculate position to center the image on the screen
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
    global last_input_time
    global previous_clk_state
    global value

    current_clk_state = clk.is_pressed
    if current_clk_state != previous_clk_state:  # If the state has changed
        if not current_clk_state:  # Falling edge detected
            if dt.is_pressed:
                value = (value + 1) % len(gpio_config['leds'])
                print("clockwise", value)
            else:
                value = (value - 1) % len(gpio_config['leds'])
                print("anti-clockwise", value)
            update_leds()
        previous_clk_state = current_clk_state
    
        last_input_time = time.time()

    if not sw.is_pressed:
        # Handle switch press if needed
        pass

def update_leds():
    # First, turn off all LEDs except the currently selected one
    for i, led in enumerate(leds):
        if i != value:
            led.off()
    
    # Now handle the currently selected LED
    leds[value].on()
    img_surface, pos = display_image(gpio_config['leds'][value])
    if img_surface:
        smooth_transition(img_surface, pos)

def handle_swipe(start_pos, end_pos, screen_size):
    global value  # Declare value as global within the function
    global last_input_time

    start_x, start_y = start_pos
    end_x, end_y = end_pos
    screen_width, screen_height = screen. get_size()
    
    # Scale up the normalized coordinates
    start_x *= screen_width
    start_y *= screen_height
    end_x *= screen_width
    end_y *= screen_height
    
    dx = end_x - start_x
    if abs(dx) > 50:  # Swipe threshold
        if dx > 0:  # Swipe right
            value = (value + 1) % len(gpio_config['leds'][value])
            print("swipe right", value)
        else:  # Swipe left
            value = (value - 1) % len(gpio_config['leds'][value])
            print("swipe left", value)
        update_leds()
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