import argparse
import os
import time
import random
import requests
import re
import base64
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.firefox.options import Options
import google.generativeai as genai
from PIL import Image
import io

# New API Configuration for custom endpoint and key
API_URL = "new.281182.xyz"
API_KEY = "sk-jFRMWzq8RG9im8FXZah4cIn5bMaC8noWLEythpLaMLP09t3E"

try:
    # Attempt to configure with a custom endpoint. This might require a specific library version.
    genai.configure(
        api_key=API_KEY,
        client_options={"api_endpoint": API_URL}
    )
    print("Successfully configured AI with custom endpoint.")
except TypeError:
    # Fallback for older library versions that don't support client_options
    print("Warning: Could not set custom API endpoint via client_options. Using default Google endpoint with the provided key.")
    genai.configure(api_key=API_KEY)

def average_of_array(arr):
    if not arr:
        return 0  # Handle edge case of empty array
    sum_elements = sum(arr)
    average = sum_elements / len(arr)
    return average - 5

def encode_image_to_base64(image_path):
    """Encodes an image file to a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def ask_recaptcha_to_chatgpt(base64_image):
    """Asks the AI model to solve a reCAPTCHA image challenge."""
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    image_data = base64.b64decode(base64_image)
    image = Image.open(io.BytesIO(image_data))
    
    prompt = """You are an expert reCAPTCHA solver with advanced computer vision capabilities. 

Analyze this reCAPTCHA challenge image carefully:

1. READ THE INSTRUCTION: Look at the top of the image for the challenge instruction (e.g., "Select all squares with cars", "Click on all images with traffic lights", etc.)

2. UNDERSTAND THE GRID: The image contains a grid of squares (usually 3x3=9 squares or 4x4=16 squares)
   - For 3x3 grid: squares are numbered 0-8 (top-left to bottom-right, row by row)
   - For 4x4 grid: squares are numbered 0-15 (top-left to bottom-right, row by row)

3. IDENTIFY OBJECTS: Carefully examine each square and identify if it contains the requested object.

4. OUTPUT FORMAT: Return ONLY the numbers of squares containing the requested object, separated by hyphens.
   Examples: "1-3-5" or "0-2-7-8-12" or "4"
   
5. BE PRECISE: Double-check your answer. Accuracy is critical.

Now analyze the image and provide the square numbers that contain the requested object."""
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content([prompt, image])
            result = response.text.strip()
            
            numbers_only = re.findall(r'\d+', result)
            if numbers_only:
                return '-'.join(numbers_only)
            else:
                return result
                
        except Exception as e:
            print(f"Attempt {attempt + 1} failed: {e}")
            if attempt == max_retries - 1:
                print("All attempts failed, returning empty result")
                return "0"
            time.sleep(2)

def ask_text_to_chatgpt(base64_image):
    """Asks the AI model to extract text from a simple captcha image."""
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    image_data = base64.b64decode(base64_image)
    image = Image.open(io.BytesIO(image_data))
    
    prompt = "You are a captcha solver. Look at this image and extract only the text/characters shown in the captcha. Return only the characters you see, nothing else."
    
    response = model.generate_content([prompt, image])
    return response.text.strip()

def ask_2captcha_text_question(question_text):
    """Asks the AI model to answer a text-based captcha question."""
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    prompt = f"You are answering a text captcha question. Answer the following question with a short, direct answer: {question_text}. Provide only the answer, no explanations."
    
    response = model.generate_content(prompt)
    return response.text.strip()

def ask_slide_to_chatgpt(base64_image):
    """Asks the AI model to solve a slider puzzle."""
    model = genai.GenerativeModel('gemini-2.5-pro')
    
    image_data = base64.b64decode(base64_image)
    image = Image.open(io.BytesIO(image_data))
    
    prompt = ("There is an slider button in the page and there is an empty gray space on puzzle. You should give "
              "give me how many pixels should i slide to complete the puzzle. The total width is 210 pixels. "
              "Give me only number of pixels in integer 50 up to 210 pixels. "
              "Analyze the slider puzzle and determine the exact pixel distance needed to complete it.")
    
    response = model.generate_content([prompt, image])
    return response.text

def handle_recaptcha(driver):
    """Handles the reCAPTCHA interaction flow."""
    number_of_challenges = 0
    try:
        recaptcha_frame = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/anchor']"))
        )
        driver.switch_to.frame(recaptcha_frame)
        
        checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
        )
        checkbox.click()
        driver.switch_to.default_content()
        time.sleep(3)
        
        try:
            challenge_iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/bframe']"))
            )
            print("Challenge detected, processing...")
            
            while True:
                try:
                    number_of_challenges += 1
                    filename = f'recaptcha_challenge_{number_of_challenges}.png'
                    
                    time.sleep(3)
                    challenge_iframe.screenshot(filename)
                    base64_string = encode_image_to_base64(filename)
                    
                    print(f"Processing challenge {number_of_challenges}...")
                    answer = ask_recaptcha_to_chatgpt(base64_string)
                    print(f"AI response: {answer}")
                    
                    array = re.split(r'[,\s-]+', answer)
                    
                    driver.switch_to.frame(challenge_iframe)
                    
                    table = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "table[class*='rc-imageselect-table-']"))
                    )
                    
                    if table:
                        all_images = table.find_elements(By.CSS_SELECTOR, "td")
                        print(f"Found {len(all_images)} image tiles")
                        
                        for each_element in array:
                            try:
                                index = int(each_element.strip())
                                if 0 <= index < len(all_images):
                                    all_images[index].click()
                                    print(f"Clicked tile {index}")
                                    time.sleep(0.5)
                            except (ValueError, IndexError) as e:
                                print(f"Error clicking tile {each_element}: {e}")
                        
                    verify_button = WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.ID, "recaptcha-verify-button"))
                    )
                    verify_button.click()
                    
                    driver.switch_to.default_content()
                    time.sleep(7)
                    
                    try:
                        driver.switch_to.frame(recaptcha_frame)
                        if driver.find_elements(By.CSS_SELECTOR, ".recaptcha-checkbox-checked"):
                            print("reCAPTCHA solved successfully!")
                            driver.switch_to.default_content()
                            break
                        driver.switch_to.default_content()
                    except:
                        pass
                        
                    challenge_iframe = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/bframe']"))
                    )
                except Exception as ex:
                    print(f"Challenge loop error: {ex}")
                    driver.switch_to.default_content()
                    break
                    
        except:
            print("No challenge required, reCAPTCHA completed by checkbox.")
            
    except Exception as ex:
        print(f"reCAPTCHA handling error: {ex}")
        driver.switch_to.default_content()
        raise

def renew_server(driver):
    """Automates the server renewal process on host2play.gratis."""
    url = "https://host2play.gratis/server/renew?i=f6fd4003-5a68-40f6-9ef3-a1d404fbfd80"
    print(f"Navigating to {url}")
    try:
        driver.get(url)
        
        print("Looking for 'Renew server' button...")
        renew_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Renew server')]"))
        )
        renew_button.click()
        print("Clicked 'Renew server' button.")
        
        print("Waiting for reCAPTCHA...")
        handle_recaptcha(driver)
        
        print("Looking for final 'Renew' button...")
        final_renew_button = WebDriverWait(driver, 20).until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'swal2-confirm')]"))
        )
        final_renew_button.click()
        print("Clicked final 'Renew' button.")
        
        time.sleep(5)
        print("Renewal process appears to be complete.")
        driver.save_screenshot('renewal_success.png')
        print("Saved screenshot to 'renewal_success.png'")

    except Exception as e:
        print(f"An error occurred during the renewal process: {e}")
        driver.save_screenshot('renewal_error.png')
        print("Saved error screenshot to 'renewal_error.png'")
        raise

def main():
    parser = argparse.ArgumentParser(description="Advanced captcha bypass and automation tool.")
    parser.add_argument('task', choices=['renew'],
                        help="Specify the task to run. Currently only 'renew' is supported.")
    args = parser.parse_args()

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    driver.set_window_size(1920, 1080)

    try:
        if args.task == 'renew':
            renew_server(driver)
    finally:
        print("Quitting driver.")
        driver.quit()

if __name__ == "__main__":
    main()
