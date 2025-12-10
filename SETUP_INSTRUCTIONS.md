# Setup Instructions for Yad2bot

## Required Python Packages

The bot requires the following Python packages to be installed:

```bash
sudo pip3 install pymysql
```

## Why pymysql is needed

The scraper uses `pymysql` to connect to the TiDB Cloud MySQL database for duplicate checking.
Without this package, `DB_CHECK_AVAILABLE` will be `False` and duplicate detection won't work.

## Verification

To verify the database connection works:

```bash
cd /root/yad2bot-service-scraper
python3.11 -c "
import sys
sys.path.insert(0, '/root/yad2bot-service-scraper')
from database import check_lead_exists_in_mysql
print('✅ Database import successful')
"
```

## Restart Bot Service

After installing dependencies:

```bash
sudo systemctl restart yad2bot.service
sudo systemctl status yad2bot.service
```

## Check Logs

To verify duplicate checking is working:

```bash
sudo journalctl -u yad2bot.service -f | grep "DUPLICATE CHECK"
```

You should see logs like:
```
[DUPLICATE CHECK] token=abc123, DB_CHECK_AVAILABLE=True
[DUPLICATE CHECK] Checking URL: https://www.yad2.co.il/item/abc123
[DUPLICATE CHECK] Result: True/False
```
