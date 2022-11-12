import json
import re
from collections import defaultdict
from json import JSONDecodeError

import requests
from bs4 import BeautifulSoup


class NaverScrapper:
    def __init__(self) -> None:
        self.parser = HtmlParser()
        self.collector = InfoCollector()
        self.store_url = "https://m.map.naver.com/search2/interestSpotMore.naver"
        self.menu_url = "https://m.place.naver.com/restaurant/{}/menu"
        self.CATEGORY_TABLE = {
            "카페": "CAFE_COFFEE",
            "프랜차이즈": "DINING_FASTFOOD",
            "분식": "DINING_SNACK",
            "한식": "DINING_KOREAN",
            "중식": "DINING_CHINESE",
            "일식": "DINING_JAPANESE",
            "양식": "DINING_WESTERN",
            "음식점": "DINING",
        }

    def search_store(self, lat, lng, category):
        catego = self.CATEGORY_TABLE[category]
        params = (
            ("type", catego),
            ("searchCoord", f"{lng};{lat}"),
            ("siteSort", "1"),  # 0 관련도, 1 거리순
            ("page", "1"),
            ("displayCount", "60"),
        )
        response = requests.get(self.store_url, params=params)
        try:
            site_list = json.loads(response.text)["result"]["site"]["list"]
        except (JSONDecodeError, KeyError):
            return "fail"
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


class NotFoundSliceWord(Exception):
    pass


class NotFoundContentWord(Exception):
    pass


class HtmlParser:
    CONTENT_WORD = "ROOT_QUERY"
    START_SLICE_WORD = "window.__APOLLO_STATE__"
    END_SLICE_WORD = "window.__PLACE_STATE__"

    def parse(self, content: str) -> BeautifulSoup | None:
        if not content:
            return None
        soup = BeautifulSoup(content, "html.parser")
        return json.loads(self.extract_content(self.find_content(soup)))

    def extract_content(self, content: str) -> str | None:
        if not all((word in content for word in (self.START_SLICE_WORD, self.END_SLICE_WORD))):
            raise NotFoundSliceWord
        # 내가 원하는 부분을 찾아서 슬라이싱 후 json.loads를 통해 dict를 얻을 수 있다.
        start_idx = re.search(self.START_SLICE_WORD, content).end()
        end_idx = re.search(self.END_SLICE_WORD, content).start()
        return content[start_idx + 2 : end_idx].strip()[:-1]  # 2까지 자르는 이유는 = 제거, -1까지 자르는 이유는 ';' 제거

    def find_content(self, soup: BeautifulSoup) -> str | None:
        for script in soup.find("body").find_all("script"):
            if self.CONTENT_WORD in str(script):
                return str(script)
        raise NotFoundContentWord


class InfoCollector:
    THRESHOLD_TABLE = {
        "카페": 2500,
        "프랜차이즈": 6000,
        "분식": 6000,
        "한식": 7000,
        "중식": 6000,
        "일식": 10000,
        "양식": 10000,
        "음식점": 10000,
    }

    def _get_threshold(self, category):
        return self.THRESHOLD_TABLE[category]

    def get_delivery_menu(self, content_dic, base_dic, id_, category):
        menu_dic = {}
        if base_dic["yogiyo"] is not None:
            deli = "yogiyo"
        elif base_dic["baemin"] is not None:
            deli = "baemin"
        else:
            return menu_dic

        # 배달 메뉴가 있다면 실행
        brend = content_dic[f"$RestaurantBase:{id_}.{deli}"]
        # 있는 메뉴 그룹 아이디 값 담기. [menugroup_id1,menugroup_id2,menugroup_id3, ...]
        tmp_id_list = [dic["id"] for dic in brend["menuGroups"]]
        # 메뉴 그룹 이름 : 메뉴 리스트([{id},{id},{id}])
        tmp_menu_dic = {content_dic[id__]["name"]: content_dic[id__]["menus"] for id__ in tmp_id_list}
        for k, list_ in tmp_menu_dic.items():
            # 메뉴 그룹 안의 메뉴들 중 하나의 아이디를 이용해 하나의 메뉴에 접근
            for dic_ in list_:
                menu = content_dic[dic_["id"]]
                # 가격이 없거나 숫자가 아닌 것은 거르기
                if re.search(r"\D", menu["price"]) is None and menu["price"] != "":
                    if int(menu["price"]) <= self._get_threshold(category):
                        menu_dic[menu["name"]] = menu["price"]

        return menu_dic

    def get_extra_menu(self, content_dic, base_dic, category):
        def _get_menu(menu_ref):
            return content_dic[menu_ref["__ref"]]

        def exist_number(price: str):
            return re.search(r"\D", price) is None and price != ""

        def not_above_threshold(price: str):
            return int(price) <= self._get_threshold(category)

        if base_dic["menus"] is None:
            # Todo. define exception
            return

        return {
            menu["name"]: menu["price"]
            for menu in map(_get_menu, base_dic["menus"])
            if exist_number(menu["price"]) and not_above_threshold(menu["price"])
        }

    # 메뉴 가져오기 return {menu_name : price}
    def get_menu(self, content_dic, base_dic, id_, category):
        # 배달메뉴가 있는지 확인
        menu_dic = self.get_delivery_menu(content_dic, base_dic, id_, category)

        # 이외에 메뉴가 있는지 확인
        menu_dic.update(self.get_extra_menu(content_dic, base_dic, category))
        return menu_dic

    def collect(self, content_dic, base_url, id_, cate) -> dict | None:
        base_info: dict = content_dic[f"RestaurantBase:{id_}"]  # base 정보가 담긴 dict / 이름, 리뷰수, 별점 찾기위함
        # 시간 정보가 담긴 dict / 운영시간 찾기 위함
        # Todo. 영업 확인 로직 수정 필요
        time_info: dict = (
            content_dic[f"RestaurantBase:{id_}.businessHours.0"] if base_info["businessHours"] is not None else ""
        )

        # 마켓이 안열었으면 pass
        if time_info != "" and time_info["isDayOff"]:
            # Todo. write fail log
            return

        # 메뉴 가져오기
        store_info = {}
        if menu_dic := self.get_menu(content_dic, base_info, id_, cate):
            # 운영시간 / 리뷰수 / 별점 / 메뉴 / id를 market_dic에 담음
            # {메뉴:{} , 별점:int ..} 하나의 가게에 정보 담음
            store_info["time"] = time_info["hourString"] if time_info != "" else "알 수 없음"
            store_info["review"] = base_info["visitorReviewsTotal"]
            store_info["star"] = base_info["visitorReviewsScore"]
            store_info["menu"] = menu_dic
            store_info["id"] = id_
            store_info["url"] = base_url
        return store_info


if __name__ == "__main__":
    category = "카페"
    lat, lng = 37.5142950, 127.0626243
    store_list = NaverScrapper().run(lat, lng, category)

    for store in store_list:
        print(store)
