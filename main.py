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
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.firefox import GeckoDriverManager

# Load environment variables from .env file
load_dotenv()

# Fetch API configuration from environment variables
CHATGPT_API_URL = os.getenv("CHATGPT_API_URL", "https://ai2gpt.xxxx.nyc.mn/v1/chat/completions")
CHATGPT_API_KEY = os.getenv("CHATGPT_API_KEY", "sk-cf-wxxx2x4x")


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

def puzzle_test(driver):
    driver.get("https://2captcha.com/demo/geetest")
    time.sleep(5)
    button = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.CLASS_NAME, "geetest_radar_tip"))
    )
    button.click()
    box = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "geetest_embed"))
    )
    time.sleep(1)
    box.screenshot('geetest_box.png')
    base64_string = encode_image_to_base64('geetest_box.png')
    time.sleep(1)
    all_results = []
    while True:
        slider = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "geetest_slider_button"))
        )
        time.sleep(2)
        action = ActionChains(driver)
        input_string = ask_slide_to_chatgpt(base64_string)
        numbers = re.findall(r'\d+', input_string)
        if numbers:
            result = int(numbers[0])
        else:
            result = 0
        if result < 110:
            result = 90
        all_results.append(result)
        action.click_and_hold(slider).perform()
        time.sleep(random.uniform(0.8, 1.2))
        total_offset = average_of_array(all_results)
        num_steps = 5
        step_offset = total_offset / num_steps
        for _ in range(num_steps):
            action.move_by_offset(step_offset, 0).perform()
            time.sleep(random.uniform(0.05, 0.1))
        action.release().perform()

def complicated_text_test(driver):
    driver.get("https://2captcha.com/demo/mtcaptcha")
    time.sleep(5)
    iframe = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.ID, "mtcaptcha-iframe-1"))
    )
    iframe.screenshot('captcha_image.png')
    base64_string = encode_image_to_base64('captcha_image.png')
    response = ask_text_to_chatgpt(base64_string)

    print(response)
    driver.switch_to.frame(iframe)
    input_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "mtcap-noborder.mtcap-inputtext.mtcap-inputtext-custom"))
    )
    input_field.send_keys(response)
    time.sleep(2)
    driver.switch_to.default_content()
    submit_button = None
    selectors = [
        (By.XPATH, "//button[contains(@class, '_buttonPrimary_') or contains(text(), 'Submit') or contains(text(), 'Check')]"),
        (By.CSS_SELECTOR, "button[class*='_buttonPrimary_']"),
        (By.CSS_SELECTOR, "button[class*='_button_']"),
        (By.TAG_NAME, "button")
    ]
    
    for selector_type, selector_value in selectors:
        try:
            submit_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((selector_type, selector_value))
            )
            break
        except:
            continue
    
    if not submit_button:
        print("Could not find submit button, trying to find any clickable button...")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        if buttons:
            submit_button = buttons[-1]
    submit_button.click()

def text_test(driver):
    driver.get("https://2captcha.com/demo/normal")
    time.sleep(5)
    captcha_image = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "_captchaImage_rrn3u_9"))
    )

    time.sleep(2)
    captcha_image.screenshot('captcha_image.png')
    base64_string = encode_image_to_base64('captcha_image.png')
    response = ask_text_to_chatgpt(base64_string)

    print(response)

    input_field = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "_inputInner_ws73z_12"))
    )
    input_field.send_keys(response)
    submit_button = None
    selectors = [
        (By.XPATH, "//button[contains(@class, '_buttonPrimary_') or contains(text(), 'Submit') or contains(text(), 'Check')]"),
        (By.CSS_SELECTOR, "button[class*='_buttonPrimary_']"),
        (By.CSS_SELECTOR, "button[class*='_button_']"),
        (By.TAG_NAME, "button")
    ]
    
    for selector_type, selector_value in selectors:
        try:
            submit_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((selector_type, selector_value))
            )
            break
        except:
            continue
    
    if not submit_button:
        print("Could not find submit button, trying to find any clickable button...")
        buttons = driver.find_elements(By.TAG_NAME, "button")
        if buttons:
            submit_button = buttons[-1]
    
    if submit_button:
        submit_button.click()
    else:
        print("No submit button found!")
    time.sleep(5)
    driver.quit()

def twocaptcha_text_test(driver):
    driver.get("https://2captcha.com/demo/text")
    time.sleep(5)
    
    try:
        question_selectors = [
            (By.CSS_SELECTOR, ".captcha-question"),
            (By.CSS_SELECTOR, "[class*='question']"),
            (By.XPATH, "//*[contains(text(), '?')]"),
        ]
        
        question_element = None
        question_text = ""
        
        for selector_type, selector_value in question_selectors:
            try:
                question_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                question_text = question_element.text.strip()
                if question_text and '?' in question_text:
                    print(f"Found question: {question_text}")
                    break
            except:
                continue
        
        if not question_text:
            print("Could not find captcha question text")
            return
        
        answer = ask_2captcha_text_question(question_text)
        print(f"AI Answer: {answer}")
        
        input_field = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input[type='text']"))
        )
        input_field.clear()
        input_field.send_keys(answer)
        
        submit_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
        )
        submit_button.click()
        print("Submitted answer")
        time.sleep(5)
            
    except Exception as e:
        print(f"Error during 2captcha text test: {str(e)}")
    
    time.sleep(3)

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

def botdetect_demo_test(driver):
    print("Starting BotDetect CAPTCHA demo bypass test...")
    driver.get("https://captcha.com/demos/features/captcha-demo.aspx")
    time.sleep(5)
    
    try:
        driver.save_screenshot('botdetect_full_page.png')
        print("Full page screenshot saved")
        
        captcha_img = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "BotDetectCaptcha_CaptchaImage"))
        )
        print(f"Found captcha image")
        
        filename = 'botdetect_captcha.png'
        captcha_img.screenshot(filename)
        print(f"Captcha screenshot saved")
        
        base64_string = encode_image_to_base64(filename)
        answer = ask_text_to_chatgpt(base64_string)
        print(f"Captcha solution: {answer}")
        
        captcha_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "BotDetectCaptcha_CaptchaCode"))
        )
        captcha_input.clear()
        captcha_input.send_keys(answer)
        print(f"Entered captcha solution")
        
        validate_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.ID, "ValidateCaptchaButton"))
        )
        validate_button.click()
        print("Clicked validate button")
        time.sleep(5)
        
        driver.save_screenshot('botdetect_result.png')
        print("Result screenshot saved")
            
    except Exception as e:
        print(f"Error during BotDetect test: {str(e)}")
        driver.save_screenshot('botdetect_error.png')

def main():
    parser = argparse.ArgumentParser(description="Advanced captcha bypass tool for text captchas and BotDetect systems.")
    parser.add_argument('captcha_type', choices=['puzzle', 'text', 'complicated_text', 'recaptcha', 'botdetect_demo', 'twocaptcha_text'],
                        help="Specify the type of captcha to test")
    args = parser.parse_args()

    options = FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")
    
    # --- FIX: Add arguments for stability in CI/CD environments ---
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    service = FirefoxService(GeckoDriverManager().install())
    driver = webdriver.Firefox(service=service, options=options)
    
    try:
        if args.captcha_type == 'puzzle':
            puzzle_test(driver)
        elif args.captcha_type == 'text':
            text_test(driver)
        elif args.captcha_type == 'complicated_text':
            complicated_text_test(driver)
        elif args.captcha_type == 'recaptcha':
            recaptcha_test(driver)
        elif args.captcha_type == 'botdetect_demo':
            botdetect_demo_test(driver)
        elif args.captcha_type == 'twocaptcha_text':
            twocaptcha_text_test(driver)
    finally:
        print("Closing the browser.")
        driver.quit()

if __name__ == "__main__":
    main()
