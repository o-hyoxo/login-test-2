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
from PIL import Image
import io

# Load environment variables from .env file
load_dotenv()

# --- NEW: Configuration for Custom ChatGPT API ---
# The API endpoint you provided
CHATGPT_API_URL = "https://ai2gpt.xxxx.nyc.mn/v1/chat/completions"
# The API key you provided. For better practice, set this as CHATGPT_API_KEY in your .env file or GitHub Secrets.
CHATGPT_API_KEY = os.getenv("CHATGPT_API_KEY", "sk-cf-wxxx2x4x")

def call_custom_chatgpt_api(prompt, base64_image=None):
    """
    NEW: A unified function to send requests to the custom ChatGPT-compatible API.
    It can handle both text-only and image-based (vision) requests.
    """
    if not CHATGPT_API_KEY:
        raise ValueError("CHATGPT_API_KEY is not set. Please provide the API key.")

    headers = {
        "Authorization": f"Bearer {CHATGPT_API_KEY}",
        "Content-Type": "application/json"
    }

    # Construct the payload based on whether an image is provided
    messages = []
    if base64_image:
        # Payload for vision models (image and text)
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                }
            ]
        })
        # Use a model name that typically supports vision
        model_name = "gpt-4-vision-preview"
    else:
        # Payload for standard text models
        messages.append({
            "role": "user",
            "content": prompt
        })
        model_name = "gpt-3.5-turbo"

    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": 500  # Increased for potentially complex answers
    }

    try:
        print("Sending request to custom ChatGPT API...")
        response = requests.post(CHATGPT_API_URL, headers=headers, json=payload, timeout=60)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

        result = response.json()
        content = result['choices'][0]['message']['content']
        print(f"API Response received: {content}")
        return content.strip()

    except requests.exceptions.RequestException as e:
        print(f"Error calling custom ChatGPT API: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response Status: {e.response.status_code}")
            print(f"Response Body: {e.response.text}")
        return ""  # Return an empty string on failure

def average_of_array(arr):
    if not arr:
        return 0
    return sum(arr) / len(arr) - 5

def encode_image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def ask_recaptcha_to_chatgpt(base64_image):
    prompt = """You are an expert reCAPTCHA solver. Analyze the reCAPTCHA image.

1.  **Instruction**: Identify the object to select from the text at the top of the image.
2.  **Grid**: The image is a grid (usually 3x3 or 4x4). Squares are numbered starting from 0 in the top-left, row by row.
3.  **Identify**: Find all squares containing the requested object, even if it's just a small part.
4.  **Output**: Return ONLY the numbers of the matching squares, separated by hyphens. Example: "1-3-5" or "0-2-7-8". Do not add any other text.

Analyze the image and provide the square numbers."""
    
    # MODIFIED: Use the new API call function
    response = call_custom_chatgpt_api(prompt, base64_image=base64_image)
    # Clean up the response to ensure proper format
    numbers_only = re.findall(r'\d+', response)
    if numbers_only:
        return '-'.join(numbers_only)
    return response # Fallback to raw response

def ask_text_to_chatgpt(base64_image):
    prompt = "You are a captcha solver. Look at this image and extract only the text/characters shown. Return only the characters you see, nothing else. Do not include any explanations or additional text."
    # MODIFIED: Use the new API call function
    return call_custom_chatgpt_api(prompt, base64_image=base64_image)

def ask_2captcha_text_question(question_text):
    prompt = f"You are answering a text captcha question. Answer the following question with a short, direct answer: '{question_text}'. Provide only the answer, no explanations."
    # MODIFIED: Use the new API call function (text-only)
    return call_custom_chatgpt_api(prompt)

def ask_slide_to_chatgpt(base64_image):
    prompt = ("Analyze the slider puzzle image. There is a piece missing and a slider below. The total width is 210 pixels. Determine the exact pixel distance from the left edge that the slider needs to move to fit the puzzle piece into the empty slot. Return ONLY the integer number of pixels. For example: 155")
    # MODIFIED: Use the new API call function
    return call_custom_chatgpt_api(prompt, base64_image=base64_image)

# --- All other test functions (puzzle_test, text_test, etc.) remain unchanged as they call the ask_* functions above ---
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
    # Try multiple selectors for the submit button
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
            submit_button = buttons[-1]  # Try the last button
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
    # Try multiple selectors for the submit button
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
            submit_button = buttons[-1]  # Try the last button
    
    if submit_button:
        submit_button.click()
    else:
        print("No submit button found!")
    time.sleep(5)
    driver.quit()

def twocaptcha_text_test(driver):
    """Test function for 2captcha.com text captcha demo"""
    driver.get("https://2captcha.com/demo/text")
    time.sleep(5)
    
    try:
        # Look for the captcha question text
        question_selectors = [
            (By.CSS_SELECTOR, ".captcha-question"),
            (By.CSS_SELECTOR, "[class*='question']"),
            (By.CSS_SELECTOR, "[class*='captcha']"),
            (By.XPATH, "//div[contains(@class, 'question') or contains(@class, 'captcha')]"),
            (By.XPATH, "//p[contains(text(), '?')]"),
            (By.XPATH, "//div[contains(text(), '?')]"),
            (By.XPATH, "//span[contains(text(), '?')]"),
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
        
        # If no specific question element found, try to get all text and find question
        if not question_text or '?' not in question_text:
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
                # Look for question patterns
                import re
                questions = re.findall(r'[^.!]*\?[^.!]*', body_text)
                if questions:
                    question_text = questions[0].strip()
                    print(f"Found question in body text: {question_text}")
            except:
                pass
        
        if not question_text:
            print("Could not find captcha question text")
            return
        
        # Get AI answer for the question
        answer = ask_2captcha_text_question(question_text)
        print(f"AI Answer: {answer}")
        
        # Find the input field
        input_selectors = [
            (By.CSS_SELECTOR, "input[type='text']"),
            (By.CSS_SELECTOR, "input[name*='captcha']"),
            (By.CSS_SELECTOR, "input[name*='answer']"),
            (By.CSS_SELECTOR, "input[class*='input']"),
            (By.XPATH, "//input[@type='text']"),
            (By.TAG_NAME, "input")
        ]
        
        input_field = None
        for selector_type, selector_value in input_selectors:
            try:
                input_field = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                break
            except:
                continue
        
        if not input_field:
            print("Could not find input field")
            return
        
        # Enter the answer
        input_field.clear()
        input_field.send_keys(answer)
        
        # Find and click submit button
        submit_selectors = [
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.CSS_SELECTOR, "input[type='submit']"),
            (By.XPATH, "//button[contains(text(), 'Submit') or contains(text(), 'Check') or contains(text(), 'Verify')]"),
            (By.CSS_SELECTOR, "button"),
            (By.TAG_NAME, "button")
        ]
        
        submit_button = None
        for selector_type, selector_value in submit_selectors:
            try:
                submit_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((selector_type, selector_value))
                )
                break
            except:
                continue
        
        if submit_button:
            submit_button.click()
            print("Submitted answer")
        else:
            print("Could not find submit button, trying Enter key")
            input_field.send_keys(Keys.RETURN)
        
        time.sleep(5)
        
        # Check for success/failure message
        try:
            success_indicators = [
                "success", "correct", "passed", "verified", "valid"
            ]
            failure_indicators = [
                "error", "incorrect", "failed", "invalid", "wrong"
            ]
            
            page_text = driver.find_element(By.TAG_NAME, "body").text.lower()
            
            if any(indicator in page_text for indicator in success_indicators):
                print("✓ Captcha solved successfully!")
            elif any(indicator in page_text for indicator in failure_indicators):
                print("✗ Captcha solution failed")
            else:
                print("Result unclear - check page manually")
        except:
            print("Could not determine result")
            
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
            if response_elements and response_elements[0].is_displayed():
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

            if not answer or not re.match(r'^[\d-]+$', answer):
                print("Invalid response from AI, trying to reload the CAPTCHA.")
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

            clicked_count = 0
            for each_element in array:
                try:
                    index = int(each_element.strip())
                    if 0 <= index < len(all_images):
                        all_images[index].click()
                        clicked_count += 1
                        print(f"Clicked tile {index}")
                        time.sleep(0.3)
                except (ValueError, IndexError) as e:
                    print(f"Error processing tile index '{each_element}': {e}")
            print(f"Clicked {clicked_count} tiles in total.")

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-verify-button"))
            ).click()
            print("Clicked 'Verify' button.")
            time.sleep(5)

            error_messages = driver.find_elements(By.CSS_SELECTOR, ".rc-imageselect-error-select-more, .rc-imageselect-error-dynamic-more")
            if any(el.is_displayed() for el in error_messages):
                print("Verification failed, a new challenge was presented.")
            else:
                print("No immediate error message. Assuming success and exiting challenge loop.")
                break
        except Exception as e:
            print(f"An unexpected error occurred during challenge #{number_of_challenges}: {e}")
            break

    print("Taking final screenshot as 'final_result.png'")
    driver.save_screenshot('final_result.png')

def botdetect_demo_test(driver):
    """Test function for BotDetect CAPTCHA demo website"""
    print("Starting BotDetect CAPTCHA demo bypass test...")
    
    # Navigate to the BotDetect demo page
    driver.get("https://captcha.com/demos/features/captcha-demo.aspx")
    time.sleep(5)
    
    try:
        # Take a full page screenshot first for debugging
        driver.save_screenshot('botdetect_full_page.png')
        print("Full page screenshot saved as 'botdetect_full_page.png'")
        
        # Try multiple selectors to find the captcha image
        captcha_img = None
        captcha_selectors = [
            (By.ID, "BotDetectCaptcha_CaptchaImage"),
            (By.XPATH, "//img[contains(@id, 'CaptchaImage')]"),
            (By.XPATH, "//img[contains(@src, 'BotDetectCaptcha.ashx')]"),
            (By.CSS_SELECTOR, "img[src*='BotDetectCaptcha']"),
            (By.CSS_SELECTOR, "img[id*='Captcha']"),
            (By.TAG_NAME, "img")
        ]
        
        for selector_type, selector_value in captcha_selectors:
            try:
                captcha_img = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((selector_type, selector_value))
                )
                print(f"Found captcha image using {selector_type}: {selector_value}")
                break
            except:
                continue
        
        if not captcha_img:
            print("Could not find captcha image, trying to find all images...")
            all_images = driver.find_elements(By.TAG_NAME, "img")
            print(f"Found {len(all_images)} images on the page")
            for i, img in enumerate(all_images):
                src = img.get_attribute('src')
                id_attr = img.get_attribute('id')
                print(f"Image {i+1}: src='{src}', id='{id_attr}'")
                if 'captcha' in str(src).lower() or 'captcha' in str(id_attr).lower():
                    captcha_img = img
                    print(f"Selected image {i+1} as captcha based on src/id")
                    break
            
            if not captcha_img and all_images:
                captcha_img = all_images[0]  # Use first image as fallback
                print("Using first image as captcha fallback")
        
        if captcha_img:
            # Take screenshot of the captcha
            filename = 'botdetect_captcha.png'
            captcha_img.screenshot(filename)
            print(f"Captcha screenshot saved as '{filename}'")
            
            # Encode image to base64
            base64_string = encode_image_to_base64(filename)
            
            # Get captcha solution from Gemini
            answer = ask_text_to_chatgpt(base64_string)  # Use text captcha function for BotDetect
            print(f"Captcha solution: {answer}")
            
            # Find the captcha input field
            captcha_input = None
            input_selectors = [
                (By.ID, "BotDetectCaptcha_CaptchaCode"),
                (By.XPATH, "//input[contains(@id, 'CaptchaCode')]"),
                (By.XPATH, "//input[@type='text']"),
                (By.CSS_SELECTOR, "input[type='text']")
            ]
            
            for selector_type, selector_value in input_selectors:
                try:
                    captcha_input = WebDriverWait(driver, 5).until(
                        EC.presence_of_element_located((selector_type, selector_value))
                    )
                    print(f"Found captcha input using {selector_type}: {selector_value}")
                    break
                except:
                    continue
            
            if captcha_input:
                # Clear and enter the captcha solution
                captcha_input.clear()
                captcha_input.send_keys(answer)
                print(f"Entered captcha solution: {answer}")
                
                # Find and click the validate button
                validate_button = None
                button_selectors = [
                    (By.ID, "ValidateCaptchaButton"),
                    (By.XPATH, "//input[@value='Validate']"),
                    (By.XPATH, "//button[contains(text(), 'Validate')]"),
                    (By.XPATH, "//input[@type='submit']"),
                    (By.CSS_SELECTOR, "input[type='submit']"),
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.TAG_NAME, "button")
                ]
                
                for selector_type, selector_value in button_selectors:
                    try:
                        validate_button = WebDriverWait(driver, 5).until(
                            EC.element_to_be_clickable((selector_type, selector_value))
                        )
                        print(f"Found validate button using {selector_type}: {selector_value}")
                        break
                    except:
                        continue
                
                if validate_button:
                    validate_button.click()
                    print("Clicked validate button")
                    time.sleep(5)  # Wait to see the result
                    
                    # Take final screenshot
                    driver.save_screenshot('botdetect_result.png')
                    print("Result screenshot saved as 'botdetect_result.png'")
                else:
                    print("Could not find validate button")
                    # Try to submit by pressing Enter
                    captcha_input.send_keys(Keys.RETURN)
                    print("Tried submitting by pressing Enter")
                    time.sleep(3)
                    driver.save_screenshot('botdetect_result.png')
            else:
                print("Could not find captcha input field")
        else:
            print("Could not find captcha image")
            
    except Exception as e:
        print(f"Error during BotDetect test: {str(e)}")
        # Take a screenshot for debugging
        driver.save_screenshot('botdetect_error.png')
        print("Error screenshot saved as 'botdetect_error.png'")

def main():
    parser = argparse.ArgumentParser(description="Advanced captcha bypass tool using a custom ChatGPT API.")
    parser.add_argument('captcha_type', choices=['puzzle', 'text', 'complicated_text', 'recaptcha', 'botdetect_demo', 'twocaptcha_text'],
                        help="Specify the type of captcha to test")
    args = parser.parse_args()

    options = FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--window-size=1920,1080")

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
