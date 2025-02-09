import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime, timedelta
import pandas as pd
import logging
import requests 
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
from pymongo import MongoClient
import streamlit as st
import requests
from bs4 import BeautifulSoup
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.text_rank import TextRankSummarizer
import google.generativeai as genai
from langchain_openai import ChatOpenAI
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException, ElementClickInterceptedException
from selenium.webdriver.support import expected_conditions as EC
import time
import requests 
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import arabic_reshaper
from bidi.algorithm import get_display
from groq import Groq
from fpdf import FPDF
import arabic_reshaper
from bidi.algorithm import get_display

genai.configure(api_key="AIzaSyCZpc1GCd6MoIykwGO-jjdrpdQRnnzXaHc")
model = genai.GenerativeModel("gemini-1.5-flash")
client = MongoClient("mongodb+srv://mgyOM62diebaI7CH:mgyOM62diebaI7CH@cluster0.ngxk8.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0") 
db = client["Main_Data"]  
scraped_collection = db["scraped_data"]  # Select collection
summary_collection = db["summary"]
def store_article(country, category, title, content, author, date, source , word):
    if not title or not content or not author or not date:
        print(f"[-] Skipping article due to missing data: {title}")
        return  # Avoid inserting empty data
    
    article_data = {
        "title": title,
        "country": country,
        "category": category,
        "content": content,
        "author": author,
        "date": date,
        "source": source,
        "word" : word,
    }

    try:
        result = scraped_collection.insert_one(article_data)
        print(f" [+] Article '{title}' stored successfully in MongoDB! ID: {result.inserted_id}")
    except Exception as e:
        print(f"[-] Error inserting article '{title}': {e}")
def get_article_content(country, category , word):
    query = {
        "country": {"$regex": country, "$options": "i"},  # Case-insensitive matching
        "category": {"$regex": category, "$options": "i"},  # Case-insensitive matching
        "word": {"$regex": word, "$options": "i"}  # Case-insensitive matching
    }
    
    projection = {
        "content": 1,  # Only retrieve the content field
        "_id": 0  # Exclude the _id field
    }

    # Retrieve articles with case-insensitive regex for country and category
    articles = scraped_collection.find(query, projection)
    all_content = " "
    # Print the content of each article found
    for article in articles:
        all_content+=article["content"]
    return all_content

def scrap_data(response, days):
    current_date = datetime.now()
    min_date = current_date - timedelta(days=int(days))

    soup = BeautifulSoup(response, 'html.parser')
    all_result = soup.find_all('div', {'class': 'info_section news-item'})
    articles_within_range = []
    for art in all_result:
        link = art.find('h2').find('a')['href']
        link = f'https://www.youm7.com{link}'
        date_parts = link.split('story/')[1].split('/')[0:3]
        article_date = datetime.strptime('/'.join(date_parts), "%Y/%m/%d")
        if min_date <= article_date <= current_date:
            articles_within_range.append(link)
    return articles_within_range

def extract_data(response):
    try:
        soup = BeautifulSoup(response, 'html.parser')
        article = soup.find('article')
        title = article.find('h1').text.strip()
        paragraphs = article.find('div',{'id': 'articleBody'}).find_all('p')
        content = '\n'.join([x.text.strip() for x in paragraphs])

        if not content.strip():
            paragraphs = article.find('div',{'id': 'articleBody'}).find_all('div')
            content = '\n'.join([x.text.strip() for x in paragraphs])
        author = article.find('span',{'class':'writeBy'}).text.replace('كتب:','').replace('كتبت:','').strip()
        date = article.find('span',{'class':'newsStoryDate'}).text.strip()
        return title, content, author, date
    
    except Exception as e:
        print('[-] Error in Extract Data',e)
        return 0 , 0 , 0, 0

def youm7(word,date,country , category):
    global headers
    articles = []
    main_word = f'{country} {word}'
    url = f'https://www.youm7.com/Home/Search'
    params = {
        'Drpcallist': '',
        'Drpseclist': '',
        'allwords': main_word,
        'page': '1'
    }
    headers = {
        'accept':'*/*',
        'accept-encoding':'gzip, deflate, br, zstd',
        'accept-language':'en-US,en;q=0.5',
        'content-type':'application/x-www-form-urlencoded',
        'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36'
        }
    payload = {
        'allwords':f'{main_word}'
    }
    response = requests.post(url,headers=headers,data=payload,params=params)
    if response.status_code == 200:
        page_count = int(response.text.split('عدد نتائج البحث  (')[1].split(')')[0]) //30
        for i in range(1, page_count + 1):
            params['page'] = f'{i}'
            response = requests.post(url,headers=headers,data=payload,params=params)
            if response.status_code == 200:
                print('[+] Success Bypass Page Count:',i)
                r = scrap_data(response.text,date)
                if len(r) == 0:
                    break
                else:
                    articles.extend(r)
            else:
                print('[-] Failed To Get Page Count',i)
                with open('failed.txt','a') as f:
                    f.write(f'{i}\n')
    print(f'[+] Will Extract {len(articles)} Article From Youm7')
    extracted_data = []
    for article in articles:
        response = requests.get(article, headers=headers)
        if response.status_code == 200:
            print('[+] Extracted Article Link:',article)
            title , content , author, date = extract_data(response.text) 
            store_article(country , category, title , content , author , date , "اليوم السابع " , word)
            if title and content and author:
                extracted_data.append({'Title':title,'Content':content,'Author':author,'Date':date,'Link':article})
        else:
            print('[-] Error To Extract Link:',article)
            with open('links.txt','a') as f:
                f.write(f'{article}\n')
                
                
##$$$$$$$$$$$$$$$$$$$$$$$$$
def Mesr_Elyoum(country, random_word, duration_days , category):
    # Start scraping process from Mesr Elyoum website
    print("[+] بدء الاستخراج من موقع مصر اليوم...")
    # Configure Selenium options
    options = Options()
    options.add_argument("--headless")  # Run browser in headless mode
    options.add_argument("--disable-gpu")  
    options.add_argument("--window-size=1920x1080")  
    options.add_argument("--no-sandbox")  
    options.add_argument("--disable-dev-shm-usage")  
    options.add_argument("--log-level=3")  
    options.add_argument("--disable-logging")  
    options.add_argument("--ignore-certificate-errors")  
    options.add_argument("--disable-blink-features=AutomationControlled")  

    # Initialize WebDriver
    service = Service(log_path=os.devnull)  
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(f"https://mesrelyoum.com/?s={country}+{random_word}")
    
    last_height = driver.execute_script("return document.body.scrollHeight")
    scraped_links = set()  # To keep track of links we've already scraped
    current_date = datetime.today()
    date_limit = current_date - timedelta(days=duration_days)  # Set date limit based on the specified duration

    articles_data = []  # List to store scraped articles data

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        articles = driver.find_elements(By.XPATH, "/html/body/div[1]/div[6]/div/div/section/div/div[1]/article")
        new_articles_found = False  # Flag to check if new articles are found

        for article in articles:
            try:
                # Extract the article's date
                date_element = article.find_element(By.XPATH, "./div[2]/div/div/div/span[2]/span/time")
                article_date = datetime.strptime(date_element.get_attribute("datetime")[:10], "%Y-%m-%d")
                # Extract the link to the article
                link_element = article.find_element(By.TAG_NAME, "a")
                article_link = link_element.get_attribute("href")

                if article_link not in scraped_links:  # Check if the article is already scraped
                    new_articles_found = True  # Mark that we found a new article

                    if article_date >= date_limit:  # If the article date is within the specified range
                        # Open the article in a new tab for scraping content
                        driver.execute_script("window.open('');")
                        driver.switch_to.window(driver.window_handles[1])
                        driver.get(article_link)
                        time.sleep(2)

                        try:
                            # Extract the title of the article
                            title_element = driver.find_element(By.XPATH, "/html/body/div[1]/div[6]/div/div/div[1]/div[1]/h1")
                            title = title_element.text

                            # Check if both country and random_word are in the title
                            if country in title and random_word in title:
                                try:
                                    # Extract the content (paragraphs) of the article
                                    paragraphs = driver.find_elements(By.XPATH, "/html/body/div[1]/div[6]/div/div/div[3]/article")
                                    content = "\n".join([p.text for p in paragraphs if p.text.strip()])

                                    # Append the article data to the list
                                    articles_data.append({
                                        "Article Title": title,
                                        "Article Link": article_link,
                                        "Article Content": content,
                                        "Article Author Name": "فريق مصر اليوم",
                                        "Article Date": article_date.strftime('%Y-%m-%d'),
                                        "Source Website Name": "مصر اليوم"
                                    })
                                    date = article_date.strftime('%Y-%m-%d')
                                    store_article(country, category, title, content , "فريق مصر اليوم" , date, "مصر اليوم" , random_word)      
                                    # Save the data to an Excel file after scraping each article
                                    df = pd.DataFrame(articles_data)
                                    df.to_excel("mesr_elyoum_articles.xlsx", index=False)
                                    print(f"[+] تمت إضافة المقال: {title}")

                                except NoSuchElementException:
                                    # If content not found in article
                                    print("[!] لم يتم العثور على المحتوى في المقال.")
                            else:
                                # Stop scraping if the article doesn't contain both country and random_word in the title
                                print("[+] انتهى الاستخراج من موقع مصر اليوم.")
                                driver.quit()
                                return
                        except NoSuchElementException:
                            # If title not found in article
                            print("[!] لم يتم العثور على العنوان في المقال.")
                        
                        # Close the article tab and switch back to the main tab
                        driver.close()
                        driver.switch_to.window(driver.window_handles[0])
                        time.sleep(1)

                    else:
                        # Stop scraping if the article is older than the date limit
                        driver.quit()
                        print("[+] انتهى الاستخراج من موقع مصر اليوم.")
                        print("[+] تم حفظ المقالات في الملف: mesr_elyoum_articles.xlsx")
                        return  

            except NoSuchElementException:
                # If date element is not found in the article
                print("[!] لم يتم العثور على تاريخ المقال.")

        # Scroll and check if new articles have been loaded
        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height and not new_articles_found:
            # Try loading more articles if no new articles were found after scrolling
            for attempt in range(3):
                try:
                    load_more_button = driver.find_element(By.XPATH, "/html/body/div[1]/div[6]/div/div/section/div/div[2]/a")
                    driver.execute_script("arguments[0].scrollIntoView();", load_more_button)
                    time.sleep(1)  
                    load_more_button.click()
                    time.sleep(3)  
                    break
                except (NoSuchElementException, ElementClickInterceptedException) as e:
                    if attempt == 2:
                        # If failed to load more articles after 3 attempts, exit
                        print(f"[!] فشل تحميل المزيد بعد 3 محاولات: {str(e)}")
                        driver.quit()
                        return  
                    time.sleep(2)

        last_height = new_height  # Update last height for the next scroll check

    # Close the browser when finished
    driver.quit()

EXCEL_FILE = "rt_articles.xlsx"

def save_article(article_data):
    """Save the article immediately after extraction without duplication"""
    if os.path.exists(EXCEL_FILE):
        df_existing = pd.read_excel(EXCEL_FILE)
        existing_links = set(df_existing["Article Link"])
    else:
        df_existing = pd.DataFrame()
        existing_links = set()

    if article_data["Article Link"] not in existing_links:
        df_new = pd.DataFrame([article_data])

        # Ensure column consistency to avoid missing fields
        df_combined = pd.concat([df_existing, df_new], ignore_index=True).fillna("غير متوفر")
        df_combined.to_excel(EXCEL_FILE, index=False)
        print(f"[✔] تم حفظ المقال: {article_data['Article Title']}")
    else:
        print(f"[!] المقال مكرر: {article_data['Article Title']}")
        
#$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

def RT_ar(random_word, country, duration_days , category):
    print("[+] بدء الاستخراج من موقع RT بالعربي ...")  

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920x1080")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--log-level=3")
    options.add_argument("--disable-logging")
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--disable-blink-features=AutomationControlled")

    service = Service(log_path=os.devnull)  
    driver = webdriver.Chrome(service=service, options=options)
    driver.get(f"https://arabic.rt.com/search?cx=012273702381800949580%3Aiy4mxcpqrji&cof=FORID%3A11&ie=utf8&q={country}+{random_word}&sa=البحث")
    
    date_limit = datetime.today() - timedelta(days=duration_days)

    while True:
        articles = driver.find_elements(By.CSS_SELECTOR, "h3.main-article__title a")
        
        for article in articles:
            link = article.get_attribute("href")
            title = article.text.strip()
            
            # التحقق من وجود country و random_word في العنوان
            if country not in title or random_word not in title:
                print("[+] انتهى الاستخراج من موقع  RT بالعربي.")
                driver.quit()
                return  # إيقاف الدالة بالكامل
            
            if link:
                driver.execute_script("window.open('');")
                driver.switch_to.window(driver.window_handles[1])
                driver.get(link)
                time.sleep(2)
                
                try:
                    date_element = driver.find_element(By.XPATH, "/html/body/div[3]/div/main/div[1]/article/div[1]/div[2]/div[1]/div[2]/span[2]")
                    date_text = date_element.text.strip()
                    date_match = re.search(r"\d{2}\.\d{2}\.\d{4}", date_text)
                    
                    if date_match:
                        article_date = datetime.strptime(date_match.group(), "%d.%m.%Y")

                        # إذا كان المقال أقدم من الحد الزمني، نوقف التنفيذ تمامًا
                        if article_date < date_limit:
                            print("[✔] تم الانتهاء من عملية الاستخراج.")
                            driver.quit()
                            return  # إنهاء الدالة بالكامل

                        try:
                            summary_element = driver.find_element(By.XPATH, "/html/body/div[3]/div/main/div[1]/article/div[1]/div[2]/div[2]/p")
                            summary = summary_element.text.strip()
                        except NoSuchElementException:
                            summary = ""
                        
                        try:
                            content_paragraphs = driver.find_elements(By.XPATH, "/html/body/div[3]/div/main/div[1]/article/div[1]/div[4]/div/p")
                            content = "\n".join([p.text.strip() for p in content_paragraphs if p.text.strip()])
                            last_paragraph = content_paragraphs[-1].text.strip() if content_paragraphs else "غير معروف"
                            source = re.sub(r"^المصدر:\s*", "", last_paragraph)
                        except NoSuchElementException:
                            content = ""
                            source = "غير معروف"
                        
                        full_content = f"{summary}\n{content}"

                        article_data = {
                            "Article Title": title,
                            "Article Link": link,
                            "Article Content": full_content,
                            "Article Author Name": source,
                            "Article Date": article_date.strftime('%Y-%m-%d'),
                            "Source Website Name": "RT Arabic"
                        }
                        date = article_date.strftime('%Y-%m-%d')
                        store_article(country, category, title, full_content , source , date, "بالعربي ART" , random_word)      
                        save_article(article_data)  
                    
                except NoSuchElementException:
                    print("[!] لم يتم العثور على المقال.")
                
                driver.close()
                driver.switch_to.window(driver.window_handles[0])
        
        try:
            load_more_button = driver.find_element(By.XPATH, "/html/body/div[3]/div/main/div[2]/section/button")
            driver.execute_script("arguments[0].scrollIntoView();", load_more_button)
            time.sleep(1)
            load_more_button.click()
            time.sleep(3)
        except (NoSuchElementException, ElementClickInterceptedException):
            break  

    driver.quit()
    print("[✔] تم الانتهاء من عملية الاستخراج.")

#--------------------------------------------------
def ecss(country, random_word, duration_days , category):
    print("[+] بدء الاستخراج من موقع ecss ...")

    # Configure Chrome options for headless mode and performance improvements
    options = Options()
    options.add_argument("--headless")  
    options.add_argument("--disable-gpu")  
    options.add_argument("--window-size=1920x1080")  
    options.add_argument("--no-sandbox")  
    options.add_argument("--disable-dev-shm-usage")  
    options.add_argument("--log-level=3")  # Reduce warnings
    options.add_argument("--disable-logging")  # Disable logging
    options.add_argument("--ignore-certificate-errors")  
    options.add_argument("--disable-blink-features=AutomationControlled")  

    # Suppress DevTools logs
    service = Service(log_path=os.devnull)  
    driver = webdriver.Chrome(service=service, options=options)

    # Navigate to search results page
    driver.get(f"https://ecss.com.eg/?s={country}%20{random_word}")
    time.sleep(5)  # Wait for the page to load

    current_date = datetime.today()
    date_limit = current_date - timedelta(days=duration_days)  # Calculate the date threshold

    # Initialize DataFrame to store extracted articles
    columns = ["Article Title", "Article Content", "Article Author Name", "Article Date", "Source Website Name"]
    df = pd.DataFrame(columns=columns)

    while True:
        try:
            # Find articles on the current page
            articles = driver.find_elements(By.XPATH, '//*[@id="uid_search_0"]/div/div')
            if not articles:
                print("[!] لم يتم العثور على أي مقالات في الصفحة الحالية!")
                break
            
            for article in articles:
                try:
                    # Extract article date and check if it falls within the required range
                    date_element = article.find_element(By.CLASS_NAME, "meta-inner.is-meta")
                    article_date_text = date_element.text.strip()
                    article_date = datetime.strptime(article_date_text, "%d/%m/%Y")

                    # إذا كان المقال خارج النطاق الزمني، نوقف التنفيذ
                    if article_date < date_limit:
                        print("[!] إيقاف البحث والاكتفاء بالبيانات المستخرجة حتى الآن.")
                        driver.quit()
                        return df  # إيقاف الدالة بالكامل

                    # Extract article link and title
                    link_element = article.find_element(By.XPATH, './/div[2]/h4/a')
                    article_link = link_element.get_attribute("href")
                    article_title = link_element.text.strip()

                    # التحقق من وجود country و random_word في العنوان
                    if country not in article_title or random_word not in article_title:
                        print("[!] إيقاف البحث والاكتفاء بالبيانات المستخرجة حتى الآن.")
                        driver.quit()
                        return df  # إيقاف الدالة بالكامل

                    # Open article in a new tab
                    driver.execute_script("window.open(arguments[0], '_blank');", article_link)
                    time.sleep(1)
                    driver.switch_to.window(driver.window_handles[-1])

                    try:
                        # Extract author name
                        author_element = driver.find_element(By.XPATH, '/html/body/div[2]/div/article/header/div[2]/div[1]/div/div/div/span[1]')
                        author_name = author_element.text.strip()
                    except NoSuchElementException:
                        author_name = "غير موجود"

                    try:
                        # Extract article content
                        content_div = driver.find_element(By.XPATH, '/html/body/div[2]/div/article/div/div[1]/div[3]/div/div[2]/div[1]')
                        paragraphs = content_div.find_elements(By.TAG_NAME, "p")
                        article_content = "\n".join([p.text.strip() for p in paragraphs if p.text.strip()])
                    except NoSuchElementException:
                        article_content = "محتوى المقال غير موجود"

                    # Store the extracted data in the DataFrame
                    df = pd.concat([df, pd.DataFrame([{
                        "Article Title": article_title,
                        "Article Link": article_link,
                        "Article Content": article_content,
                        "Article Author Name": author_name,
                        "Article Date": article_date.strftime('%Y-%m-%d'),
                        "Source Website Name": "ecss.com.eg"
                    }])], ignore_index=True)
                    date = article_date.strftime('%Y-%m-%d')
                    store_article(country, category, article_title, article_content , author_name , date,"المركز المصرى للفكر والدراسات الاستراتيجية", random_word)   

                    # Save data to an Excel file
                    df.to_excel("ecss_articles.xlsx", index=False)
                    print(f"[+] تمت إضافة المقال: {article_title}")

                    time.sleep(1)
                    driver.close()  # Close the article tab
                    driver.switch_to.window(driver.window_handles[0])  # Switch back to main tab

                except NoSuchElementException:
                    print("[!] لم يتم العثور على تاريخ المقال.")
                except ValueError as e:
                    print(f"[!] خطأ في تحويل التاريخ: {str(e)}")

            # Check for and navigate to the next page
            try:
                next_page_button = driver.find_element(By.XPATH, '//a[contains(@class, "next page-numbers")]')
                next_page_url = next_page_button.get_attribute("href")
                if next_page_url:
                    driver.get(next_page_url)
                    print(f"[+] تم الانتقال للصفحة التالية")
                    time.sleep(5)
                else:
                    print("[!] لم يتم العثور على رابط للصفحة التالية. انتهى البحث.")
                    break

            except NoSuchElementException:
                print("[!] لم يتم العثور على زر الانتقال للصفحة التالية. انتهى البحث.")
                break
        except Exception as e:
            print(f"[!] خطأ أثناء معالجة المقالات أو الانتقال بين الصفحات: {str(e)}")
            break

    driver.quit()
    return df

#.......................................................................................................................

# Dictionary to map Arabic months to their English equivalents
arabic_to_english_months = {
    "يناير": "January", "فبراير": "February", "مارس": "March", "أبريل": "April",
    "مايو": "May", "يونيو": "June", "يوليو": "July", "أغسطس": "August",
    "سبتمبر": "September", "أكتوبر": "October", "نوفمبر": "November", "ديسمبر": "December"
}

def convert_arabic_date(*args):
    """Convert Arabic date string to English date that can be parsed"""
    try:
        arabic_date = args[0]  # Assuming the first argument is the Arabic date
        parts = arabic_date.split()  # Split the Arabic date string
        if len(parts) != 3:  # Ensure the date has day, month, and year
            return None

        day, arabic_month, year = parts
        english_month = arabic_to_english_months.get(arabic_month)  # Get the English month name
        if not english_month:  # If the month is not found, return None
            return None

        english_date_str = f"{day} {english_month} {year}"  # Construct the full English date string
        return datetime.strptime(english_date_str, "%d %B %Y")  # Parse the date into a datetime object
    except Exception:
        return None  # In case of any error, return None

def extract_article_content_and_author(*args, **kwargs):
    """Extract article content and author name based on available div structure"""
    try:
        driver = kwargs.get('driver', args[0] if args else None)
        content_div = None
        author_class = None
        author_inside_a_tag = False  # To check if author is inside an <a> tag within an <h> tag

        # Check for four div structures in order to find the correct one
        for div_class, author_cls, inside_a in [
            ("post-content__details", "author", False),
            ("book-details", "authors__author", False),
            ("article-content", "author", True),  # Author is inside <a> tag within <h> tag
            ("page-content page-content--article", None, False)  # Backup div for last resort
        ]:
            try:
                content_div = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.CLASS_NAME, div_class))
                )
                author_class = author_cls
                author_inside_a_tag = inside_a
                break  # Stop if content div is found
            except:
                continue  # Move to next div class if the current one is not found

        # If no content div is found, search using Full XPath
        if not content_div:
            try:
                author_element = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/form/div[5]/div/div[4]/div/span/div[1]/div[2]/div/div[1]/div[1]/div/div[1]/div[2]/div[1]/div/h2/a"))
                )
                author = author_element.text.strip()  # Extract the author from the located element
            except:
                author = "فريق المركز العربي للأبحاث والدراسات السياسية"  # Default author if not found
            return None, author  # Return None for content and the author name

        # Extract all paragraphs and headings inside the div
        elements = content_div.find_elements(By.XPATH, ".//p | .//h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//h6")
        article_content = [element.text.strip() for element in elements if element.text.strip()]  # Clean text

        # Default author name
        author = "فريق المركز العربي للأبحاث والدراسات السياسية"
        
        if author_class:  # If the author class is available
            try:
                author_div = content_div.find_element(By.CLASS_NAME, author_class)

                # Check if the author's name is within <a> tags inside headings
                if author_inside_a_tag:
                    author_h_tags = author_div.find_elements(By.XPATH, ".//h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//h6")
                    author_names = []
                    for h in author_h_tags:
                        a_tag = h.find_elements(By.TAG_NAME, "a")
                        if a_tag:
                            author_names.extend([a.text.strip() for a in a_tag if a.text.strip()])
                else:  # Other cases where the author might be in headings or divs
                    author_h_tags = author_div.find_elements(By.XPATH, ".//h1 | .//h2 | .//h3 | .//h4 | .//h5 | .//h6")
                    author_names = []
                    for h in author_h_tags:
                        if h.text.strip():
                            author_names.append(h.text.strip())
                        else:
                            sub_div = h.find_element(By.TAG_NAME, "div")
                            if sub_div.text.strip():
                                author_names.append(sub_div.text.strip())

                if author_names:  # If names were found, join them with a separator
                    author = " | ".join(author_names)

            except:
                pass  # In case of any error, pass and continue

        return article_content, author  # Return the content and author name

    except Exception as e:
        print(f"[✘] خطأ أثناء استخراج البيانات: {e}")  # Error handling with a print statement
        return None, "فريق المركز العربي للأبحاث والدراسات السياسية"  # Return default author name in case of error

def dohainstitute(country, random_word, duration_days , category):
    """Start extracting articles from dohainstitute website"""
    print("[+] بدء الاستخراج من موقع dohainstitute...")
    
    # List to store articles
    stored_articles_list = []

    options = Options()
    options.add_argument("--headless")  
    options.add_argument("--disable-gpu")  
    options.add_argument("--window-size=1920x1080")  
    options.add_argument("--no-sandbox")  
    options.add_argument("--disable-dev-shm-usage")  
    options.add_argument("--log-level=3")  # تقليل ظهور التحذيرات
    options.add_argument("--disable-logging")  # تعطيل تسجيل الأخطاء
    options.add_argument("--ignore-certificate-errors")  
    options.add_argument("--disable-blink-features=AutomationControlled")  

    service = Service(log_path=os.devnull)  # تعطيل تسجيل DevTools
    driver = webdriver.Chrome(service=service, options=options)

    driver.get(f"https://www.dohainstitute.org/ar/Pages/SearchPage.aspx?ACRPSAll=\"{country}\"%20OR%20ACRPSAll:\"{random_word}\"&Path=https://www.dohainstitute.org/ar&ddlSection=الكل&CT0=ACRPS-ArticlePageContentType&CT1=ACRPS-FilePageContentType&CT2=ACRPS-NewsPageContentType&CT3=ACRPS-JournalPageContentType&CT4=ACRPS-BookPageContentType&CT5=ACRPS-UpComingEventContentType&CT6=ACRPS-EventDetailPageContentType&CT7=ACRPS-PreviousEventListContentType&#k=")
    time.sleep(5)

    today = datetime.today()
    duration_limit = today - timedelta(days=duration_days)
    printed_articles = set()

    while True:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        articles = soup.find_all("span", class_="meta__date")

        for idx, article in enumerate(articles):
            article_date_text = article.text.strip()
            article_date = convert_arabic_date(article_date_text)

            # Validate the date and ensure it falls within the specified duration
            if article_date is None or article_date < duration_limit:
                print(f"[✘] المقال خارج النطاق الزمني أو تاريخه غير صحيح: {article_date_text}")
                driver.quit()
                save_to_excel(stored_articles_list)  # Save the data before exiting
                return  # Stop processing further if an invalid article is found

            try:
                # Extract article title and link
                title_div = driver.find_elements(By.CLASS_NAME, "title")[idx]
                article_link_element = title_div.find_element(By.TAG_NAME, "a")
                article_title = article_link_element.text.strip()
                article_link = article_link_element.get_attribute("href")

                # التحقق من وجود country و random_word في العنوان
                if country not in article_title or random_word not in article_title:
                    print("[✘] إيقاف البحث والاكتفاء بالبيانات المستخرجة حتى الآن.")
                    driver.quit()
                    save_to_excel(stored_articles_list)  # Save the data before exiting
                    return  # Stop processing further if the condition is not met

            except:
                article_title = "No Title Available"
                article_link = "No Link Available"

            # Prevent duplicate articles and display results immediately
            article_key = f"{article_date_text} - {article_title}"
            if article_key not in printed_articles:
                printed_articles.add(article_key)
                print(f"[✔] استخراج المقال: {article_title}")

                # Open the link in a new tab
                driver.execute_script("window.open(arguments[0], '_blank');", article_link)
                driver.switch_to.window(driver.window_handles[-1])  # Switch to the new tab
                time.sleep(2)

                # Extract content and author
                article_content, author = extract_article_content_and_author(driver)

                # Store article data in the list
                stored_articles_list.append({
                    "Article Title": article_title,
                    "Article Link": article_link,
                    "Article Content": "\n".join(article_content) if article_content else "Content Not Available",
                    "Article Author Name": author,
                    "Article Date": article_date_text,
                    "Source Website Name": "Doha Institute"
                })
                store_article(country, category, article_title, article_content , author , article_date_text, "المركز العربي للابحاث والدراسات السياسيه", random_word)   

                driver.close()  # Close the current tab
                driver.switch_to.window(driver.window_handles[0])  # Switch back to the main tab

        print("[✔] تم استخراج جميع المقالات المتاحة.")

        try:
            load_more_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), 'تحميل المزيد')]"))
            )
            driver.execute_script("arguments[0].click();", load_more_button)
            print("[INFO] تحميل المزيد من المقالات...")
            time.sleep(3)
        except:
            print("[INFO] لا يوجد مقالات متاحه.")
            break

    driver.quit()
    save_to_excel(stored_articles_list)  # Save the data after finishing

def save_to_excel(stored_articles_list):
    """Save the extracted data to an Excel file"""
    df = pd.DataFrame(stored_articles_list)
    df.to_excel("dohainstitute_articles.xlsx", index=False)  # Save as Excel file
    print("[✔] تم حفظ البيانات في ملف dohainstitute_articles.xlsx")  # Indicate successful saving

#//////////////////////////////////////////////////////////////////////////////////

genai.configure(api_key="AIzaSyCZpc1GCd6MoIykwGO-jjdrpdQRnnzXaHc")
model = genai.GenerativeModel("gemini-1.5-flash")

def summarize_arabic_text(text, np):
    """
    Summarizes a given Arabic text into a specified number of paragraphs in arabic .
    """
    prompt = f"""
    Summarize the following Arabic text in {np} paragraphs in arabic , ensuring each paragraph is well-structured 
    and flows naturally like a news article. Use proper spacing between paragraphs.
    Retain key details while maintaining coherence.
    
    Text: {text}
    """

    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.5,
                "top_p": 0.8,
                "top_k": 40,
                "max_output_tokens": 4096
            }
        )
        
        if response and response.candidates:
            return response.candidates[0].content.parts[0].text
        
        return "Error: No valid summary returned."
    
    except Exception as e:
        return f"Error: {str(e)}"

np_map = {
    '10 days' : 2 ,
    '1 month': 3,
    '3 months': 6,
    '6 months': 9,
    '9 months': 12,
    '12 months': 15
}
# Define options

countries = ['مصر', 'السعوديه', 'إسرائيل', 'غزه', 'قطر']
categories = [
    'سياسه',
    'اقتصاد',
    'رياضه'
]
websites = [
    "مصر اليوم",
    "اليوم السابع",
    "بالعربي CNN",
    "بالعربي ART",
    "المركز العربي للابحاث والدراسات السياسيه",
    "المركز المصرى للفكر والدراسات الاستراتيجية"
]

durations = ['10 days' ,'1 month', '3 months', '6 months', '9 months' , '12 months']

# Streamlit interface
st.markdown(
    """
    <style>
    .stMarkdown, .stTextInput, .stSelectbox, .stMultiselect, .stButton button {
        font-size: 18px;
    }
    .stTextArea textarea {
        font-size: 18px;
        height: auto !important;
        overflow: hidden !important;
        resize: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title('News Search App')

# Sidebar for country and category selection
st.sidebar.header('Selection Menu')
country = st.sidebar.selectbox('Select Country', countries)
category = st.sidebar.selectbox('Select Category', categories)

# Websites as checkboxes 
website = st.multiselect("Select Websites", websites)

# Word input
word = st.text_input('Enter Word to Search')

# Duration selection
duration = st.selectbox('Select Duration', durations)
duration_map = {
    '10 days' : 10 ,
    '1 month' : 30 , 
    '3 months' : 90, 
    '6 months' : 180, 
    '9 months'  : 270 , 
    '12 months': 360
}
# Validation logic
all_fields_filled = (
    country and
    category and
    website and
    word.strip() and
    duration
)
def your_function(res):
        return f"{summarize_arabic_text(res , np_map[duration] )}"
#youm7(word , duration_map[duration] , country , category)
#res = get_article_content(country , category , word)

# Search button
if not all_fields_filled:
    st.warning("Please complete all fields to enable the search.")
else:
    if st.button('Search'):
        # Function call
        #youm7(word , duration_map[duration] , country , category)
        if "اليوم السابع" in website:
            youm7(word , duration_map[duration] , country , category)
        #Mesr_Elyoum(country, word, duration_map[duration] , category)
        if "مصر اليوم" in website:
            Mesr_Elyoum(country, word, duration_map[duration] , category)
        if  "بالعربي ART" in website:
            RT_ar(word, country, duration_map[duration] , category)
        if "المركز المصرى للفكر والدراسات الاستراتيجية" in website:    
            ecss(country, word, duration_map[duration] , category)
        if  "المركز العربي للابحاث والدراسات السياسيه"  in website:
            dohainstitute(country, word, duration_map[duration] , category)
            
        
        res = get_article_content(country , category , word)

        #result = your_function(country, category, websites_selected, word, duration)
        st.markdown(
            f"""
            <div style="border: 1px solid #ccc; padding: 10px; border-radius: 5px; font-size: 18px;">
                {your_function(res)}
            </div>
            """,
            unsafe_allow_html=True,
        )
        def reshape_text(text):
                reshaped_text = arabic_reshaper.reshape(text)
                return get_display(reshaped_text)
 
        def create_formatted_pdf(word, country, category, website, duration, articles):
            pdf = FPDF()
            pdf.add_page()
 
            # Add Arabic-supported font
            pdf.add_font("Amiri", "", "Amiri-Regular.ttf", uni=True)
            pdf.add_font("Amiri", "B", "Amiri-Bold.ttf", uni=True)
            pdf.set_font("Amiri", size=14)
 
            # Title
            pdf.set_font("Amiri", style="B", size=18)
            pdf.cell(0, 10, txt=reshape_text("نتائج البحث"), ln=True, align="C")
            pdf.ln(10)
 
            # Search Details
            pdf.set_font("Amiri", style="B", size=16)
            pdf.cell(0, 10, txt=reshape_text("تفاصيل البحث"), ln=True, align="R")
            pdf.ln(5)
 
            pdf.set_font("Amiri", size=14)
            pdf.cell(0, 8, txt=reshape_text(f"كلمة البحث: {word}"), ln=True, align="R")
            pdf.cell(0, 8, txt=reshape_text(f"الدولة: {country}"), ln=True, align="R")
            pdf.cell(0, 8, txt=reshape_text(f"الفئة: {category}"), ln=True, align="R")
            pdf.cell(0, 8, txt=reshape_text(f"المواقع: {', '.join(website)}"), ln=True, align="R")
            pdf.cell(0, 8, txt=reshape_text(f"المدة: {duration}"), ln=True, align="R")
            pdf.ln(10)
 
            # Content Section
            pdf.set_font("Amiri", style="B", size=16)
            pdf.cell(0, 10, txt=reshape_text("المحتوى"), ln=True, align="R")
            pdf.ln(5)
 
            pdf.set_font("Amiri", size=14)
            reshaped_articles = reshape_text(res)
            pdf.multi_cell(0, 8, txt=reshaped_articles, align="R")
 
            # Save the PDF
            file_name = f'{word}_search_results.pdf'
            pdf.output(file_name)
 
            with open(file_name, "rb") as file:
                pdf_data = file.read()
 
            return pdf_data
 
 
 
        # Add download button
        st.download_button(
            label="Download as PDF",
            data=create_formatted_pdf(word, country, category, website, duration, res),
            file_name=f"{word}_search_results.pdf",
            mime="application/pdf"
        )
