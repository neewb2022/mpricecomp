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

def InitItemDict(basket_item_line):
    """
    Initialize default Item dict
    @params:
        basket_item_line   - Required  : basket item line from config (Str)        
    """
    item_dict = {}
    item_dict['Name'] = basket_item_line.replace('|', ' ')    
    item_dict['ItemURL'] = ''
    item_dict['Prices'] = {}
    item_dict['URLs'] = {}
    
    return item_dict

def getItemSearchString(shop_data, basket_item_line):
    """
    Get formatted item search string for remote web pages
    @params:
        shop_data          - Required  : element with shop config data (Dict element)        
        basket_item_line   - Required  : basket item line from config (Str)        
    """
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
    """
    Get prices item info from remote web sources and returns as dict
    @params:
        basket_item_line   - Required  : basket item line from config (Str)        
        shops_dict         - Required  : dict with shops config data (Dict)        
    """
    item_dict = InitItemDict(basket_item_line)
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
    """
    Creates items dict for each basket entry and launches multi/singlethreaded data-fetching from remote sources
    @params:
        basket_lines       - Required  : list with lines of basket file config (Str)        
        shops_dict         - Required  : dict with shops config data (Dict)        
        singlethread       - Required  : parameter for singlethreaded execution (Bool)        
    """    
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
            prices_dict['item' + str(items_counter)] = prices_async_dict['item' + str(items_counter)].get(timeout=200)
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
    """
    Reads config file and creates shops dict from it
    @params:
        config_shops       - Required  : shops config object (Config)                
    """
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
    """
    Creates and write default shops config
    @params:
        path       - Required  : path to shops config file (Str)                
    """    
    default_shops = """[Scalemates]
url_template = "https://www.scalemates.com"
search_string_template = "%%VENDOR%% "%%NUM%%"'"
search_string_overrides = "Freedom Model Kits|Hero Hobby Kits;Hobby Boss|HobbyBoss;Rye Field Models|Rye Field Model.."
search_url_encode = ""
search_url_template = "/search.php?fkSECTION[]=Kits&q=%%%SEARCH_STRING%%%&fkTYPENAME[]=%22Full%20kits%22"
search_item_template = "div[class='ar p5']"
root_entry = true
add_search_check = false
shop_active = true

[ali]
url_template = "https://aliexpress.ru"
search_string_template = %%VENDOR%% %%NUM%%
#search_url_template = "/wholesale?SearchText=%%%SEARCH_STRING%%%&SortType=total_tranpro_desc&g=y&page=1"
#search_url_template = "/wholesale?SearchText=%%%SEARCH_STRING%%%&SortType=default&g=y&page=1"
search_url_template = "/wholesale?SearchText=%%%SEARCH_STRING%%%"
#search_url_template = "/category/202000013/toys-hobbies/w-%%%SEARCH_STRING%%%"
search_string_overrides = "Rye Field Model|RFM;Звезда|Zvezda.."
search_url_encode = ""
search_item_template = "div[class='product-snippet_ProductSnippet__content__1ettdy']"
search_price_template = "div[class='snow-price_SnowPrice__mainS__18x8np']" 
search_instock_template = ""
info_on_item_page = true
add_search_check = false
delivery_template_on_item_page = "span[class='snow-ali-kit_Typography__base__1shggo snow-ali-kit_Typography__base__1shggo snow-ali-kit_Typography__sizeTextM__1shggo']"
delivery_template_on_item_page_elnum = 1
free_delivery_threshold = 0
delivery_cost = 0
discount_percent = 0
root_entry = false
shop_active = true"""
           
    with open(path, encoding='utf-8', mode='wt') as config_file:
        config_file.write(default_shops)

def createBasketConfig(path):
    """
    Creates default basket config file
    @params:
        path       - Required  : path to shops config file (Str)                
    """    
    
    default_basket = """Hobby Boss|82442|
Meng|TS-030|gepard
Amusing Hobby|35A028|"""

    with open(path, encoding='utf-8', mode='wt') as config_file:
        config_file.write(default_basket)

def get_file(filename):
    """
    Returns file from path
    @params:
        filename       - Required  : path to file (Str)                
    """    
    return open(filename, 'rt', encoding='utf-8')

def sum_delivery(shops_dict, prices_dict):
    """
    Counts total basket sums for shops and stores it in prices dict
    @params:
        shops_dict       - Required  : dict with shops info (dict element)                
        prices_dict      - Required  : dict with prices info (dict element)                
    """    
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
    """
    Returns html-templates for export html-file    
    """    
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
    """
    Returns html-string for shops row-headers for export html file
    @params:
        shops_dict       - Required  : dict with shops info (dict element)                        
    """    
    up_titles_text = "<th></th>\n"
    for shop in shops_dict:
        if shops_dict[shop]['shop_active'] == 'false':
            continue
        shop_url = shops_dict[shop]['url_template']
        up_titles_text = up_titles_text + f"<th><a href=\"{shop_url}\">{shop}</a></th>\n"      
        
    return up_titles_text

def getRowsText(prices_dict):
    """
    Returns html-string for item-row in table for export html file
    @params:        
        prices_dict      - Required  : dict with prices info (dict element)                
    """    
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
    """
    Gathers all data, generates and writes export html-file with table
    @params:        
        prices_dict      - Required  : dict with prices info (dict element)                
        shops_dict       - Required  : dict with shops info (dict element)                        
        export_filename  - Required  : path to export html file (Str)                        
    """    
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
  """
   Gathers all data, generates and writes export html-file with table
   @params:        
       prices_dict      - Required  : dict with prices info (dict element)                
       shops_dict       - Required  : dict with shops info (dict element)                        
       export_filename  - Required  : path to export html file (Str)                        
  """      
  args = sys.argv[1:]
  
  shops = 'default_shops.ini'
  export = False
  singlethread = False

  if not args:
    print ("""usage: [--singlethread] [--shops <shops .ini-file>] [--export] <basket .ini-file>
    example 1: mpricecomp --singlethread --export basket1.ini 
        Launches data fetch in sigle-thread (slow but less resource hungry), using specified basket config file, exports results in html-file
    example 2: mpricecomp basket.ini
        Launches data fetch in multi-thread (default), using specified basket config file
    example 3: mpricecomp --shops my_shops.ini my_basket.ini
        Launches data fetch in multi-thread (default), using specified shops config file, using specified basket config file""")

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
