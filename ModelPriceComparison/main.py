import os
import re
import sys
import urllib
import urllib.request
import urllib.parse
import configparser
from bs4 import BeautifulSoup

def InitItemDict(basket_item_line, shops_dict):
    item_dict = {}
    item_dict['Name'] = basket_item_line
    item_dict['Number'] = ''
    item_dict['ItemURL'] = ''
    
    return item_dict

def getItemDict(basket_item_line, shops_dict):
    item_dict = InitItemDict(basket_item_line, shops_dict)
    price_counter = 0
    for shop in shops_dict:
        price_key = 'price' + str(price_counter)
        item_dict[price_key] = 'ERR'
        price_counter = price_counter + 1
        search_url = shops_dict[shop]['search_url_template'].replace('%%%SEARCH_STRING%%%', urllib.parse.quote(basket_item_line))
        if search_url.rstrip() == '':
            continue       
        try:
            search_result = urllib.request.urlopen(search_url).read().decode('utf-8')
            soup = BeautifulSoup(search_result, "html.parser")
            text = soup.find(attrs={"class": shops_dict[shop]['search_page_template']})
            item_url = text.find_all('a')[0].get('href')    
            item_dict['ItemURL'] = item_url
            item_result = urllib.request.urlopen(item_url).read().decode('utf-8')
            if shops_dict[shop]['root_entry'] == 'true':
                basket_item_line = item_result.find('title').string
                break
            item_price_regex = r"\b(?=\w)" + re.escape(shops_dict[shop]['item_page_price_regex']) + r"\b(?!\w)"
            match = re.search(item_price_regex, item_result)
            if match:
              shops_dict[shop][price_key] = match.group()
        except Exception as e: 
            print(e)
        #text.get('href')
     #text.contents[1].attrs['href']
def getPricesDict(basket_lines, shops_dict):

    prices_dict = {}
    items_counter = 0
    
    for basket_item_line in basket_lines:
        prices_dict['item' + str(items_counter)] = getItemDict(basket_item_line, shops_dict)    
        items_counter = items_counter + 1
            

def getShopsDict(config_shops):
  shops_dict = {}
  Root_added = False
  for section in config_shops.sections():
    shops_dict[section] = {}
    for key in config_shops[section]:  
        shops_dict[section][key] = config_shops.get(section, key)
    if shops_dict[section]['root_entry'] == 'true' and not Root_added:
        shops_dict['Root'] = shops_dict.pop(section)
        Root_added = 'true'

  return shops_dict       

def createShopsConfig(path):
    
    config = configparser.RawConfigParser()
    config.add_section("Scalemates")
    config.set("Scalemates", "Search_url_template", "")
    config.set("Scalemates", "Search_page_template", "")
    config.set("Scalemates", "Item_page_template", "")
    config.set("Scalemates", "Root_entry", "true")

    config.add_section("Model-lavka")
    config.set("Model-lavka", "Search_url_template", "")
    config.set("Model-lavka", "Search_page_template", "")
    config.set("Model-lavka", "Item_page_template", "")
    config.set("Model-lavka", "Root_entry", "false")

    config.add_section("i-modelist")
    config.set("i-modelist", "Search_url_template", "")
    config.set("i-modelist", "Search_page_template", "")
    config.set("i-modelist", "Item_page_template", "")
    config.set("i-modelist", "Root_entry", "false")
           
    with open(path, "w") as config_file:
        config.write(config_file)

def createBasketConfig(path):
    
    default_basket = """MENG Army HUSKY TSV VS-009
MENG French FT-17 Light Tank (Riveted Turret) TS-011
Rye Field Models RM-5041"""

    with open(path, encoding='utf-8', mode='wt') as config_file:
        config_file.write(default_basket)

def get_file(filename):
   return open(filename, 'rt', encoding='utf-8')

def main():
  args = sys.argv[1:]
  
  shops = 'default_shops.ini'

  if not args:
    print ("""usage: [--shops <shops .ini-file>] <basket .ini-file>
    example 1: mpricecomp basket.ini
    example 2: mpricecomp --shops my_shops.ini my_basket.ini""")
    sys.exit(1)

  if args[0] == '--shops':
    shops = args[1]
    del args[0:2]
  
  if not args[0] or args[0].rstrip() == '':
    print("Expecting basket file")
    sys.exit(1)
  
  basket = args[0]

  if not os.path.exists(shops):
    createShopsConfig(shops)

  #try:
  #  shopsfile = get_file(shops)
  #except FileNotFoundError:
  #  print("Can't access shops file")
  #  sys.exit(1)  

  config_shops = configparser.RawConfigParser()
  config_shops.read(shops)

  if not os.path.exists(basket):
    createBasketConfig(basket)
   
  try:
    basketfile = get_file(basket)
  except FileNotFoundError:
    print("Can't access basket file")
    sys.exit(1)
  
  with basketfile as file:
      basket_lines = [line.rstrip() for line in file]

  shops_dict = getShopsDict(config_shops)
  
  prices_dict = getPricesDict(basket_lines, shops_dict)

if __name__ == '__main__':
  main()
