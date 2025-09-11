import argparse
import os
import time
import random
import requests
import re
import base64
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService # Keep this import
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
# --- FIX: webdriver-manager is no longer needed and can be removed ---
# from webdriver_manager.firefox import GeckoDriverManager

# Load environment variables from .env file
load_dotenv()

# Fetch API configuration from environment variables
CHATGPT_API_URL = os.getenv("CHATGPT_API_URL", "https://ai2gpt.oiio.nyc.mn/v1/chat/completions")
CHATGPT_API_KEY = os.getenv("CHATGPT_API_KEY", "sk-cf-wasd2048")


def average_of_array(arr):
    if not arr:
        return 0
    sum_elements = sum(arr)
    average = sum_elements / len(arr)
    return average - 5

def encode_image_to_base64(image_path):
    """Encodes an image file to a base64 string."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def ask_recaptcha_to_chatgpt(base64_image):
    """Solves reCAPTCHA challenges using a ChatGPT-compatible vision API."""
    headers = {
        "Authorization": f"Bearer {CHATGPT_API_KEY}",
        "Content-Type": "application/json"
    }

    prompt = """You are an expert reCAPTCHA solver with advanced computer vision capabilities. 

Analyze this reCAPTCHA challenge image carefully:

1. READ THE INSTRUCTION: Look at the top of the image for the challenge instruction (e.g., "Select all squares with cars", "Click on all images with traffic lights", etc.)
2. UNDERSTAND THE GRID: The image contains a grid of squares (usually 3x3=9 squares or 4x4=16 squares)
   - For 3x3 grid: squares are numbered 0-8 (top-left to bottom-right, row by row)
   - For 4x4 grid: squares are numbered 0-15 (top-left to bottom-right, row by row)
3. IDENTIFY OBJECTS: Carefully examine each square and identify if it contains the requested object.
4. OUTPUT FORMAT: Return ONLY the numbers of squares containing the requested object, separated by hyphens. Examples: "1-3-5" or "0-2-7-8-12" or "4"
5. BE PRECISE: Double-check your answer. Accuracy is critical.

Now analyze the image and provide the square numbers that contain the requested object."""

    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    }
                ]
            }
        ],
        "max_tokens": 300
    }

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(CHATGPT_API_URL, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()['choices'][0]['message']['content'].strip()
            
            numbers_only = re.findall(r'\d+', result)
            return '-'.join(numbers_only) if numbers_only else result
                
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt + 1} failed with network error: {e}")
            if attempt == max_retries - 1:
                print("All attempts failed, returning empty result")
                return "0"
            time.sleep(2)
        except (KeyError, IndexError) as e:
            print(f"Attempt {attempt + 1} failed parsing API response: {e}. Response: {response.text}")
            if attempt == max_retries - 1:
                return "0"
            time.sleep(2)

def ask_text_to_chatgpt(base64_image):
    """Extracts text from a CAPTCHA image using a ChatGPT-compatible vision API."""
    headers = {
        "Authorization": f"Bearer {CHATGPT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = "You are a captcha solver. Look at this image and extract only the text/characters shown in the captcha. Return only the characters you see, nothing else. Do not include any explanations or additional text."
    
    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    }
                ]
            }
        ],
        "max_tokens": 100
    }
    
    try:
        response = requests.post(CHATGPT_API_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error calling ChatGPT API for text extraction: {e}")
        return ""

def ask_2captcha_text_question(question_text):
    """Answers a text-based CAPTCHA question using a ChatGPT-compatible API."""
    headers = {
        "Authorization": f"Bearer {CHATGPT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"You are answering a text captcha question. Answer the following question with a short, direct answer: {question_text}. Provide only the answer, no explanations."
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 50
    }
    
    try:
        response = requests.post(CHATGPT_API_URL, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error calling ChatGPT API for text question: {e}")
        return ""

def ask_slide_to_chatgpt(base64_image):
    """Analyzes a puzzle CAPTCHA to determine the sliding distance."""
    headers = {
        "Authorization": f"Bearer {CHATGPT_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = ("There is an slider button in the page and there is an empty gray space on puzzle. You should give "
              "give me how many pixels should i slide to complete the puzzle. You can simulate the slider for "
              "the exact fit before giving the answer.The total width is 210 pixels. "
              "Give me only number of pixels in integer 50 up to 210 pixels. "
              "Analyze the slider puzzle and determine the exact pixel distance needed to complete it.")
    
    payload = {
        "model": "gpt-4-vision-preview",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{base64_image}"}
                    }
                ]
            }
        ],
        "max_tokens": 50
    }

    try:
        response = requests.post(CHATGPT_API_URL, headers=headers, json=payload, timeout=45)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error calling ChatGPT API for puzzle slider: {e}")
        return "90"

# ... (All other test functions like puzzle_test, text_test, etc., remain unchanged) ...
def recaptcha_test(driver):
    driver.get("https://www.google.com/recaptcha/api/fallback?k=6LdjOBMTAAAAAFmv8eSu7I8_qw5qaF0o6sGrqXbA")
    print("Navigated to reCAPTCHA fallback page.")
    time.sleep(3)

    number_of_challenges = 0
    max_challenges = 5

    while number_of_challenges < max_challenges:
        number_of_challenges += 1
        print(f"--- Starting Challenge #{number_of_challenges} ---")

        try:
            response_elements = driver.find_elements(By.ID, "g-recaptcha-response")
            # A solved CAPTCHA has a non-empty value in the response textarea
            if response_elements and response_elements[0].get_attribute("value"):
                print("CAPTCHA appears to be solved. A response token is present.")
                break

            challenge_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "rc-imageselect"))
            )
            filename = f'recaptcha_challenge_{number_of_challenges}.png'
            challenge_element.screenshot(filename)
            print(f"Screenshot of challenge taken: {filename}")

            base64_string = encode_image_to_base64(filename)
            answer = ask_recaptcha_to_chatgpt(base64_string)
            print(f"AI response: {answer}")

            if not answer or not re.match(r'^[\d-]+$', answer):
                print("Invalid response from AI, trying to reload the CAPTCHA for a new image.")
                try:
                    driver.find_element(By.ID, "recaptcha-reload-button").click()
                    time.sleep(3)
                    continue
                except Exception as e:
                    print(f"Could not find reload button: {e}")
                    break

            array = re.split(r'[,-]', answer)

            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".rc-imageselect-table-33, .rc-imageselect-table-44"))
            )
            all_images = table.find_elements(By.CSS_SELECTOR, "td")
            print(f"Found {len(all_images)} image tiles.")

            for each_element in array:
                try:
                    index = int(each_element.strip())
                    if 0 <= index < len(all_images):
                        all_images[index].click()
                        print(f"Clicked tile {index}")
                        time.sleep(0.3)
                except (ValueError, IndexError) as e:
                    print(f"Error processing tile index '{each_element}': {e}")

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-verify-button"))
            ).click()
            print("Clicked 'Verify' button.")

            time.sleep(5)

            error_messages = driver.find_elements(By.CSS_SELECTOR, ".rc-imageselect-error-select-more, .rc-imageselect-error-dynamic-more")
            if any(el.is_displayed() for el in error_messages):
                print("Verification failed, a new challenge was presented.")
            else:
                print("No immediate error message found. Assuming success and exiting challenge loop.")
                break

        except Exception as e:
            print(f"An unexpected error occurred during challenge #{number_of_challenges}: {e}")
            break

    print("Taking final screenshot as 'final_result.png'")
    driver.save_screenshot('final_result.png')

def main():
    parser = argparse.ArgumentParser(description="Advanced captcha bypass tool.")
    parser.add_argument('captcha_type', choices=['puzzle', 'text', 'complicated_text', 'recaptcha', 'botdetect_demo', 'twocaptcha_text'],
                        help="Specify the type of captcha to test")
    args = parser.parse_args()

    options = FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # --- FIX: Initialize Service() without webdriver-manager. ---
    # Selenium will now find the geckodriver installed by the setup-firefox action in the PATH.
    service = FirefoxService()
    driver = webdriver.Firefox(service=service, options=options)
    
    try:
        # ... (rest of the main function is unchanged)
        if args.captcha_type == 'recaptcha':
            recaptcha_test(driver)
        # ...
    finally:
        print("Closing the browser.")
        driver.quit()

if __name__ == "__main__":
    # Simplified main function body for clarity
    parser = argparse.ArgumentParser(description="Advanced captcha bypass tool.")
    parser.add_argument('captcha_type', choices=['puzzle', 'text', 'complicated_text', 'recaptcha', 'botdetect_demo', 'twocaptcha_text'],
                        help="Specify the type of captcha to test")
    args = parser.parse_args()

    options = FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    service = FirefoxService()
    driver = None # Initialize driver to None
    try:
        print("Initializing Firefox WebDriver...")
        driver = webdriver.Firefox(service=service, options=options)
        print("WebDriver initialized successfully.")
        
        if args.captcha_type == 'recaptcha':
            recaptcha_test(driver)
        # Add other captcha types back if needed
        # elif args.captcha_type == 'text':
        #     text_test(driver)
        
    except Exception as e:
        print(f"An error occurred in main execution: {e}")
        # Take a screenshot if the driver was initialized before the error
        if driver:
            driver.save_screenshot('main_error.png')
            
    finally:
        if driver:
            print("Closing the browser.")
            driver.quit()
