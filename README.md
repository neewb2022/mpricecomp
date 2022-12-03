# ModelPriceComparison
README 1.0.0.2
----------------------

CONTENTS OF THIS FILE
---------------------

 * Introduction
 * Installation
 * Starting App
 * Using App
 
INTRODUCTION
------------

Current Maintainer: neewb2022 <tmp_mail2023@proton.me>

Model Price Comparison is a console win32 app which gathers model kits price data from configured web-sources
(shops), displays and exports it to html-files.

INSTALLATION
------------

Simply unpack to desired folder. Archive contains:
- executable
- default basket config file - contains sample list of items to gather data for
- default shops config file - contains sample configuration for different shops to gather data from
- this file

STARTING APP
----------------

Simple launch .exe file.

App can be launched even without config-files and will create default ones if cant find configs in 
default or specified locations.

App can be launched without console parameters but if you need more specific settings - you can try "--help"

USING APP
-------------

App uses 2 config files listed above in Installation section. After launch app cycles through lines from
basket config file and starts fetching data through shop-entries from shops config file.

Data gathering goes in multithreaded (if not configured otherwise) mode and simultaneisly making requests to
configured web-sources. So be careful about activating anti-request spam protection which can be relevant for
some web-sites.

After gathering data app displays results in a form of a table and saves to .html file (preferred)

Additional usage tips:

usage: mpricecomp.exe [-h] [-b BASKET] [-s SHOPS] [-e EXPORTFILE] [-st] [-dp]

Fetches model kits price data from configured web-sources, displays and exports it.

optional arguments:
  -h, --help            show this help message and exit
  
  -b BASKET, --basket BASKET
                        Path to basket file with products to fetch data about. If not specified or do not exists -
                        will be created with default content.
                        
  -s SHOPS, --shops SHOPS
                        Path to shops config file to fetch data from. If not specified or do not exists - will be
                        created with default content.
                        
  -e EXPORTFILE, --export EXPORTFILE
                        Path to html-file to export result data. If not specified or do not exists - will be created
                        with name similar to basket config file name.
                        
  -st, --singlethread   Execute data-fetching in single-threaded mode instead of multi-threaded by default. Slow but
                        less resource-hungry.
                        
  -dp, --dontpause      Don't pause and wait for input after execution.
