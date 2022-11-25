import os
import re
import sys
import urllib
import urllib.request
import urllib.parse
import configparser
import datetime
import multiprocessing
import http.cookiejar
from argparse import ArgumentParser
from bs4 import BeautifulSoup
from multiprocessing import Pool

def urlEncodeNonAscii(b):
    return re.sub('[\x80-\xFF]', lambda c: '%%%02x' % ord(c.group(0)), b)

def iriToUri(iri):
    iri = urllib.parse.urlsplit(iri)
    iri = list(iri)
    iri[2] = urllib.parse.quote(iri[2])
    iri = urllib.parse.urlunsplit(iri)
    return iri

def url_is_absolute(url):
    return bool(urllib.parse.urlparse(url).netloc)

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

def getItemSearchString(shop_data, shop_configentry_to_process, basket_item_line):
    """
    Get formatted item search string for remote web pages
    @params:
        shop_data          - Required  : element with shop config data (Dict element)        
        shop_configentry_to_process - Required  : config entry to get prepared string from (Str)
        basket_item_line   - Required  : basket item line from config (Str)        
    """
    basket_item_line_list = basket_item_line.split('|')
    basket_item_line_result_def = basket_item_line.replace('|', ' ')
    if len(basket_item_line_list) < 3:
        print('Wrong basket file format on line: ' + basket_item_line)
        basket_item_line_result = basket_item_line_result_def
    else:
        if shop_data[shop_configentry_to_process] != '':
            overrides_str = shop_data['search_string_overrides'].strip().lower()
            overrides_list = overrides_str.split('.')
            if len(overrides_list) == 3:
                for over_count in [0, 1, 2]:
                    for override_pair in overrides_list[over_count].split(';'):
                        if override_pair.strip() == '':
                            continue
                        override_pair_list = override_pair.split('|')
                        basket_item_line_list[over_count] = basket_item_line_list[over_count].lower().replace(override_pair_list[0], override_pair_list[1])                

            basket_item_line_result = shop_data[shop_configentry_to_process].replace('%%VENDOR%%', basket_item_line_list[0])
            basket_item_line_result = basket_item_line_result.replace('%%NUM%%', basket_item_line_list[1])
            basket_item_line_result = basket_item_line_result.replace('%%NAME%%', basket_item_line_list[2])
        else:
            basket_item_line_result = basket_item_line_result_def

    return basket_item_line_result

def TrimString(str_to_trim):
    str_result = str_to_trim.strip()
    str_result = str_result.replace(' ','')
    str_result = str_result.replace('\n','')
    str_result = str_result.replace('\r','')
    return str_result.lower()

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
                
        search_string = getItemSearchString(shops_dict[shop], 'search_string_template', basket_item_line)

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
                        
            headers={}
            headers['User-Agent'] = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'                        
            
            if shops_dict[shop]['use_cookies'] == 'true':
                cj = http.cookiejar.MozillaCookieJar()            
                cookies_filename = shops_dict[shop]['cookies_path'].strip()
                if cookies_filename != '':
                    try:
                        cj.load(cookies_filename)
                    except:
                        print('Error loading cookies from: "' + cookies_filename + '"')

                opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
                urllib.request.install_opener(opener)
            
            req = urllib.request.Request(search_url, headers=headers)                            
            response = urllib.request.urlopen(req, timeout=20)
            
            search_result = response.read()
            soup = BeautifulSoup(search_result, "html.parser")
<<<<<<< HEAD

            search_item_check = False
            if shops_dict[shop]['search_item_check_template'] != '' and shops_dict[shop]['search_item_check_string'].strip() != '':
                search_item_check = True
                
            if shops_dict[shop]['info_on_item_page'] == 'true' and shops_dict[shop]['search_itempage_template'] != '':
                el_items = []
                el_items_process = soup.select(shops_dict[shop]['search_item_template'])
                max_items_to_process = 3
                items_processed = 0
                for el_item_it in el_items_process:
                    item_url = el_item_it.find_all('a')[0].get('href')
                    if not url_is_absolute(item_url):
                        item_url = shops_dict[shop]['url_template'] + el_item_it.find_all('a')[0].get('href')                    
                    item_result = urllib.request.urlopen(iriToUri(item_url), timeout=20).read().decode('utf-8')                                        
                    soup_tmp = BeautifulSoup(item_result, 'html.parser')
                    el_items.append(soup_tmp.select(shops_dict[shop]['search_itempage_template'])[0])
                    if not search_item_check:
=======

            search_item_check = False
            if shops_dict[shop]['search_item_check_template'] != '' and shops_dict[shop]['search_item_check_string'].strip() != '':
                search_item_check = True
                
            if shops_dict[shop]['info_on_item_page'] == 'true' and shops_dict[shop]['search_itempage_template'] != '':
                el_items = []
                el_items_process = soup.select(shops_dict[shop]['search_item_template'])
                max_items_to_process = 3
                items_processed = 0
                for el_item_it in el_items_process:
                    item_url = el_item_it.find_all('a')[0].get('href')
                    if not url_is_absolute(item_url):
                        item_url = shops_dict[shop]['url_template'] + el_item_it.find_all('a')[0].get('href')                    
                    item_result = urllib.request.urlopen(iriToUri(item_url), timeout=20).read().decode('utf-8')                                        
                    soup_tmp = BeautifulSoup(item_result, 'html.parser')
                    el_items.append(soup_tmp.select(shops_dict[shop]['search_itempage_template'])[0])
                    if not search_item_check:
                        break
                    items_processed = items_processed + 1
                    if items_processed == max_items_to_process:
                        break
            else:
                el_items = soup.select(shops_dict[shop]['search_item_template'])
                        
            el_item = el_items[0]
            el_items_filtered = []

            if shops_dict[shop]['add_search_check'] == 'true':
                
                for sel_item in el_items:
                    el_item_text = ''.join(sel_item.find_all(text=True, recursive=True)).strip().lower()
                    check_text = search_string
                    if shops_dict[shop]['add_search_check_template'].strip() != '':
                        check_text = getItemSearchString(shops_dict[shop], 'add_search_check_template', basket_item_line)
                    item_text_cheched = True
                
                    for check_basket_string in check_text.split(' '):
                        if el_item_text.find(check_basket_string.lower()) == -1:
                            item_text_cheched = False
                            break
                    if item_text_cheched == False:
                        continue            
                    else:
                        el_items_filtered.append(sel_item)

                el_item = el_items_filtered[0]

            else:
                el_items_filtered = el_items            

            if search_item_check:
                el_item = None
                check_phrase = TrimString(getItemSearchString(shops_dict[shop], 'search_item_check_string', basket_item_line))
                for sel_item in el_items_filtered:
                    check_item = sel_item.select(shops_dict[shop]['search_item_check_template'])[0]
                    check_item_text = TrimString(''.join(check_item.find_all(text=True, recursive=False)))                    
                    
                    if shops_dict[shop]['search_item_check_exact_match'] == 'true':
                        if check_phrase == check_item_text:
                            el_item = sel_item
                            break           
                    else:
                        if check_item_text.find(check_phrase) != -1:
                            el_item = sel_item
                            break                              
            if el_item == None:        
<<<<<<< HEAD
                continue

            #Check if we've found wrong item
            if shops_dict[shop]['add_search_check'] == 'true':
                el_item_text = ''.join(el_item.find_all(text=True, recursive=True)).strip().lower()
                check_text = search_string
                if shops_dict[shop]['add_search_check_template'].strip() != '':
                    check_text = getItemSearchString(shops_dict[shop], 'add_search_check_template', basket_item_line)
                item_text_cheched = True
                
                for check_basket_string in check_text.split(' '):
                    if el_item_text.find(check_basket_string.lower()) == -1:
                        item_text_cheched = False
>>>>>>> update
                        break
                    items_processed = items_processed + 1
                    if items_processed == max_items_to_process:
                        break
            else:
                el_items = soup.select(shops_dict[shop]['search_item_template'])
                        
            el_item = el_items[0]
            el_items_filtered = []

            if shops_dict[shop]['add_search_check'] == 'true':
                
                for sel_item in el_items:
                    el_item_text = ''.join(sel_item.find_all(text=True, recursive=True)).strip().lower()
                    check_text = search_string
                    if shops_dict[shop]['add_search_check_template'].strip() != '':
                        check_text = getItemSearchString(shops_dict[shop], 'add_search_check_template', basket_item_line)
                    item_text_cheched = True
                
                    for check_basket_string in check_text.split(' '):
                        if el_item_text.find(check_basket_string.lower()) == -1:
                            item_text_cheched = False
                            break
                    if item_text_cheched == False:
                        continue            
                    else:
                        el_items_filtered.append(sel_item)

                el_item = el_items_filtered[0]

            else:
                el_items_filtered = el_items            

            if search_item_check:
                el_item = None
                check_phrase = TrimString(getItemSearchString(shops_dict[shop], 'search_item_check_string', basket_item_line))
                for sel_item in el_items_filtered:
                    check_item = sel_item.select(shops_dict[shop]['search_item_check_template'])[0]
                    check_item_text = TrimString(''.join(check_item.find_all(text=True, recursive=False)))                    
                    
                    if shops_dict[shop]['search_item_check_exact_match'] == 'true':
                        if check_phrase == check_item_text:
                            el_item = sel_item
                            break           
                    else:
                        if check_item_text.find(check_phrase) != -1:
                            el_item = sel_item
                            break                              
            if el_item == None:        
=======
>>>>>>> update
                continue            

            if root_shop:                
                item_url = shops_dict[shop]['url_template'] + el_item.find_all('a')[0].get('href')
                item_result = urllib.request.urlopen(item_url,  timeout=20).read().decode('utf-8')
                soup = BeautifulSoup(item_result, 'html.parser')
                item_dict['ItemURL'] = item_url
                item_dict['Name'] = str(soup.find('title').string)
                continue
<<<<<<< HEAD
<<<<<<< HEAD
=======

            if shops_dict[shop]['info_on_item_page'] == 'true':
                item_url = shops_dict[shop]['url_template'] + el_item.find_all('a')[0].get('href')
                item_result = urllib.request.urlopen(item_url,  timeout=20).read().decode('utf-8')
                item_dict['URLs'][url_key] = item_url
                el_item = BeautifulSoup(item_result, 'html.parser')
>>>>>>> update
=======
>>>>>>> update
        
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
            printProgressBar(items_counter,len(basket_lines))
    else:    
        for basket_item_line in basket_lines:
            prices_async_dict['item' + str(items_counter)] = pool.apply_async(getItemDict, [basket_item_line, shops_dict])
            items_counter = items_counter + 1

        items_counter = 0

        for basket_item_line in basket_lines:
            printProgressBar(items_counter,len(basket_lines))
            try:
                prices_dict['item' + str(items_counter)] = prices_async_dict['item' + str(items_counter)].get(timeout=100)
            except:
                e = True
            items_counter = items_counter + 1
            printProgressBar(items_counter,len(basket_lines))
          
    
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
info_on_item_page = false
search_item_check_template = ""
search_item_check_string = ""
search_item_check_exact_match = ""
use_cookies = false
cookies_path = ""
root_entry = true
add_search_check = false
shop_active = true

[ali]
# URL of remote source
url_template = "https://aliexpress.ru"
# Template to form search string for each basket item. Special keywords %%VENDOR%%, %%NUM%%, %%NAME%% will be replaced
# with corresponding values from basket config file.
search_string_template = %%VENDOR%% %%NUM%%
# Template for remote web-source search URL, keyword %%%SEARCH_STRING%%% will be replaced with value formed from 'search_string_template'
search_url_template = "/wholesale?SearchText=%%%SEARCH_STRING%%%&SortType=total_tranpro_desc"
# Web-source specific search overrides for better search results. '.' separates groups: Vendor, Num, Name. ';' separates replacement pairs in each group.
# "|" separates value to replace and replacement value in each pair.
search_string_overrides = "Rye Field Model|RFM;Звезда|Zvezda.ss-014|ss014."
# (optional) Force to encode search string for search URL in specific codepage. Rarely needed
search_url_encode = ""
# Template to find code block of desired item/items in web-page
search_item_template = "div[class='product-snippet_ProductSnippet__content__1ettdy']"
# (optional) Template to find block to check if item is correct (not same string in name etc.) like unique item num, sku or so, for better search results, works only with 'search_item_check_template'
search_item_check_template = ""
# (optional) Search string template to check if item is correct, keywords processed same as for 'search_string_template', works only with 'search_item_check_template'
search_item_check_string = ""
# (optional) Search string must match found check string exactly (only symbols count, not spaces or non-printable)
search_item_check_exact_match = false
# Template to find price code block of desired item/items in web-page
search_price_template = "div[class='snow-price_SnowPrice__mainS__18x8np']" 
# (optional) Template to find price code block for determining item availability
search_instock_template = ""
# Use site cookies
use_cookies = false
# Path to load site cookies from, must be in netscape format (for example may be generated manually with 'get cookies.txt' extension for chrome-based browsers)
cookies_path = "ali_cookies.txt"
# Needed for some shops if full desired info only situated on item page
info_on_item_page = true
# Template to find block to extract data on item page, works only with 'info_on_item_page = true'
search_itempage_template = "body"
# Needed for some shops to check if search result corresponds to search string
add_search_check = false
# (optional) Check string template similar as for 'search_string_template' if needed, if not filled - equals to 'search_string_template'
add_search_check_template = ""
# (optional) Needed for some shops (ali for example) to find block with delivery price on item page
delivery_template_on_item_page = "span[class='snow-ali-kit_Typography__base__1shggo snow-ali-kit_Typography__base__1shggo snow-ali-kit_Typography__sizeTextM__1shggo']"
# Needed for some shops (ali for example) to find block with delivery price on item page
delivery_template_on_item_page_elnum = 1
# If shop has delivery price and certain amount of your order (basket) to make delivery free of charge - this threshold can be entered here.
free_delivery_threshold = 0
# If shop has delivery price - amount can be entered here. During calculation deliver cost splits equally between item prices of certain shop.
delivery_cost = 0
# Discount in percent from 100 applied to all items from shop before delivery cost.
discount_percent = 0
# Marks root web-source (scalemates for exmpl.) to download item full naming, root entry not used to search price data
root_entry = false
# Shop-entries with 'false' in this line will be skipped during data-fetching
shop_active = true

[yandex_market]
url_template = "https://market.yandex.ru"
search_string_template = %%VENDOR%% %%NUM%%
search_url_template = "/search?text=%%%SEARCH_STRING%%%"
search_string_overrides = ""
search_url_encode = ""
search_item_template = "div[class='_2im8- _2S9MU _2jRxX']"
search_item_check_template = ""
search_item_check_string = ""
search_item_check_exact_match = false
search_price_template = "span[data-auto='mainPrice'] span"
search_instock_template = "span[class='_1CSaT _2mcnk']"
use_cookies = false
cookies_path = "yandex_cookies.txt"
info_on_item_page = false
search_itempage_template = ""
add_search_check = true
add_search_check_template = "%%NUM%%"
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 0
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = true

[leonardo]
url_template = "https://leonardo.ru"
search_string_template = %%VENDOR%% %%NUM%%
search_url_template = "/ishop/?search=%%%SEARCH_STRING%%%"
search_string_overrides = "Звезда|Zvezda.."
search_url_encode = ""
search_item_template = "div[class='goods catalog-goods']"
search_item_check_template = ""
search_item_check_string = ""
search_item_check_exact_match = false
search_price_template = "p[class='price-new']"
search_instock_template = ""
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = true
add_search_check_template = "%%VENDOR%% %%NUM%%"
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 0
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = true

[det_mir]
url_template = "https://www.detmir.ru"
search_string_template = %%VENDOR%% %%NUM%%
search_url_template = "/search/results/?qt=%%%SEARCH_STRING%%%"
search_string_overrides = ""
search_url_encode = ""
search_item_template = "div[class='xH xL xK']"
search_item_check_template = "td[class='r_7']"
search_item_check_string = "%%NUM%%"
search_item_check_exact_match = true
search_price_template = ".RE"
search_instock_template = ""
use_cookies = false
cookies_path = "detmir_cookies.txt"
info_on_item_page = true
search_itempage_template = "div[class='a']"
add_search_check = false
add_search_check_template = %%VENDOR%%
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 0
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = true

[Model-lavka]
url_template = "https://model-lavka.ru"
search_string_template = %%VENDOR%% %%NUM%%
search_url_template = "/catalog?query=%%%SEARCH_STRING%%%&_csrf=&name=&priceFrom=&priceTo=&availability=&availability=all&scale="
search_string_overrides = "USTAR|Takom;HobbyBoss|Hobby Boss.."
search_url_encode = ""
search_item_template = ".item__wrap div[class='item__bottom']"
search_item_check_template = "div[class='article__wrap']"
search_item_check_string = " Артикул: %%NUM%% "
search_item_check_exact_match = true
search_price_template = "div[class='price']"
search_instock_template = "div[class='shiping__wrap']"
use_cookies = false
cookies_path = "model-lavka_cookies.txt"
info_on_item_page = false
search_itempage_template = ""
add_search_check = false
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 200
free_delivery_threshold = 2000
discount_percent = 0
root_entry = false
shop_active = true

[Modelist_lad]
url_template = "https://spb.modelist.spb.ru"
search_string_template = %%NUM%% %%VENDOR%%
search_string_overrides = "Freedom Model Kits|Hero;HobbyBoss|Hobby Boss.."
search_url_encode = ""
search_url_template = "/search/index.php?q=%%%SEARCH_STRING%%%&s="
search_item_template = ".container div[class='catalog_item']"
search_item_check_template = "span[class='hidden-xs']"
search_item_check_string = " Производитель: %%VENDOR%% "
search_item_check_exact_match = true
search_price_template = "span[class='main_price']"
search_instock_template = "span[class='main_price']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = false
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 200
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = true

[Modelist_sen]
url_template = "https://sennaya.modelist.spb.ru"
search_string_template = %%NUM%% %%VENDOR%%
search_string_overrides = "Freedom Model Kits|Hero;HobbyBoss|Hobby Boss.."
search_url_encode = ""
search_url_template = "/search/index.php?q=%%%SEARCH_STRING%%%&s="
search_item_template = ".container div[class='catalog_item']"
search_item_check_template = "span[class='hidden-xs']"
search_item_check_string = " Производитель: %%VENDOR%% "
search_item_check_exact_match = true
search_price_template = "span[class='main_price']"
search_instock_template = "span[class='main_price']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = false
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 200
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = false

[Modelist_koms]
url_template = "https://lavka.modelist.spb.ru"
search_string_template = %%NUM%% %%VENDOR%%
search_string_overrides = "Freedom Model Kits|Hero;HobbyBoss|Hobby Boss.."
search_url_encode = ""
search_url_template = "/search/index.php?q=%%%SEARCH_STRING%%%&s="
search_item_template = ".container div[class='catalog_item']"
search_item_check_template = "span[class='hidden-xs']"
search_item_check_string = " Производитель: %%VENDOR%% "
search_item_check_exact_match = true
search_price_template = "span[class='main_price']"
search_instock_template = "span[class='main_price']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = false
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 200
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = false

[Modelist_len]
url_template = "https://msk.modelist.spb.ru"
search_string_template = %%NUM%% %%VENDOR%%
search_string_overrides = "Freedom Model Kits|Hero;HobbyBoss|Hobby Boss.."
search_url_encode = ""
search_url_template = "/search/index.php?q=%%%SEARCH_STRING%%%&s="
search_item_template = ".container div[class='catalog_item']"
search_item_check_template = "span[class='hidden-xs']"
search_item_check_string = " Производитель: %%VENDOR%% "
search_item_check_exact_match = true
search_price_template = "span[class='main_price']"
search_instock_template = "span[class='main_price']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = false
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 200
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = false

[i-modelist]
url_template = "https://i-modelist.ru"
search_string_template = %%NUM%% %%VENDOR%%
search_url_template = "/search.html?all=1&q=%%%SEARCH_STRING%%%&x=0&y=0"
search_string_overrides = "Hobby Boss|HobbyBoss;Freedom Model Kits|Hero;Trumpeter|Трубач.."
search_url_encode = ""
search_item_template = ".container div[class='prod-item']"
search_item_check_template = "div[class='d-flex txt_14px align-items-center']"
search_item_check_string = " Артикул: %%NUM%% "
search_item_check_exact_match = true
search_price_template = ".prod-item__price span[data-thousand-separate='']"
search_instock_template = "i[class='icon icon_cart text-white txt_12px mr-2']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = false
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 200
free_delivery_threshold = 3000
discount_percent = 0
root_entry = false
shop_active = true

[platcdarm]
url_template = "https://www.platcdarm.ru"
search_string_template = %%NUM%% %%VENDOR%%
search_string_overrides = "Rye Field Model|RFM;HobbyBoss|Hobby Boss.RM-|."
search_url_encode = ""
search_url_template = "/tovar/?q=%%%SEARCH_STRING%%%"
search_item_template = ".catalog div[class='product']"
search_item_check_template = ""
search_item_check_string = ""
search_item_check_exact_match = true
search_price_template = "div .price"
search_instock_template = "div[class='product_submit']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = false
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 200
free_delivery_threshold = 3000
discount_percent = 0
root_entry = false
shop_active = true

[Arma-models]
url_template = "https://arma-models.ru"
search_string_template = %%VENDOR%% %%NUM%%
search_string_overrides = "HobbyBoss|Hobby Boss.."
search_url_encode = "cp1251"
search_url_template = "/catalog/?q=%%%SEARCH_STRING%%%&how=r"
search_item_template = ".container div[class='inner_wrap TYPE_1']"
search_item_check_template = "div[class='muted font_sxs']"
search_item_check_string = "Арт.: %%NUM%%"
search_item_check_exact_match = true
search_price_template = "span[class='price_value']"
search_instock_template = "span[class='icon stock']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = false
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 0
free_delivery_threshold = 0
discount_percent = 20
root_entry = false
shop_active = true

[mirmodelista]
url_template = "https://mirmodelista.ru"
search_string_template = %%NUM%%
search_string_overrides = ""
search_url_encode = ""
search_url_template = "/searchSmart/?query=%22%%%SEARCH_STRING%%%%22"
search_item_template = ".item_container_small div[class='item_one']"
search_item_check_template = ".item_one_title a"
search_item_check_string = "%%NUM%% %%VENDOR%%"
search_item_check_exact_match = false
search_price_template = "div[class='item_one_price']"
search_instock_template = "a[class='btn-ya-go item_one_to_cart btn-buy smallbut1']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = true
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 200
free_delivery_threshold = 7500
discount_percent = 0
root_entry = false
shop_active = true

[mirmodspb]
url_template = "https://mirmodspb.ru"
search_string_template = %%NUM%%
search_string_overrides = ""
search_url_encode = ""
search_url_template = "/search?search=%%%SEARCH_STRING%%%"
search_item_template = ".site-main__inner li"
search_item_check_template = "div[class='shop2-product-article']"
search_item_check_string = "%%NUM%%"
search_item_check_exact_match = true
search_price_template = ".price-current strong"
search_instock_template = "button[class='shop2-product-btn']"
use_cookies = false
cookies_path = ""
info_on_item_page = true
search_itempage_template = "div[class='site-main__inner page-shop page-product']"
add_search_check = true
add_search_check_template = "%%NUM%% %%VENDOR%%"
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 350
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = true

[modelismus]
url_template = "https://www.modelismus.com"
search_string_template = %%NUM%% %%VENDOR%%
search_url_template = "/search?q=%%%SEARCH_STRING%%%"
search_string_overrides = "Freedom Model Kits|Hero.."
search_url_encode = ""
search_item_template = ".sDS4bMt li[class='sERPSMg']"
search_item_check_template = "div[class='_1rwRc']"
search_item_check_string = "Артикул: %%NUM%%"
search_item_check_exact_match = false
search_price_template = "span[data-hook='formatted-primary-price']"
search_instock_template = "span[class='buttonnext1749291004__content']"
use_cookies = false
cookies_path = ""
info_on_item_page = true
search_itempage_template = "main"
add_search_check = true
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 310
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = true

[ruscale]
url_template = "https://ruscale.ru"
search_string_template = %%VENDOR%% %%NUM%%
search_url_template = "/search/?query=%%%SEARCH_STRING%%%"
search_string_overrides = "Rye Field Model|RFM Model.."
search_url_encode = ""
search_item_template = ".s-products-list div[class='s-product-block']"
search_item_check_template = ""
search_item_check_string = ""
search_item_check_exact_match = false
search_price_template = "span[class='s-price']"
search_instock_template = "input[class='s-button js-add-button']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = true
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 300
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = true

[worldofscale]
url_template = "https://worldofscale.ru"
search_string_template = %%VENDOR%% %%NUM%%
search_url_template = "/products?keyword=%%%SEARCH_STRING%%%"
search_string_overrides = ""
search_url_encode = ""
search_item_template = "div[class='row m-b-1 ProductView product']"
search_item_check_template = ""
search_item_check_string = ""
search_item_check_exact_match = false
search_price_template = ".price span[itemprop='price']"
search_instock_template = "button[class='btn btn-primary']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = false
add_search_check_template = ""
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 300
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = true

[warmodel]
url_template = "https://warmodel.ru"
search_string_template = %%NUM%%
search_url_template = "/search/?query=%%%SEARCH_STRING%%%"
search_string_overrides = ""
search_url_encode = ""
search_item_template = "li[itemtype='http://schema.org/Product']"
search_item_check_template = ""
search_item_check_string = ""
search_item_check_exact_match = false
search_price_template = "span[class='price nowrap']"
search_instock_template = "input[type='submit']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = true
add_search_check_template = "%%NUM%%"
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 500
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = true

[models-market]
url_template = "https://models-market.ru"
search_string_template = %%NUM%%
search_url_template = "/search?search=%%%SEARCH_STRING%%%&brand_search=&scale=&category="
search_string_overrides = "Rye Field Model|RFM.."
search_url_encode = ""
search_item_template = "div[class='product']"
search_item_check_template = "div[class='prodnumber']"
search_item_check_string = "%%VENDOR%% %%NUM%%"
search_item_check_exact_match = true
search_price_template = ".product_price b"
search_instock_template = "div[class='prod_avail']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = true
add_search_check_template = "%%NUM%%"
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 300
free_delivery_threshold = 0
discount_percent = 0
root_entry = false
shop_active = true

[imhobby]
url_template = "http://www.imhobby.ru"
search_string_template = %%NUM%%
search_url_template = "/?subcats=Y&pcode_from_q=Y&pshort=Y&pfull=Y&pname=Y&pkeywords=Y&search_performed=Y&q=%%%SEARCH_STRING%%%&dispatch=products.search"
search_string_overrides = ""
search_url_encode = ""
search_item_template = "div[class='ty-product-list clearfix']"
search_item_check_template = "span[class='ty-control-group__item']"
search_item_check_string = "%%NUM%%"
search_item_check_exact_match = false
search_price_template = "span[class='ty-price-num']"
search_instock_template = "i[class='ty-icon-ok']"
use_cookies = false
cookies_path = ""
info_on_item_page = false
search_itempage_template = ""
add_search_check = true
add_search_check_template = "%%VENDOR%% %%NUM%%"
delivery_template_on_item_page = ""
delivery_template_on_item_page_elnum = 
delivery_cost = 200
free_delivery_threshold = 5000
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
        print('\nResults exported to: ' + '"' + result_file.name + '"')
    print()

def appquit(message, dontpause = False):
    """
    Quiting app with specified message with waiting or not of user input
    @params:        
        message          - Required  : message displayed before exit (Str)                
        dontpause        - Optional  : pause and wait user input before exiting or not (bool)                                
    """ 
    if message.strip() != '':
        print(message)
    if not dontpause:
        os.system('pause')        
    else:
        sys.exit()

def app_version():
    return '1.0.0.1'

def main():
  """
   Gathers all data, generates displays and writes export html-file with table   
  """   
  print("""
        ___
     __(   )====::
    /~~~~~~~~~\\
    \O.O.O.O.O/
Model Price Comparison """ + app_version() + '\n'
  )

  parser = ArgumentParser(description='Fetches model kits price data from configured web-sources, displays and exports it.')
  parser.add_argument("-b", "--basket", dest="basket",
                    help="Path to basket file with products to fetch data about. If not specified or do not exists - will be created with default content.")
  parser.add_argument("-s", "--shops", dest="shops",
                    help="Path to shops config file to fetch data from. If not specified or do not exists - will be created with default content.")
  parser.add_argument("-e", "--export", dest="exportfile",
                    help="Path to html-file to export result data. If not specified or do not exists - will be created with name similar to basket config file name.")
  parser.add_argument("-st", "--singlethread", action="store_true",
                    help="Execute data-fetching in single-threaded mode instead of multi-threaded by default. Slow but less resource-hungry.")
  parser.add_argument("-dp", "--dontpause", action="store_true",
                    help="Don't pause and wait for input after execution.")

  args = parser.parse_args() 
  
  shops = 'default_shops.ini'
  basket = 'default_basket.ini'
  exportfilename = 'default_basket.htm'
    
  if args.shops != None:
    shops = args.shops  
  else:
    print('Shops config file not specified, using default destination: ' + '"' + shops + '"')  
  if args.basket != None:
    basket = args.basket    
  else:
    print('Basket config file not specified, using default destination: ' + '"' + basket + '"')  
  if args.exportfile != None:
    exportfilename = args.exportfile    
  
  singlethread = args.singlethread
  dontpause = args.dontpause

  if singlethread:
      print('Fetchinbg data in single-threaded mode, may be slow..')  
    
  try:
      if not os.path.exists(shops):
          print('Can\'t find shops config file, creating default one in: ' + '"' + shops + '"')      
          createShopsConfig(shops)
      else:
          print('Found shops config file in: ' + '"' + shops + '"')      
  except:
      appquit('Error while creating shop config file in:' + shops, dontpause)      

  try:
      config_shops = configparser.RawConfigParser()
      config_shops.read(shops, encoding='utf-8')
  except:
      appquit('Error reading shops congif file in:' + shops, dontpause)      

  try:
      if not os.path.exists(basket):
          print('Can\'t find basket config file, creating default one in: ' + '"' + basket + '"')      
          createBasketConfig(basket)
      else:
          print('Found basket config file in: ' + '"' + basket + '"')      
  except:
      appquit('Error while creating shop config file in:' + basket, dontpause)     
   
  try:
      basketfile = get_file(basket)
  except FileNotFoundError:
      appquit('Error accessing basket config file in:' + basket, dontpause)     
  
  with basketfile as file:
      basket_lines = [line.rstrip() for line in file if line.rstrip()[0] != ';']

  shops_dict = getShopsDict(config_shops)  
  prices_dict = getPricesDict(basket_lines, shops_dict, singlethread)

  del shops_dict['Root']

  sum_delivery(shops_dict, prices_dict)

  print('\n')
  print(' '*50 + '|'.join([f'{key:^13.13}' for key in shops_dict.keys() if shops_dict[key]['shop_active'] == 'true']))

  for item in prices_dict:      
      Name = prices_dict[item]['Name'] 
      if item == 'SUM':
          print('-'* (50 + 13 * len(prices_dict[item]['Prices'])))

      print(f'{str(Name):50.50}' + '|'.join([f'{str(value):^13.13}' for value in prices_dict[item]['Prices'].values()]))
        
  export_result_file(shops_dict, prices_dict, exportfilename)
  
  appquit('', dontpause)

if __name__ == '__main__':
  multiprocessing.freeze_support()
  main()