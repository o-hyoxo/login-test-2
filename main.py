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
import json
import google.generativeai as genai
from PIL import Image
import io

# New API Configuration for custom endpoint and key
API_URL = "https://new.281182.xyz/v1beta/models/gemini-2.5-pro:generateContent"
API_KEY = "sk-jFRMWzq8RG9im8FXZah4cIn5bMaC8noWLEythpLaMLP09t3E"

# The genai library is kept for other functions, but the failing one will use requests
try:
    genai.configure(api_key=API_KEY)
    print("Successfully configured AI with standard endpoint for fallback functions.")
except Exception as e:
    print(f"Could not configure genai: {e}")

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
    """Asks the AI model to solve a reCAPTCHA image challenge using a direct HTTP request."""
    headers = {
        "Content-Type": "application/json",
    }
    
    prompt = """You are an expert reCAPTCHA solver with advanced computer vision capabilities. 
Analyze this reCAPTCHA challenge image carefully:
1. READ THE INSTRUCTION: Look at the top of the image for the challenge instruction.
2. UNDERSTAND THE GRID: The image contains a grid of squares (3x3 or 4x4).
3. IDENTIFY OBJECTS: Carefully examine each square for the requested object.
4. OUTPUT FORMAT: Return ONLY the numbers of squares containing the object, separated by hyphens. Example: "1-3-5".
Now analyze the image and provide the square numbers."""

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt},
                    {
                        "inline_data": {
                            "mime_type": "image/png",
                            "data": base64_image
                        }
                    }
                ]
            }
        ]
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(f"{API_URL}?key={API_KEY}", headers=headers, json=payload, timeout=60)
            
            if response.status_code == 200:
                response_json = response.json()
                result = response_json['candidates'][0]['content']['parts'][0]['text'].strip()
                
                numbers_only = re.findall(r'\d+', result)
                if numbers_only:
                    return '-'.join(numbers_only)
                else:
                    # If no numbers found, return the raw text in case it's an error message or something else
                    return result
            else:
                print(f"Attempt {attempt + 1} failed with status {response.status_code}: {response.text}")

        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed with network error: {e}")
        except (KeyError, IndexError) as e:
            print(f"Attempt {attempt + 1} failed parsing response: {e} - Response: {response.text}")
        except Exception as e:
            print(f"An unexpected error occurred on attempt {attempt + 1}: {e}")

        if attempt < max_retries - 1:
            time.sleep(2)

    print("All attempts failed, returning empty result")
    return "0"

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
    """Handles the reCAPTCHA interaction flow, returning True on success and False on failure."""
    number_of_challenges = 0
    try:
        # Wait for the main reCAPTCHA iframe (the checkbox)
        recaptcha_frame = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/anchor']"))
        )
        driver.switch_to.frame(recaptcha_frame)
        
        # Click the "I'm not a robot" checkbox
        checkbox = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
        )
        checkbox.click()
        driver.switch_to.default_content()
        time.sleep(3) # Wait for the challenge iframe to potentially appear
        
        # Check if a visual challenge (bframe) has appeared
        try:
            challenge_iframe = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/bframe']"))
            )
            print("Challenge detected, processing...")
            
            while True:
                number_of_challenges += 1
                if number_of_challenges > 10:
                    print("Reached maximum number of reCAPTCHA attempts (10). Aborting.")
                    return False # Indicate failure
                    
                filename = f'recaptcha_challenge_{number_of_challenges}.png'
                
                time.sleep(random.uniform(2.5, 4.0))
                challenge_iframe.screenshot(filename)
                base64_string = encode_image_to_base64(filename)
                
                print(f"Processing challenge {number_of_challenges}...")
                answer = ask_recaptcha_to_chatgpt(base64_string)
                print(f"AI response: {answer}")

                if not re.match(r'^[\d\s,-]+$', answer):
                    print("AI returned a non-numeric answer. Refreshing challenge...")
                    driver.switch_to.frame(challenge_iframe)
                    try:
                        reload_button = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "recaptcha-reload-button")))
                        reload_button.click()
                    except Exception as reload_err:
                        print(f"Could not find or click reload button: {reload_err}")
                    driver.switch_to.default_content()
                    continue

                array = re.split(r'[,\s-]+', answer)
                driver.switch_to.frame(challenge_iframe)
                
                all_images = driver.find_elements(By.CSS_SELECTOR, "td")
                print(f"Found {len(all_images)} image tiles")
                
                for each_element in array:
                    try:
                        if each_element:
                            index = int(each_element.strip())
                            if 0 <= index < len(all_images):
                                all_images[index].click()
                                print(f"Clicked tile {index}")
                                time.sleep(random.uniform(0.4, 0.8))
                    except (ValueError, IndexError) as e:
                        print(f"Error clicking tile '{each_element}': {e}")
                
                driver.find_element(By.ID, "recaptcha-verify-button").click()
                driver.switch_to.default_content()
                time.sleep(5) # Wait for verification
                
                # Check if the checkbox is now checked (success)
                driver.switch_to.frame(recaptcha_frame)
                if driver.find_elements(By.CSS_SELECTOR, ".recaptcha-checkbox-checked"):
                    print("reCAPTCHA solved successfully!")
                    driver.switch_to.default_content()
                    return True # Indicate success
                driver.switch_to.default_content()
                
                # Re-locate challenge iframe for the next loop
                challenge_iframe = WebDriverWait(driver, 5).until(EC.presence_of_element_located((By.CSS_SELECTOR, "iframe[src*='recaptcha/api2/bframe']")))

        except:
            # This block is reached if the bframe (visual challenge) does not appear after clicking the checkbox.
            # This means the checkbox click was enough to solve it.
            print("No visual challenge required, reCAPTCHA likely passed.")
            return True

    except Exception as ex:
        print(f"An error occurred in handle_recaptcha: {ex}")
        driver.switch_to.default_content()
        return False # Indicate failure

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
        recaptcha_solved = handle_recaptcha(driver)
        
        if recaptcha_solved:
            print("reCAPTCHA passed. Attempting to click final 'Renew' button...")
            final_renew_button = WebDriverWait(driver, 20).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(@class, 'swal2-confirm')]"))
            )
            driver.execute_script("arguments[0].click();", final_renew_button)
            print("Clicked final 'Renew' button.")
            
            time.sleep(5) # Wait to observe the result
            print("Renewal process appears to be complete.")
            driver.save_screenshot('renewal_success.png')
            print("Saved screenshot to 'renewal_success.png'")
        else:
            # If reCAPTCHA failed, raise an exception to fail the whole process.
            raise Exception("Failed to solve reCAPTCHA after multiple attempts.")

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
