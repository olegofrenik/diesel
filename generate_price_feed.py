import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import re

# --- Загружаем украинский sitemap ---
sitemap_url = "https://www.rsg-shop.com.ua/sitemapproducts.xml"
resp = requests.get(sitemap_url)
soup = BeautifulSoup(resp.content, "xml")
urls_ukr = [loc.get_text() for loc in soup.find_all("loc")]

# --- Преобразуем URL в русскую версию ---
urls_ru = []
for url in urls_ukr:
    parts = url.split("https://www.rsg-shop.com.ua")
    if len(parts) == 2:
        urls_ru.append("https://www.rsg-shop.com.ua/ru" + parts[1])
    else:
        urls_ru.append(url)

print(f"Найдено {len(urls_ru)} товаров для русской версии")

# --- XML структура ---
rss = ET.Element("rss", attrib={"xmlns:g": "http://base.google.com/ns/1.0", "version": "2.0"})
channel = ET.SubElement(rss, "channel")
ET.SubElement(channel, "title").text = "RSG-SHOP RU update"
ET.SubElement(channel, "link").text = "https://www.rsg-shop.com.ua/ru/"

# --- Парсинг товаров ---
for i, url in enumerate(urls_ru, 1):
    try:
        r = requests.get(url, timeout=10)
        psoup = BeautifulSoup(r.content, "html.parser")

        # --- Артикул ---
        art_match = re.search(r"Артикул[:\s]*([A-Za-z0-9\-]+)", psoup.get_text())
        art = art_match.group(1) if art_match else f"ID{i}"

        # --- Цена + скидка ---
        price_block = psoup.find("div", style=re.compile("font-size: 14px; font-weight: bold;"))
        price = None
        sale_price = None
        if price_block:
            old_price = price_block.find("s")
            new_price = price_block.find("span", {"class": "productSpecialPrice"})
            if old_price and new_price:
                price = re.sub(r"\D", "", old_price.get_text())
                sale_price = re.sub(r"\D", "", new_price.get_text())
            else:
                m = re.search(r"(\d+)\s*грн", price_block.get_text())
                if m:
                    price = m.group(1)

        # --- Наличие ---
        availability = "out of stock"
        avail_tag = psoup.find("span", class_="availability")
        if avail_tag:
            try:
                if int(avail_tag.get_text(strip=True)) > 0:
                    availability = "in stock"
            except:
                pass

        # --- XML item (только id, цена, скидка, наличие) ---
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "g:id").text = art
        if price: ET.SubElement(item, "g:price").text = f"{price} UAH"
        if sale_price: ET.SubElement(item, "g:sale_price").text = f"{sale_price} UAH"
        ET.SubElement(item, "g:availability").text = availability

    except Exception as e:
        print(f"❌ Ошибка для {url}: {e}")

    # --- Прогресс ---
    if i % 10 == 0 or i == len(urls_ru):
        percent = round(i / len(urls_ru) * 100, 2)
        print(f"✅ Обработано {i}/{len(urls_ru)} ({percent}%)")

# --- Сохраняем ---
tree = ET.ElementTree(rss)
tree.write("feed_prices.xml", encoding="utf-8", xml_declaration=True)
print("Файл feed_prices.xml создан.")
