from dotenv import load_dotenv
load_dotenv()

import os
from utils.api_safety import check_api_permissions

api_key = os.getenv("BYBIT_API_KEY", "")
api_secret = os.getenv("BYBIT_API_SECRET", "")

if not api_key:
    print("BYBIT_API_KEY가 .env에 없습니다. 실제 키 없이는 테스트 불가.")
else:
    result = check_api_permissions(api_key, api_secret)
    print(f"유효: {result['valid']}")
    print(f"읽기전용: {result['read_only']}")
    if result['trade_permissions']:
        print(f"거래 권한: {result['trade_permissions']}")
    if result['warning']:
        print(f"경고: {result['warning']}")
    print(f"전체 권한: {result['permissions']}")
