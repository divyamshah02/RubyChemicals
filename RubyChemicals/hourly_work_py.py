import requests


try:
    resp_petty = requests.get(url="https://portal.rubychemicals.co/operation-api/today-petty-cash-log-api/").json()
    print(resp_petty)
except:
    print("XXXXX error occured in petty cash")

try:
    resp_stock = requests.get(url="https://portal.rubychemicals.co/operation-api/today-stock-log-api/").json()
    print(resp_stock)
except:
    print("XXXXX error occured in stock item")