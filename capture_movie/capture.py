import os
import re
import random
import requests
from bs4 import BeautifulSoup
import time

# --- 请在此处粘贴你的 Cookie ---
USER_COOKIE = '''bid=V6jcC_ir2YM; ll="108296"; _vwo_uuid_v2=DD0DCD33F41D8A1D0049CC81BD9270489|0b161152834165d95bab3d8b23d3f6c1; _ga=GA1.1.452011444.1758722101; _ga_Y4GN1R87RG=GS2.1.s1758722100$o1$g1$t1758722112$j48$l0$h0; _pk_id.100001.8cb4=154127fb61a85081.1765894397.; _pk_ref.100001.8cb4=%5B%22%22%2C%22%22%2C1765975839%2C%22https%3A%2F%2Fsec.douban.com%2F%22%5D; dbsawcv1=MTc2NjIxMjE3M0AyMDBkY2I5NWQ3MjZhMWIwMmFiZDM3ZWIyNTVjMmM5MjRkZTA3YzZmN2QxNjI3NWY4Y2E3MmExODE4NDgwNzdmQDg3YTlkNDk5MGM5MTkxZmJAODM5NTFmZjc1MGMy; dbcl2="149438407:zrjEnXeyPyE"; ck=xdsG; frodotk_db="e8744c41fe5d028ab95ce4c5fb17079e"; push_noty_num=0; push_doumail_num=0'''

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Cookie': USER_COOKIE,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9',
    'Referer': 'https://www.douban.com/'
}

def get_douban_rating(movie_name):
    """搜索电影并获取评分"""
    # 增加 search_text 参数模拟真实搜索行为
    search_url = f"https://www.douban.com/search?cat=1002&q={movie_name}"
    
    try:
        response = requests.get(search_url, headers=HEADERS, timeout=15)
        
        if response.status_code == 403:
            return "403_ERR"
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 豆瓣搜索结果通常在 div.result 中
        result = soup.find('div', class_='result')
        if result:
            rating_nums = result.find('span', class_='rating_nums')
            if rating_nums:
                return float(rating_nums.text)
    except Exception as e:
        return None
    return None

def parse_folder_name(folder_name):
    # 提取格式：电影名.2023.xxx
    match = re.search(r'^(.+?)[. \s](\d{4})', folder_name)
    if match:
        return match.group(1).replace('.', ' ').strip()
    return folder_name

def main():
    if USER_COOKIE == "YOUR_COOKIE_HERE":
        print("错误：请先在脚本中填入你的豆瓣 Cookie！")
        return

    path = input("请输入文件夹的完整路径: ").strip()
    if not os.path.exists(path):
        print("路径不存在。")
        return

    # 获取文件夹列表
    folders = [f for f in os.listdir(path) if os.path.isdir(os.path.join(path, f)) and not f.startswith('.')]
    
    print(f"\n共找到 {len(folders)} 个目录，开始安全查询...\n")

    for folder in folders:
        movie_title = parse_folder_name(folder)
        rating = get_douban_rating(movie_title)
        
        if rating == "403_ERR":
            print("!!! 账号被限制访问 (403)，请更换 Cookie 或过段时间再试。")
            break
        
        if rating is not None and isinstance(rating, float):
            if rating < 6.0:
                print(f"【评分 {rating}】 {movie_title}")
        
        # 必须保持间隔，模拟人类行为
        time.sleep(random.uniform(3.0, 7.0))

    print("\n扫描结束。")

if __name__ == "__main__":
    main()