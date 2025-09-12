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
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from openai import OpenAI
from PIL import Image
import io

load_dotenv()
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

client = OpenAI(
    api_key="sk-jFRMWzq8RG9im8FXZah4cIn5bMaC8noWLEythpLaMLP09t3E",
    base_url="https://new.281182.xyz/v1/chat/completions"
)

def ask_recaptcha_to_chatgpt(base64_image):
    prompt = """You are an expert reCAPTCHA solver with advanced computer vision capabilities. 

Analyze this reCAPTCHA challenge image carefully:

1. READ THE INSTRUCTION: Look at the top of the image for the challenge instruction (e.g., "Select all squares with cars", "Click on all images with traffic lights", etc.)

2. UNDERSTAND THE GRID: The image contains a grid of squares (usually 3x3=9 squares or 4x4=16 squares)
   - For 3x3 grid: squares are numbered 0-8 (top-left to bottom-right, row by row)
   - For 4x4 grid: squares are numbered 0-15 (top-left to bottom-right, row by row)

3. IDENTIFY OBJECTS: Carefully examine each square and identify if it contains the requested object:
   - Look for partial objects (even if only a small part is visible)
   - Consider objects that might be partially cut off at edges
   - Be inclusive rather than exclusive - if unsure, include it
   - Pay attention to similar objects (e.g., motorcycles vs bicycles, cars vs trucks)

4. COMMON OBJECTS TO RECOGNIZE:
   - Vehicles: cars, trucks, buses, motorcycles, bicycles
   - Infrastructure: traffic lights, crosswalks, bridges, fire hydrants
   - Transportation: trains, boats, airplanes
   - Other: stairs, chimneys, palm trees, mountains

5. OUTPUT FORMAT: Return ONLY the numbers of squares containing the requested object, separated by hyphens.
   Examples: "1-3-5" or "0-2-7-8-12" or "4"
   
6. BE PRECISE: Double-check your answer. Accuracy is critical.

Now analyze the image and provide the square numbers that contain the requested object."""
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gemini-2.5-pro",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{base64_image}"
                                }
                            },
                        ],
                    }
                ],
                max_tokens=300,
            )
            result = response.choices[0].message.content.strip()
            
            import re
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
    prompt = "You are a captcha solver. Look at this image and extract only the text/characters shown in the captcha. Return only the characters you see, nothing else. Do not include any explanations or additional text."
    response = client.chat.completions.create(
        model="gemini-2.5-pro",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    },
                ],
            }
        ],
        max_tokens=50,
    )
    return response.choices[0].message.content.strip()

def ask_2captcha_text_question(question_text):
    prompt = f"You are answering a text captcha question. Answer the following question with a short, direct answer: {question_text}. Provide only the answer, no explanations."
    response = client.chat.completions.create(
        model="gemini-2.5-pro",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50,
    )
    return response.choices[0].message.content.strip()

def ask_slide_to_chatgpt(base64_image):
    prompt = ("There is an slider button in the page and there is an empty gray space on puzzle. You should give "
              "give me how many pixels should i slide to complete the puzzle. You can simulate the slider for "
              "the exact fit before giving the answer.The total width is 210 pixels. "
              "Give me only number of pixels in integer 50 up to 210 pixels. "
              "Analyze the slider puzzle and determine the exact pixel distance needed to complete it.")
    response = client.chat.completions.create(
        model="gemini-2.5-pro",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        }
                    },
                ],
            }
        ],
        max_tokens=10,
    )
    return response.choices[0].message.content.strip()

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

def recaptcha_test(driver, url):
    driver.get(url)
    number_of_challenges = 0
    try:
        while True:
            number_of_challenges += 1
            filename = 'recaptcha_challenge_' + str(number_of_challenges) + '.png'
            
            # Wait for the challenge image to load
            challenge_image = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "recaptcha_challenge_image"))
            )
            time.sleep(2) # allow image to load fully
            challenge_image.screenshot(filename)
            base64_string = encode_image_to_base64(filename)
            
            print(f"Processing challenge {number_of_challenges}...")
            answer = ask_text_to_chatgpt(base64_string)
            print(f"AI response: {answer}")
            
            # Enter the answer
            input_field = driver.find_element(By.ID, "recaptcha_response_field")
            input_field.clear()
            input_field.send_keys(answer)
            input_field.send_keys(Keys.RETURN) # Submit the form
            
            time.sleep(5) # Wait for the result
            
            # Check if the captcha is solved by looking for the absence of the image
            try:
                driver.find_element(By.ID, "recaptcha_challenge_image")
                print("Challenge not solved, trying again.")
            except:
                print("reCAPTCHA solved successfully!")
                driver.save_screenshot("recaptcha_solved.png")
                print("Screenshot saved as recaptcha_solved.png")
                break
    except Exception as ex:
        # It might be that the captcha was solved on the first try, or another state.
        # Let's check for success message or take a final screenshot.
        body_text = driver.find_element(By.TAG_NAME, "body").text
        if "try again" not in body_text.lower():
            print("reCAPTCHA likely solved.")
            driver.save_screenshot("recaptcha_solved.png")
            print("Screenshot saved as recaptcha_solved.png")
        else:
            print(f"An unexpected error occurred: {ex}")
            driver.save_screenshot("recaptcha_error.png")



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
    parser = argparse.ArgumentParser(description="Advanced captcha bypass tool for text captchas and BotDetect systems.")
    parser.add_argument('captcha_type', choices=['puzzle', 'text', 'complicated_text', 'recaptcha', 'botdetect_demo', 'twocaptcha_text'],
                        help="Specify the type of captcha to test")
    parser.add_argument('--url', help="URL for the reCAPTCHA test")
    args = parser.parse_args()

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    try:
        if args.captcha_type == 'puzzle':
            puzzle_test(driver)
        elif args.captcha_type == 'text':
            text_test(driver)
        elif args.captcha_type == 'complicated_text':
            complicated_text_test(driver)
        elif args.captcha_type == 'recaptcha':
            url = args.url if args.url else "https://www.google.com/recaptcha/api/fallback?k=6LdjOBMTAAAAAFmv8eSu7I8_qw5qaF0o6sGrqXbA"
            recaptcha_test(driver, url)
        elif args.captcha_type == 'botdetect_demo':
            botdetect_demo_test(driver)
        elif args.captcha_type == 'twocaptcha_text':
            twocaptcha_text_test(driver)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
