import os
import re
import sys
import urllib
import urllib.request
import urllib.parse
import configparser
import datetime
from bs4 import BeautifulSoup
from multiprocessing import Pool

def InitItemDict(basket_item_line, shops_dict):
    item_dict = {}
    item_dict['Name'] = basket_item_line.replace('|', ' ')    
    item_dict['ItemURL'] = ''
    item_dict['Prices'] = {}
    item_dict['URLs'] = {}
    
    return item_dict

def getItemSearchString(shop_data, basket_item_line):

    basket_item_line_list = basket_item_line.split('|')
    basket_item_line_result_def = basket_item_line.replace('|', ' ')
    if len(basket_item_line_list) < 3:
        print('Wrong basket file format on line: ' + basket_item_line)
        basket_item_line_result = basket_item_line_result_def
    else:
        if shop_data['search_string_template'] != '':
            overrides_str = shop_data['search_string_overrides'].strip().lower()
            overrides_list = overrides_str.split('.')
            if len(overrides_list) == 3:
                for over_count in [0, 1, 2]:
                    for override_pair in overrides_list[over_count].split(';'):
                        if override_pair.strip() == '':
                            continue
                        override_pair_list = override_pair.split('|')
                        basket_item_line_list[over_count] = basket_item_line_list[over_count].lower().replace(override_pair_list[0], override_pair_list[1])                

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
            url_key = 'price' + str(price_counter)
            item_dict['Prices'][price_key] = '_'
            item_dict['URLs'][url_key] = ''
            price_counter = price_counter + 1

    
        search_string = getItemSearchString(shops_dict[shop], basket_item_line)

        if shops_dict[shop]['search_url_encode'].strip() != '':
            search_string = search_string.encode(shops_dict[shop]['search_url_encode'].strip())

        search_url = shops_dict[shop]['url_template'] + shops_dict[shop]['search_url_template'].replace('%%%SEARCH_STRING%%%', urllib.parse.quote(search_string))         
                
        if search_url.strip() == '':
            continue       
        try:
            if root_shop:                
                item_dict['ItemURL'] = search_url
            else:
                item_dict['URLs'][url_key] = search_url
            search_result = urllib.request.urlopen(search_url).read()
            soup = BeautifulSoup(search_result, "html.parser")
            el_item = soup.select(shops_dict[shop]['search_item_template'])[0]

            #Check if we've found wrong item
            if shops_dict[shop]['add_search_check'] == 'true':
                el_item_text = ''.join(el_item.find_all(text=True, recursive=True)).strip().lower()
                item_text_cheched = True
                #for check_basket_string in basket_item_line.split('|'):
                for check_basket_string in search_string.split(' '):
                    if el_item_text.find(check_basket_string.lower()) == -1:
                        item_text_cheched = False
                        break
                if item_text_cheched == False:
                    continue            

            if root_shop:                
                item_url = shops_dict[shop]['url_template'] + el_item.find_all('a')[0].get('href')
                item_result = urllib.request.urlopen(item_url).read().decode('utf-8')
                soup = BeautifulSoup(item_result, 'html.parser')
                item_dict['ItemURL'] = item_url
                item_dict['Name'] = str(soup.find('title').string)
                continue

            if shops_dict[shop]['info_on_item_page'] == 'true':
                item_url = shops_dict[shop]['url_template'] + el_item.find_all('a')[0].get('href')
                item_result = urllib.request.urlopen(item_url).read().decode('utf-8')
                item_dict['URLs'][url_key] = item_url
                el_item = BeautifulSoup(item_result, 'html.parser')
        
            if shops_dict[shop]['search_instock_template'] != '' and len(el_item.select(shops_dict[shop]['search_instock_template'])) == 0:
                item_dict['Prices'][price_key] = 'OOS'
                continue

            el_price = el_item.select(shops_dict[shop]['search_price_template'])
            #price_text = el_price[0].text.strip() 
            price_text = ''.join(el_price[0].find_all(text=True, recursive=False)).strip() 

            if price_text == '':
                item_dict['Prices'][price_key] = 'OOS'
                continue

            price = float(re.sub("[^0-9,]", "", price_text).replace(',','.'))

            if shops_dict[shop]['delivery_template_on_item_page'] != '':
                el_price_delivery = el_item.select(shops_dict[shop]['delivery_template_on_item_page'])
                price_delivery_text = el_price_delivery[int(shops_dict[shop]['delivery_template_on_item_page_elnum'])].text
                price_delivery = float(re.sub("[^0-9,]", "", price_delivery_text.strip()).replace(',','.'))
                price = round(price + price_delivery, 2)               

            item_dict['Prices'][price_key] = price

        except Exception as e: 
            expt = e
           #print(e)
    
    return item_dict        
        
def getPricesDict(basket_lines, shops_dict, singlethread):
    
    prices_dict = {}
    prices_async_dict = {}
    items_counter = 0    

    pool = Pool()

    if singlethread:
        #non multiprocess ver
        for basket_item_line in basket_lines:
            printProgressBar(items_counter,len(basket_lines))
            prices_dict['item' + str(items_counter)] = getItemDict(basket_item_line, shops_dict)
            items_counter = items_counter + 1         
    else:    
        for basket_item_line in basket_lines:
            prices_async_dict['item' + str(items_counter)] = pool.apply_async(getItemDict, [basket_item_line, shops_dict])
            items_counter = items_counter + 1

        items_counter = 0

        for basket_item_line in basket_lines:
            printProgressBar(items_counter,len(basket_lines))
            prices_dict['item' + str(items_counter)] = prices_async_dict['item' + str(items_counter)].get(timeout=100)
            items_counter = items_counter + 1
          
    
    prices_dict['SUM'] = {}
    prices_dict['SUM']['Name'] = 'TOTAL:'
    prices_dict['SUM']['Prices'] = {}
    
    return prices_dict
            
def printProgressBar (iteration, total, prefix = '', suffix = '', decimals = 1, length = 100, fill = '█', printEnd = "\r"):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + '-' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end = printEnd)
    # Print New Line on Complete
    if iteration == total: 
        print()

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

def sum_delivery(shops_dict, prices_dict):
    
    shop_num = 0

    for shop_key in shops_dict:

        if shops_dict[shop_key]['shop_active'] != 'true':
            continue

        prices_dict['SUM']['Prices']['sum' + str(shop_num)] = 0
        item_keys_toapply = []        
                
        for item_key in prices_dict:
            if item_key == 'SUM':
                continue
            if isinstance(prices_dict[item_key]['Prices']['price' + str(shop_num)], float) and prices_dict[item_key]['Prices']['price' + str(shop_num)] != 0:
                item_keys_toapply.append(item_key)    
                       
        for item_key_toapply in item_keys_toapply:            
            if float(shops_dict[shop_key]['discount_percent']) != 0:
                prices_dict[item_key_toapply]['Prices']['price' + str(shop_num)] = round(prices_dict[item_key_toapply]['Prices']['price' + str(shop_num)] * (1 - float(shops_dict[shop_key]['discount_percent'])/100),2)
            prices_dict['SUM']['Prices']['sum' + str(shop_num)] = round(prices_dict['SUM']['Prices']['sum' + str(shop_num)] + prices_dict[item_key_toapply]['Prices']['price' + str(shop_num)], 2)

        if float(shops_dict[shop_key]['free_delivery_threshold']) != 0 and prices_dict['SUM']['Prices']['sum' + str(shop_num)] < float(shops_dict[shop_key]['free_delivery_threshold']):                           
            prices_dict['SUM']['Prices']['sum' + str(shop_num)] = 0
            for item_key_toapply in item_keys_toapply:            
                prices_dict[item_key_toapply]['Prices']['price' + str(shop_num)] = round(prices_dict[item_key_toapply]['Prices']['price' + str(shop_num)] + float(shops_dict[shop_key]['delivery_cost']) / len(item_keys_toapply), 2)
                prices_dict['SUM']['Prices']['sum' + str(shop_num)] = round(prices_dict['SUM']['Prices']['sum' + str(shop_num)] + prices_dict[item_key_toapply]['Prices']['price' + str(shop_num)], 2)
                     
        shop_num = shop_num + 1       

def getHtmExportTemplate():
    tpl_text = """<!DOCTYPE HTML>
                    <html>
                     <head>
                      <meta charset="utf-8">
                      <title>%%%TABLE_TITLE%%%</title>
                     </head>
                     <body>
                      <table border="1">
                       <caption>%%%TABLE_TITLE%%%</caption>
                       <tr>
                        %%%UP_TITLES%%%                        
                       </tr>
                       %%%ROWS%%%                        
                      </table>
                     </body>
                    </html>"""
    tpl_text = tpl_text.replace('%%%TABLE_TITLE%%%', 'Basket on ' + str(datetime.datetime.now()))
    return tpl_text

def getUpTitlesText(shops_dict):    
    up_titles_text = "<th></th>\n"
    for shop in shops_dict:
        if shops_dict[shop]['shop_active'] == 'false':
            continue
        shop_url = shops_dict[shop]['url_template']
        up_titles_text = up_titles_text + f"<th><a href=\"{shop_url}\">{shop}</a></th>\n"      
        
    return up_titles_text


def getRowsText(prices_dict):
    rows_text = ''
    for item in prices_dict:
      Name = prices_dict[item]['Name'] 
      if item == 'SUM':
          rows_text = rows_text +'<tr><td>---</td>' + f'<tr><td>{Name}</td>' + ''.join([f'<td>{value}</td>' for value in prices_dict[item]['Prices'].values()])           
      else:
          ItemURL = prices_dict[item]['ItemURL']
          rows_text = rows_text + f'<tr><td><a href="{ItemURL}">{Name}</a></td>'

          min_price = 10000000000000
          min_prices_keys = []

          for price_key in prices_dict[item]['Prices']:
              try:
                  if float(prices_dict[item]['Prices'][price_key]) <= min_price:
                      min_price = prices_dict[item]['Prices'][price_key]
              except ValueError:
                  continue

          for price_key in prices_dict[item]['Prices']:
              price_value = prices_dict[item]['Prices'][price_key]
              price_url = prices_dict[item]['URLs'][price_key]
              
              mark_min_price = False              
              try:
                  if float(prices_dict[item]['Prices'][price_key]) == min_price:
                      mark_min_price = True
              except ValueError:
                  mark_min_price = False                  
              
              if mark_min_price:
                  rows_text = rows_text + f'<td bgcolor="#90EE90"><a href="{price_url}">{price_value}</a></td>'
              else:
                  rows_text = rows_text + f'<td><a href="{price_url}">{price_value}</a></td>'
        
    return rows_text

def export_result_file(shops_dict, prices_dict, export_filename):
    htm_result = getHtmExportTemplate()
    up_titles_text = getUpTitlesText(shops_dict)
    htm_result = htm_result.replace('%%%UP_TITLES%%%', up_titles_text)
    rows_text = getRowsText(prices_dict)
    htm_result = htm_result.replace('%%%ROWS%%%', rows_text)
    with open(export_filename, encoding='utf-8', mode='wt') as result_file:
        result_file.write(htm_result)
        print('Exported to: ' + result_file.name)
    print()

def main():
    
  args = sys.argv[1:]
  
  shops = 'default_shops.ini'
  export = False
  singlethread = False

  if not args:
    print ("""usage: [--shops <shops .ini-file>] [--export] <basket .ini-file>
    example 1: mpricecomp basket.ini
    example 2: mpricecomp --shops my_shops.ini my_basket.ini
    example 2: mpricecomp --shops my_shops.ini --export my_basket.ini""")

    sys.exit(1)

  if args[0] == '--shops':
    shops = args[1]
    del args[0:2]

  if args[0] == '--singlethread':
    singlethread = True
    del args[0]

  if args[0] == '--export':
    export = True
    del args[0]      
  
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
  prices_dict = getPricesDict(basket_lines, shops_dict, singlethread)

  del shops_dict['Root']

  sum_delivery(shops_dict, prices_dict)

  print(' '*50 + '|'.join([f'{key:^13.13}' for key in shops_dict.keys() if shops_dict[key]['shop_active'] == 'true']))

  for item in prices_dict:      
      Name = prices_dict[item]['Name'] 
      if item == 'SUM':
          print('-'* (50 + 13 * len(prices_dict[item]['Prices'])))

      print(f'{str(Name):50.50}' + '|'.join([f'{str(value):^13.13}' for value in prices_dict[item]['Prices'].values()]))

  if export:
      export_result_file(shops_dict, prices_dict, os.path.splitext(basket)[0]+'.htm')

if __name__ == '__main__':
  main()
