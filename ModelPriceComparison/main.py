from base64 import decodebytes
from ntpath import join
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
    item_dict['Name'] = basket_item_line.replace('|', ' ')
    #item_dict['Number'] = ''
    item_dict['ItemURL'] = ''
    item_dict['Prices'] = {}
    
    return item_dict

def getItemSearchString(shop_data, basket_item_line):

    basket_item_line_list = basket_item_line.split('|')
    basket_item_line_result_def = basket_item_line.replace('|', ' ')
    if len(basket_item_line_list) < 3:
        print('Wrong basket file format on line: ' + basket_item_line)
        basket_item_line_result = basket_item_line_result_def
    else:
        if shop_data['search_string_template'] != '':
            basket_item_line_result = shop_data['search_string_template'].replace('%%VENDOR%%', basket_item_line_list[0])
            basket_item_line_result = basket_item_line_result.replace('%%NUM%%', basket_item_line_list[1])
            basket_item_line_result = basket_item_line_result.replace('%%NAME%%', basket_item_line_list[2])
        else:
            basket_item_line_result = basket_item_line_result_def

    return basket_item_line_result

def getItemDict(basket_item_line, shops_dict):
    item_dict = InitItemDict(basket_item_line, shops_dict)
    price_counter = 0
    for shop in shops_dict:
        if shops_dict[shop]['shop_active'] == 'false':
            continue
        root_shop = False
        if shops_dict[shop]['root_entry'] == 'true':
            root_shop = True
        else:
            price_key = 'price' + str(price_counter)
            item_dict['Prices'][price_key] = 'NOTFOUND'
            price_counter = price_counter + 1

        search_string = getItemSearchString(shops_dict[shop], basket_item_line)
        search_url = shops_dict[shop]['url_template'] + shops_dict[shop]['search_url_template'].replace('%%%SEARCH_STRING%%%', urllib.parse.quote(search_string))
        
        if search_url.strip() == '':
            continue       
        try:
            search_result = urllib.request.urlopen(search_url).read()
            soup = BeautifulSoup(search_result, "html.parser")
            el_item = soup.select(shops_dict[shop]['search_item_template'])[0]
            if root_shop:
                item_url = shops_dict[shop]['url_template'] + el_item.find_all('a')[0].get('href')
                item_result = urllib.request.urlopen(item_url).read().decode('utf-8')
                soup = BeautifulSoup(item_result, 'html.parser')
                item_dict['ItemURL'] = item_url
                item_dict['Name'] = soup.find('title').string
                continue

            if shops_dict[shop]['info_on_item_page'] == 'true':
                item_url = shops_dict[shop]['url_template'] + el_item.find_all('a')[0].get('href')
                item_result = urllib.request.urlopen(item_url).read().decode('utf-8')
                el_item = BeautifulSoup(item_result, 'html.parser')
        
            if shops_dict[shop]['search_instock_template'] != '' and len(el_item.select(shops_dict[shop]['search_instock_template'])) == 0:
                item_dict['Prices'][price_key] = 'OUTOFSTOCK'
                continue

            el_price = el_item.select(shops_dict[shop]['search_price_template'])
            price_text = el_price[0].text
            price = float(re.sub("[^0-9,]", "", price_text.strip()).replace(',','.'))

            if shops_dict[shop]['delivery_template_on_item_page'] != '':
                el_price_delivery = el_item.select(shops_dict[shop]['delivery_template_on_item_page'])
                price_delivery_text = el_price_delivery[int(shops_dict[shop]['delivery_template_on_item_page_elnum'])].text
                price_delivery = float(re.sub("[^0-9,]", "", price_delivery_text.strip()).replace(',','.'))
                price = round(price + price_delivery, 2)               

            item_dict['Prices'][price_key] = price

        except Exception as e: 
            print(e)
    return item_dict
        
def getPricesDict(basket_lines, shops_dict):

    prices_dict = {}
    items_counter = 0
    
    for basket_item_line in basket_lines:
        prices_dict['item' + str(items_counter)] = getItemDict(basket_item_line, shops_dict)    
        items_counter = items_counter + 1

    return prices_dict
            

def getShopsDict(config_shops):
  shops_dict = {}
  Root_added = False
  for section in config_shops.sections():
    shops_dict[section] = {}
    for key in config_shops[section]:  
        shops_dict[section][key] = config_shops.get(section, key).strip('"')
    if shops_dict[section]['root_entry'] == 'true' and not Root_added:
        shops_dict['Root'] = shops_dict.pop(section)
        Root_added = True

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

  config_shops = configparser.RawConfigParser()
  config_shops.read(shops, encoding='utf-8')

  if not os.path.exists(basket):
    createBasketConfig(basket)
   
  try:
    basketfile = get_file(basket)
  except FileNotFoundError:
    print("Can't access basket file")
    sys.exit(1)
  
  with basketfile as file:
      basket_lines = [line.rstrip() for line in file if line.rstrip()[0] != '#']

  shops_dict = getShopsDict(config_shops)
  
  prices_dict = getPricesDict(basket_lines, shops_dict)

  del shops_dict['Root']

  #apply_deliverycost_onitem(shops_dict, prices_dict)

  print(' '*50 + '|'.join([f'{key:^13.13}' for key in shops_dict.keys() if shops_dict[key]['shop_active'] == 'true']))

  for item in prices_dict:      
      Name = prices_dict[item]['Name'] 
      print(f'{str(Name):50.50}' + '|'.join([f'{str(value):^13.13}' for value in prices_dict[item]['Prices'].values()]))

#def apply_deliverycost_onitem(shops_dict, prices_dict):
    

if __name__ == '__main__':
  main()
