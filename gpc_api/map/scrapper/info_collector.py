import re

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


class InfoCollector:
    def _get_threshold(self, category):
        return THRESHOLD_TABLE[category]

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

    def get_today_busuness_hour_info(self, content_dic) -> dict:
        root_dic = content_dic["ROOT_QUERY"]
        for key in root_dic.keys():
            if key.startswith("restaurant") and (newBusinessHours := root_dic[key]["newBusinessHours"]):
                return newBusinessHours[0]["businessStatusDescription"]

    def collect(self, content_dic, base_url, id_, cate) -> dict | None:
        base_info: dict = content_dic[f"RestaurantBase:{id_}"]  # base 정보가 담긴 dict / 이름, 리뷰수, 별점 찾기위함
        # 시간 정보가 담긴 dict / 운영시간 찾기 위함
        if not (time_info := self.get_today_busuness_hour_info(content_dic)) or re.search("휴무|종료", time_info["status"]):
            return

        # 메뉴 가져오기
        store_info = {}
        if menu_dic := self.get_menu(content_dic, base_info, id_, cate):
            # 운영시간 / 리뷰수 / 별점 / 메뉴 / id를 market_dic에 담음
            # {메뉴:{} , 별점:int ..} 하나의 가게에 정보 담음
            store_info["time"] = time_info["description"]
            store_info["review"] = base_info["visitorReviewsTotal"]
            store_info["star"] = base_info["visitorReviewsScore"]
            store_info["menu"] = menu_dic
            store_info["id"] = id_
            store_info["url"] = base_url
        return store_info
