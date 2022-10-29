import json
import re
import sys
from collections import defaultdict
from json import JSONDecodeError

import requests
from bs4 import BeautifulSoup


class NaverScrapper:
    def __init__(self) -> None:
        self.content_word = "ROOT_QUERY"
        self.start_slice_word = "window.__APOLLO_STATE__"
        self.end_slice_word = "window.__PLACE_STATE__"
        self.store_url = "https://m.map.naver.com/search2/interestSpotMore.naver"
        self.menu_url = "https://m.place.naver.com/restaurant/{}/menu"
        self.cate_dict = {
            "카페": ["CAFE_COFFEE", 2500],
            "프랜차이즈": ["DINING_FASTFOOD", 6000],
            "분식": ["DINING_SNACK", 6000],
            "한식": ["DINING_KOREAN", 7000],
            "중식": ["DINING_CHINESE", 6000],
            "일식": ["DINING_JAPANESE", 10000],
            "양식": ["DINING_WESTERN", 10000],
            "음식점": ["DINING", 10000],
        }

    def _get_threshold(self, category):
        return self.cate_dict[category][1]

    def get_delivery_menu(self, content_dic, base_dic, menu_dic, id_, category):
        if base_dic["yogiyo"] is not None:
            deli = "yogiyo"
        elif base_dic["baemin"] is not None:
            deli = "baemin"
        else:
            return

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

    def get_menu(self, content_dic, base_dic, id_, menu_dic, category):
        def exist_number(price: str):
            return re.search(r"\D", price) is None and price != ""

        def not_above_threshold(price: str):
            return int(price) <= self._get_threshold(category)

        if base_dic["menus"] is None:
            return
        for idx in range(len(base_dic["menus"])):
            menu = content_dic[f"Menu:{id_}_{str(idx)}"]
            if exist_number(menu["price"]) and not_above_threshold(menu["price"]):
                menu_dic[menu["name"]] = menu["price"]

    def store_search(self, lat, lng, category):
        catego = self.cate_dict[category][0]
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

    def error_msg(self, e, msg):
        err_line = "Error on line {}".format(sys.exc_info()[-1].tb_lineno)
        fin_err_msg = msg + " " + err_line + " " + type(e).__name__ + " " + str(e)
        return print(fin_err_msg)

    # 메뉴 가져오기 return {menu_name : price}
    def collect_menu(self, content_dic, base_dic, id_, category):
        menu_dic = {}
        # 배달메뉴가 있는지 확인
        self.get_delivery_menu(content_dic, base_dic, menu_dic, id_, category)

        # 이외에 메뉴가 있는지 확인
        self.get_menu(content_dic, base_dic, menu_dic, id_, category)

        return menu_dic

    def get_soup(self, url: str) -> BeautifulSoup | None:
        response = requests.get(url)
        soup = BeautifulSoup(response.content.decode("utf-8", "replace"), "html.parser")
        return None if "20" not in str(response.status_code) else soup

    def extract_content(self, content: str) -> str | None:
        if not all((word in content for word in (self.start_slice_word, self.end_slice_word))):
            return
        # 내가 원하는 부분을 찾아서 슬라이싱 후 json.loads를 통해 dict를 얻을 수 있다.
        start_idx = re.search(self.start_slice_word, content).end()
        end_idx = re.search(self.end_slice_word, content).start()
        return content[start_idx + 2 : end_idx].strip()[:-1]  # 2까지 자르는 이유는 = 제거, -1까지 자르는 이유는 ';' 제거

    def find_content(self, soup: BeautifulSoup) -> str | None:
        for script in soup.find("body").find_all("script"):
            if "ROOT_QUERY" in str(script):
                return str(script)

    def get_content(self, soup: BeautifulSoup) -> dict | None:
        if not soup:
            return
        # html에서 바디 > 스크립트 태그 가져오기
        return json.loads(self.extract_content(self.find_content(soup)))

    def _get_store_info(self, content_dic, base_url, id_, cate) -> dict | None:
        base_info: dict = content_dic[f"RestaurantBase:{id_}"]  # base 정보가 담긴 dict / 이름, 리뷰수, 별점 찾기위함
        # 시간 정보가 담긴 dict / 운영시간 찾기 위함
        time_info: dict = (
            content_dic[f"RestaurantBase:{id_}.businessHours.0"] if base_info["businessHours"] is not None else ""
        )

        # 마켓이 안열었으면 pass
        if time_info != "" and time_info["isDayOff"]:
            return

        # 메뉴 가져오기
        store_info = {}
        if menu_dic := self.collect_menu(content_dic, base_info, id_, cate):
            # 운영시간 / 리뷰수 / 별점 / 메뉴 / id를 market_dic에 담음
            # {메뉴:{} , 별점:int ..} 하나의 가게에 정보 담음
            store_info["time"] = time_info["hourString"] if time_info != "" else "알 수 없음"
            store_info["review"] = base_info["visitorReviewsTotal"]
            store_info["star"] = base_info["visitorReviewsScore"]
            store_info["menu"] = menu_dic
            store_info["id"] = id_
            store_info["url"] = base_url
        return store_info

    # 가게이름 : {{운영시간}, {리뷰수}, {별점}, {메뉴}, {id}} 반환
    def get_store_info(self, site_dic: dict, cate: str) -> dict:
        """
        return: {가게이름 : 운영시간, 리뷰수, 별점, {메뉴}, id} 반환
        """
        store_info = {}
        for id_, name in zip(site_dic["id"], site_dic["name"]):
            base_url = self.menu_url.format(id_)
            if store_info := self._get_store_info(self.get_content(self.get_soup(base_url)), base_url, id_, cate):
                store_info[name] = store_info
        return store_info

    def run(self, lat, lng, category=None):
        store_list = []
        category = category or "음식점"
        site_dic = self.store_search(lat, lng, category)
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
