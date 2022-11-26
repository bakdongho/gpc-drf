import json
from collections import defaultdict
from json import JSONDecodeError

import requests

from gpc_api.map.scrapper.html_parser import HtmlParser
from gpc_api.map.scrapper.info_collector import InfoCollector

CATEGORY_TABLE = {
    "카페": "CAFE_COFFEE",
    "프랜차이즈": "DINING_FASTFOOD",
    "분식": "DINING_SNACK",
    "한식": "DINING_KOREAN",
    "중식": "DINING_CHINESE",
    "일식": "DINING_JAPANESE",
    "양식": "DINING_WESTERN",
    "음식점": "DINING",
}


class FailRequests(Exception):
    pass


class NaverScrapper:
    def __init__(self) -> None:
        self.parser = HtmlParser()
        self.collector = InfoCollector()
        self.store_url = "https://m.map.naver.com/search2/interestSpotMore.naver"
        self.menu_url = "https://m.place.naver.com/restaurant/{}/menu"
        self.headers = {
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/107.0.5304.101 Mobile/15E148 Safari/604.1",
        }

    def search_store(self, lat, lng, category):
        catego = CATEGORY_TABLE[category]

        response = requests.get(
            self.store_url,
            headers=self.headers,
            params=(
                ("type", catego),
                ("searchCoord", f"{lng};{lat}"),
                ("siteSort", "1"),  # 0 관련도, 1 거리순
                ("page", "1"),
                ("displayCount", "60"),
            ),
        )
        try:
            site_list = json.loads(response.text)["result"]["site"]["list"]
        except (JSONDecodeError, KeyError):
            raise FailRequests
        site_dic = defaultdict(list)
        for site in site_list:
            if site["menuExist"] == "1":
                # print(site['name'])
                site_dic["name"].append(site["name"])
                site_dic["id"].append(site["id"][1:])
                site_dic["distance"].append(site["distance"])
                site_dic["lat"].append(site["y"])
                site_dic["lng"].append(site["x"])
                site_dic["NPay"].append(True if site["hasNPay"] else False)

        return site_dic

    def get_html(self, url: str) -> str | None:
        response = requests.get(url)
        return None if "20" not in str(response.status_code) else response.content.decode("utf-8", "replace")

    # 가게이름 : {{운영시간}, {리뷰수}, {별점}, {메뉴}, {id}} 반환
    def get_store_info(self, site_dic: dict, cate: str) -> dict:
        """
        return: {가게이름 : 운영시간, 리뷰수, 별점, {메뉴}, id} 반환
        """
        store_info = {}
        for id_, name in zip(site_dic["id"], site_dic["name"]):
            base_url = self.menu_url.format(id_)
            if html := self.get_html(base_url):
                if store_info := self.collector.collect(self.parser.parse(html), base_url, id_, cate):
                    store_info[name] = store_info
        return store_info

    def run(self, lat, lng, category=None):
        store_list = []
        category = category or "음식점"
        site_dic = self.search_store(lat, lng, category)
        store_info = self.get_store_info(site_dic, category)

        for store, info in store_info.items():
            idx = site_dic["id"].index(info["id"])
            store = {
                "lng": site_dic["lng"][idx],
                "lat": site_dic["lat"][idx],
                "store_name": store,
                "store_url": info["url"],
            }
            store_list.append(store)
        return store_list


if __name__ == "__main__":
    category = "카페"
    lat, lng = 37.5142950, 127.0626243
    store_list = NaverScrapper().run(lat, lng, category)

    for store in store_list:
        print(store)
