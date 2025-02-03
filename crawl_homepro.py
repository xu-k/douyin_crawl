import os
import execjs
import configparser
import re
from functools import lru_cache
import requests
from loguru import logger
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from datetime import datetime

from utils import XBogusUtil
from utils import my_util


def read_cookie_from_file():
    try:
        config = configparser.RawConfigParser()
        config.read('config.ini')
        con = dict(config.items('douyin'))
        if con == {}:
            raise Exception
        cookie = con.get('cookie')
        if cookie == '':
            logger.error('cookie值为空，请尝试手动填入cookie')
            raise Exception
    except Exception as e:
        logger.error(e)
        exit('请检查当前目录下的config.ini文件配置')
    return cookie


@lru_cache(maxsize=10)
def get_global_session():
    s = requests.Session()

    # 设置全局headers
    s.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
        'Referer': 'https://www.douyin.com/'
    })
    s.cookies.update({'Cookie': read_cookie_from_file()})
    s.mount('http://', HTTPAdapter(max_retries=3))
    s.mount('https://', HTTPAdapter(max_retries=3))
    return s


def analyze_user_input(user_in: str):
    try:
        u = re.search(r'user/([-\w]+)', user_in)
        if u:
            return u.group(1)
        u = re.search(r'https://v.douyin.com/(\w+)/', user_in)
        if u:
            url = u.group(0)
            res = get_global_session().get(url=url).url
            uid = re.search(r'user/([-\w]+)', res)
            if uid:
                return uid.group(1)

    except Exception as e:
        print(e)
        return


def filter_by_date(videos, start_date, end_date):
    # 转换日期为datetime格式
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    end_date = datetime.strptime(end_date, "%Y-%m-%d")

    filtered_videos = []
    for video in videos:
        create_time = datetime.fromtimestamp(video['create_time'])  # 抖音时间戳转为datetime
        if start_date <= create_time <= end_date:
            filtered_videos.append(video)

    return filtered_videos


def crawl_media(user_in: str, start_date: str, end_date: str):
    # douyin不使用代理
    os.environ['NO_PROXY'] = 'douyin.com'
    video_list = []
    picture_list = []
    session = get_global_session()
    # 抖音用户唯一标识 sec_uid
    sec_uid = analyze_user_input(user_in)
    if sec_uid is None:
        exit("粘贴的用户主页地址格式错误")

    cursor = 0
    while 1:
        home_url = f'https://www.douyin.com/aweme/v1/web/aweme/post/?aid=6383&sec_user_id={sec_uid}&count=18&max_cursor={cursor}&cookie_enabled=true&platform=PC&downlink=6.9'
        xbs = XBogusUtil.generate_url_with_xbs(home_url, get_global_session().headers.get('User-Agent'))
        # 计算出X-Bogus参数拼接到url
        url = home_url + '&X-Bogus=' + xbs
        json_str = session.get(url).json()

        cursor = json_str["max_cursor"]  # 当页页码
        for i in json_str["aweme_list"]:
            #  视频收集
            if i["images"] is None:
                # 过滤视频
                if 'create_time' in i and i["create_time"]:
                    video_list.append(i)
            #  图片收集
            else:
                picture_list += list(map(lambda x: x["url_list"][-1], i["images"]))

        # 如果has_more为0说明已经到了尾页，结束爬取
        if json_str["has_more"] == 0:
            break
        # 随机睡眠
        my_util.random_sleep()

    # 过滤指定日期范围内的视频
    video_list = filter_by_date(video_list, start_date, end_date)

    print(f'视频数量: {len(video_list)}')
    print(f'图片数量: {len(picture_list)}')
    print(f'开始下载到本地文件 {sec_uid}...')
    download_media(session, sec_uid, video_list, picture_list)


def download_media(session: requests.Session, sec_uid, video_list, picture_list):
    if not os.path.exists(sec_uid):
        os.mkdir(sec_uid)
    os.chdir(sec_uid)

    with tqdm(total=len(video_list) + len(picture_list), desc="下载进度", unit="文件") as pbar:

        for i in video_list:
            des = i["desc"]
            url = i["video"]["play_addr"]["url_list"][0]
            create_time = datetime.fromtimestamp(i['create_time']).strftime('%Y-%m-%d')
            with session.get(url, stream=True) as response:
                if response.status_code == 200:
                    file_name = my_util.sanitize_filename(f"{des}_{create_time}")
                    with open(f'{file_name}.mp4', "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                else:
                    print(f"网络异常 Status code: {response.status_code}")
            pbar.update(1)  # 完成当前文件的处理
        for i in picture_list:
            url = i
            with session.get(url, stream=True) as response:
                if response.status_code == 200:
                    file_name = my_util.IDGenerator.generate_unique_id()
                    with open(f'{file_name}.jpg', "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            if chunk:
                                f.write(chunk)
                else:
                    print(f"网络异常 Status code: {response.status_code}")
            pbar.update(1)  # 完成当前文件的处理

    print('用户视频图片已全部下载完成')
    os.chdir('..')


if __name__ == '__main__':

    while 1:
        user_input = input("请在此填入用户链接（输入exit退出）: \n")
        if user_input.lower() == "exit":
            break

        start_date = input("请输入开始日期（格式：YYYY-MM-DD）: \n")
        end_date = input("请输入结束日期（格式：YYYY-MM-DD）: \n")

        crawl_media(user_input, start_date, end_date)
