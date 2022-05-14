import re
import requests
import json
import sys
from collections import defaultdict
from bs4 import BeautifulSoup


class NaverScrapper:
    start_re = re.compile("window.__APOLLO_STATE__")
    end_re = re.compile("window.__PLACE_STATE__")
    store_url = "https://m.map.naver.com/search2/interestSpotMore.naver"
    menu_url = "https://m.place.naver.com/restaurant/"
    cate_dic = {
        "카페": ["CAFE_COFFEE", 2500],
        "프랜차이즈": ["DINING_FASTFOOD", 6000],
        "분식": ["DINING_SNACK", 6000],
        "한식": ["DINING_KOREAN", 7000],
        "중식": ["DINING_CHINESE", 6000],
        "일식": ["DINING_JAPANESE", 10000],
        "양식": ["DINING_WESTERN", 10000],
        "음식점": ["DINING", 10000],
    }

    @classmethod
    def store_search(cls, lat, lng, category):
        catego = cls.cate_dic[category][0]
        params = (
            ("type", catego),
            ("searchCoord", f"{lng};{lat}"),
            ("siteSort", "1"),  # 0 관련도, 1 거리순
            ("page", "1"),
            ("displayCount", "60"),
        )
        response = requests.get(cls.store_url, params=params)
        try:
            site_list = json.loads(response.text)["result"]["site"]["list"]
        except:
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

    @classmethod
    def error_msg(cls, e, msg):
        err_line = "Error on line {}".format(sys.exc_info()[-1].tb_lineno)
        fin_err_msg = msg + " " + err_line + " " + type(e).__name__ + " " + str(e)
        return print(fin_err_msg)

    # 메뉴 가져오기 return {menu_name : price}
    @classmethod
    def collect_menu(cls, content_dic, base_dic, id_, cate):
        menu_dic = {}
        # 카테고리별 가격 임계치 설정.
        threshold = cls.cate_dic[cate][1]

        # 배달메뉴가 있는지 확인
        if base_dic["yogiyo"] is not None:
            deli = "yogiyo"
        elif base_dic["baemin"] is not None:
            deli = "baemin"

        # 배달 메뉴가 있다면 실행
        if "deli" in locals():
            brend = content_dic[f"$RestaurantBase:{id_}.{deli}"]
            # 있는 메뉴 그룹 아이디 값 담기. [menugroup_id1,menugroup_id2,menugroup_id3, ...]
            tmp_id_list = [dic["id"] for dic in brend["menuGroups"]]
            # 메뉴 그룹 이름 : 메뉴 리스트([{id},{id},{id}])
            tmp_menu_dic = {
                content_dic[id__]["name"]: content_dic[id__]["menus"]
                for id__ in tmp_id_list
            }
            for k, list_ in tmp_menu_dic.items():
                # 메뉴 그룹 안의 메뉴들 중 하나의 아이디를 이용해 하나의 메뉴에 접근
                for dic_ in list_:
                    menu = content_dic[dic_["id"]]
                    # 가격이 없거나 숫자가 아닌 것은 거르기
                    if re.search(r"\D", menu["price"]) is None and menu["price"] != "":
                        if int(menu["price"]) <= threshold:
                            menu_dic[menu["name"]] = menu["price"]

        # 이외에 메뉴가 있는지 확인
        elif base_dic["menus"] is not None:
            for i in range(len(base_dic["menus"])):
                menu = content_dic[f"Menu:{id_}_{str(i)}"]
                if re.search(r"\D", menu["price"]) is None and menu["price"] != "":
                    if int(menu["price"]) <= threshold:
                        menu_dic[menu["name"]] = menu["price"]

        return menu_dic

    # 가게이름 : {{운영시간}, {리뷰수}, {별점}, {메뉴}, {id}} 반환
    @classmethod
    def get_menu(cls, site_dic, cate):
        stores_dic = {}
        for id_, name in zip(site_dic["id"], site_dic["name"]):
            base_url = cls.menu_url + id_ + "/menu"
            response = requests.get(base_url)
            soup = BeautifulSoup(
                response.content.decode("utf-8", "replace"), "html.parser"
            )
            if "20" not in str(response.status_code):
                continue

            # 초기화
            market_dic = {}  # {메뉴:{} , 별점:int ..} 하나의 가게에 정보 담음

            # html에서 바디 > 스크립트 태그 가져오기
            body = soup.find("body")
            content = ""
            # 필요한 부분을 찾아서 str으로 만든다
            for i in body.find_all("script"):
                if "ROOT_QUERY" in str(i):
                    content = str(i)
                    break

            # 내가 원하는 부분을 찾아서 슬라이싱 후 json.loads를 통해 dict를 얻을 수 있다.
            start_idx = cls.start_re.search(content).end()
            end_idx = cls.end_re.search(content).start()
            str_dic = content[start_idx + 3 : end_idx - 12]

            # 가게에 대한 정보가 들어있는 dict 만들기
            content_dic = json.loads(str_dic)  # original dict

            # print(content_dic)
            base_dic = content_dic[
                f"RestaurantBase:{id_}"
            ]  # base 정보가 담긴 dict / 이름, 리뷰수, 별점 찾기위함
            # 시간 정보가 담긴 dict / 운영시간 찾기 위함
            time_dic = (
                content_dic[f"RestaurantBase:{id_}.businessHours.0"]
                if base_dic["businessHours"] is not None
                else ""
            )

            # 마켓이 안열었으면 pass
            if time_dic != "" and time_dic["isDayOff"]:
                continue

            # 메뉴 가져오기
            menu_dic = cls.collect_menu(content_dic, base_dic, id_, cate)

            if len(menu_dic) < 1:
                continue

            # 운영시간 / 리뷰수 / 별점 / 메뉴 / id를 market_dic에 담음
            market_dic["time"] = time_dic["hourString"] if time_dic != "" else "알 수 없음"
            market_dic["review"] = base_dic["visitorReviewsTotal"]
            market_dic["star"] = base_dic["visitorReviewsScore"]
            market_dic["menu"] = menu_dic
            market_dic["id"] = id_
            market_dic["url"] = base_url

            # 전체 가게 딕셔너리 각 {가게 이름 : 가게정보}
            stores_dic[name] = market_dic

        return stores_dic

    @classmethod
    def run(cls, lat, lng, category):
        store_list = []
        category = category or "음식점"
        site_dic = NaverScrapper.store_search(lat, lng, category)
        menu_dic = NaverScrapper.get_menu(site_dic, category)

        for store, store_info in menu_dic.items():
            idx = site_dic["id"].index(store_info["id"])
            store = {
                "lng": site_dic["lng"][idx],
                "lat": site_dic["lat"][idx],
                "store_name": store,
                "store_url": store_info["url"],
            }
            store_list.append(store)
        return store_list


if __name__ == "__main__":
    category = "카페"
    store_list = NaverScrapper.run(37.5142950, 127.0626243, category)

    for store in store_list:
        print(store)
