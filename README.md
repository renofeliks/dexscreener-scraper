# DexScreener Token Holder Watcher

A python bot that monitors token holders [DexScreener](https://dexscreener.com) and sends updates to Telegram.
It tracks changes such as new holders, removed holders and balance updates in near real time.

## Features

+ Scrapes top holders of any Solana token page on DexScreener
+ Compares with previously saved holders
+ Sends updates via Telegram bot
+ Saves holders data to CSV
+ Runs in the background, with the option to stop program via keyboard

## Requirements
+ Python 3.8+
+ SeleniumBase
+ Pandas, Schedule, Requests
+ Chrome installed for Selenium

# Usage
+ Clone the repository
+ Make your Telegram bot
+ Get bot token and chat id
**In code**
+ Put bot token and chat id in required space
+ Put path for CSV file
+ Update url for DexScreener token based on your needs
+ Run the script: ```python final.py```
+ Stop the script with 'q'

# Author
Reno Feliks Lindvere

Email: renofeliks.lindvere@gmail.com
